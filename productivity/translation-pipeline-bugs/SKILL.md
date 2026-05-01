---
name: translation-pipeline-bugs
description: YouTube→Obsidian翻译流水线的已知bug和workaround
---
# Translation Pipeline Bug Notes

## Bug 1: Index Collision in Batch拼接
**问题**: 每个batch的JSON返回从`[1]`开始，拼接后后面的batch覆盖前面的翻译。
```python
# 错误写法
batches = [batch1, batch2, ...]  # 每个batch返回 [["1", zh], ["2", zh], ...]
zh_map = {int(k): v for k, v in batches[0] + batches[1] + ...}  # 后面的覆盖前面的！

# 正确写法：用 global_offset
offset = 0
for batch in batches:
    for item in batch:
        idx = int(item[0]) + offset
        zh_map[idx] = item[1]
    offset += len(batch)
```

## Bug 2: Minimax模型生成<think>消耗token
**问题**: `minimax/minimax-m2.7/b1d92` 模型现在先输出`<think>`思考文本，消耗大量token，导致：
- 翻译被截断（只剩2-3条）
- 直接返回思考过程而非JSON
- 21条空翻译

**影响范围**: 2026-04-22起，batch 40 (Cursor-2.0)、batch 8 (Codex-CLI最后8条)

**Workaround**:
1. 换用Claude模型处理剩余翻译
2. 或者找能禁用</think>的Minimax端点/模型

## 当前状态 (2026-04-22)
- Claude-Full: ✅ 221/221
- Cursor-Tutorial: ✅ 126/126
- Cursor-2.0: ⚠️ 63/84 (21条空)
- Kevin: ✅ 111/111
- Codex-CLI: ⚠️ 165/173 (最后8条0提取)

**已写入Obsidian**: 5个课程markdown + Index.md 均已保存

---

## Bug: LLM Thinking Block 干扰翻译提取 (2026-04-22 发现)

**问题**: `minimax/m2.7` 模型响应不稳定时，`<think>` 思考块内容混入翻译输出，导致 `extract_translations()` 提取失败（第一批 10 条返回 0 条）。

**根因**: 思考块第一行可能是类似 `[0] 思考内容...` 导致正则 `^\[(\d+)\]` 不匹配；但更危险的是思考块内容被当成翻译行。

**Fix** (已应用在 `translator.py`):
```python
def extract_translations(raw: str, expected: int) -> dict:
    translations = {}
    for line in raw.strip().split('\n'):
        line = line.strip()
        if not line.startswith('['):   # 跳过思考块等非翻译行
            continue
        m = re.match(r'\[(\d+)\]\s*(.+)', line)
        if m:
            idx, zh = int(m.group(1)), m.group(2).strip()
            if zh:
                translations[idx] = zh
    return translations
```

**关键**: `if not line.startswith('['): continue` — 必须跳过所有不以 `[` 开头的行，包括思考块内容。

---

## Bug: ASR 字幕时间窗口预合并导致文章被压缩成 4 段 (2026-04-22 发现)

**症状**: 35 分钟视频翻译后只有 4 段落（如 "4 paragraphs"），内容严重缺失。

**根因**: ASR 自动字幕（YouTube 自动生成）的时间戳是连续密集的（每 1-3 秒一条），没有自然停顿。所有碎片都在 15 秒时间窗口内 → `pre_merge_by_time(gap=3.0)` 把 2236 条合并成 ~1 条 → LLM 只能看到 ~1 条输入 → 输出 4 段概括而非逐段翻译。

**正确 Fix** (`paragraph_weaver.py`): 预合并只做去重，不做时间窗口合并：
```python
def pre_merge_by_time(entries: list[dict], dedup_window: float = 10.0) -> list[dict]:
    """只去重（同时间窗口内相同文本保留最新），不合并时间相近的碎片"""
    if not entries:
        return []
    # 按 start 排序
    sorted_entries = sorted(entries, key=lambda x: x['start'])
    seen: dict[str, float] = {}  # text → latest start
    result = []
    for e in sorted_entries:
        key = e['text']
        # 10 秒窗口内相同文本只保留最新的
        if key not in seen or e['start'] - seen[key] > dedup_window:
            result.append(e)
            seen[key] = e['start']
    return result
```

**验证结果** (batch_size=100, concurrent=3):
- Claude Code Full Tutorial: 2236 → 2235 条 → **192 段落**（原来 4 段）✅
- Cursor Tutorial: 905 → 904 条 → **73 段落** ✅

**为什么时间窗口合并错误**: 时间窗口合并假设"时间接近的碎片 = 语义相关"，但 ASR 字幕的时间戳是连续录制的，不反映语义边界。只有 LLM 能判断语义边界。

