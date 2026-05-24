"""反转因子：5 个。"""
from __future__ import annotations

from typing import Any

import pandas as pd


def get_factors(panel: dict[str, pd.DataFrame], ctx: dict[str, Any]) -> dict[str, pd.DataFrame]:
    close = panel["close"]
    open_ = panel.get("open", pd.DataFrame()).reindex_like(close)
    out: dict[str, pd.DataFrame] = {}

    out["ret_1d"] = close.pct_change(1, fill_method=None)
    out["ret_5d"] = close.pct_change(5, fill_method=None)
    out["ret_10d"] = close.pct_change(10, fill_method=None)

    # 隔夜收益：今日开盘 / 昨日收盘 - 1
    if not open_.empty:
        out["overnight_ret"] = open_ / close.shift(1) - 1.0
        out["intraday_ret"] = close / open_ - 1.0

    return out
