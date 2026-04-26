from __future__ import annotations

import pandas as pd

from ._base import correlation, decay_linear, rank, vwap


def compute_alpha063(open_df: pd.DataFrame, close_df: pd.DataFrame, amount_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or close_df.empty or amount_df.empty or volume_df.empty:
        return close_df.copy()
    vw = vwap(amount_df, volume_df)
    return -rank(decay_linear(correlation(open_df, volume_df, 5), 8)) + rank(close_df - vw)
