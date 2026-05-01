#!/usr/bin/env python3
"""
video-obsidian-save/formatter.py

纯存储逻辑：将 video-translate-to-table 输出的完整 markdown 文件归档到 Obsidian vault。

translator.py 已输出含 frontmatter 的 Obsidian 格式文件，
formatter 只负责复制 + 更新 Index。

用法:
  python3 formatter.py \
    --video-dir "~/youtube_videos/Your-Body-Language-..." \
    --course-name "Your-Body-Language-..."
"""

import argparse
import json
import os
import re
from pathlib import Path


def find_translate_md(video_dir: Path) -> Path | None:
    matches = list(video_dir.glob("*-translate.md"))
    return matches[0] if matches else None


def find_info_json(video_dir: Path) -> Path | None:
    matches = list(video_dir.glob("*.info.json"))
    return matches[0] if matches else None


def format_duration(sec: int) -> str:
    h, m = divmod(sec, 3600)
    m, s = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def run(video_dir: str, course_name: str,
        obsidian_vault: str = "/Users/ray/Library/Mobile Documents/iCloud~md~obsidian/Documents/Ray") -> None:
    video_dir = Path(video_dir).expanduser()
    obsidian_vault = Path(obsidian_vault).expanduser()

    # 1. 找文件
    translate_path = find_translate_md(video_dir)
    info_path = find_info_json(video_dir)

    if not translate_path:
        raise FileNotFoundError(f"未找到 *-translate.md in {video_dir}")

    info = {}
    if info_path:
        info = json.loads(info_path.read_text(encoding="utf-8"))

    # 2. 复制到 Obsidian
    dest_dir = obsidian_vault / "Clippings-Videos" / course_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / f"{course_name}.md"

    shutil.copy2(translate_path, dest_file)
    print(f"✅ 已保存: {dest_file}")

    # 3. 更新 Index
    index_path = obsidian_vault / "Clippings-Videos" / "Index.md"
    _update_index(index_path, course_name, info)


def _update_index(index_path: Path, course_name: str, info: dict) -> None:
    """追加课程到 Index（去重）"""
    idx_content = index_path.read_text(encoding="utf-8") if index_path.exists() else ""

    if f"[[{course_name}]]" in idx_content:
        print(f"⏭️  Index 已存在 [[{course_name}]]，跳过")
        return

    nums = [int(m) for m in re.findall(r"^\|\s*(\d+)\s*\|", idx_content, re.MULTILINE)]
    next_num = max(nums) + 1 if nums else 1

    uploader = info.get("uploader", info.get("channel", ""))
    duration = format_duration(info["duration"]) if info.get("duration") else "?"
    source_url = info.get("webpage_url", "")

    new_entry = (
        f"| {next_num} | [[{course_name}]] | {uploader} | "
        f"{duration} | [YouTube]({source_url}) |\n"
    )

    if "|--|" in idx_content:
        idx_content = idx_content.replace("|--|\n|", f"|--|\n{new_entry}|")
    else:
        idx_content = idx_content + "\n" + new_entry

    index_path.write_text(idx_content, encoding="utf-8")
    print(f"✅ Index 已更新: {index_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="将翻译好的视频笔记归档到 Obsidian")
    parser.add_argument("--video-dir", required=True)
    parser.add_argument("--course-name", required=True)
    parser.add_argument("--obsidian-vault", default=DEFAULT_VAULT)
    args = parser.parse_args()
    run(args.video_dir, args.course_name, args.obsidian_vault)


if __name__ == "__main__":
    import shutil
    DEFAULT_VAULT = "/Users/ray/Library/Mobile Documents/iCloud~md~obsidian/Documents/Ray"
    main()
