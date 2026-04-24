from __future__ import annotations

import pandas as pd


def compute_return_mean_60(close_df: pd.DataFrame) -> pd.DataFrame:
    """60日日收益均值。"""
    if close_df.empty:
        return close_df.copy()
    return close_df.pct_change().rolling(60, min_periods=60).mean()

