"""流通股本变化因子：3 个（增发/减持探测）。"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ._helpers import safe_div


def get_factors(panel: dict[str, pd.DataFrame], ctx: dict[str, Any]) -> dict[str, pd.DataFrame]:
    close = panel["close"]
    fs = panel.get("float_shares", pd.DataFrame()).reindex_like(close)
    out: dict[str, pd.DataFrame] = {}

    if fs.empty or fs.notna().sum().sum() == 0:
        return out

    out["float_shares_chg_20"] = safe_div(fs - fs.shift(20), fs.shift(20))
    out["float_shares_chg_60"] = safe_div(fs - fs.shift(60), fs.shift(60))

    # zigzag：60 日内是否出现单日跳变（变化率绝对值 > 5%）
    daily_chg = fs.pct_change(fill_method=None).abs()
    out["float_shares_zigzag"] = (daily_chg > 0.05).astype(float).rolling(60).sum()

    return out
