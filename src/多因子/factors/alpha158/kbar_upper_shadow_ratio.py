from __future__ import annotations

import pandas as pd


def compute_kbar_upper_shadow_ratio(high_df: pd.DataFrame, open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """(high - max(open, close)) / close。"""
    if high_df.empty or open_df.empty or close_df.empty:
        return close_df.copy()
    body_top = pd.DataFrame(index=close_df.index, columns=close_df.columns, data=open_df.where(open_df >= close_df, close_df))
    base = close_df.replace(0, pd.NA)
    return ((high_df - body_top) / base).astype(float)

