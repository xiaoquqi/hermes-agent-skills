---
name: bilibili-hot
description: 获取B站（Bilibili）热榜视频列表，支持全站榜、分类榜。自动走 Clash 代理。热榜抓取无需登录。
author: hermes
version: 1.0.0
triggers:
  - "b站热榜"
  - "bilibili热门"
  - "b站排行"
  - "刷b站"
  - "b站热搜"
  - "bilibili hot"
metadata: {"clawdbot":{"emoji":"🔥","requires":{"bins":["curl","python3"]}}}
---

# Bilibili 热榜

获取 Bilibili 热门视频排行榜，支持全站榜和分类榜。

## 使用方式

```bash
# 全站热榜 Top 20
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py

# 全站热榜 Top N（自定义数量）
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --count 50

# 分类热榜（rid）
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --rid 1     # 动画
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --rid 3     # 音乐
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --rid 4     # 游戏
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --rid 5     # 娱乐
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --rid 11    # 电视剧
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --rid 23    # 电影
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --rid 36    # 科技
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --rid 188   # 手机游戏
python3 ~/.hermes/skills/media/bilibili-hot/scripts/get_hot.py --rid 234   # 生活
```

## RID 参考

| RID | 分类 | RID | 分类 |
|-----|------|-----|------|
| 0   | 全站 | 4   | 游戏 |
| 1   | 动画 | 5   | 娱乐 |
| 2   | 番剧 | 11  | 电视剧 |
| 3   | 音乐 | 23 | 电影 |
| 36   | 科技 | 188 | 手游 |
| 234 | 生活 | 181 | 军事 |

## 输出格式

每行格式：`排名. 标题 (播放量) @UP主`

## 注意事项

- 通过 Clash 代理（SOCKS5 127.0.0.1:7890）访问，走 clash-verge
- 无需登录，公开 API
- 支持自动重试 1 次
