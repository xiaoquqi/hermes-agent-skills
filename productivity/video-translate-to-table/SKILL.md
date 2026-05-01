---
name: video-translate-to-table
description: YouTube 视频 EN VTT 字幕 → 段落级整理 + LLM 上下文翻译 → translate.md 表格文件
triggers:
  - 翻译 YouTube 视频字幕为表格
  - 生成 Obsidian 可用的双语笔记
  - 整理视频字幕为段落
---

# Video Translate to Table

YouTube 视频的 EN 字幕（VTT）→ 段落级整理 → 带上下文 LLM 翻译 → translate.md 表格文件。

## 流程概述

```
EN VTT (.en.vtt)
    ↓ vtt_parser.py（解析为时间戳+碎片列表）
时间戳碎片列表 [(ts, text), ...]
    ↓ paragraph_weaver.py（LLM 合并为段落，保留时间戳）
段落列表 [(ts_start, duration, en_text), ...]
    ↓ translator.py（带上下文分批翻译）
translate.md 表格文件
```

## 输出格式

`{视频标题}-translate.md`：

```markdown
# {视频标题}

> Source: {YouTube URL}

| 开始时间 | English | 中文 |
| -------- | ------- | ---- |
| 00:00:15 | Hello and welcome to this tutorial... | 你好，欢迎来到本教程... |
| 00:00:25 | Today we're going to talk about agents... | 今天我们来聊一聊 Agent... |
```

格式规范：
- 时间戳格式：`HH:MM:SS`（24小时制）
- 中文保持简体中文，专有名词（OpenAI、Claude、Harness 等）不翻译
- 段落紧密：一个段落 = 一个意思单元，通常 1-3 句话

## 段落整理策略

**输入**：YouTube EN 自动字幕是单词级碎片（每句话 3-8 条），时间戳精确到毫秒。

**LLM 合并规则**：
1. 时间相近（≤ 3 秒间隔）的碎片合并为同一段落
2. 修复截断词（如 "execu" → "execute"）
3. 去除 [Music]、重复 subword artifacts
4. 保留原始 start timestamp（每个段落取第一个碎片的时间戳）

**输出格式**：JSON array，每项包含 `start`、`duration`、`en`：

```json
[
  {"start": "00:00:15", "duration": 4.2, "en": "Hello and welcome to this tutorial on AI agents."},
  {"start": "00:00:19", "duration": 6.8, "en": "Today I'll show you three patterns that..."}
]
```

## 翻译策略

**上下文感知翻译**：
- 每批翻译 10 条段落
- 每条包含：当前段落 EN + 前 1 条段落的 EN（作为上下文）
- 上下文帮助专有名词一致性和语气连贯

**Prompt 设计**：
```
你是一个专业的英文字幕翻译，擅长技术演讲。
将 English 列翻译为简体中文，保留专有名词（保持英文）。
只看 English 列，不要看中文。
输出格式：[N] 中文翻译（N 从 0 开始）

上下文（前一条）：
{prev_en}

当前待翻译：
[0] {en_0}
[1] {en_1}
...
```

**分批处理**：
- 每批 10 条（防止 context 过长）
- 上一批最后 1 条的翻译作为下一批的参考
- tiktoken 精确分批（~2000-4000 tokens/批）

## 文件命名

```
输入 VTT：~/youtube_videos/{Sanitized-Title}/{Sanitized-Title}.en.vtt
输出 MD：  ~/youtube_videos/{Sanitized-Title}/{Sanitized-Title}-translate.md
```

## 使用方法

```bash
# 方式一：直接运行 main.py
python3 ~/.hermes/skills-mine/productivity/video-translate-to-table/scripts/main.py \
  --vtt "~/youtube_videos/Your-Body-Language-May-Shape-Who-You-Are-_-Amy-Cuddy-_-TED/Your-Body-Language-May-Shape-Who-You-Are-_-Amy-Cuddy-_-TED.en.vtt" \
  --url "https://www.youtube.com/watch?v=Ks-_Mh1QhMc"

# 方式二：通过 youtube-to-obsidian orchestration skill 调用
# （由 orchestration skill 串联 yt-download + video-translate-to-table + video-obsidian-save）
```

## 已知问题与解决

### EN 字幕单词级碎片导致句子不完整
**解决**：paragraph_weaver.py 用 LLM 合并碎片为完整段落，修复截断词。

### 翻译专有名词不一致
**解决**：每批翻译提供上下文（前一条 EN），prompt 明确要求专有名词保持英文。

### 长视频翻译 token 超出限制
**解决**：tiktoken 精确分批，每批 10 条，2000-4000 tokens/批。

## 依赖

- Python 3.8+
- `tiktoken`（精确分批）
- `minimax` API（通过 `~/.hermes/.env` 的 `MINIMAX_API_KEY`）
- `vtt_parser.py`、`paragraph_weaver.py`、`translator.py`、`main.py`
