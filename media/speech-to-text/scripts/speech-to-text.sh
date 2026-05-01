#!/bin/bash
set -euo pipefail

VIDEO_OR_DIR="${1:-}"
MODEL="${2:-medium}"

if [[ -z "$VIDEO_OR_DIR" ]]; then
    echo "Usage: $0 <VIDEO_FILE_OR_DIR> [MODEL]" >&2
    echo "Example: $0 ~/youtube_videos/Harness/video.webm medium" >&2
    exit 1
fi

# ─────────────────────────────────────────
# Step 1: 解析输入 — 找到视频文件
# ─────────────────────────────────────────
if [[ -f "$VIDEO_OR_DIR" ]]; then
    VIDEO_FILE="$VIDEO_OR_DIR"
    VIDEO_DIR="$(dirname "$VIDEO_FILE")"
    VIDEO_NAME="$(basename "$VIDEO_FILE" | sed 's/\.[^.]*$//')"
    echo "[INFO] 输入: 文件模式"
elif [[ -d "$VIDEO_OR_DIR" ]]; then
    VIDEO_DIR="$VIDEO_OR_DIR"
    VIDEO_FILE=$(find "$VIDEO_DIR" -maxdepth 1 \( -name "*.mp4" -o -name "*.webm" -o -name "*.mkv" -o -name "*.avi" \) | head -1)
    if [[ -z "$VIDEO_FILE" ]]; then
        echo "Error: 目录中未找到视频文件: $VIDEO_DIR" >&2
        exit 1
    fi
    VIDEO_NAME="$(basename "$VIDEO_FILE" | sed 's/\.[^.]*$//')"
    echo "[INFO] 输入: 目录模式"
    echo "[INFO] 找到视频: $VIDEO_NAME"
else
    echo "Error: 路径不存在: $VIDEO_OR_DIR" >&2
    exit 1
fi

echo "[INFO] 模型: $MODEL"
echo "[INFO] 视频: $VIDEO_NAME"

# ─────────────────────────────────────────
# Step 2: 字幕检查 — 有任何 VTT 则跳过 Whisper
# ─────────────────────────────────────────
# yt-download 只下载英文字幕 (.en.vtt)，质量通常足够
# Whisper 用于获得更高质量的转录（带词级时间戳）
# 如果已有任何 VTT（来自 yt-download）→ 认为够用，跳过 Whisper
ANY_VTT=$(find "$VIDEO_DIR" -maxdepth 1 -name "*.vtt" 2>/dev/null | head -1)
if [[ -n "$ANY_VTT" ]]; then
    echo "[SKIP] 英文字幕已存在: $ANY_VTT"
    echo "[INFO] Whisper 跳过（yt-download 英文字幕够用）"
    exit 0
fi

# ─────────────────────────────────────────
# Step 3: 运行 Whisper
# ─────────────────────────────────────────
echo "[INFO] 开始语音识别..."
echo "[INFO] 无 GPU，CPU 运行，较慢，请耐心等待..."

# Whisper 输出到视频同目录，命名 {VIDEO_NAME}.vtt
# --fp16 False:        Mac CPU 必须 fp32
# --output_format all: vtt + txt + srt + json + tsv
whisper "$VIDEO_FILE" \
    --model "$MODEL" \
    --language en \
    --task transcribe \
    --output_format all \
    --word_timestamps True \
    --output_dir "$VIDEO_DIR" \
    --fp16 False \
    2>&1 | tee -a "$VIDEO_DIR/whisper.log"

FINAL_VTT="$VIDEO_DIR/${VIDEO_NAME}.vtt"

echo ""
echo "[DONE] 语音识别完成"
echo "[DONE] 输出目录: $VIDEO_DIR"

# ─────────────────────────────────────────
# Step 4: 幂等确认
# ─────────────────────────────────────────
if [[ -f "$FINAL_VTT" ]]; then
    VTT_SIZE=$(wc -c < "$FINAL_VTT")
    VTT_LINES=$(wc -l < "$FINAL_VTT")
    echo "[VERIFIED] VTT: ${VIDEO_NAME}.vtt (${VTT_SIZE} bytes, ${VTT_LINES} lines)"
else
    ACTUAL=$(find "$VIDEO_DIR" -name "*.vtt" | head -1)
    if [[ -n "$ACTUAL" ]]; then
        echo "[VERIFIED] VTT: $(basename "$ACTUAL") ($(wc -c < "$ACTUAL") bytes)"
    else
        echo "[ERROR] VTT 未生成" >&2
        exit 1
    fi
fi

echo ""
echo "[FILES]"
ls -lh "$VIDEO_DIR"/${VIDEO_NAME}.* 2>/dev/null
