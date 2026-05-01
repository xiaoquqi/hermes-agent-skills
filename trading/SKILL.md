---
name: trading
description: 量化交易技能集 — Herme+TradingAgents 自动化交易系统。支持A股/港股/美股分析、风险提示、仓位管理和定投策略。
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [量化交易, TradingAgents, AKShare, 股票分析, 自动化交易, A股, 港股, 美股]
    related_skills: [trading-risk-alert, trading-position-manager, trading-dca]
---

# Trading Skills — 量化交易技能集

本技能集包含三个子技能，协同工作：

## 子技能

### 1. `trading-risk-alert` — 风险提示
当 TradingAgents 建议买入时自动触发。检查：
- 单只股票仓位是否超过上限（稳健型 20%）
- 近期涨幅是否超过 20%（警惕回调）
- 是否设置止损线（建议 -8%）
- 市场整体估值水平

### 2. `trading-position-manager` — 仓位管理
根据风险偏好计算建议仓位：
- 保守型：单只 ≤10%，总仓位 50-70%
- 稳健型：单只 ≤20%，总仓位 70-90%
- 激进型：单只 ≤30%，总仓位 90-100%

### 3. `trading-dca` — 定投策略
设置定投计划：
- 标的：股票/基金代码
- 金额：每次投入金额
- 频率：每周/每月
- 止盈线：20-30%
- 止损线：-8% 到 -10%

## 触发方式

```
/analyze NVDA
/analyze 000001
/riskanalyze NVDA
/dcastatus
```

## 核心脚本

脚本路径: `~/.hermes/skills/trading/scripts/`

- `run_analysis.py <ticker>` — 运行完整分析
- `risk_check.py <ticker> <price> <change_pct>` — 风险检查
- `position_calc.py <risk_preference> <ticker>` — 仓位计算

## 数据源

- **MiniMax LLM**: 配置于 `~/.hermes/config.yaml`
- **AKShare**: 无需 API Key，支持 A股/港股/美股

## 环境

```bash
conda activate trading
cd ~/trading-system
python quant_system.py <股票代码>
```
