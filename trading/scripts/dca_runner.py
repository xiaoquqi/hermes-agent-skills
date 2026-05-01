#!/usr/bin/env python3
"""
定投策略脚本 (DCA - Dollar Cost Averaging)
设置定期定额投资计划，自动提醒买入
"""
import sys
import json
import os
from datetime import datetime
from pathlib import Path

MINIMAX_BASE_URL = "https://zh.agione.co/hyperone/xapi/api"
MINIMAX_API_KEY = "ak-29c67e1cf9f3461190ce639ab469a0c1"

os.environ["OPENAI_API_KEY"] = MINIMAX_API_KEY
os.environ["OPENAI_BASE_URL"] = MINIMAX_BASE_URL

import akshare as ak

DCA_DB = Path.home() / ".hermes" / "skills" / "trading" / "dca_portfolio.json"


def load_portfolio() -> dict:
    """加载定投组合"""
    if DCA_DB.exists():
        with open(DCA_DB) as f:
            return json.load(f)
    return {"plans": [], "total_invested": 0, "total_value": 0}


def save_portfolio(portfolio: dict):
    """保存定投组合"""
    DCA_DB.parent.mkdir(parents=True, exist_ok=True)
    with open(DCA_DB, "w") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)


def add_dca_plan(ticker: str, amount: float, frequency: str = "每月",
                 stop_loss_pct: float = -0.08, take_profit_pct: float = 0.25) -> dict:
    """添加定投计划"""
    ticker = ticker.upper().strip()
    portfolio = load_portfolio()

    # 检查是否已存在
    for plan in portfolio["plans"]:
        if plan["ticker"] == ticker:
            return {"error": f"❌ {ticker} 已在定投组合中", "plan": plan}

    # 获取当前价格
    price = get_current_price(ticker)
    shares = amount / price if price > 0 else 0

    plan = {
        "ticker": ticker,
        "amount": amount,
        "frequency": frequency,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct,
        "created_at": datetime.now().isoformat(),
        "total_invested": amount,
        "total_shares": shares,
        "avg_cost": price,
        "last_invest_date": datetime.now().strftime("%Y-%m-%d"),
        "status": "active"
    }

    portfolio["plans"].append(plan)
    save_portfolio(portfolio)

    return {"success": True, "plan": plan, "price": price}


def get_current_price(ticker: str) -> float:
    """获取当前价格"""
    ticker = ticker.upper().strip()
    try:
        if ticker.isdigit() and len(ticker) == 6:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == ticker]
            if not row.empty:
                return float(row.iloc[0].get("最新价", 0))
        else:
            df = ak.stock_us_spot_em()
            row = df[df['代码'] == ticker]
            if not row.empty:
                return float(row.iloc[0].get("最新价", 0))
    except Exception:
        pass
    return 0.0


def check_dca_signals() -> list:
    """检查定投信号"""
    portfolio = load_portfolio()
    signals = []
    today = datetime.now().strftime("%Y-%m-%d")

    for plan in portfolio["plans"]:
        if plan["status"] != "active":
            continue

        ticker = plan["ticker"]
        price = get_current_price(ticker)
        if not price:
            continue

        # 计算当前盈亏
        current_value = price * plan["total_shares"]
        invested = plan["total_invested"]
        profit_loss_pct = (current_value - invested) / invested if invested > 0 else 0
        profit_loss = current_value - invested

        # 检查是否触发止损/止盈
        if profit_loss_pct <= plan["stop_loss_pct"]:
            signals.append({
                "type": "🚨 止损提醒",
                "ticker": ticker,
                "message": f"{ticker} 亏损 {profit_loss_pct*100:.1f}%，触及止损线 {plan['stop_loss_pct']*100:.0f}%"
            })
        elif profit_loss_pct >= plan["take_profit_pct"]:
            signals.append({
                "type": "🎯 止盈提醒",
                "ticker": ticker,
                "message": f"{ticker} 盈利 {profit_loss_pct*100:.1f}%，达到止盈线 {plan['take_profit_pct']*100:.0f}%"
            })

        # 检查是否到定投日期
        last_date = plan["last_invest_date"]
        should_invest = False

        if plan["frequency"] == "每周" and today >= last_date:
            should_invest = True
        elif plan["frequency"] == "每月":
            # 简单检查：每月1号
            if today.endswith("-01"):
                should_invest = True

        if should_invest and price > 0:
            shares_to_buy = int(plan["amount"] / price)
            if shares_to_buy > 0:
                signals.append({
                    "type": "💰 定投提醒",
                    "ticker": ticker,
                    "message": f"今日定投 {ticker}，买入 ~{shares_to_buy} 股，当前价 ¥{price}"
                })

        # 更新现值
        plan["current_price"] = price
        plan["current_value"] = current_value
        plan["profit_loss_pct"] = profit_loss_pct
        plan["profit_loss"] = profit_loss

    save_portfolio(portfolio)
    return signals


