---
name: fund-analysis-cn
description: Analyze Chinese A-share mutual funds using EastMoney/akshare data — real-time quotes, historical NAV, and expert risk/return metrics.
category: data-science
---

# Fund Analysis - Chinese A-Share Funds (Expert System)

## When to Use
Analyzing Chinese mutual funds (A股基金) — query real-time quotes, historical performance, and produce expert-level analysis with risk metrics.

## Data Sources

### 1. Real-Time Quote (估值)
```bash
curl -s "https://fundgz.1234567.com.cn/js/003984.js?rt=$(date +%s)000" \
  -H "Referer: https://fund.eastmoney.com/"
```
Returns: fundcode, name, NAV date, unit NAV, estimated NAV, daily change %, estimated time.

### 2. Historical NAV Data (净值历史)
```python
import akshare as ak
import pandas as pd
import numpy as np

df = ak.fund_open_fund_info_em(symbol="003984")
df.columns = ['date', 'nav', 'daily_return']
df['date'] = pd.to_datetime(df['date'])
df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
df['daily_return'] = pd.to_numeric(df['daily_return'], errors='coerce')
df = df.sort_values('date').reset_index(drop=True)
```

> **IMPORTANT**: Yahoo Finance (yfinance) does NOT reliably cover Chinese A-share funds. Do NOT waste time with Yahoo Finance for CN funds. EastMoney via akshare is the reliable source.

## Expert Analysis Metrics

Calculate and report the following:

| Metric | Formula | Good | Bad |
|--------|---------|------|-----|
| 年化收益率 | ((end_nav/start_nav)^(365/days)-1)*100 | >12% | <8% |
| 年化波动率 | daily_ret.std() * sqrt(252) | <20% | >30% |
| 最大回撤 | (nav - rolling_max)/rolling_max * 100, take min | >-20% | <-40% |
| 夏普比率 | (annual_ret - rf) / annual_vol | >1.0 | <0.5 |
| 卡玛比率 | annual_ret / abs(max_drawdown) | >0.5 | <0.2 |
| 日胜率 | (daily_ret > 0).sum() / len | >55% | <48% |
| 月胜率 | positive_months / total_months | >55% | <48% |

## Expert Report Template

```
【收益能力】
  成立至今总收益:  {total_return:+.2f}%
  年化收益率:      {annualized_return:+.2f}%

【风险指标】
  年化波动率:      {annual_vol:.2f}%
  最大回撤:        {max_dd:.2f}%
  夏普比率:        {sharpe:.3f}
  卡玛比率:        {calmar:.3f}

【胜率统计】
  日胜率:          {win_rate:.1f}%
  月胜率:          {monthly_wr:.1f}%

【年度收益】
  (list each year)

【极端收益】
  单日涨幅最大:    {daily_ret.max():+.2f}%
  单日跌幅最大:    {daily_ret.min():+.2f}%
```

## 获取基金基本信息（经理、规模、类型）
```python
info = ak.fund_individual_basic_info_xq(symbol="003984")
# 返回 DataFrame: item/value 列，包含基金经理、成立时间、最新规模、基金类型等
```
> akshare 的 `fund_manager_em()` 和 `fund_scale_change_em()` 不支持单基金参数，直接用雪球接口。

## Pitfalls
- Fund codes like `003984` may be `.SZ` or `.SS` on Yahoo Finance — **do not use Yahoo Finance**
- EastMoney's direct API endpoints (`push2his.eastmoney.com`) return RC=100 for funds — use akshare instead
- Daily return from akshare may be percentage string `"3.87"` — cast to float before calculations
- Max drawdown date: use `drawdown.idxmin()` to find approximate date index
- `fund_value_estimation_em(symbol="003984")` 对部分基金报错（如 `KeyError: '003984'`），估值直接用 fundgz.1234567.com.cn 接口更稳定
- `fund_etf_hist_em` 仅适用于 ETF，对普通基金返回空 DataFrame，不要误用
