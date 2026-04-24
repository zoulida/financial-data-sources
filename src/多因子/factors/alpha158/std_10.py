from __future__ import annotations

import pandas as pd


def compute_std_10(close_df: pd.DataFrame) -> pd.DataFrame:
    """10日收益波动率。"""
    if close_df.empty:
        return close_df.copy()
    return close_df.pct_change().rolling(10, min_periods=10).std()

