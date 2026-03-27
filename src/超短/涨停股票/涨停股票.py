from __future__ import annotations

import datetime as dt
from typing import Optional

import akshare as ak
import pandas as pd


def _resolve_trade_date(target: Optional[dt.date] = None) -> str:
    """生成 AKShare 所需的交易日（YYYYMMDD），遇周末顺延至上一交易日。"""
    current = target or dt.date.today()
    while current.weekday() >= 5:
        current -= dt.timedelta(days=1)
    return current.strftime("%Y%m%d")


def fetch_limit_up_pool(target_date: Optional[dt.date] = None) -> pd.DataFrame:
    """
    调用 AKShare stock_zt_pool_em 获取涨停股池。
    如果接口返回为空，抛出 ValueError 方便上层处理。
    """
    date_str = _resolve_trade_date(target_date)
    data = ak.stock_zt_pool_em(date=date_str)
    if data is None or data.empty:
        raise ValueError(f"stock_zt_pool_em 在 {date_str} 返回空数据")
    data["日期"] = date_str
    return data


if __name__ == "__main__":
    df = fetch_limit_up_pool()
    preferred_columns = [
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

    existing_columns = [col for col in preferred_columns if col in df.columns]
    missing_columns = sorted(set(preferred_columns) - set(existing_columns))
    if missing_columns:
        print(f"以下列暂不可用，将自动忽略：{', '.join(missing_columns)}")

    df = df[existing_columns] if existing_columns else df
    pd.set_option("display.max_columns", None)
    print(df.head())

