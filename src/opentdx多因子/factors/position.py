"""高低位 / 相对位置因子：8 个。"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ._helpers import safe_div


def get_factors(panel: dict[str, pd.DataFrame], ctx: dict[str, Any]) -> dict[str, pd.DataFrame]:
    close = panel["close"]
    high = panel.get("high", pd.DataFrame()).reindex_like(close).fillna(close)
    low = panel.get("low", pd.DataFrame()).reindex_like(close).fillna(close)
    out: dict[str, pd.DataFrame] = {}

    for w in (60, 120, 250):
        rh = high.rolling(w).max()
        rl = low.rolling(w).min()
        out[f"hl_ratio_{w}"] = safe_div(close - rl, rh - rl)

    high_20 = high.rolling(20).max()
    low_20 = low.rolling(20).min()
    out["dist_to_high_20"] = 1.0 - safe_div(close, high_20)
    out["dist_to_low_20"] = safe_div(close, low_20) - 1.0

    # 20 日内创新高/新低次数
    is_new_high = (close >= close.rolling(20).max()).astype(float)
    is_new_low = (close <= close.rolling(20).min()).astype(float)
    out["new_high_count_20"] = is_new_high.rolling(20).sum()
    out["new_low_count_20"] = is_new_low.rolling(20).sum()

    # 乖离率
    ma20 = close.rolling(20).mean()
    out["bias_20"] = safe_div(close - ma20, ma20)

    return out
