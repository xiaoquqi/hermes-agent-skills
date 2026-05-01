#!/usr/bin/env python3
"""
仓位管理脚本
根据风险偏好计算建议仓位
"""
import sys
import json

MINIMAX_BASE_URL = "https://zh.agione.co/hyperone/xapi/api"
MINIMAX_API_KEY = "ak-29c67e1cf9f3461190ce639ab469a0c1"

import os
os.environ["OPENAI_API_KEY"] = MINIMAX_API_KEY
os.environ["OPENAI_BASE_URL"] = MINIMAX_BASE_URL

import akshare as ak


def get_account_balance() -> float:
    """获取账户余额（模拟）"""
    # 实际使用时对接券商API
    return 100000.0  # 默认10万模拟资金


def get_current_position(ticker: str) -> dict:
    """获取当前持仓"""
    # 实际使用时对接持仓API
    # 这里返回模拟数据
    return {
        "shares": 0,
        "avg_cost": 0.0,
        "market_value": 0.0,
        "profit_loss": 0.0,
        "profit_loss_pct": 0.0
    }


def calculate_position(ticker: str, risk_preference: str = "稳健",
                       total_value: float = None, price: float = None) -> dict:
    """
    计算建议仓位
    风险偏好:
      - 保守型: 单只 ≤10%, 总仓位 50-70%
      - 稳健型: 单只 ≤20%, 总仓位 70-90%
      - 激进型: 单只 ≤30%, 总仓位 90-100%
    """
    limits = {
        "保守": {"single": 0.10, "total_min": 0.50, "total_max": 0.70},
        "稳健": {"single": 0.20, "total_min": 0.70, "total_max": 0.90},
        "激进": {"single": 0.30, "total_min": 0.90, "total_max": 1.00}
    }

    if total_value is None:
        total_value = get_account_balance()

    limit = limits.get(risk_preference, limits["稳健"])

    # 获取当前价格
    if price is None:
        try:
            ticker_clean = ticker.upper().strip()
            if ticker_clean.isdigit() and len(ticker_clean) == 6:
                df = ak.stock_zh_a_spot_em()
                row = df[df['代码'] == ticker_clean]
                if not row.empty:
                    price = float(row.iloc[0].get("最新价", 0))
            else:
                df = ak.stock_us_spot_em()
                row = df[df['代码'] == ticker_clean]
                if not row.empty:
                    price = float(row.iloc[0].get("最新价", 0))
        except Exception:
            price = 0.0

    # 计算最大仓位金额
    max_single_value = total_value * limit["single"]
    max_shares = int(max_single_value / price) if price > 0 else 0

    # 计算总仓位建议
    recommended_total = int(total_value * limit["total_max"])
    min_total = int(total_value * limit["total_min"])

    return {
        "ticker": ticker,
        "risk_preference": risk_preference,
        "account_value": total_value,
        "current_price": price,
        "max_single_position_pct": f"{limit['single']*100:.0f}%",
        "max_single_amount": max_single_value,
        "max_shares": max_shares,
        "total_position_range": f"{min_total} ~ {recommended_total}",
        "limit": limit
    }


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    risk_pref = sys.argv[2] if len(sys.argv) > 2 else "稳健"

    result = calculate_position(ticker, risk_pref)

    print(f"\n📊 仓位管理报告 — {ticker}")
    print("=" * 50)
    print(f"  风险偏好: {result['risk_preference']}")
    print(f"  账户总值: ¥{result['account_value']:,.2f}")
    print(f"  当前价格: {result['current_price']}")
    print("-" * 50)
    print(f"  单只仓位上限: {result['max_single_position_pct']}")
    print(f"  单只金额上限: ¥{result['max_single_amount']:,.2f}")
    print(f"  建议买入股数: {result['max_shares']} 股")
    print("-" * 50)
    print(f"  总仓位建议范围: {result['total_position_range']}")
    print("=" * 50)
