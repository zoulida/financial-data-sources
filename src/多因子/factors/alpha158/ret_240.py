from __future__ import annotations

import pandas as pd


def compute_ret_240(close_df: pd.DataFrame) -> pd.DataFrame:
    """240日收益率。"""
    if close_df.empty:
        return close_df.copy()
    return close_df.pct_change(240)

