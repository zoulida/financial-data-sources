from __future__ import annotations

import pandas as pd

from ._base import correlation, delay, rank


def compute_alpha037(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or close_df.empty:
        return close_df.copy()
    return rank(correlation(delay(open_df - close_df, 1), close_df, 200)) + rank(open_df - close_df)
