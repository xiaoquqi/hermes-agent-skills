---
name: "multi-search-engine"
description: "集成7大搜索引擎（百度、必应、360、搜狗、搜狗微信、头条）进行网页搜索。Invoke when user needs to search information online, compare search results from different engines, or fetch web content without API keys."
---

# 多搜索引擎集成技能

本技能集成了7个主流中文搜索引擎，支持通过网页抓取方式获取搜索结果，无需API密钥。

## 支持的搜索引擎

| 搜索引擎 | URL模板 | 类型 | 状态 | 特点说明 |
|---------|---------|------|------|----------|
| **百度** | `https://www.baidu.com/s?wd={keyword}` | 综合搜索 | 可用 | 国内最大搜索引擎，覆盖全面 |
| **必应国内版** | `https://cn.bing.com/search?q={keyword}&ensearch=0` | 综合搜索 | 可用 | ensearch=0表示国内搜索，结果更本土化 |
| **必应国际版** | `https://cn.bing.com/search?q={keyword}&ensearch=1` | 综合搜索 | 可用 | ensearch=1表示国际搜索，适合查找英文内容 |
| **360搜索** | `https://www.so.com/s?q={keyword}` | 综合搜索 | 可用 | 奇虎360出品，安全搜索特色 |
| **搜狗** | `https://sogou.com/web?query={keyword}` | 综合搜索 | 可用 | 腾讯旗下，支持微信内容搜索 |
| **搜狗微信** | `https://wx.sogou.com/weixin?type=2&query={keyword}` | 微信搜索 | 可用 | 专门搜索微信公众号文章 |
| **头条搜索** | `https://so.toutiao.com/search?keyword={keyword}` | 资讯搜索 | 可用 | 字节跳动旗下，聚合今日头条内容 |

## 使用方法

### 基本搜索命令

使用 `web_fetch` 工具抓取搜索结果页面：

```
// 使用百度搜索
web_fetch({"url": "https://www.baidu.com/s?wd=关键词"})

// 使用必应国内版搜索
web_fetch({"url": "https://cn.bing.com/search?q=关键词&ensearch=0"})

// 使用必应国际版搜索
web_fetch({"url": "https://cn.bing.com/search?q=关键词&ensearch=1"})

// 使用360搜索
web_fetch({"url": "https://www.so.com/s?q=关键词"})

// 使用搜狗搜索
web_fetch({"url": "https://sogou.com/web?query=关键词"})

// 使用头条搜索
web_fetch({"url": "https://so.toutiao.com/search?keyword=关键词"})

// 使用搜狗微信搜索公众号文章
web_fetch({"url": "https://wx.sogou.com/weixin?type=2&query=关键词"})
```

### 实际示例

```
// 搜索"贵州茅台"相关信息
web_fetch({"url": "https://www.baidu.com/s?wd=贵州茅台"})

// 搜索技术文档（使用必应国际版获取英文资料）
web_fetch({"url": "https://cn.bing.com/search?q=python tutorial&ensearch=1"})

// 搜索最新资讯（使用头条搜索）
web_fetch({"url": "https://so.toutiao.com/search?keyword=人工智能"})
```

## 搜索引擎选择建议

| 搜索场景 | 推荐引擎 | 原因 |
|---------|---------|------|
| 日常中文搜索 | 百度 | 覆盖面广，结果全面 |
| 国内新闻资讯 | 头条搜索 | 聚合今日头条内容，时效性强 |
| 英文资料查找 | 必应国际版 | 国际搜索结果更丰富 |
| 技术问题排查 | 必应国内版/搜狗 | 技术社区内容收录较好 |
| 安全相关查询 | 360搜索 | 安全过滤机制完善 |
| 微信文章搜索 | 搜狗微信 | 专门搜索微信公众号文章，内容更精准 |

## 注意事项

1. **URL编码**：如果关键词包含特殊字符（如空格、中文等），需要进行URL编码
2. **反爬虫机制**：部分搜索引擎可能有反爬虫机制，频繁请求可能导致临时限制
3. **结果解析**：返回的是HTML页面内容，需要根据具体需求提取有效信息
4. **网络环境**：部分搜索引擎在特定网络环境下可能访问受限

## 工作原理

本技能基于 `web_fetch` 工具实现网页抓取功能：

- 将用户输入的关键词替换URL模板中的 `{keyword}` 占位符
- 通过网页抓取工具获取搜索结果页面的HTML内容
- 解析并返回格式化的搜索结果（标题、链接、摘要）

**优势**：
- 无需申请API密钥
- 支持多个搜索引擎对比
- 直接获取原始搜索结果页面

## 故障排除

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 无法获取结果 | 网络连接问题 | 检查网络环境，尝试切换搜索引擎 |
| 返回内容为空 | 反爬虫拦截 | 降低请求频率，更换搜索引擎尝试 |
| 结果格式异常 | 页面结构变化 | 尝试其他搜索引擎获取对比结果 |

