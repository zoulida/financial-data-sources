from __future__ import annotations

import pandas as pd

from ._base import correlation, delay, rank, scale, ts_mean, vwap


def compute_alpha032(close_df: pd.DataFrame, amount_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or amount_df.empty or volume_df.empty:
        return close_df.copy()
    return scale(ts_mean(close_df, 7) - close_df) + 20 * scale(correlation(vwap(amount_df, volume_df), delay(close_df, 5), 230))
