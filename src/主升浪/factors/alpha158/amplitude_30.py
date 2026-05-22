from __future__ import annotations

import pandas as pd


def compute_amplitude_30(high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """30日平均振幅。"""
    if high_df.empty or low_df.empty or close_df.empty:
        return close_df.copy()
    daily_range = (high_df - low_df) / close_df.replace(0, pd.NA)
    return daily_range.rolling(30, min_periods=30).mean()

