#!/usr/bin/env python3
"""
vtt_translator.py - VTT字幕翻译器

设计思路（Ray 实战经验）：
- 使用 tiktoken 精确计算 token 数，每次请求 2k-6k tokens
- 模型输出 JSON 格式，避免解析歧义
- 分批时带前批摘要保证术语一致性
- JSON 结构: {"translations": [{"index": 0, "text": "中文翻译"}, ...]}

用法:
    python3 vtt_translator.py -f input.vtt -o output.vtt
"""

import argparse
import json
import os
import re
import sys
from typing import List, Optional

try:
    import tiktoken
except ImportError:
    print("错误: 请安装 tiktoken: pip install tiktoken", file=sys.stderr)
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("错误: 请安装 openai: pip install openai", file=sys.stderr)
    sys.exit(1)


# 编码器（cl100k_base 适用于 GPT-4/GPT-3.5-turbo 系列，也适用于 Minimax 兼容接口）
ENCODER = tiktoken.get_encoding("cl100k_base")

# 每批 token 上限（留余量给 prompt 和响应）
BATCH_TOKEN_LIMIT = 4000

SYSTEM_PROMPT = """You are a professional subtitle translator for English technical talks.
Translate each English subtitle to Simplified Chinese (简体中文).

Output format: Return one translation per line, in the same order.
Format: [N] Chinese translation
Example:
[0] 我们的下一位演讲者将为大家介绍线束工程
[1] 当人类掌舵、代理执行时，如何构建软件？

Critical rules:
1. Output exactly one line per subtitle, starting with [0], [1], [2]...
2. No explanation, no thinking, no analysis, no quotes - only the translation
3. Keep proper nouns in English: names (Ryan, London, OpenAI), product names, technical terms
4. Maintain consistent terminology with previous translations if provided
5. The first character of your output must be '[' (start of [0])
"""

SYSTEM_PROMPT_WITH_CONTEXT = """You are a professional subtitle translator for English technical talks.
Translate each English subtitle to Simplified Chinese (简体中文).

IMPORTANT: Follow the terminology from previous translations below:
{prev_summary}

Output format: Return one translation per line, in the same order.
Format: [N] Chinese translation
Example:
[0] 我们的下一位演讲者将为大家介绍线束工程
[1] 当人类掌舵、代理执行时，如何构建软件？

Critical rules:
1. Output exactly one line per subtitle, starting with [0], [1], [2]...
2. No explanation, no thinking, no analysis, no quotes - only the translation
3. Match the terminology patterns from previous translations above
4. The first character of your output must be '[' (start of [0])
"""


def count_tokens(text: str) -> int:
    """精确计算 token 数（tiktoken）"""
    return len(ENCODER.encode(text))


def parse_vtt(content: str) -> List[dict]:
    """解析VTT内容，返回cue列表"""
    cues = []
    lines = content.strip().split('\n')
    i = 0
    while i < len(lines) and 'WEBVTT' not in lines[i]:
        i += 1
    i += 1

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('NOTE') or line.startswith('Kind:') or line.startswith('Language:'):
            i += 1
            continue
        if not line:
            i += 1
            continue

        timecode_match = re.match(r'([\d:\.]+)\s*-->\s*([\d:\.]+)', line)
        if timecode_match:
            start = timecode_match.group(1)
            end = timecode_match.group(2)
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            text = ' '.join(text_lines)
            if text:
                cues.append({'start': start, 'end': end, 'text': text})
            continue
        i += 1

    return cues


def format_vtt(cues: List[dict]) -> str:
    """将cue列表格式化为VTT"""
    lines = ['WEBVTT', '']
    for cue in cues:
        lines.append(f"{cue['start']} --> {cue['end']}")
        lines.append(cue['text'])
        lines.append('')
    return '\n'.join(lines)


def is_likely_english_prose(text: str) -> bool:
    """
    判断文本是否像英文摘要/解释性文字（非字幕翻译）。
    典型特征：首字母大写、含 the/and/are/is 等常见词、长句子。
    """
    if not text:
        return False
    # 纯中文 → 不是英文
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        return False
    # 含中文标点混入 → 不是纯英文
    if any(c in text for c in '，。？！：；""''（）'):
        return False
    # 首字母大写 + 含有常见英文虚词
    if text[0].isupper() and len(text.split()) >= 3:
        english_markers = [' the ', ' and ', ' are ', ' is ', ' that ', ' this ',
                          ' with ', ' for ', ' you ', ' your ', ' our ', ' their ',
                          ' remarks ', ' gratitude ', ' audience ', ' engagement ',
                          ' everyone ', ' folks ', ' conclusion ']
        if any(m in ' ' + text.lower() + ' ' for m in english_markers):
            return True
    return False


