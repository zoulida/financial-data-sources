from __future__ import annotations

import pandas as pd

from ._base import adv, correlation, rank, scale, vwap


def compute_alpha028(high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame, volume_df: pd.DataFrame, amount_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or low_df.empty or close_df.empty or volume_df.empty or amount_df.empty:
        return close_df.copy()
    return scale(correlation(adv(volume_df, 20), low_df, 5) + ((high_df + low_df) / 2 - close_df))
