---
name: subtitle-translate
description: VTT字幕翻译工具 — 使用Minimax API将英文字幕翻译成中文，支持tiktoken精确分批和术语一致性
triggers:
  - 翻译YouTube字幕
  - VTT字幕中译
  - 批量翻译字幕
---

# subtitle-translate

VTT字幕翻译工具，使用Minimax API将英文字幕翻译成中文。

## 核心功能

- 解析VTT格式字幕文件
- 调用Minimax API批量翻译（tiktoken精确分批，2k-6k tokens/批）
- 分批时带前批摘要，保证术语一致性
- 输出翻译后的VTT文件

## 环境依赖

- Python 3
- `openai` 包: `pip install openai`
- `tiktoken` 包: `pip install tiktoken`

## 环境变量

```bash
MINIMAX_API_KEY=ak-29c67e1cf9f3461190ce639ab469a0c1
MINIMAX_BASE_URL=https://zh.agione.co/hyperone/xapi/api
```

## 使用方法

```bash
# 翻译成中文（默认）
python3 ~/.hermes/skills/media/subtitle-translate/scripts/vtt_translator.py \
  -f /path/to/video.vtt

# 指定输出路径
python3 ~/.hermes/skills/media/subtitle-translate/scripts/vtt_translator.py \
  -f /path/to/video.vtt \
  -o /path/to/video.zh.vtt

# 指定模型
python3 ~/.hermes/skills/media/subtitle-translate/scripts/vtt_translator.py \
  -f /path/to/video.vtt \
  -m minimax/minimax-m2.7/b1d92

# 自定义每批token数（默认4000，建议2000-6000）
python3 ~/.hermes/skills/media/subtitle-translate/scripts/vtt_translator.py \
  -f /path/to/video.vtt \
  -b 5000
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-f` | 输入VTT文件路径 | 必填 |
| `-o` | 输出VTT文件路径 | `{原名}.{语言}.vtt` |
| `-t` | 目标语言 | zh |
| `-m` | 模型名称 | minimax/minimax-m2.7/b1d92 |
| `-b` | 每批最大token数 | 4000 |

## 技术细节

### 分批策略
- 使用 `tiktoken.get_encoding("cl100k_base")` 精确计算token数
- 每批 ~4000 tokens（可配置），而非固定条数
- cue < 50 且总token < 8k 时整文件一次性翻，减少API调用

### 术语一致性
- 每批翻译带前批最后5条的原文摘要
- system prompt 引导模型匹配前批术语

### 提取逻辑（重要）
- **Minimax M2.7 是思考模型**，输出结构: `<think>...</think>\n\n[N] 翻译1\n---\n[N] 翻译2\n...\n[英文原文]`（模型会echo英文原文）
- 提取三步走：去掉 `<think>...</think>` 块 → split on `[N]` 前缀 → 每N取最后一条
- `is_likely_english_prose()` 过滤英文摘要（如 "Concluding remarks express gratitude..."）
- 优先选：含中文、无英文引号、不像英文散文、长度合理（3-80字符）

### EN VTT 词级片段合并算法（Python 实现）

```python
import re

def parse_en_vtt_words(path):
    """解析 EN VTT，保留词级时间戳"""
    with open(path, encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'^WEBVTT.*?\n', '', content, flags=re.MULTILINE)
    blocks = re.split(r'\n\n+', content.strip())
    entries = []
    for block in blocks:
        lines = block.strip().split('\n')
        ts, texts = None, []
        for line in lines:
            m = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
            if m:
                ts = m.group(1)
            elif line.strip():
                clean = re.sub(r'<c[^>]*>(.*?)</c>', r'\1', line)
                clean = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', clean).strip()
                if clean:
                    texts.append(clean)
        if ts and texts:
            entries.append((ts, ' '.join(texts)))
    return entries

def to_sec(ts):
    h, m, s = ts[:8].split(':')
    return int(h)*3600 + int(m)*60 + float(s)

def merge_en_sentences(entries, gap=2.5):
    """按时间窗口合并 EN 词级片段为句子级"""
    merged = []
    for ts, text in entries:
        if not merged:
            merged.append((ts, text))
        else:
            last_ts, last_text = merged[-1]
            if abs(to_sec(ts) - to_sec(last_ts)) <= gap:
                # 选较长的（最完整），不去重避免误删
                merged[-1] = (last_ts, max([last_text, text], key=len))
            else:
                merged.append((ts, text))
    return merged
```

关键参数：`gap=2.5` 秒（**不要用 gap=3**，会跨句合并）。YouTube 自动字幕词级片段通常间隔 0.2-0.7s，句子间间隔 1.5s+。

验证：40句 EN 覆盖 2 分 26 秒视频（约 146s），粒度合理。检查合并结果中无句子跨度过大（>5s）的情况。

### ⚠️ YouTube 自动字幕的 EN/ZH 配对陷阱

YouTube 自动生成的字幕有**根本性的时间粒度差异**：
- **EN 自动字幕**：词级时间戳（同一秒多次 entry，如 "Building" @ 2.0s、"effective" @ 2.7s、"agentic" @ 3.0s — 全是单独行）
- **ZH 自动字幕**：句子级但切分异常细（一个英文句子的每个词被分散到 4-6 个 ZH entry）

这导致配对算法产生**一对多重复**（1句 EN 对 3-6 条 ZH），且ZH顺序与EN严重错位。**无法通过算法修复**，因为原始数据本身就不是一对一的。

**正确做法（已验证）**：跳过 ZH 字幕
1. 解析 EN VTT → 词级片段
2. 按 **2.5-3秒时间窗口** 合并相邻 EN 片段 → 句子级
3. 对合并后的 EN 句子**直接翻译**（调用 Minimax API）
4. 用 EN 时间戳 + 翻译后的 ZH → 生成双语笔记
5. 可选：如有高质量 ZH VTT（人工字幕），用配对逻辑；自动字幕一律不用

### 已知无效的方案（别再试）

❌ **要求模型输出 JSON 格式** — 思考模型生成 JSON 不稳定，会混入大量非JSON内容，解析失败率高。
❌ **直接用 `re.findall(r'\{.*?\}', raw, re.DOTALL)`** — 被思考块污染。
❌ **每N取第一个候选** — 模型往往在前面放英文原文或注释，应取每N的**最后一个**候选。

### 验证过的可靠方案

✅ System prompt 只要求 `[N] 中文翻译` 分行格式，不要求JSON
✅ `extract_translations_from_raw(raw, num_expected)` 提取：去掉 think 块 → split on `[N]` → 每N取最后一条含中文行
✅ `is_likely_english_prose()` 过滤英文摘要/解释性文字
✅ tiktoken 精确分批（2k-6k tokens/批），带前批摘要保证术语一致

## 完整Pipeline示例

```bash
# 1. 下载视频（含字幕）
bash ~/.hermes/skills/media/yt-download/scripts/download.sh "https://www.youtube.com/watch?v=VIDEO_ID"

# 2. 语音识别（如需）
bash ~/.hermes/skills/media/speech-to-text/scripts/speech-to-text.sh "~/youtube_videos/Video-Title"

# 3. 翻译字幕
python3 ~/.hermes/skills/media/subtitle-translate/scripts/vtt_translator.py \
  -f "~/youtube_videos/Video-Title/Video-Title.vtt"
```

## 注意事项

- VTT格式支持Whisper和YouTube自动字幕
- 翻译时会保留原始时间轴
- 专有名词（OpenAI、Harness等）保持英文
- 分批翻译，显示进度条
