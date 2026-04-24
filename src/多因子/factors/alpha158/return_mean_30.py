from __future__ import annotations

import pandas as pd


def compute_return_mean_30(close_df: pd.DataFrame) -> pd.DataFrame:
    """30日日收益均值。"""
    if close_df.empty:
        return close_df.copy()
    return close_df.pct_change().rolling(30, min_periods=30).mean()