def extract_translations_from_raw(raw: str, num_expected: int) -> List[str]:
    """
    从模型原始输出中提取翻译结果。
    思考模型输出混合了：think内容、英文原文、中文翻译。
    提取策略：
    1. 去掉 <think>...</think> 思考块
    2. 按 [N] 前缀分行
    3. 每 N 取最后一条，且优先选含中文的行（无引号的纯翻译）
    """
    # 去掉 think 块
    think_start = raw.rfind('\n\n\n')
    if think_start >= 0:
        clean = raw[think_start:].strip()
    else:
        clean = raw.strip()

    lines = clean.split('\n')
    translations = {}  # index -> list of candidate texts

    for line in lines:
        line = line.strip()
        m = re.match(r'^\[(\d+)\]\s*(.+)$', line)
        if not m:
            continue
        idx = int(m.group(1))
        text = m.group(2).strip()
        if idx not in translations:
            translations[idx] = []
        translations[idx].append(text)

    result = []
    for idx in range(num_expected):
        candidates = translations.get(idx, [])
        # 优先选：含中文、不像英文摘要、不含引号、长度合理
        chinese_candidates = [
            c for c in candidates
            if any('\u4e00' <= c <= '\u9fff' for c in c)
            and not is_likely_english_prose(c)
            and not c.startswith('"')
            and 3 < len(c) < 80
        ]
        if chinese_candidates:
            result.append(chinese_candidates[-1])  # 取最后一个（含中文的）
        elif candidates:
            # 过滤掉英文摘要/解释性文字
            non_english = [c for c in candidates if not is_likely_english_prose(c)]
            if non_english:
                result.append(non_english[-1])
            else:
                result.append("")  # 全是英文 → 缺失，保留空
        else:
            result.append("")  # 完全缺失

    return result


def build_prev_summary(cues: List[dict], max_items: int = 5) -> str:
    """生成前批摘要，用于下一批的术语一致性"""
    items = cues[-max_items:]
    return '\n'.join([f"- {c['text']}" for c in items])


def make_batches(cues: List[dict], token_limit: int) -> List[List[dict]]:
    """
    按 token 数分批，每批含前批摘要用于一致性。
    """
    batches = []
    batch = []
    batch_tokens = 0
    system_tokens = count_tokens(SYSTEM_PROMPT) + 100

    for cue in cues:
        cue_text = cue['text']
        cue_tokens = count_tokens(cue_text)

        # 单条字幕超长处理（截断到限制的一半）
        if cue_tokens > token_limit - system_tokens - 200:
            cue_tokens = min(cue_tokens, token_limit // 3)

        # 超过限制则开启新批
        if batch and batch_tokens + cue_tokens > token_limit - system_tokens:
            batches.append(batch)
            batch = []
            batch_tokens = 0

        batch.append(cue)
        batch_tokens += cue_tokens

    if batch:
        batches.append(batch)

    return batches


def translate_batch(client: OpenAI, batch: List[dict], model: str,
                   prev_summary: str, batch_idx: int, total_batches: int) -> List[dict]:
    """翻译单个批次"""
    batch_text = '\n'.join([f"[{i}] {c['text']}" for i, c in enumerate(batch)])

    if prev_summary:
        system = SYSTEM_PROMPT_WITH_CONTEXT.format(prev_summary=prev_summary)
    else:
        system = SYSTEM_PROMPT

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": batch_text}
            ],
            temperature=0.3,
            max_tokens=min(count_tokens(batch_text) * 2 + 300, 8000)
        )
        raw = response.choices[0].message.content.strip()
        translations = extract_translations_from_raw(raw, len(batch))

        for i, cue in enumerate(batch):
            if i < len(translations) and translations[i]:
                cue['text'] = translations[i]
            # 缺失的保持原文

        return batch

    except Exception as e:
        print(f"  [WARN] 批次 {batch_idx + 1} 请求失败: {e}", file=sys.stderr)
        return batch


