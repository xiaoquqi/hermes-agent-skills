# 伊朗战争局势多区域新闻分析示例

本示例展示如何使用Google News多区域分析技能，从美国、中国、新加坡三个不同地区获取伊朗战争局势的最新报道，并进行综合分析。

## 分析目标
- 获取伊朗战争局势的最新发展
- 对比美国、中国、新加坡三地的报道角度
- 识别报道差异和共同关注点
- 提供综合态势评估

## 分析步骤

### 1. 定义分析参数

```javascript
// 分析主题：伊朗战争局势
const analysisTopic = "伊朗战争局势2026年3月";

// 各地区搜索关键词
const regionConfigs = [
  {
    name: "美国",
    lang: "en-US",
    country: "US",
    keyword: "Iran war latest news 2026",
    characteristics: "地缘政治视角，军事行动关注，国会辩论"
  },
  {
    name: "中国", 
    lang: "zh-CN",
    country: "CN",
    keyword: "伊朗最新战况 2026",
    characteristics: "经济影响关注，外交立场，地区稳定"
  },
  {
    name: "新加坡",
    lang: "en-SG", 
    country: "SG",
    keyword: "iran war situation singapore",
    characteristics: "航运安全，经济分析，中立评估"
  }
];

// 搜索时间范围：近24小时
const timeRange = "1d";
```

### 2. 构建各地区搜索URL

```javascript
function buildGoogleNewsUrl(keyword, lang, country, timeRange = null) {
  const params = new URLSearchParams({
    q: encodeURIComponent(keyword),
    hl: lang,
    gl: country,
    ceid: `${country}:${lang.split('-')[0]}`
  });
  
  if (timeRange) {
    params.append('when', timeRange);
  }
  
  return `https://news.google.com/search?${params.toString()}`;
}

// 生成各地区搜索URL
const searchUrls = regionConfigs.map(config => ({
  region: config.name,
  url: buildGoogleNewsUrl(config.keyword, config.lang, config.country, timeRange),
  characteristics: config.characteristics
}));
```

### 3. 执行新闻获取（实际使用web_fetch工具）

在实际使用中，需要为每个URL调用web_fetch工具：

```javascript
// 美国新闻搜索
web_fetch({
  "url": "https://news.google.com/search?q=Iran+war+latest+news+2026&hl=en-US&gl=US&ceid=US%3Aen&when:1d",
  "maxChars": 8000
})

// 中国新闻搜索
web_fetch({
  "url": "https://news.google.com/search?q=%E4%BC%8A%E6%9C%97%E6%9C%80%E6%96%B0%E6%88%98%E5%86%B5+2026&hl=zh-CN&gl=CN&ceid=CN%3Azh&when:1d",
  "maxChars": 8000
})

