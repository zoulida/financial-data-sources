from __future__ import annotations

import pandas as pd

from ._base import rank, vwap


def compute_alpha041(high_df: pd.DataFrame, low_df: pd.DataFrame, amount_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or low_df.empty or amount_df.empty or volume_df.empty:
        return high_df.copy()
    return ((high_df * low_df) ** 0.5) - vwap(amount_df, volume_df)
