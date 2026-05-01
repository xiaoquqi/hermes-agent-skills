---
name: video-translate-pipeline
description: YouTube VTT 字幕 → 语义段落合并 → 双语 Obsidian 笔记，端到端自动化
tags: [youtube, vtt, obsidian, translation, pipeline]
---

# Video Translate Pipeline

## 用途
YouTube VTT 字幕 → 语义段落合并 → 双语 Obsidian 笔记，端到端自动化。

## 流程（4步）
1. `python paragraph_weaver.py <vtt>` — VTT 碎片 dedup-only 合并为语义段落，输出 `paragraphs.json`
2. `python translator.py <paragraphs.json>` — 生成完整 Obsidian markdown（含 frontmatter + 双语表格），输出 `*-translate.md`
3. `python formatter.py` — 找到 `*-translate.md`，复制到 Obsidian vault，更新 Index
4. 手动更新 TASK-005 和 INDEX.md

## 关键参数
```bash
# paragraph_weaver.py
python paragraph_weaver.py "视频名.en.vtt" --model minimax/minimax-m2.7/b1d92 --batch-size 100 --max-concurrent 3

# translator.py（必须加 -o）
python translator.py paragraphs.json -o "视频名-translate.md"

# formatter.py
python formatter.py
```

## 已知 bug 和修复
1. **ASR字幕无间隙**：VTT 时间戳密集无停顿（2235条/35分钟），时间窗口预合并会全部压成1条。修复：dedup-only（10秒去重 + 过滤<5字符），不做时间窗口合并。
2. **as_completed乱序**：并发结果返回顺序不确定。修复：dict 按 batch_idx 存储，return 前 `sorted(results.keys())` 再 extend。
3. **translator.py -o 丢失**：output=None 时不保存文件。修复：加 `default=None`，main() 里自动推断 `output_path = args.output or paragraphs_path.replace('.json', '-translate.md')`。

## 依赖
- MiniMax API（`MINIMAX_API_KEY` 环境变量）
- ffprobe（`/opt/anaconda3/bin/ffprobe`，Python subprocess 调用时用全路径）
- info.json（需与 VTT stem 匹配：`视频名.info.json`）
- Obsidian vault：`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Ray/Clippings-Videos/`

## 验证结果
| 视频 | VTT条目 | 去重后 | 输出行数 |
|------|---------|--------|----------|
| Claude Code Full Tutorial | 2236 | 2235 | 194 |
| Cursor Tutorial | 905 | 904 | 75 |
| Cursor 2.0 | ~1766 | — | 109 |
| Codex CLI | ~1044 | — | 169 |
