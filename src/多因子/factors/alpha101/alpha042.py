from __future__ import annotations

import pandas as pd

from ._base import rank, vwap


def compute_alpha042(high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame, amount_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or low_df.empty or close_df.empty or amount_df.empty or volume_df.empty:
        return high_df.copy()
    return rank(vwap(amount_df, volume_df) - close_df) / rank(vwap(amount_df, volume_df) + close_df)
