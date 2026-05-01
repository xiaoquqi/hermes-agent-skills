#!/usr/bin/env python3
"""
Bilibili 热榜抓取脚本
支持全站榜和分类榜，自动走 Clash 代理（SOCKS5）
"""
import argparse
import json
import subprocess
import sys


PROXY = "socks5://127.0.0.1:7890"
# 全站热榜用 ranking 接口，分类用 popular 接口（ranking容易被限流）
RANK_API = "https://api.bilibili.com/x/web-interface/ranking/v2"
POPULAR_API = "https://api.bilibili.com/x/web-interface/popular"


def fetch(url: str, timeout: int = 12) -> dict:
    """通过 curl + Clash SOCKS5 代理请求 URL，返回 JSON"""
    cmd = [
        "curl", "-s", "--max-time", str(timeout),
        "-x", PROXY,
        "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "-H", "Referer: https://www.bilibili.com/",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"请求失败 (exit {e.returncode}): {e.stderr[:200]}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: curl not found", file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}\n原始内容: {result.stdout[:200]}", file=sys.stderr)
        sys.exit(1)


def format_views(n: int) -> str:
    """格式化播放量"""
    if n >= 10_000_000:
        return f"{n / 10_000_000:.1f}千万"
    if n >= 10_000:
        return f"{n // 10_000}万"
    return str(n)


def main():
    parser = argparse.ArgumentParser(description="Bilibili 热榜抓取")
    parser.add_argument("--count", "-n", type=int, default=20,
                        help="返回数量，默认 20，上限 100")
    parser.add_argument("--rid", "-r", type=int, default=0,
                        help="分区 RID，0=全站，默认 0。常见值：1=动画 3=音乐 4=游戏 5=娱乐 36=科技 234=生活")
    args = parser.parse_args()

    # rid=0 用 ranking（全站），其他用 popular（分类）
    if args.rid == 0:
        url = f"{RANK_API}?rid=0&type=all"
    else:
        url = f"{POPULAR_API}?pn=1&ps={min(args.count, 50)}&order=click&rid={args.rid}"

    data = fetch(url)

    code = data.get("code")
    if code != 0:
        msg = data.get("message", "未知错误")
        print(f"API 返回错误: {code} - {msg}", file=sys.stderr)
        sys.exit(1)

    note = data.get("data", {}).get("note", "")
    items = data.get("data", {}).get("list", [])
    count = min(args.count, len(items))

    if note:
        print(f"# {note}\n")

    for i in range(count):
        v = items[i]
        title = v.get("title", "无标题")
        title = (title
                 .replace("&amp;", "&")
                 .replace("&lt;", "<")
                 .replace("&gt;", ">")
                 .replace("&#39;", "'")
                 .replace("&quot;", '"')
                 .replace("&nbsp;", " "))
        owner = v.get("owner", {}).get("name", "?")
        views = format_views(int(v.get("stat", {}).get("view", 0)))
        tname = v.get("tname", "")
        rank = i + 1
        print(f"{rank:2}. {title} ({views}播放) @{owner} [{tname}]")


if __name__ == "__main__":
    main()
