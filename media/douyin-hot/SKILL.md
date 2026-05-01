---
name: douyin-hot
description: 获取抖音热榜 Top 50，支持全站榜和话题标签，自动走 Clash SOCKS5 代理
triggers: [抖音热榜, douyin hot, 抖音热搜]
---
# douyin-hot 技能

## 抓取抖音热榜

```bash
python3 ~/.hermes/skills/media/douyin-hot/scripts/get_hot.py
python3 ~/.hermes/skills/media/douyin-hot/scripts/get_hot.py -n 50   # 指定数量
```

## 技术细节

- **API**: `https://www.douyin.com/aweme/v1/web/hot/search/list/`
- **代理**: `socks5://127.0.0.1:7890`（Clash）
- **关键**: 必须使用 Mobile UA，否则抖音返回 `Unsupported path(Janus)` 错误
- **字段**: `word_list` 包含话题，`trending_list` 包含实时上升热点
- **sentence_tag**: 话题分类标签（20002=情感, 10000=春日, 2012=演唱会, 5000=娱乐 等）
