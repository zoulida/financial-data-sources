from __future__ import annotations

import pandas as pd


def compute_gap_ratio(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """(open / prev_close) - 1。"""
    if open_df.empty or close_df.empty:
        return close_df.copy()
    prev_close = close_df.shift(1).replace(0, pd.NA)
    return (open_df / prev_close - 1.0).astype(float)

