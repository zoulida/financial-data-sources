from __future__ import annotations

import pandas as pd


def compute_std_60(close_df: pd.DataFrame) -> pd.DataFrame:
    """60日收益波动率。"""
    if close_df.empty:
        return close_df.copy()
    return close_df.pct_change().rolling(60, min_periods=60).std()