def list_portfolio() -> dict:
    """列出定投组合"""
    portfolio = load_portfolio()
    signals = check_dca_signals()

    return {"portfolio": portfolio, "signals": signals}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "add":
        ticker = sys.argv[2] if len(sys.argv) > 2 else "NVDA"
        amount = float(sys.argv[3]) if len(sys.argv) > 3 else 1000
        freq = sys.argv[4] if len(sys.argv) > 4 else "每月"

        result = add_dca_plan(ticker, amount, freq)
        if result.get("success"):
            p = result["plan"]
            print(f"\n✅ 定投计划已创建 — {p['ticker']}")
            print("=" * 45)
            print(f"  标的: {p['ticker']}")
            print(f"  金额: ¥{p['amount']:,.0f}/{p['frequency']}")
            print(f"  买入价: ¥{result['price']}")
            print(f"  止损线: {p['stop_loss_pct']*100:.0f}%")
            print(f"  止盈线: {p['take_profit_pct']*100:.0f}%")
            print("=" * 45)
        else:
            print(result.get("error"))

    elif cmd == "signals":
        signals = check_dca_signals()
        if not signals:
            print("\n📊 无新的定投信号")
        else:
            print(f"\n📊 定投信号 ({len(signals)} 条)")
            print("=" * 50)
            for s in signals:
                print(f"  {s['type']} {s['ticker']}")
                print(f"    {s['message']}")
            print("=" * 50)

    else:  # status
        result = list_portfolio()
        portfolio = result["portfolio"]
        signals = result["signals"]

        if not portfolio["plans"]:
            print("\n📊 定投组合为空，使用以下命令添加:")
            print("  python dca_runner.py add NVDA 1000 每月")
        else:
            print(f"\n📊 定投组合 — 共 {len(portfolio['plans'])} 个计划")
            print("=" * 55)

            total_invested = 0
            total_value = 0

            for p in portfolio["plans"]:
                price = p.get("current_price", 0)
                val = p.get("current_value", price * p["total_shares"])
                invested = p["total_invested"]
                pl = val - invested
                pl_pct = (pl / invested * 100) if invested > 0 else 0

                total_invested += invested
                total_value += val

                emoji = "🟢" if pl >= 0 else "🔴"
                print(f"\n  {emoji} {p['ticker']} ({p['frequency']})")
                print(f"     投入: ¥{invested:,.0f} | 现值: ¥{val:,.0f}")
                print(f"     盈亏: {pl:+,.0f} ({pl_pct:+.1f}%)")
                print(f"     止损: {p['stop_loss_pct']*100:.0f}% | 止盈: {p['take_profit_pct']*100:.0f}%")

            total_pl = total_value - total_invested
            total_pl_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0
            print("-" * 55)
            print(f"  💰 合计投入: ¥{total_invested:,.0f}")
            print(f"  💰 合计现值: ¥{total_value:,.0f}")
            print(f"  📈 总盈亏: {total_pl:+,.0f} ({total_pl_pct:+.1f}%)")

        if signals:
            print("\n" + "=" * 55)
            print("  📋 今日信号:")
            for s in signals:
                print(f"    {s['type']} {s['message']}")

        print("=" * 55)
        print("\n  命令:")
        print("    python dca_runner.py add NVDA 1000 每月  — 添加计划")
        print("    python dca_runner.py signals              — 检查信号")
