"""成交 / 换手因子：10 个。"""
from __future__ import annotations

from typing import Any

import pandas as pd

from ._helpers import rolling_zscore, safe_div


def get_factors(panel: dict[str, pd.DataFrame], ctx: dict[str, Any]) -> dict[str, pd.DataFrame]:
    close = panel["close"]
    amount = panel.get("amount", pd.DataFrame()).reindex_like(close)
    vol = panel.get("vol", pd.DataFrame()).reindex_like(close)
    turnover = panel.get("turnover", pd.DataFrame()).reindex_like(close)
    out: dict[str, pd.DataFrame] = {}

    if not amount.empty:
        amt_5 = amount.rolling(5).mean()
        amt_20 = amount.rolling(20).mean()
        amt_60 = amount.rolling(60).mean()
        out["amount_mean_5"] = amt_5
        out["amount_mean_20"] = amt_20
        out["amount_mean_60"] = amt_60
        out["amount_ratio_5_20"] = safe_div(amt_5, amt_20)
        # 成交额分布偏度（看是否集中放量）
        out["amount_skew_20"] = amount.rolling(20).skew()

    if not turnover.empty and turnover.notna().sum().sum() > 0:
        out["turnover_mean_5"] = turnover.rolling(5).mean()
        out["turnover_mean_20"] = turnover.rolling(20).mean()
        out["turnover_mean_60"] = turnover.rolling(60).mean()
        out["turnover_z20"] = rolling_zscore(turnover, 20)

    if not vol.empty:
        out["vol_ratio_20"] = safe_div(vol, vol.rolling(20).mean())

    return out
