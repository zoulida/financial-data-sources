from __future__ import annotations

import pandas as pd

from ._base import correlation, delay, rank, ts_mean


def compute_alpha045(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    return -rank(ts_mean(delay(close_df, 5), 20)) * correlation(close_df, volume_df, 2) * rank(correlation(ts_mean(close_df, 5), ts_mean(close_df, 20), 2))
