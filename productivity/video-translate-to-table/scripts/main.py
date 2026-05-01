#!/usr/bin/env python3
"""
main.py — video-translate-to-table 端到端入口

用法：
    python3 main.py --vtt <VTT文件> --url <YouTube_URL> [--title <标题>] [--output <md路径>]

流程：
    1. vtt_parser.py      解析 VTT → 碎片列表
    2. paragraph_weaver.py LLM 合并碎片 → 段落列表
    3. translator.py       LLM 翻译 → translate.md 表格
"""

import sys
import json
import argparse
import os
import tempfile
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def run_step(name: str, cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """运行一个步骤，带进度打印"""
    print(f"\n{'='*50}")
    print(f"  Step {name}")
    print(f"{'='*50}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ {name} 失败！")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        sys.exit(1)
    if result.stdout.strip():
        print(result.stdout)
    return result


def main():
    parser = argparse.ArgumentParser(description='EN VTT → translate.md 表格')
    parser.add_argument('--vtt', required=True, help='VTT 文件路径')
    parser.add_argument('--url', required=True, help='YouTube URL')
    parser.add_argument('--title', help='视频标题（默认从 VTT 文件名推断）')
    parser.add_argument('--output', '-o', help='输出 .md 路径（默认与 VTT 同目录）')
    args = parser.parse_args()

    vtt_path = Path(args.vtt).expanduser().resolve()
    if not vtt_path.exists():
        print(f"❌ VTT 文件不存在: {vtt_path}")
        sys.exit(1)

    # 推断标题：优先用 info.json，其次从 VTT 文件名推断
    info_path = vtt_path.parent / f"{vtt_path.stem.replace('.en','')}.info.json"
    if info_path.exists():
        with open(info_path, encoding="utf-8") as f:
            info_data = json.load(f)
        video_title = info_data.get("title", args.title or vtt_path.stem.replace('.en', ''))
    elif args.title:
        video_title = args.title
    else:
        video_title = vtt_path.name.replace('.en.vtt', '').replace('.vtt', '')

    # 输出路径
    if args.output:
        output_path = Path(args.output).expanduser()
    else:
        output_path = vtt_path.parent / f"{video_title}-translate.md"

    # 临时文件
    fragments_json = vtt_path.parent / f".{vtt_path.stem}_fragments.json"
    paragraphs_json = vtt_path.parent / f".{vtt_path.stem}_paragraphs.json"

    try:
        # Step 1: 解析 VTT
        run_step("1/3: 解析 VTT", [
            sys.executable, str(SCRIPT_DIR / "vtt_parser.py"),
            str(vtt_path), "--output-json", str(fragments_json)
        ])

        # Step 2: LLM 段落合并
        run_step("2/3: LLM 合并段落", [
            sys.executable, str(SCRIPT_DIR / "paragraph_weaver.py"),
            str(fragments_json), "--output", str(paragraphs_json)
        ])

        # Step 3: LLM 翻译
        run_step("3/3: LLM 翻译", [
            sys.executable, str(SCRIPT_DIR / "translator.py"),
            str(paragraphs_json),
            "--url", args.url,
            "--title", video_title,
            "--info", str(vtt_path.parent / f"{vtt_path.stem.replace('.en','')}.info.json"),
            "--output", str(output_path)
        ])

        print(f"\n{'='*50}")
        print(f"✅ 完成！translate.md → {output_path}")
        print(f"{'='*50}")

    finally:
        # 清理临时 JSON
        for tmp in [fragments_json, paragraphs_json]:
            if tmp.exists():
                tmp.unlink()


if __name__ == '__main__':
    main()
