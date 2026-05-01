---
name: "google-news-analyzer"
description: "从Google News不同区域（中国、美国、新加坡等）获取新闻并进行综合分析。支持多区域视角对比、新闻趋势分析和跨文化报道差异识别。"
---

# Google News多区域新闻分析技能

本技能专门用于从Google News不同区域版本获取新闻内容，进行多视角对比分析和综合评估。

## 支持的新闻区域

| 区域 | 语言代码 | 国家代码 | Google News URL | 特点说明 |
|------|----------|----------|----------------|----------|
| **美国** | `en-US` | `US` | `https://news.google.com/search?q={keyword}&hl=en-US&gl=US` | 国际视角，西方媒体报道 |
| **中国** | `zh-CN` | `CN` | `https://news.google.com/search?q={keyword}&hl=zh-CN&gl=CN` | 中文报道，中国视角 |
| **新加坡** | `en-SG` | `SG` | `https://news.google.com/search?q={keyword}&hl=en-SG&gl=SG` | 东南亚视角，中立报道 |
| **英国** | `en-GB` | `GB` | `https://news.google.com/search?q={keyword}&hl=en-GB&gl=GB` | 欧洲视角，BBC等媒体 |
| **日本** | `ja` | `JP` | `https://news.google.com/search?q={keyword}&hl=ja&gl=JP` | 亚洲视角，日经新闻等 |
| **印度** | `en-IN` | `IN` | `https://news.google.com/search?q={keyword}&hl=en-IN&gl=IN` | 南亚视角，发展中国家视角 |
| **俄罗斯** | `ru` | `RU` | `https://news.google.com/search?q={keyword}&hl=ru&gl=RU` | 俄语媒体，不同政治视角 |

## 核心功能

### 1. 多区域新闻采集
- 同时从多个地区获取同一主题的新闻报道
- 支持自定义区域组合
- 自动处理语言编码和地区参数

### 2. 跨文化报道分析
- 识别不同地区报道的重点差异
- 分析报道角度和立场偏向
- 比较信息完整度和深度

### 3. 新闻趋势识别
- 发现全球关注的热点话题
- 识别地区性特殊关注点
- 跟踪事件发展的时间线

### 4. 综合分析报告
- 生成多区域新闻对比报告
- 提供综合态势评估
- 识别信息缺口和矛盾点

## 使用方法

### 基本搜索命令

```javascript
// 单区域搜索 - 美国视角
web_fetch({
  "url": "https://news.google.com/search?q=伊朗+战争&hl=en-US&gl=US&ceid=US%3Aen"
})

// 单区域搜索 - 中国视角
web_fetch({
  "url": "https://news.google.com/search?q=伊朗+战争&hl=zh-CN&gl=CN&ceid=CN%3Azh"
})

// 单区域搜索 - 新加坡视角  
web_fetch({
  "url": "https://news.google.com/search?q=iran+war&hl=en-SG&gl=SG&ceid=SG%3Aen"
})

// 时间限定搜索 - 近24小时
web_fetch({
  "url": "https://news.google.com/search?q=iran+war&hl=en-US&gl=US&when:1d"
})
```

### 多区域综合分析流程

```javascript
// 1. 定义分析主题
const topic = "伊朗战争局势";
const keywords = ["iran war", "伊朗战争", "伊朗局势"];

// 2. 配置要分析的地区
const regions = [
  { name: "美国", lang: "en-US", country: "US", keyword: "iran war" },
  { name: "中国", lang: "zh-CN", country: "CN", keyword: "伊朗战争" },
  { name: "新加坡", lang: "en-SG", country: "SG", keyword: "iran war" }
];

// 3. 并行获取各地区新闻
// （在实际使用中，这里会进行多个web_fetch调用）

// 4. 进行分析对比
// - 提取各地区头条新闻
// - 比较报道角度和重点
// - 识别共识点和差异点

// 5. 生成综合分析报告
```

## 参数说明

### 基本参数
- `q`：搜索关键词（需要URL编码）
- `hl`：界面语言（语言-国家代码）
- `gl`：地区/国家代码
- `ceid`：完整的语言/地区代码（格式：国家:语言）

### 高级参数
- `when`：时间范围（`1d`=近一天，`7d`=近一周）
- `sort`：排序方式（`r`=相关性，`d`=日期）
- `num`：结果数量（默认10）

### 语言代码参考
- `en-US`：美国英语
- `zh-CN`：简体中文（中国）
- `zh-TW`：繁体中文（台湾）
- `ja`：日语
- `ko`：韩语
- `ru`：俄语
- `ar`：阿拉伯语

