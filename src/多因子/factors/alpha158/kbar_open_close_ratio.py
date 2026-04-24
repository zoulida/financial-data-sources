from __future__ import annotations

import pandas as pd


def compute_kbar_open_close_ratio(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """(close - open) / open。"""
    if open_df.empty or close_df.empty:
        return close_df.copy()
    base = open_df.replace(0, pd.NA)
    return ((close_df - open_df) / base).astype(float)