## 深度搜索功能

各搜索引擎支持的高级搜索参数，用于精准筛选搜索结果：

### 百度高级搜索

| 功能 | URL参数 | 示例 |
|------|---------|------|
| 近一天内 | `lm=1` | `https://www.baidu.com/s?wd={keyword}&lm=1` |
| 近一周内 | `lm=7` | `https://www.baidu.com/s?wd={keyword}&lm=7` |
| 近一月内 | `lm=30` | `https://www.baidu.com/s?wd={keyword}&lm=30` |
| 近一年内 | `lm=360` | `https://www.baidu.com/s?wd={keyword}&lm=360` |
| 站点内搜索 | `site=域名` | `https://www.baidu.com/s?wd={keyword}&site=zhihu.com` |
| PDF文档 | `filetype:pdf` | `https://www.baidu.com/s?wd={keyword}+filetype%3Apdf` |

### 必应时间筛选

| 功能 | URL参数 | 示例 |
|------|---------|------|
| 过去24小时 | `filters=ex1%3a%22ez1%22` | `https://cn.bing.com/search?q={keyword}&filters=ex1%3a%22ez1%22` |
| 过去一周 | `filters=ex1%3a%22ez2%22` | `https://cn.bing.com/search?q={keyword}&filters=ex1%3a%22ez2%22` |
| 过去一月 | `filters=ex1%3a%22ez3%22` | `https://cn.bing.com/search?q={keyword}&filters=ex1%3a%22ez3%22` |
| 过去一年 | `filters=ex1%3a%22ez5%22` | `https://cn.bing.com/search?q={keyword}&filters=ex1%3a%22ez5%22` |

### 搜狗微信时间筛选

| 功能 | URL参数 | 示例 |
|------|---------|------|
| 一天内更新 | `tsn=1` | `https://wx.sogou.com/weixin?type=2&query={keyword}&tsn=1` |
| 一周内更新 | `tsn=2` | `https://wx.sogou.com/weixin?type=2&query={keyword}&tsn=2` |
| 一月内更新 | `tsn=3` | `https://wx.sogou.com/weixin?type=2&query={keyword}&tsn=3` |
| 一年内更新 | `tsn=4` | `https://wx.sogou.com/weixin?type=2&query={keyword}&tsn=4` |
| 搜索公众号 | `type=1` | `https://wx.sogou.com/weixin?type=1&query={keyword}` |
| 搜索文章 | `type=2` | `https://wx.sogou.com/weixin?type=2&query={keyword}` |

### 360搜索垂直搜索

| 功能 | URL参数 | 示例 |
|------|---------|------|
| 新闻搜索 | `tn=news` | `https://www.so.com/s?q={keyword}&tn=news` |
| 图片搜索 | `tn=image` | `https://www.so.com/s?q={keyword}&tn=image` |
| 视频搜索 | `tn=video` | `https://www.so.com/s?q={keyword}&tn=video` |

### 头条搜索垂直搜索

| 功能 | URL参数 | 示例 |
|------|---------|------|
| 视频搜索 | `pd=video` | `https://so.toutiao.com/search?keyword={keyword}&pd=video` |
| 资讯搜索 | `pd=news` | `https://so.toutiao.com/search?keyword={keyword}&pd=news` |
| 图片搜索 | `pd=image` | `https://so.toutiao.com/search?keyword={keyword}&pd=image` |

## 深度搜索使用示例

```javascript
// 百度搜索知乎站内内容
web_fetch({"url": "https://www.baidu.com/s?wd=人工智能&site=zhihu.com"})

// 必应搜索近一周内容
web_fetch({"url": "https://cn.bing.com/search?q=人工智能&filters=ex1%3a%22ez2%22"})

// 搜狗微信搜索近三天文章
web_fetch({"url": "https://wx.sogou.com/weixin?type=2&query=人工智能&tsn=1"})

// 360新闻搜索
web_fetch({"url": "https://www.so.com/s?q=人工智能&tn=news"})

// 百度搜索PDF文档
web_fetch({"url": "https://www.baidu.com/s?wd=人工智能+filetype%3Apdf"})
```

## 扩展开发

如需添加更多搜索引擎，只需在配置中新增条目：

```json
{
  "name": "新搜索引擎名称",
  "url": "https://example.com/search?q={keyword}",
  "type": "搜索类型",
  "status": "可用",
  "notes": "特点说明"
}
```

## 专业领域深度搜索指南

详见 [references/advanced-search.md](references/advanced-search.md) 获取专业领域搜索策略：
- 行业资讯与新闻热点搜索
- 财务数据与金融数据搜索
- 政策信息与法规搜索
- 高级搜索技巧汇总