### 国家代码参考
- `US`：美国
- `CN`：中国
- `SG`：新加坡
- `GB`：英国
- `JP`：日本
- `IN`：印度
- `RU`：俄罗斯
- `DE`：德国
- `FR`：法国

## 分析维度

### 1. 报道角度分析
- **美国视角**：关注地缘政治、军事行动、国际影响
- **中国视角**：关注经济影响、外交立场、地区稳定
- **新加坡视角**：关注航运安全、经济影响、中立分析

### 2. 信息完整性对比
- 各地区的报道深度
- 信息来源的多样性
- 数据支持的完整性

### 3. 立场偏向识别
- 报道语言的倾向性
- 引用来源的选择性
- 事件解释的框架

### 4. 重点关注差异
- 各地区关注的不同侧面
- 优先报道的内容差异
- 忽视或弱化的信息

## 实际应用示例

### 伊朗战争局势分析
```javascript
// 步骤1：获取各地区新闻
const usNews = await getGoogleNews("iran war", "en-US", "US");
const cnNews = await getGoogleNews("伊朗战争", "zh-CN", "CN");
const sgNews = await getGoogleNews("iran war", "en-SG", "SG");

// 步骤2：提取关键信息
// - 美国报道：军事行动、国会辩论、撤侨情况
// - 中国报道：经济影响、外交表态、地区安全
// - 新加坡报道：航运影响、经济分析、中立评估

// 步骤3：生成分析报告
// 1. 共同关注点：霍尔木兹海峡安全、平民伤亡
// 2. 差异点：美国强调军事行动，中国强调外交解决
// 3. 信息缺口：具体军事伤亡数据、经济影响估算
```

### 经济事件分析
```javascript
// 不同地区对同一经济事件的不同报道
const usEconomicNews = await getGoogleNews("stock market crash", "en-US", "US");
const cnEconomicNews = await getGoogleNews("股市崩盘", "zh-CN", "CN");
const jpEconomicNews = await getGoogleNews("株価暴落", "ja", "JP");
```

## 技术实现

### URL构建函数
```javascript
function buildGoogleNewsUrl(keyword, lang, country, options = {}) {
  const params = new URLSearchParams({
    q: encodeURIComponent(keyword),
    hl: lang,
    gl: country,
    ceid: `${country}:${lang.split('-')[0]}`
  });
  
  if (options.when) params.append('when', options.when);
  if (options.sort) params.append('sort', options.sort);
  if (options.num) params.append('num', options.num.toString());
  
  return `https://news.google.com/search?${params.toString()}`;
}
```

### 新闻解析函数
```javascript
function parseGoogleNewsContent(htmlContent, region) {
  // 解析HTML提取新闻条目
  // 每个条目包含：标题、来源、时间、摘要、链接
  // 根据region信息添加地区标签
}
```

## 最佳实践

### 1. 关键词优化
- 为不同地区使用合适的语言和关键词
- 考虑文化差异和表达习惯
- 使用同义词扩展搜索范围

### 2. 时间控制
- 重要事件：搜索近24小时内容
- 趋势分析：搜索近7天内容
- 背景研究：搜索近30天内容

### 3. 地区组合建议
- **地缘政治事件**：美国 + 中国 + 俄罗斯
- **经济事件**：美国 + 中国 + 日本 + 德国
- **地区冲突**：当事国 + 周边国家 + 大国

### 4. 报告结构
1. **执行摘要**：核心发现和结论
2. **各地区报道概述**：分地区简要介绍
3. **对比分析**：重点差异和共识
4. **综合评估**：整体态势判断
5. **信息缺口**：需要进一步了解的内容
6. **建议**：后续关注点和行动建议

## 故障排除

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 无搜索结果 | 关键词不合适 | 调整关键词，使用同义词 |
| 地区限制 | 某些地区访问受限 | 尝试代理服务器或VPN |
| 语言问题 | 语言代码错误 | 检查语言代码格式 |
| 内容解析失败 | 页面结构变化 | 更新解析逻辑 |

## 扩展开发

### 添加新地区
```javascript
const newRegion = {
  name: "澳大利亚",
  lang: "en-AU",
  country: "AU",
  characteristics: "大洋洲视角，资源贸易关注"
};
```

### 集成其他新闻源
- 将BBC、CNN、新华社等权威媒体纳入分析
- 使用RSS订阅获取实时更新
- 集成社交媒体趋势分析

### 自动化分析
- 设置定期新闻监控
- 自动生成日报/周报
- 关键事件实时警报

---

**使用建议**：对于重大事件，建议至少选择3个不同地区的视角进行分析，以获得全面、平衡的认知。