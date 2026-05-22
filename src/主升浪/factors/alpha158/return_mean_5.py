from __future__ import annotations

import pandas as pd


def compute_return_mean_5(close_df: pd.DataFrame) -> pd.DataFrame:
    """5日日收益均值。"""
    if close_df.empty:
        return close_df.copy()
    return close_df.pct_change().rolling(5, min_periods=5).mean()

