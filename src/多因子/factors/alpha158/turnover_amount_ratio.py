from __future__ import annotations

import pandas as pd


def compute_turnover_amount_ratio(amount_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    """amount / volume，可近似成交均价。"""
    if amount_df.empty or volume_df.empty:
        return amount_df.copy()
    base = volume_df.replace(0, pd.NA)
    return (amount_df / base).astype(float)

