"""动量因子：10 个。"""
from __future__ import annotations

from typing import Any

import pandas as pd

from ._helpers import rolling_zscore


def get_factors(panel: dict[str, pd.DataFrame], ctx: dict[str, Any]) -> dict[str, pd.DataFrame]:
    close = panel["close"]
    returns = close.pct_change(fill_method=None)
    out: dict[str, pd.DataFrame] = {}

    out["mom_5"] = close / close.shift(5) - 1.0
    out["mom_10"] = close / close.shift(10) - 1.0
    out["mom_20"] = close / close.shift(20) - 1.0
    out["mom_60"] = close / close.shift(60) - 1.0
    out["mom_120"] = close / close.shift(120) - 1.0
    out["mom_250"] = close / close.shift(250) - 1.0

    # 跳过最近 5 日的 20 日动量（剔除短期反转干扰）：用 5 日前的 close / 25 日前的 close
    out["mom_skip5_20"] = close.shift(5) / close.shift(25) - 1.0

    # 中长 - 短期
    out["mom_60_minus_5"] = out["mom_60"] - out["mom_5"]

    # 60 日动量相对自身近 20 日的 zscore
    out["mom_60_z20"] = rolling_zscore(out["mom_60"], 20)

    # 动量 / 波动（信噪比）
    vol_20 = returns.rolling(20).std()
    out["mom_volatility_adj"] = out["mom_20"] / vol_20

    return out
