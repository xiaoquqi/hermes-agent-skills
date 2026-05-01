---
name: video-trending
description: 获取各视频平台的热点/热门内容，返回标准化数据
category: media
---

# Video Trending - 视频平台热点获取

## 支持的平台

| 平台 | 源ID | 说明 |
|------|------|------|
| B站 (Bilibili) | `bilibili-hot-video` | 热门视频榜 |
| B站 (Bilibili) | `bilibili-hot-article` | 热门文章 |
| 抖音 (Douyin) | `douyin-hot-video` | 抖音热榜 |
| 微博 (Weibo) | `weibo-hot` | 微博热搜 |
| 知乎 (Zhihu) | `zhihu-hot` | 知乎热榜 |
| 微信 (Wechat) | `weixin-hot` | 微信热点 |

## 使用方式

```
/video-trending <平台> [数量]
```

或通过 cron 定时获取：

```
/video-trending bilibili-hot-video 10
```

## 返回格式

```json
{
  "platform": "bilibili",
  "source": "bilibili-hot-video",
  "updatedTime": "2024-01-15T12:00:00Z",
  "items": [
    {
      "id": "BV1xx411c7mD",
      "title": "视频标题",
      "url": "https://www.bilibili.com/video/BV1xx411c7mD",
      "pubDate": 1705312800000,
      "extra": {
        "info": "UP主名 · 100万播放",
        "icon": "https://i0.hdslb.com/bfs/archive/xxx.jpg"
      }
    }
  ]
}
```

## 实现原理

每个平台的热点通过以下步骤获取：

1. **调用平台公开 API** 或解析页面
2. **数据映射** → 标准化 NewsItem 格式
3. **缓存结果** → 避免频繁请求

### B站示例

```typescript
// API: https://api.bilibili.com/x/web-interface/popular
const res = await fetch("https://api.bilibili.com/x/web-interface/popular?ps=20", {
  headers: { "User-Agent": "Mozilla/5.0" }
})
const data = await res.json()

// 映射到标准格式
return data.data.list.map(video => ({
  id: video.bvid,
  title: video.title,
  url: `https://www.bilibili.com/video/${video.bvid}`,
  pubDate: video.pubdate * 1000,
  extra: {
    info: `${video.owner.name} · ${formatNumber(video.stat.view)}播放`,
    icon: video.pic
  }
}))
```

## 添加新平台

在 `server/sources/` 下创建新文件，如 `twitter.ts`：

```typescript
export const twitterTrending = defineSource(async () => {
  const res = await myFetch("https://api.twitter.com/xxx/trending")
  return res.data.map(item => ({
    id: item.id,
    title: item.text,
    url: `https://twitter.com/i/status/${item.id}`,
    pubDate: item.created_at,
    extra: { info: `${item.retweet_count}转发` }
  }))
})
```

然后在 `sources.ts` 注册即可。

## 注意事项

- 部分平台 API 可能有访问限制
- 热点数据通常有缓存，过期后自动刷新
- 微信热点需要登录态，NewsNow 服务端已处理
