---
name: whisper
description: OpenAI's general-purpose speech recognition model. Supports 99 languages, transcription, translation to English, and language identification. Six model sizes from tiny (39M params) to large (1550M params). Use for speech-to-text, podcast transcription, or multilingual audio processing. Best for robust, multilingual ASR.
version: 1.0.0
author: Orchestra Research
license: MIT
dependencies: [openai-whisper, transformers, torch]
metadata:
  hermes:
    tags: [Whisper, Speech Recognition, ASR, Multimodal, Multilingual, OpenAI, Speech-To-Text, Transcription, Translation, Audio Processing]

---

# Whisper - Robust Speech Recognition

OpenAI's multilingual speech recognition model.

## When to use Whisper

**Use when:**
- Speech-to-text transcription (99 languages)
- Podcast/video transcription
- Meeting notes automation
- Translation to English
- Noisy audio transcription
- Multilingual audio processing

**Metrics**:
- **72,900+ GitHub stars**
- 99 languages supported
- Trained on 680,000 hours of audio
- MIT License

**Use alternatives instead**:
- **AssemblyAI**: Managed API, speaker diarization
- **Deepgram**: Real-time streaming ASR
- **Google Speech-to-Text**: Cloud-based

## Video-to-Bilingual-Transcript Pipeline

When YouTube videos have no embedded subtitles and yt-dlp download is slow/unreliable,
use this pipeline instead:

### Step 1 — Extract audio from local video

```bash
ffmpeg -i "video.mp4" -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav -y
```

- `-ar 16000` required for Whisper
- `-ac 1` (mono) reduces file size ~50%

### Step 2 — Transcribe with Whisper

```python
import whisper, json

model = whisper.load_model("base")  # USE base, NOT turbo/large (they get stuck)

for video, out_json in [("/tmp/audio-01.wav", "/tmp/01.json"), ...]:
    result = model.transcribe(video, language="en", task="transcribe")
    with open(out_json, "w") as f:
        json.dump(result, f)
    print(f"{out_json}: {len(result['segments'])} segments")
```

**Background execution** (for long videos >30min):
- Run with `background=true` + `notify_on_complete=true`
- Monitor progress: `ls -la /tmp/subs-*/` — transcript.json grows in size as it processes
- Check process: `ps aux | grep whisper` — should show ~300% CPU when actively transcribing
- **Always kill orphaned processes first**: `kill -9 $(pgrep -f whisper)` to prevent CPU contention

### Model selection for technical content (IMPORTANT — practical findings)

| Model | Parameters | Speed | Reliability | Notes |
|-------|------------|-------|-------------|-------|
| **base** | 74M | ~16x realtime | ✅ **Recommended** | Already cached locally (base.pt ~145MB). Works reliably. |
| turbo | 809M | ~8x realtime | ❌ **Gets stuck** | Download/init hangs at 0% CPU, never recovers |
| large | 1550M | ~1x realtime | ❌ **Gets stuck** | Same issue as turbo, ~2.9GB download |

**Practical finding**: Do NOT use turbo or large — their download/get stuck frequently at 0% CPU during initialization. Use `base` instead. base.pt is already cached locally and works reliably for English technical narration.

**If turbo/large appears stuck** (0% CPU, no output for >5min after "Loading model..."), kill it immediately:
```bash
kill -9 $(pgrep -f whisper)
```
Then retry with `base`.

### Step 3 — Generate bilingual markdown

```python
# For each segment, produce Chinese + English pair:
# - Chinese translation first
# - English original second
# - Insert screenshot references at relevant timestamps
```

### Key insight
**Don't rely on yt-dlp for subtitles** — many videos have no embedded captions and
yt-dlp download is slow. Extract audio + use Whisper directly from downloaded video file.

## Model sizes

| Model | Parameters | Speed | Best for |
|-------|------------|-------|----------|
| turbo | 809M | ~8x realtime | Good default |
| large | 1550M | ~1x realtime | Code/technical terms |
| base | 74M | ~16x realtime | Prototyping |

## Transcription options

### Language specification

```python
# Auto-detect language
result = model.transcribe("audio.mp3")

# Specify language (faster)
result = model.transcribe("audio.mp3", language="en")

# Supported: en, es, fr, de, it, pt, ru, ja, ko, zh, and 89 more
```

### Task selection

```python
# Transcription (default)
result = model.transcribe("audio.mp3", task="transcribe")

# Translation to English
result = model.transcribe("spanish.mp3", task="translate")
# Input: Spanish audio → Output: English text
```

### Initial prompt

