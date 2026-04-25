from __future__ import annotations

import pandas as pd

from ._base import rank


def compute_alpha005(open_df: pd.DataFrame, close_df: pd.DataFrame, vwap_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or close_df.empty or vwap_df.empty:
        return close_df.copy()
    vwap_mean = vwap_df.rolling(10, min_periods=10).mean()
    return rank(open_df - vwap_mean) * (-1.0 * rank(close_df - vwap_df).abs())
