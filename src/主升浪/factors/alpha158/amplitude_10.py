from __future__ import annotations

import pandas as pd


def compute_amplitude_10(high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """10日平均振幅。"""
    if high_df.empty or low_df.empty or close_df.empty:
        return close_df.copy()
    daily_range = (high_df - low_df) / close_df.replace(0, pd.NA)
    return daily_range.rolling(10, min_periods=10).mean()