```python
# Improve accuracy with context
result = model.transcribe(
    "audio.mp3",
    initial_prompt="This is a technical podcast about machine learning and AI."
)

# Helps with:
# - Technical terms
# - Proper nouns
# - Domain-specific vocabulary
```

### Timestamps

```python
# Word-level timestamps
result = model.transcribe("audio.mp3", word_timestamps=True)

for segment in result["segments"]:
    for word in segment["words"]:
        print(f"{word['word']} ({word['start']:.2f}s - {word['end']:.2f}s)")
```

### Temperature fallback

```python
# Retry with different temperatures if confidence low
result = model.transcribe(
    "audio.mp3",
    temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
)
```

## Command line usage

```bash
# Basic transcription
whisper audio.mp3

# Specify model
whisper audio.mp3 --model turbo

# Output formats
whisper audio.mp3 --output_format txt     # Plain text
whisper audio.mp3 --output_format srt     # Subtitles
whisper audio.mp3 --output_format vtt     # WebVTT
whisper audio.mp3 --output_format json    # JSON with timestamps

# Language
whisper audio.mp3 --language Spanish

# Translation
whisper spanish.mp3 --task translate
```

## Batch processing

```python
import os

audio_files = ["file1.mp3", "file2.mp3", "file3.mp3"]

for audio_file in audio_files:
    print(f"Transcribing {audio_file}...")
    result = model.transcribe(audio_file)

    # Save to file
    output_file = audio_file.replace(".mp3", ".txt")
    with open(output_file, "w") as f:
        f.write(result["text"])
```

## Real-time transcription

```python
# For streaming audio, use faster-whisper
# pip install faster-whisper

from faster_whisper import WhisperModel

model = WhisperModel("base", device="cuda", compute_type="float16")

# Transcribe with streaming
segments, info = model.transcribe("audio.mp3", beam_size=5)

for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

## GPU acceleration

```python
import whisper

# Automatically uses GPU if available
model = whisper.load_model("turbo")

# Force CPU
model = whisper.load_model("turbo", device="cpu")

# Force GPU
model = whisper.load_model("turbo", device="cuda")

# 10-20× faster on GPU
```

## Integration with other tools

### Subtitle generation

```bash
# Generate SRT subtitles
whisper video.mp4 --output_format srt --language English

# Output: video.srt
```

### With LangChain

```python
from langchain.document_loaders import WhisperTranscriptionLoader

loader = WhisperTranscriptionLoader(file_path="audio.mp3")
docs = loader.load()

# Use transcription in RAG
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

vectorstore = Chroma.from_documents(docs, OpenAIEmbeddings())
```

### Extract audio from video

```bash
# Use ffmpeg to extract audio
ffmpeg -i video.mp4 -vn -acodec pcm_s16le audio.wav

# Then transcribe
whisper audio.wav
```

## Best practices

1. **Use base model** — turbo/large get stuck during download/init; base is reliable and cached locally
2. **Specify language** — Faster than auto-detect (use `language="en"` for English)
3. **Add initial prompt** — Improves technical terms
4. **Use GPU** — 10-20× faster
5. **Batch process** — More efficient
6. **Convert to WAV** — Better compatibility
7. **Split long audio** — <30 min chunks
8. **Check language support** — Quality varies by language
9. **Use faster-whisper** — 4× faster than openai-whisper
10. **Monitor VRAM** — Scale model size to hardware
11. **Kill orphaned processes first** — Multiple Whisper processes compete for CPU and slow everything down

## Performance

| Model | Real-time factor (CPU) | Real-time factor (GPU) |
|-------|------------------------|------------------------|
| tiny | ~0.32 | ~0.01 |
| base | ~0.16 | ~0.01 |
| turbo | ~0.08 | ~0.01 |
| large | ~1.0 | ~0.05 |

*Real-time factor: 0.1 = 10× faster than real-time*

## Language support

Top-supported languages:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Japanese (ja)
- Korean (ko)
- Chinese (zh)

Full list: 99 languages total

## Limitations

1. **Hallucinations** - May repeat or invent text
2. **Long-form accuracy** - Degrades on >30 min audio
3. **Speaker identification** - No diarization
4. **Accents** - Quality varies
5. **Background noise** - Can affect accuracy
6. **Real-time latency** - Not suitable for live captioning

## Resources

- **GitHub**: https://github.com/openai/whisper ⭐ 72,900+
- **Paper**: https://arxiv.org/abs/2212.04356
- **Model Card**: https://github.com/openai/whisper/blob/main/model-card.md
- **Colab**: Available in repo
- **License**: MIT


