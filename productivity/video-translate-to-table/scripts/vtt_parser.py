#!/usr/bin/env python3
"""
vtt_parser.py — 解析 EN VTT 文件，返回时间戳+文本碎片列表

用法：
    python3 vtt_parser.py <vtt文件路径>
    python3 vtt_parser.py <vtt文件路径> --output-json <输出json路径>

返回：
    [
        {"start": "00:00:12.340", "start_sec": 12.34, "text": "Hello and welcome"},
        ...
    ]
"""

import re
import sys
import json
import argparse
from pathlib import Path


def parse_vtt(vtt_path: str) -> list[dict]:
    """解析 VTT 文件，返回 [(start_sec, start_display, text), ...]"""
    with open(vtt_path, encoding='utf-8') as f:
        content = f.read()

    # 去掉 WEBVTT 头
    content = re.sub(r'^WEBVTT.*?\n', '', content, flags=re.MULTILINE)

    # 按空行分割 blocks
    blocks = re.split(r'\n\n+', content.strip())

    entries = []
    for block in blocks:
        lines = block.strip().split('\n')
        ts = None
        texts = []

        for line in lines:
            # 匹配时间戳行：00:00:12.340 --> 00:00:14.500
            ts_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
            if ts_match:
                ts = ts_match.group(1)
            elif line.strip():
                # 去掉 VTT 标签 <c>...</c> <00:00:12.340>
                clean = re.sub(r'<c[^>]*>(.*?)</c>', r'\1', line)
                clean = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', clean)
                clean = clean.strip()
                # 去掉 <> 标签
                clean = re.sub(r'<[^>]+>', '', clean)
                if clean and not clean.startswith('WEBVTT'):
                    texts.append(clean)

        if ts and texts:
            # 取该 block 最后一个时间戳（ VTT 有时会拆分同义词条）
            start_sec = timestamp_to_seconds(ts)
            text = ' '.join(texts)
            entries.append({
                "start": ts,
                "start_sec": start_sec,
                "text": text
            })

    return entries


def timestamp_to_seconds(ts: str) -> float:
    """'00:01:23.456' → 83.456 秒"""
    h, m, rest = ts.split(':')
    s, ms = rest.split('.')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def seconds_to_display(seconds: float) -> str:
    """83.456 → '00:01:23'"""
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_timestamp(ts: str) -> str:
    """'00:01:23.340' → '00:01:23'"""
    return ts.split('.')[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='解析 VTT 文件')
    parser.add_argument('vtt', help='VTT 文件路径')
    parser.add_argument('--output-json', help='输出 JSON 文件路径（可选）')
    args = parser.parse_args()

    entries = parse_vtt(args.vtt)

    if args.output_json:
        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        print(f"✅ 解析完成：{len(entries)} 条碎片 → {args.output_json}")
    else:
        print(f"共 {len(entries)} 条碎片：")
        for e in entries:
            print(f"  {e['start']}  {e['text'][:60]}")
