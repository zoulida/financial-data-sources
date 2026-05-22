from __future__ import annotations

import pandas as pd


def compute_return_mean_20(close_df: pd.DataFrame) -> pd.DataFrame:
    """20日日收益均值。"""
    if close_df.empty:
        return close_df.copy()
    return close_df.pct_change().rolling(20, min_periods=20).mean()

