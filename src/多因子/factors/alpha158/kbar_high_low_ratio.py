from __future__ import annotations

import pandas as pd


def compute_kbar_high_low_ratio(high_df: pd.DataFrame, low_df: pd.DataFrame) -> pd.DataFrame:
    """(high - low) / low。"""
    if high_df.empty or low_df.empty:
        return high_df.copy()
    base = low_df.replace(0, pd.NA)
    return ((high_df - low_df) / base).astype(float)

