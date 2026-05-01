#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节假日查询 - 查询指定日期的假日安排
API: https://apis.juhe.cn/fapig/calendar/day
依赖: 环境变量 JUHE_HOLIDAY_KEY
"""
import os, sys, json, urllib.request
from pathlib import Path

API_URL = "https://apis.juhe.cn/fapig/calendar/day"
CACHE_DIR = Path.home() / ".hermes" / "holiday-cache"

def get_api_key():
    key = os.environ.get("JUHE_HOLIDAY_KEY", "").strip()
    if not key:
        # 尝试从 .env 加载
        env_path = Path.home() / ".hermes" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("JUHE_HOLIDAY_KEY="):
                    key = line.split("=", 1)[1].strip()
    return key

def query_holiday(date_str, detail=0):
    """
    查询指定日期的假日安排
    date_str: 格式 yyyy-MM-dd，如 "2026-04-16"
    detail: 0=简要 / 1=详细信息
    返回: dict
    """
    key = get_api_key()
    if not key:
        return {"error": "未配置 JUHE_HOLIDAY_KEY"}

    url = f"{API_URL}?key={key}&date={date_str}&detail={detail}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

    if data.get("error_code") != 0:
        return {"error": f"API错误: {data.get('reason', '未知')}", "code": data.get("error_code")}

    return data.get("result", {})

def format_result(result, detail=0):
    """格式化输出"""
    if "error" in result:
        return f"❌ {result['error']}"

    date    = result.get("date", "")
    week    = result.get("week", "")
    status  = result.get("statusDesc", "")
    desc    = result.get("desc", "")
    value   = result.get("value", "")

    # emoji
    if status == "节假日":
        icon = "🎉"
    elif status == "工作日":
        icon = "💼"
    else:
        icon = "🗓"

    lines = []
    lines.append(f"{icon} {date}（{week}）")
    lines.append(f"   类型：{status}")

    if desc and desc != value:
        lines.append(f"   节日：{desc}")
    elif value:
        lines.append(f"   节日：{value}")

    if detail == 1:
        suit = result.get("suit", "")
        avoid = result.get("avoid", "")
        if suit:
            lines.append(f"   宜：{suit[:60]}{'...' if len(suit) > 60 else ''}")
        if avoid:
            lines.append(f"   忌：{avoid[:60]}{'...' if len(avoid) > 60 else ''}")
        lunar = f"{result.get('lunarYear', '')}年{result.get('lunarMonth', '')}月{result.get('lDate', '')}"
        if lunar and lunar != "年":
            lines.append(f"   农历：{lunar}")

    return "\n".join(lines)

def is_workday(date_str):
    """判断是否为工作日，返回 True/False/None(未知)"""
    r = query_holiday(date_str)
    if "error" in r:
        return None
    s = r.get("statusDesc", "")
    if s == "工作日":
        return True
    if s in ("节假日", "周末"):
        return False
    # status 为 null 时，根据 week 判断
    week = r.get("week", "")
    if "六" in week or "日" in week:
        return False
    return True

def next_workday(date_str):
    """返回指定日期之后的下一个工作日"""
    from datetime import datetime, timedelta
    d = datetime.strptime(date_str, "%Y-%m-%d")
    for _ in range(10):
        d += timedelta(days=1)
        nxt = d.strftime("%Y-%m-%d")
        if is_workday(nxt):
            return nxt
    return None

def prev_workday(date_str):
    """返回指定日期之前的上一个工作日（字符串版本）"""
    from datetime import datetime, timedelta
    d = datetime.strptime(date_str, "%Y-%m-%d")
    for _ in range(10):
        d -= timedelta(days=1)
        prev = d.strftime("%Y-%m-%d")
        if is_workday(prev):
            return prev
    return None

def prev_workday_fast(dt):
    """
    快速版本：输入 datetime，返回上一个工作日 datetime。
    使用农历 API 做精确校验（周一至周五正常返回，土豪节/调休由API判断）。
    """
    from datetime import datetime, timedelta
    d = dt - timedelta(days=1)
    # 快速路径：不是周末直接返回
    if d.weekday() < 5:
        return d
    # 周末/疑似调休：用 API 精确校验
    date_str = d.strftime("%Y-%m-%d")
    if is_workday(date_str):
        return d
    # 递归找到真正的上一个工作日
    return prev_workday_fast(d)

# ── 入口 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="查询节假日安排")
    parser.add_argument("date", nargs="?", default=None, help="日期 yyyy-MM-dd，默认今天")
    parser.add_argument("--detail", "-d", action="store_true", help="显示详细信息（宜/忌/农历）")
    parser.add_argument("--next", "-n", action="store_true", help="显示距下一个工作日天数")
    parser.add_argument("--prev", "-p", action="store_true", help="显示上一个工作日")
    args = parser.parse_args()

    if args.date is None:
        from datetime import date
        today = date.today()
        # 周末时自动查下周第一个工作日
        if today.weekday() >= 5:
            target = next_workday(today.strftime("%Y-%m-%d"))
        else:
            target = today.strftime("%Y-%m-%d")
    else:
        target = args.date

    # 校验格式
    import re
    if not re.match(r"\d{4}-\d{2}-\d{2}", target):
        print("❌ 日期格式错误，请使用 yyyy-MM-dd")
        sys.exit(1)

    detail = 1 if args.detail else 0
    result = query_holiday(target, detail=detail)
    print(format_result(result, detail=detail))

    if args.next and "error" not in result:
        is_wd = is_workday(target)
        if is_wd is True:
            print(f"\n📅 {target} 是工作日")
        elif is_wd is False:
            nxt = next_workday(target)
            if nxt:
                from datetime import datetime, timedelta
                days = (datetime.strptime(nxt, "%Y-%m-%d") - datetime.strptime(target, "%Y-%m-%d")).days
                print(f"\n📅 {target} 是休息日，下一个工作日是 {nxt}（{days} 天后）")

    if args.prev and "error" not in result:
        prev = prev_workday(target)
        if prev:
            from datetime import datetime, timedelta
            days = (datetime.strptime(target, "%Y-%m-%d") - datetime.strptime(prev, "%Y-%m-%d")).days
            print(f"\n📅 {target} 的上一个工作日是 {prev}（{days} 天前）")