**batch_size 建议**: ASR 字幕 100 条/批，并发 3，预计 4-6 分钟（35 分钟视频，2235 条碎片）

**实测 timing**: 2235 条碎片，batch_size=100 → 23 批次，3 并发 → ~8 轮 × 31s/轮 ≈ 248s ≈ 4 分钟。单个 LLM 调用（100 条）：31.5s 返回 ~7 段落。

**最优 batch_size**: 100（batch_size=200 耗时 84s，只多 2 段落，不值得）

---

## Bug: as_completed 不保证顺序 (2026-04-22 发现)

**症状**: `as_completed()` 返回 future 的顺序是完成顺序，不是提交顺序。并发 3 个 worker 时，提交顺序 [A,B,C] 但完成顺序可能是 [B,A,C]，导致结果段落乱序。

**Fix** (`paragraph_weaver.py`):
```python
results: dict[int, list[dict]] = {}  # batch_idx → paragraphs
with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
    futures = {executor.submit(weave_batch, client, batch): i
               for i, batch in enumerate(batches)}
    for future in as_completed(futures):
        i = futures[future]
        results[i] = future.result()
# 按提交顺序输出（不是完成顺序）
for i in sorted(results.keys()):
    all_paragraphs.extend(results[i])
```

---

## Bug: translator.py -o 参数缺失导致不保存文件 (2026-04-22 发现)

**症状**: translator.py 运行完成（显示 "翻译完成 192/192 条"）但 translate.md 文件是旧的。

**根因**: argparse 的 `default=None`，但代码里 `if args.output:` 判断为 False，走不到保存分支。

**Fix**:
```python
# translator.py main() 里自动推断 output_path
if args.output is None:
    args.output = str(Path(args.paragraphs_json).with_suffix('')).replace('.paragraphs', '-translate').replace('.en', '') + '.md'
```

同时 argparse 里加 `default=None`:
```python
parser.add_argument('--output', '-o', default=None, help='...')
```

---

## Bug: "powerless" 等核心词漏翻 (2026-04-22 发现)

**问题**: LLM 把 `powerless`、`assertive`、`dominance`、`alpha` 等心理学核心术语当专有名词保留英文。

**Fix** (已应用在 `translator.py` system prompt):
```
2. ALWAYS translate these words (do NOT leave them in English):
   - powerful / powerless → 有权势的 / 没有权势的
   - power (as noun/adjective) → 权力/有权势的
   - assertive, dominance, dominant → 自信的、主导的、支配的
   - hormones (testosterone, cortisol) → 荷尔蒙（睾酮、皮质醇）
   - alpha (in "alpha male") → alpha（阿尔法）
3. Keep person names in English: Nalini Ambady, Dana Carney, Susan Fiske, Amy Cuddy
4. Keep institution names in English: Tufts University, Princeton, Berkeley
```

---

## 已知现象: VTT 时间戳跳跃 (非 bug)

**观察**: VTT 字幕常有 2-4 分钟的时间戳跳跃（如 00:10:51 → 00:14:57），这是视频编辑/幻灯片切换造成，非 pipeline 问题，不需要处理。

---

## Bug: MiniMax 把结构化内容写在 <think>...</think> 内 (2026-04-26 发现)

**问题**: `jira_summarize.py` 调用 MiniMax 时，LLM 把格式化的结构化内容写在 `<think>...</think>` 思考块内，块外只有引导语。导致 `strip_thinking_blocks()` 取不到内容，或取到了错误的文本。

**症状**: parsed 文件里是"让我分析这个JIRA Issue并按照要求的格式输出"，真正的摘要埋在思考块底部。

**根因**: MiniMax 对话模式倾向于把"正式输出"放在 thinking block 里，把"铺垫说明"放在外面。

**Fix** (`jira_summarize.py`):
```python
def strip_thinking_blocks(text: str) -> str:
    """剥掉 LLM 思考块，返回纯净的 structured 输出"""
    # 用 sub 删除所有思考块（标签+内容），用剩余内容
    clean = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    if len(clean) > 30:
        return clean
    # 否则 fallback 到最后一个思考块内容
    blocks = re.findall(r"<think>([\s\S]*?)</think>", text)
    if blocks:
        return blocks[-1].strip()
    return clean
```

**关键**: 先用 `re.sub` 删掉思考块，取块外内容（MiniMax 结构化内容有时在块外）。只有块外内容 < 30 字符时才 fallback 到思考块内容。

**另一个坑**: description 字段超长（含 base64 截图）导致 LLM 忽略格式指令。Fix：截断到前 300 字符。
```python
if len(description) > 300:
    description = description[:300] + "\n（...内容已截断）"
```
