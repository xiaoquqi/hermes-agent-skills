#!/usr/bin/env python3
"""
抖音热榜抓取脚本
自动走 Clash SOCKS5 代理，必须使用 Mobile UA 才能请求成功
"""
import argparse
import json
import subprocess
import sys


PROXY = "socks5://127.0.0.1:7890"
API_URL = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
# 抖音 API 必须用 Mobile UA，否则返回 "Unsupported path(Janus)"
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"


def fetch(url: str, timeout: int = 12) -> dict:
    cmd = [
        "curl", "-s", "--max-time", str(timeout),
        "-x", PROXY,
        "-A", MOBILE_UA,
        "-H", "Accept: application/json, text/plain, */*",
        "-H", "Accept-Language: zh-CN,zh;q=0.9",
        "-H", f"Referer: https://www.douyin.com/",
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


def label_str(label: int) -> str:
    if label == 1:  return "🆕新"
    if label == 3:  return "📈上升"
    if label == 9:  return "🔥爆"
    if label == 8:  return "🔥爆"
    if label == 16: return "🔺进"
    return ""


def format_hot(hval: int) -> str:
    """格式化热度值"""
    if hval >= 10_000_000:
        return f"{hval/10_000_000:.1f}千万"
    if hval >= 10_000:
        return f"{hval//10_000}万"
    return str(hval)


def main():
    parser = argparse.ArgumentParser(description="抖音热榜抓取")
    parser.add_argument("-n", "--count", type=int, default=20,
                        help="返回数量，默认 20，上限 50")
    args = parser.parse_args()

    url = API_URL + "?device_platform=webapp&aid=6383&channel=channel_pc_web"
    data = fetch(url)

    code = data.get("status_code")
    if code != 0:
        msg = data.get("message", "未知错误")
        print(f"API 返回错误: {code} - {msg}", file=sys.stderr)
        sys.exit(1)

    active_time = data.get("data", {}).get("active_time", "")
    items = data.get("data", {}).get("word_list", [])
    count = min(args.count, len(items))

    print(f"🔥 抖音热榜 Top {count}  (更新时间: {active_time})")
    print("=" * 60)

    for i in range(count):
        v = items[i]
        word = v.get("word", "?")
        hval = v.get("hot_value", 0)
        label = label_str(v.get("label", 0))
        tag = ""
        st = v.get("sentence_tag", 0)
        # sentence_tag: 20002=情感, 10000=春天, 2012=演唱, 5000=娱乐, 3001=新闻, 16000=穿搭
        tag_map = {20002:"情感",10000:"春日",2012:"演唱",5000:"娱乐",3001:"新闻",
                   16000:"穿搭",6000:"航天",4003:"国际",9000:"日常",4007:"人物",
                   1001:"挑战",1002:"音乐",2003:"影视",2005:"明星",13000:"番剧",
                   12000:"游戏",21000:"政治",11000:"美食"}
        if st in tag_map:
            tag = f"[{tag_map[st]}]"
        lbl = f" {label}" if label else ""
        print(f"{i+1:2}. {word}{lbl} {tag} ({format_hot(hval)})")


if __name__ == "__main__":
    main()
