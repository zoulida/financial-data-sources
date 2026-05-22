from __future__ import annotations

import pandas as pd

from ._base import correlation, delta, rank, stddev


def compute_alpha022(high_df: pd.DataFrame, close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or close_df.empty or volume_df.empty:
        return close_df.copy()
    corr = correlation(high_df, volume_df, 5)
    return -delta(corr, 5) * rank(stddev(close_df, 20))
