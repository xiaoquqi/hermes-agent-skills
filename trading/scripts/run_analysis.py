#!/usr/bin/env python3
"""
完整分析脚本 — TradingAgents
调用 MiniMax LLM + AKShare 数据进行股票分析
"""
import sys
import json
import os

MINIMAX_BASE_URL = "https://zh.agione.co/hyperone/xapi/api"
MINIMAX_API_KEY = "ak-29c67e1cf9f3461190ce639ab469a0c1"

os.environ["OPENAI_API_KEY"] = MINIMAX_API_KEY
os.environ["OPENAI_BASE_URL"] = MINIMAX_BASE_URL

import akshare as ak
from datetime import datetime, timedelta


def get_stock_info(ticker: str) -> dict:
    """获取股票基本信息"""
    ticker = ticker.upper().strip()
    info = {"ticker": ticker, "error": None}

    try:
        if ticker.isdigit() and len(ticker) == 6:
            # A股
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker]
            if not row.empty:
                info["market"] = "A股"
                info["name"] = row.iloc[0].get("名称", ticker)
                info["price"] = row.iloc[0].get("最新价")
                info["change_pct"] = row.iloc[0].get("涨跌幅")
                info["volume"] = row.iloc[0].get("成交量")
                info["turnover"] = row.iloc[0].get("成交额")
                info["amplitude"] = row.iloc[0].get("振幅")  # 振幅
                info["high"] = row.iloc[0].get("最高")
                info["low"] = row.iloc[0].get("最低")
                info["open"] = row.iloc[0].get("今开")
                info["close_prev"] = row.iloc[0].get("昨收")
                info["market_cap"] = row.iloc[0].get("总市值")
                info["float_cap"] = row.iloc[0].get("流通市值")

                # 估值
                try:
                    fin = ak.stock_financial_analysis_indicator(symbol=ticker, start_year="2023")
                    if not fin.empty:
                        latest = fin.iloc[-1]
                        info["pe"] = latest.get("市盈率(动)")
                        info["pb"] = latest.get("市净率")
                        info["ps"] = latest.get("市销率(TTM)")
                        info["roe"] = latest.get("净资产收益率(%)")
                        info["gross_margin"] = latest.get("销售毛利率(%)")
                        info["debt_ratio"] = latest.get("资产负债率(%)")
                except Exception as e:
                    info["fin_error"] = str(e)

            # 近期走势 (日线)
            end = datetime.now().strftime("%Y%m%d")
            start = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
            hist = ak.stock_zh_a_hist(symbol=ticker, start_date=start, end_date=end, adjust="qfq")
            if not hist.empty:
                prices = hist.tail(20)
                info["hist_20d"] = prices["收盘"].tolist()
                info["hist_20d_dates"] = prices["日期"].tolist()
                info["high_20d"] = prices["最高"].max()
                info["low_20d"] = prices["最低"].min()
                info["avg_20d"] = prices["收盘"].mean()

        else:
            # 美股
            df = ak.stock_us_spot_em()
            row = df[df['代码'] == ticker]
            if not row.empty:
                info["market"] = "美股"
                info["name"] = row.iloc[0].get("名称", ticker)
                info["price"] = row.iloc[0].get("最新价")
                info["change_pct"] = row.iloc[0].get("涨跌幅")
                info["volume"] = row.iloc[0].get("成交量")
                info["market_cap"] = row.iloc[0].get("总市值")

            end = datetime.now().strftime("%Y%m%d")
            start = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
            hist = ak.stock_us_hist(symbol=ticker, period="daily",
                                    start_date=start, end_date=end, adjust="qfq")
            if not hist.empty:
                prices = hist.tail(20)
                info["hist_20d"] = prices["收盘"].tolist()
                info["hist_20d_dates"] = prices["日期"].tolist()
                info["high_20d"] = prices["最高"].max()
                info["low_20d"] = prices["最低"].min()
                info["avg_20d"] = prices["收盘"].mean()

    except Exception as e:
        info["error"] = str(e)

    return info


