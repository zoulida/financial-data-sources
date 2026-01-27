from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from typing import Optional

import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)  # 将当前目录加入 sys.path，方便相对导入

from 涨停股票 import fetch_limit_up_pool


def _previous_trade_date(date: dt.date) -> dt.date:
    """推算上一个交易日（仅跳过周末）"""
    d = date - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def fetch_two_consecutive_limit_up(target_date: Optional[dt.date] = None) -> pd.DataFrame:
    """根据当日涨停池，向前逐日相交计算连板次数，直到没有连板为止。返回含 _连板 列。"""
    base_date = target_date or dt.date.today()
    try:
        today_pool = fetch_limit_up_pool(base_date)
    except ValueError:
        return pd.DataFrame()

    if today_pool is None or today_pool.empty or "代码" not in today_pool.columns:
        return pd.DataFrame()

    # 当日真实交易日
    if "日期" in today_pool.columns and not today_pool.empty:
        resolved_str = str(today_pool["日期"].iloc[0])
        resolved_date = dt.datetime.strptime(resolved_str, "%Y%m%d").date()
    else:
        resolved_date = base_date

    codes_today = set(today_pool["代码"].astype(str))
    if not codes_today:
        return pd.DataFrame()

    # 逐日向前相交，构建梯队
    tiers: dict[int, set[str]] = {}
    current_set = set(codes_today)
    k = 1
    cursor_date = resolved_date
    while True:
        prev_date = _previous_trade_date(cursor_date)
        try:
            prev_pool = fetch_limit_up_pool(prev_date)
        except ValueError:
            tiers[k] = set(current_set)
            break
        if prev_pool is None or prev_pool.empty or "代码" not in prev_pool.columns:
            tiers[k] = set(current_set)
            break
        prev_set = set(prev_pool["代码"].astype(str))
        next_set = current_set & prev_set
        exact_k = current_set - next_set
        if exact_k:
            tiers[k] = exact_k
        current_set = next_set
        cursor_date = prev_date
        if not current_set:
            break
        k += 1

    # 汇总映射并回填到当日明细
    code_to_k: dict[str, int] = {}
    for level, codes in tiers.items():
        for c in codes:
            code_to_k[c] = max(code_to_k.get(c, 0), level)
    result = today_pool.copy()
    result["_连板"] = result["代码"].astype(str).map(code_to_k).fillna(0).astype(int)
    result = result[result["_连板"] >= 1].copy()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="YYYY-MM-DD，可选，不填则默认今天")
    args = parser.parse_args()

    date_obj = dt.date.fromisoformat(args.date) if args.date else None
    df = fetch_two_consecutive_limit_up(date_obj)

    pd.set_option("display.max_columns", None)

    if df is None or df.empty:
        print("未获取到当日涨停池数据，或无有效连板记录。")
        raise SystemExit(0)

    # 选择展示列
    display_columns = [
        "日期",
        "代码",
        "名称",
        "最新价",
        "涨跌幅",
        "成交额",
        "流通市值",
        "首次涨停时间",
        "最后涨停时间",
        "连续涨停天数",
    ]
    existing_columns = [c for c in display_columns if c in df.columns]

    # 按连板次数分组打印（高到低）
    for k in sorted(df["_连板"].unique(), reverse=True):
        sub = df[df["_连板"] == k].copy()
        print(f"\n===== 连板次数 = {k}，数量 = {len(sub)} =====")
        to_show = sub[existing_columns] if existing_columns else sub
        print(to_show)