def translate_full(client: OpenAI, cues: List[dict], model: str) -> List[dict]:
    """一次性翻译所有cue（cue较少时）"""
    all_text = '\n'.join([f"[{i}] {c['text']}" for i, c in enumerate(cues)])

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": all_text}
        ],
        temperature=0.3,
        max_tokens=min(count_tokens(all_text) * 2 + 300, 32000)
    )

    raw = response.choices[0].message.content.strip()
    translations = extract_translations_from_raw(raw, len(cues))

    for i, cue in enumerate(cues):
        if i < len(translations) and translations[i]:
            cue['text'] = translations[i]

    return cues


def translate_batched(client: OpenAI, cues: List[dict], model: str,
                     token_limit: int, show_progress: bool) -> List[dict]:
    """分批翻译，每批带前批摘要"""
    batches = make_batches(cues, token_limit)
    print(f"  分 {len(batches)} 批翻译，每批 ~{token_limit} tokens")

    prev_summary = ""
    result_cues = []

    for batch_idx, batch in enumerate(batches):
        translated_batch = translate_batch(client, batch, model, prev_summary, batch_idx, len(batches))
        result_cues.extend(translated_batch)

        # 生成前批摘要
        prev_summary = build_prev_summary(result_cues)

        if show_progress:
            done = sum(len(b) for b in batches[:batch_idx + 1])
            print(f"  批次 {batch_idx + 1}/{len(batches)} 完成 ({done}/{len(cues)} 条)")

    return result_cues


def translate_cues(cues: List[dict], client: OpenAI, model: str, target_lang: str,
                   token_limit: int, show_progress: bool) -> List[dict]:
    """
    主入口：
    - cue < 50 且总 token < 8k：整文件一次性翻
    - 否则：按 token_limit 分批，每批带前批摘要
    """
    total_tokens = count_tokens('\n'.join([c['text'] for c in cues]))

    if len(cues) < 50 and total_tokens < 8000:
        print(f"  [模式] 整文件翻译（{len(cues)} 条，~{total_tokens} tokens）")
        return translate_full(client, cues, model)
    else:
        print(f"  [模式] 分批翻译（{len(cues)} 条，~{total_tokens} tokens，每批 ~{token_limit} tokens）")
        return translate_batched(client, cues, model, token_limit, show_progress)


def main():
    parser = argparse.ArgumentParser(description="VTT字幕翻译器（tiktoken精确分批 + JSON输出）")
    parser.add_argument("-f", "--file", required=True, help="输入VTT文件路径")
    parser.add_argument("-o", "--output", help="输出VTT文件路径")
    parser.add_argument("-t", "--to", dest="to_lang", default="zh", help="目标语言 (默认: zh)")
    parser.add_argument("-m", "--model", default="minimax/minimax-m2.7/b1d92", help="模型名称")
    parser.add_argument("--api-key", help="API密钥 (也可使用 MINIMAX_API_KEY)")
    parser.add_argument("--base-url", help="API基础URL")
    parser.add_argument("-b", "--batch-tokens", type=int, default=4000,
                        dest="batch_tokens",
                        help="每批最大token数 (默认: 4000，建议 2000-6000)")

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        print("错误: 未设置 MINIMAX_API_KEY", file=sys.stderr)
        sys.exit(1)

    base_url = args.base_url or os.environ.get("MINIMAX_BASE_URL", "https://zh.agione.co/hyperone/xapi/api")

    if not os.path.exists(args.file):
        print(f"错误: 文件不存在: {args.file}", file=sys.stderr)
        sys.exit(1)

    with open(args.file, 'r', encoding='utf-8') as f:
        content = f.read()

    output_file = args.output
    if not output_file:
        basename = os.path.splitext(os.path.basename(args.file))[0]
        output_file = f"{basename}.{args.to_lang}.vtt"

    print(f"[INFO] 输入: {args.file}")
    print(f"[INFO] 输出: {output_file}")
    print(f"[INFO] 模型: {args.model}")
    print(f"[INFO] API: {base_url}")
    print(f"[INFO] 每批: ~{args.batch_tokens} tokens")
    print()

    cues = parse_vtt(content)
    total_tokens = count_tokens('\n'.join([c['text'] for c in cues]))
    print(f"[INFO] 共 {len(cues)} 条字幕，~{total_tokens} tokens")

    client = OpenAI(api_key=api_key, base_url=base_url)

    print("[INFO] 开始翻译...")
    translated_cues = translate_cues(
        cues, client, args.model, args.to_lang,
        token_limit=args.batch_tokens, show_progress=True
    )

    output_vtt = format_vtt(translated_cues)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_vtt)

    print(f"\n[DONE] 翻译完成: {output_file}")


if __name__ == "__main__":
    main()
