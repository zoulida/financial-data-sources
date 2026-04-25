from __future__ import annotations

import pandas as pd

from ._base import correlation, rank, stddev, _safe_divide


def compute_alpha018(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or close_df.empty:
        return close_df.copy()
    return -rank(stddev((close_df - open_df).abs(), 5) + (close_df - open_df) + correlation(close_df, open_df, 10))

