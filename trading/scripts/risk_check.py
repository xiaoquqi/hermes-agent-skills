#!/usr/bin/env python3
"""
风险提示脚本
触发条件: TradingAgents 建议买入时自动调用
"""
import sys
import json

MINIMAX_BASE_URL = "https://zh.agione.co/hyperone/xapi/api"
MINIMAX_API_KEY = "ak-29c67e1cf9f3461190ce639ab469a0c1"

import os
os.environ["OPENAI_API_KEY"] = MINIMAX_API_KEY
os.environ["OPENAI_BASE_URL"] = MINIMAX_BASE_URL

import akshare as ak
from datetime import datetime


def get_spot_data(ticker: str) -> dict:
    """获取实时行情"""
    ticker = ticker.upper().strip()
    try:
        if ticker.isdigit() and len(ticker) == 6:
            # A股
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker]
            if not row.empty:
                return {
                    "ticker": ticker,
                    "name": row.iloc[0].get("名称", ticker),
                    "price": row.iloc[0].get("最新价"),
                    "change": row.iloc[0].get("涨跌幅"),
                    "volume": row.iloc[0].get("成交量"),
                    "market_cap": row.iloc[0].get("总市值"),
                    "market": "A股"
                }
        elif ticker.endswith(".HK") or (ticker.isdigit() and len(ticker) == 5):
            # 港股
            code = ticker if ticker.endswith(".HK") else f"{int(ticker):05d}.HK"
            df = ak.stock_hk_spot_em()
            row = df[df['代码'] == code]
            if not row.empty:
                return {
                    "ticker": code,
                    "name": row.iloc[0].get("名称", ticker),
                    "price": row.iloc[0].get("最新价"),
                    "change": row.iloc[0].get("涨跌幅"),
                    "market": "港股"
                }
        else:
            # 美股
            df = ak.stock_us_spot_em()
            row = df[df['代码'] == ticker]
            if not row.empty:
                return {
                    "ticker": ticker,
                    "name": row.iloc[0].get("名称", ticker),
                    "price": row.iloc[0].get("最新价"),
                    "change": row.iloc[0].get("涨跌幅"),
                    "market": "美股"
                }
    except Exception as e:
        return {"error": str(e)}
    return {}


def get_fundamentals(ticker: str) -> dict:
    """获取基本面数据"""
    import akshare as ak
    ticker = ticker.upper().strip()
    fundamentals = {}

    try:
        if ticker.isdigit() and len(ticker) == 6:
            # A股基本面
            try:
                fin = ak.stock_financial_analysis_indicator(symbol=ticker, start_year="2023")
                if not fin.empty:
                    latest = fin.iloc[-1]
                    fundamentals["roe"] = latest.get("净资产收益率(%)")
                    fundamentals["pe"] = latest.get("市盈率(动)")
                    fundamentals["pb"] = latest.get("市净率")
                    fundamentals["gross_margin"] = latest.get("销售毛利率(%)")
                    fundamentals["debt_ratio"] = latest.get("资产负债率(%)")
            except Exception:
                pass
        else:
            # 美股历史数据
            try:
                hist = ak.stock_us_hist(symbol=ticker, period="daily",
                                        start_date="20230101",
                                        end_date=datetime.now().strftime("%Y%m%d"),
                                        adjust="qfq")
                if not hist.empty:
                    fundamentals["price"] = hist.iloc[-1].get("收盘")
            except Exception:
                pass
    except Exception as e:
        fundamentals["error"] = str(e)

    return fundamentals


def risk_check(ticker: str, risk_preference: str = "稳健") -> dict:
    """执行风险检查"""
    spot = get_spot_data(ticker)
    fundamentals = get_fundamentals(ticker)

    warnings = []
    price = spot.get("price", 0)
    change_pct = spot.get("change", 0)

    prefs = {"保守": 10, "稳健": 20, "激进": 30}.get(risk_preference, 20)

    # 涨幅检查
    if abs(change_pct) > 15:
        warnings.append(f"今日涨幅 {change_pct:.1f}%，注意回调风险")
    if change_pct > 20:
        warnings.append("⚠️ 涨幅超过 20%，强烈建议设置止损线")

    # 止损/止盈
    stop_loss = round(price * 0.92, 2) if price else 0
    take_profit_1 = round(price * 1.20, 2) if price else 0
    take_profit_2 = round(price * 1.30, 2) if price else 0

    # 基本面风险
    if fundamentals.get("pe"):
        try:
            pe = float(fundamentals.get("pe", 0))
            if pe > 50:
                warnings.append(f"⚠️ 市盈率 {pe}，估值偏高")
            elif pe < 0:
                warnings.append(f"⚠️ 市盈率 {pe}，盈利为负")
        except (ValueError, TypeError):
            pass

    if fundamentals.get("debt_ratio"):
        try:
            debt = float(fundamentals.get("debt_ratio", 0))
            if debt > 80:
                warnings.append(f"⚠️ 资产负债率 {debt}%，财务风险偏高")
        except (ValueError, TypeError):
            pass

    return {
        "ticker": ticker,
        "market": spot.get("market", "unknown"),
        "price": price,
        "change_pct": change_pct,
        "warnings": warnings,
        "stop_loss": stop_loss,
        "take_profit_1": take_profit_1,
        "take_profit_2": take_profit_2,
        "risk_level": "🔴 高" if len(warnings) >= 2 else "🟡 中" if warnings else "🟢 低",
        "fundamentals": {k: v for k, v in fundamentals.items() if k != "error"}
    }


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    risk_pref = sys.argv[2] if len(sys.argv) > 2 else "稳健"

    result = risk_check(ticker, risk_pref)

    print(f"\n🔍 风险检查报告 — {ticker}")
    print("=" * 45)
    print(f"  市场: {result['market']}")
    print(f"  价格: {result['price']}  ({result['change_pct']:+.2f}%)" if result['price'] else "  价格: N/A")
    print(f"  风险等级: {result['risk_level']}")
    print("-" * 45)

    if result["warnings"]:
        print("  ⚠️ 风险提示:")
        for w in result["warnings"]:
            print(f"    • {w}")
        print()
        print(f"  🛡️ 止损价: {result['stop_loss']}")
        print(f"  🎯 止盈线1: {result['take_profit_1']} (+20%)")
        print(f"  🎯 止盈线2: {result['take_profit_2']} (+30%)")
    else:
        print("  ✅ 无明显风险提示")

    if result.get("fundamentals"):
        print("-" * 45)
        print("  📋 基本面:")
        for k, v in result["fundamentals"].items():
            if v is not None:
                print(f"    {k.upper()}: {v}")

    print("=" * 45)
