#!/usr/bin/env python3
"""
科技自媒体热点获取工具 v3
支持: 抖音, B站, 微博, Hacker News

Usage:
    python3 newsnow_trending.py [platform] [limit]
    platform: all/douyin/bilibili/weibo/hackernews
    limit: 每榜数量，默认10
"""

import json
import urllib.request
import re
from datetime import datetime

# ─── 平台配置 ────────────────────────────────────────────

LABEL_MAP = {0:'', 1:'🔺', 3:'🔥', 8:'🎵', 16:'📰', 4003:'🌐',
             5000:'🎬', 20002:'💬', 5005:'📱', 5006:'🔬', 5010:'🎮', 5003:'💻'}
WB_LABEL_MAP = {5003:'🔬', 5005:'🌐', 5010:'🎮', 5006:'📱'}

HEADERS_COMMON = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# ─── 平台获取函数 ──────────────────────────────────────────

def fetch_hackernews(limit=10):
    req = urllib.request.Request('https://hnrss.org/frontpage', headers=HEADERS_COMMON)
    with urllib.request.urlopen(req, timeout=10) as r:
        xml = r.read().decode()
    titles = re.findall(r'<title><!\[CDATA\[([^\]]+)\]\]></title>', xml)
    titles = [t for t in titles if t != 'Hacker News: Front Page']
    return {'platform': 'hackernews', 'name': '💻 Hacker News', 'items': titles[:limit]}

def fetch_douyin(limit=10):
    url = ('https://www.douyin.com/aweme/v1/web/hot/search/list/'
           '?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1')
    req = urllib.request.Request(url, headers={
        **HEADERS_COMMON, 'Referer': 'https://www.douyin.com/'
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.loads(r.read())
    items = []
    for item in d['data']['word_list'][:limit]:
        lb = LABEL_MAP.get(item.get('label', 0), '')
        items.append(f"{item['word']} {lb}".strip())
    return {'platform': 'douyin', 'name': '📱 抖音热搜', 'items': items}

def fetch_bilibili(limit=10):
    url = 'https://api.bilibili.com/x/web-interface/popular?ps=20'
    req = urllib.request.Request(url, headers={**HEADERS_COMMON, 'Referer': 'https://www.bilibili.com/'})
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.loads(r.read())
    items = []
    for v in d['data']['list'][:limit]:
        views = v['stat']['view'] // 10000
        likes = v['stat']['like'] // 10000
        items.append(f"{v['title']} @{v['owner']['name']} 👁 {views}万 ❤️ {likes}万")
    return {'platform': 'bilibili', 'name': '📺 B站热门视频', 'items': items}

def fetch_weibo(limit=10):
    url = 'https://weibo.com/ajax/side/hotSearch'
    req = urllib.request.Request(url, headers={**HEADERS_COMMON, 'Referer': 'https://weibo.com'})
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.loads(r.read())
    items = [item['word'] for item in d['data']['realtime'][:limit]]
    return {'platform': 'weibo', 'name': '📣 微博热搜', 'items': items}

# ─── 入口 ────────────────────────────────────────────────

def main():
    import sys
    platform = sys.argv[1] if len(sys.argv) > 1 else 'all'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    platforms = {
        'hackernews': fetch_hackernews,
        'douyin': fetch_douyin,
        'bilibili': fetch_bilibili,
        'weibo': fetch_weibo,
    }
    if platform != 'all' and platform not in platforms:
        print(f'未知平台: {platform}')
        return

    targets = platforms if platform == 'all' else {platform: platforms[platform]}

    print(f"{'='*55}")
    print(f"   ⚡ 科技热点日报 · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")

    for key, fn in targets.items():
        try:
            data = fn(limit)
            print(f"\n{data['name']}")
            print("-" * 45)
            for i, item in enumerate(data['items'], 1):
                print(f"  {i:2d}. {item}")
        except Exception as e:
            print(f"\n{data['name']}")
            print("-" * 45)
            print(f"  ❌ 获取失败: {e}")

if __name__ == '__main__':
    main()
