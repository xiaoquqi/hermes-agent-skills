---
name: tech-trending-fetcher
description: 多平台科技热点获取工具 —— 抓取抖音、B站、微博、Hacker News 热搜榜，支持按平台筛选，输出格式化热点日报
category: productivity
---

# 科技热点获取工具

## 支持的平台

| 平台 | API/源 | 状态 | 说明 |
|------|--------|------|------|
| 💻 Hacker News | `https://hnrss.org/frontpage` | ✅ 稳定 | RSS，解析 `<title><![CDATA[...]]></title>` |
| 📱 抖音热搜 | `https://www.douyin.com/aweme/v1/web/hot/search/list/` | ✅ 稳定 | 需 User-Agent + Referer，label_map 见下方 |
| 📺 B站热门 | `https://api.bilibili.com/x/web-interface/popular?ps=20` | ✅ 稳定 | 无需认证 |
| 📺 B站科技区 | `https://api.bilibili.com/x/web-interface/ranking/v2?rid=36&type=all` | ⚠️ 限速 | code=-352 时说明触发限速 |
| 📣 微博热搜 | `https://weibo.com/ajax/side/hotSearch` | ✅ 稳定 | flag映射见下方，可能SSL超时 |

## 已验证不可用的平台（2026-04 测试）
- **知乎**：`/api/v4/creators/rank/hot` → 404，API已改
- **IT之家**：需签名/动态参数
- **36氪**：`/api/newsflash/homepage/list` → SSL超时
- **小红书**：301重定向，需Cookie，Browserbase环境下需额外验证
- **贴吧**：`/hottopic/browse/topicList` → 返回空
- **虎扑**：`games-mobile.api.hupu.com` → 限速
- **GitHub Trending**：`/trending` 页面JS渲染，正则匹配失败
- **GitHub API**：`/search/repositories` → 需认证+限速，今日新项目返回空

## 平台访问限制（2026-04 实测）

| 平台 | 终端curl | 浏览器/Bing | 备注 |
|------|----------|-------------|------|
| 抖音热搜API | ❌ 超时/BLOCKED | ⚠️ captcha风险 | 搜索关键词触发验证码劫持；热榜API终端可用但可能被限 |
| 小红书 | ❌ 301+验证 | ❌ 需Cookie | 搜索关键词无法直接抓取 |
| B站科技区API | ❌ 超时/BLOCKED | ✅ Bing搜索可用 | 终端API普遍超时，切换Bing搜索作为替代 |
| 微博 | ✅ 稳定 | ✅ | 偶尔SSL超时 |

## Bing搜索作为备选

当平台API不可用时，用 Bing 搜索替代：
- `https://cn.bing.com/search?q=<关键词>+site:<平台域名>`
- 示例：`https://cn.bing.com/search?q=算力+site:douyin.com`
- Bing对中文平台收录较好，可获取标题+摘要+时间

## 关键代码片段

### Hacker News RSS 解析
```python
import urllib.request, re
req = urllib.request.Request('https://hnrss.org/frontpage', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=8) as r:
    xml = r.read().decode()
titles = re.findall(r'<title><!\[CDATA\[([^\]]+)\]\]></title>', xml)
titles = [t for t in titles if t != 'Hacker News: Front Page']
```

### 抖音热搜 + label映射
```python
url = 'https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.douyin.com/'
})
label_map = {0:'', 1:'🔺', 3:'🔥', 8:'🎵', 16:'📰', 4003:'🌐', 5000:'🎬', 20002:'💬', 5005:'📱', 5006:'🔬', 5010:'🎮', 5003:'💻'}
```

### 微博热搜 flag映射（科技类过滤）
```python
labels = {5003:'🔬科学', 5005:'🌐互联', 5010:'🎮游戏', 5006:'📱数码'}
# flag不在此列表的为非科技内容，需单独判断是否展示
```

## 已知坑

1. **SSL超时**：微博/36氪在某些网络环境下 SSL handshake 超时，属网络问题非API问题，加 timeout=8 即可，超时则跳过
2. **B站限速**：频繁请求 `rid=36` 会触发 code=-352，切换到整体热门 `popular?ps=20` 即可
3. **抖音 label**：label 值可能扩展，不要用固定枚举，get不到时返回空字符串
4. **B站视频数格式化**：`views//10000` 得万为单位，避免浮点

## 使用方式

```bash
python3 newsnow_trending.py [platform] [limit]
# platform: all/douyin/bilibili/weibo/hackernews
# limit: 每榜数量，默认10
```
