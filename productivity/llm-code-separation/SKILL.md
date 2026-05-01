---
name: llm-code-separation
description: 开发原则：LLM 负责综合/判断，代码只做确定性数据采集。拿到需求先判断边界。
---

# LLM / Code 职责划分原则

## 核心原则

| 任务类型 | 处理方式 |
|---------|---------|
| 数据采集（HTTP/文件 IO、格式稳定解析） | 代码 |
| 理解意图、总结判断、多变规则 | LLM |
| Workflow 调度 | LongChain 框架 |

## 判断流程

拿到任何新需求时，先问：
1. 这里有没有"易变的逻辑"（规则、判断、综合）？→ LLM
2. 是不是"稳定的重复动作"（抓数据、格式化、读写文件）？→ 代码
3. 需要重试/缓存/断点续跑吗？→ LongChain

## 常见错误

- ❌ 用代码写复杂的 if-else 规则来判断"这条 issue 算什么类型" → 应该 LLM
- ❌ 用代码解析 LLM 输出的结构化内容再做二次综合 → 应该直接让 LLM 出最终结果
- ❌ 所有东西都塞进一个脚本 → 应该拆分原子技能 + 编排技能

## 分块策略

- 用 tiktoken 动态计算，批量上限 8000 tokens（给输出留余量）
- 不要撑满 200K 上下文，无法输出就没意义了

## LongChain 组件

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=60))
def llm_call(...):
    ...
```

## 目录规范

- 原子技能：各功能目录（devops/、media/、productivity/）
- 编排技能：`orchestration/`
- 禁止：跨功能混写 / 编排技能里写实现细节
