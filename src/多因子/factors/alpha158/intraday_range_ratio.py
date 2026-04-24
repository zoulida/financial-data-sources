from __future__ import annotations

import pandas as pd


def compute_intraday_range_ratio(high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """(high - low) / close。"""
    if high_df.empty or low_df.empty or close_df.empty:
        return close_df.copy()
    base = close_df.replace(0, pd.NA)
    return ((high_df - low_df) / base).astype(float)

