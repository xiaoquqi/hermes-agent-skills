---
name: speech-to-text
description: >
  使用 OpenAI Whisper (本地) 对 YouTube 视频进行语音识别。
  输入：视频文件路径（mp4/webm/mkv）或 yt-download 输出目录。
  逻辑：已有 VTT 字幕则跳过，否则用 medium 模型运行语音识别。
  输出：VTT 时间戳字幕 + TXT 纯文本，保存到视频同目录。
  注意：无 GPU 的 Mac 用 medium 模型（large 太慢）；有 GPU 可用 large。
triggers:
  - 语音识别
  - whisper 语音转文字
  - 视频转文字
  - speech to text
  - speech-to-text
author: ray
version: 1.0.0
---

# speech-to-text — 本地 Whisper 语音识别

## 执行模型

```bash
bash ~/.hermes/skills/media/speech-to-text/scripts/speech-to-text.sh "<VIDEO_OR_DIR>" [MODEL]
```

参数：
- `VIDEO_OR_DIR`：视频文件路径 或 包含视频的目录（自动查找第一个视频）
- `MODEL`：Whisper 模型，可选 `tiny/base/small/medium/large`（默认：`medium`，Mac CPU 推荐）

## 工作流

```
输入路径（视频文件 或 目录）
    │
    ▼
Step 1 ─── 解析：若输入是目录，查找第一个视频文件
    │
    ▼
Step 2 ─── 字幕检查：同目录是否存在 .vtt 文件
    │         已有 VTT → [SKIP] 跳过 Whisper
    │         无 VTT → 继续
    ▼
Step 3 ─── 运行 Whisper（medium 模型）
    │         --model medium
    │         --language en（可改为 auto 自动检测）
    │         --task transcribe
    │         --output_format vtt,txt
    │         --word_timestamps True
    │         --output_dir <视频目录>
    ▼
Step 4 ─── 输出文件
    │         {VIDEO_NAME}.vtt  ← 带时间戳的字幕
    │         {VIDEO_NAME}.txt  ← 纯文本转录
    ▼
Step 5 ─── 幂等确认：文件存在即算成功
```

## 幂等性保证

- 已有同目录 `.vtt` 文件 → 跳过，不重复识别
- `.txt` 已有但无 `.vtt` → 跳过（VTT 是主要产出）
- Whisper 每次重新运行会覆盖旧输出（由调用方保证幂等）

## 已有字幕的情况

```bash
# yt-download 自带字幕，无需 Whisper
~/youtube_videos/Harness-Engineering-.../
├── ...webm   ← 有字幕
├── ...en.vtt ✅ → speech-to-text 自动跳过
└── ...zh-Hans.vtt ✅
```

Whisper 仅在**无字幕文件**时运行。

## 模型选择

| 模型 | 参数量 | CPU 速度 | 推荐场景 |
|------|--------|---------|---------|
| `tiny` | ~39M | 实时 | 测试/快速预览 |
| `base` | ~74M | 略慢 | 快速处理 |
| `small` | ~244M | 中等 | 平衡 |
| `medium` | ~769M | 较慢 | **Mac CPU 推荐** |
| `large` | ~1550M | 很慢 | GPU 推荐 |

Mac 无 GPU，CPU 运行 `large` 模型极慢，用 `medium`。

## 依赖

| 工具 | 状态 |
|------|------|
| openai-whisper | ✅ 已装 `20250625` |
| medium 模型 | ✅ 已有缓存 `~/.cache/whisper/medium.pt` |
| ffmpeg | ✅ yt-dlp 自带（用于音频提取） |

## 示例

```bash
# 方式1：传入视频文件
bash speech-to-text.sh ~/youtube_videos/Harness-.../...webm

# 方式2：传入目录（自动找视频）
bash speech-to-text.sh ~/youtube_videos/Harness-.../

# 指定 large 模型（如果有 GPU）
bash speech-to-text.sh ~/youtube_videos/.../video.webm large
```
