---
name: video-obsidian-save
description: 将 video-translate-to-table 输出的完整 markdown（含 frontmatter）归档到 Obsidian — 纯存储逻辑
triggers:
  - 视频字幕翻译完成
  - 保存双语笔记到 Obsidian
  - 视频笔记存档
---

# Video Obsidian Save

translator.py 输出完整 Obsidian 格式，formatter.py 只做存储。

## 前置条件

`video-translate-to-table` pipeline 已完成，translator.py 输出含 frontmatter 的 markdown。

## 存储路径

```
Obsidian根目录/
└── Clippings-Videos/
    └── <course-name>/
        └── <course-name>.md
```

## 一句话调用

```bash
python3 ~/.hermes/skills-mine/productivity/video-obsidian-save/scripts/formatter.py \
  --video-dir "~/youtube_videos/Your-Body-Language-..." \
  --course-name "Your-Body-Language-..."
```

## formatter.py 工作流程

1. 找到 `{video_dir}/*-translate.md`（已是完整 Obsidian 格式）
2. 复制 → `Clippings-Videos/{course-name}/{course-name}.md`
3. 更新 `Clippings-Videos/Index.md`（去重追加）

## Index 格式

```markdown
| #  | 课程           | 来源 | 时长    | 链接 |
| -- | -------------- | ---- | ------- | ---- |
| 1  | [[Course-Name]] | TED  | 20:09   | [YouTube](url) |
```