def build_prompt(ticker: str, info: dict) -> str:
    """构建分析提示词"""
    price = info.get("price", 0)
    change = info.get("change_pct", 0)
    pe = info.get("pe", "N/A")
    pb = info.get("pb", "N/A")
    roe = info.get("roe", "N/A")
    high20 = info.get("high_20d", 0)
    low20 = info.get("low_20d", 0)
    avg20 = info.get("avg_20d", 0)
    market = info.get("market", "未知")

    # 计算技术位置
    tech_pos = "高位" if price and high20 and (price / high20 > 0.95) else \
               "低位" if price and low20 and (price / low20 < 1.05) else "中部"

    prompt = f"""
## 股票分析报告 — {ticker} ({info.get('name', ticker)})

### 市场 & 价格
- 市场: {market}
- 当前价: {price} ({change:+.2f}%)
- 今日开盘: {info.get('open', 'N/A')} | 昨收: {info.get('close_prev', 'N/A')}
- 今日最高: {info.get('high', 'N/A')} | 最低: {info.get('low', 'N/A')}
- 成交量: {info.get('volume', 'N/A')} | 成交额: {info.get('turnover', 'N/A')}

### 估值指标
- 市盈率 P/E: {pe}
- 市净率 P/B: {pb}
- ROE: {roe}%
- 毛利率: {info.get('gross_margin', 'N/A')}%
- 资产负债率: {info.get('debt_ratio', 'N/A')}%
- 总市值: {info.get('market_cap', 'N/A')}

### 技术分析 (近20日)
- 20日最高: {high20:.2f} | 20日最低: {low20:.2f} | 20日均值: {avg20:.2f}
- 当前技术位置: {tech_pos} (现价/{high20:.2f} = {price/high20*100:.1f}%)

### 风险提示检查
1. 涨幅检查: {"⚠️ 今日涨幅超过15%" if abs(change) > 15 else "✅ 正常"}
2. 高位风险: {"⚠️ 接近20日高点，注意回调" if price and high20 and (price/high20 > 0.95) else "✅ 距离高点有空间"}
3. PE估值: {"⚠️ 市盈率偏高(>50)" if isinstance(pe, (int, float)) and pe > 50 else "✅ 估值合理" if isinstance(pe, (int, float)) else "⚠️ 亏损股无PE"}

### 仓位建议
- 建议止损价: {round(price * 0.92, 2) if price else 'N/A'} (现价×0.92)
- 止盈线1: {round(price * 1.20, 2) if price else 'N/A'} (现价×1.20)
- 止盈线2: {round(price * 1.30, 2) if price else 'N/A'} (现价×1.30)

---

请给出综合分析:
1. 基本面: 估值是否合理？财务状况如何？
2. 技术面: 当前趋势如何？支撑/压力位在哪？
3. 操作建议: 买入/持有/卖出？仓位控制在多少？
4. 风险评估: 主要风险点是什么？

请用中文回复，语气专业但易懂。
"""
    return prompt


def call_llm(prompt: str) -> str:
    """调用 MiniMax LLM"""
    from openai import OpenAI
    client = OpenAI(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)

    response = client.chat.completions.create(
        model="MiniMax-Text-01",
        messages=[
            {"role": "system", "content": "你是一位专业的股票分析师，擅长基本面和技术面分析，给出客观、专业的投资建议。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"

    print(f"\n🔍 正在分析 {ticker}...")
    print("=" * 55)

    info = get_stock_info(ticker)

    if info.get("error"):
        print(f"❌ 获取数据失败: {info['error']}")
        sys.exit(1)

    # 构建提示词
    prompt = build_prompt(ticker, info)

    # 调用LLM分析
    try:
        analysis = call_llm(prompt)
        print(analysis)
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        print("\n--- 本地数据分析 ---")
        print(f"  市场: {info.get('market')}")
        print(f"  名称: {info.get('name')}")
        print(f"  价格: {info.get('price')} ({info.get('change_pct', 0):+.2f}%)")
        print(f"  市盈率: {info.get('pe')}")
        print(f"  市净率: {info.get('pb')}")
        print(f"  ROE: {info.get('roe')}")
        print(f"  20日高点: {info.get('high_20d', 0):.2f}")
        print(f"  20日低点: {info.get('low_20d', 0):.2f}")
        print(f"  20日均价: {info.get('avg_20d', 0):.2f}")

    print("=" * 55)