// 新加坡新闻搜索
web_fetch({
  "url": "https://news.google.com/search?q=iran+war+situation+singapore&hl=en-SG&gl=SG&ceid=SG%3Aen&when:1d",
  "maxChars": 8000
})
```

### 4. 基于Google News搜索结果的分析

根据之前从Google News获取的实际搜索结果，以下是各地区的报道特点分析：

## 各地区报道分析

### 🇺🇸 美国视角报道特点
1. **关注重点**：
   - 国会政治斗争（战争权力法案投票）
   - 军事行动细节（航母部署、空袭行动）
   - 平民伤亡事件（学校袭击调查）

2. **主要来源**：
   - AP News（美联社）
   - ABC News（美国广播公司）
   - CBS News（哥伦比亚广播公司）
   - Fox News（福克斯新闻）

3. **报道角度**：
   - 强调美国军事行动的合法性
   - 关注国际法律和人权问题
   - 报道国内政治辩论

### 🇨🇳 中国视角报道特点
1. **关注重点**：
   - 经济影响（油价波动、贸易影响）
   - 地区安全局势
   - 外交努力和和平呼吁

2. **主要来源**：
   - 中国官方媒体
   - 国际新闻的中文翻译
   - 地区专家分析

3. **报道角度**：
   - 强调和平解决方案
   - 关注对全球经济的影响
   - 呼吁各方克制

### 🇸🇬 新加坡视角报道特点
1. **关注重点**：
   - 航运安全和霍尔木兹海峡状况
   - 东南亚地区经济影响
   - 中立分析和风险评估

2. **主要来源**：
   - 新加坡本地媒体
   - 国际通讯社报道
   - 经济分析机构

3. **报道角度**：
   - 务实的经济影响分析
   - 航运和贸易安全关注
   - 中立、平衡的报道立场

## 综合对比分析

### 共同关注点（三地区一致）
1. **霍尔木兹海峡安全**：都报道了伊朗关闭海峡进行军事演习
2. **平民伤亡**：都关注了学校袭击事件
3. **国际影响**：都分析了冲突对全球的影响

### 主要差异点
1. **报道重点**：
   - 美国：军事行动和政治斗争
   - 中国：经济影响和外交努力
   - 新加坡：航运安全和地区经济

2. **立场偏向**：
   - 美国：更多批评伊朗政府的行动
   - 中国：更强调和平解决和对话
   - 新加坡：相对中立的技术性分析

3. **信息来源**：
   - 美国：大量引用官方军事报告
   - 中国：更多专家分析和官方声明
   - 新加坡：侧重经济数据和航运报告

### 信息缺口识别
1. **军事伤亡数据**：各方报道都不完整
2. **伊朗内部情况**：缺乏第一手报道
3. **长期影响评估**：缺乏系统性的长期分析

## 综合分析结论

### 1. 当前局势评估
- **紧张程度**：非常高，军事对抗持续升级
- **国际化程度**：已经从双边冲突扩展到多国介入
- **人道危机**：平民伤亡日益严重

### 2. 各地区报道的启示
- **美国视角**：显示了西方对军事行动的关注
- **中国视角**：反映了发展中国家对经济稳定的重视
- **新加坡视角**：提供了中小国家的中立风险评估

### 3. 建议关注点
1. **霍尔木兹海峡**：航运安全的关键节点
2. **俄罗斯介入**：可能改变冲突格局的因素
3. **经济连锁反应**：油价、贸易、金融市场影响

## 后续行动建议

### 1. 信息补充
- 增加欧洲（英国、德国）视角分析
- 获取中东本地媒体（阿拉伯语）报道
- 跟踪联合国和国际组织的反应

### 2. 监控重点
- 美国国会后续立法行动
- 中国外交斡旋进展
- 新加坡航运数据变化

### 3. 定期更新
- 每天更新新闻汇总
- 每周进行趋势分析
- 重大事件实时监控

## 技术实现建议

### 1. 自动化脚本
```bash
#!/bin/bash
# 自动化多区域新闻获取脚本

REGIONS=("US:en-US:Iran war latest" "CN:zh-CN:伊朗最新战况" "SG:en-SG:iran war singapore")

for region in "${REGIONS[@]}"; do
  IFS=':' read -r country lang keyword <<< "$region"
  url="https://news.google.com/search?q=${keyword}&hl=${lang}&gl=${country}&ceid=${country}:${lang%-*}"
  echo "获取 ${country} 新闻..."
  # 调用web_fetch工具
done
```

### 2. 分析报告模板
```markdown
# [日期] 伊朗局势多区域新闻分析报告

## 执行摘要
[简要总结核心发现]

## 各地区报道概览
### 美国
- 头条新闻：[...]
- 主要关注点：[...]

### 中国
- 头条新闻：[...]
- 主要关注点：[...]

### 新加坡
- 头条新闻：[...]
- 主要关注点：[...]

## 对比分析
### 共同关注点
1. [...]
2. [...]

### 主要差异
1. [...]
2. [...]

## 综合评估
[整体态势判断]

## 建议
[后续关注点和行动建议]
```

---

**使用提示**：这个分析框架可以扩展到其他重大新闻事件的分析，只需要调整地区配置和搜索关键词即可。