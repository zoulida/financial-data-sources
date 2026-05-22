from __future__ import annotations

import pandas as pd

from ._base import correlation, rank, stddev


def compute_alpha040(high_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or volume_df.empty:
        return high_df.copy()
    return -rank(stddev(high_df, 10)) * correlation(high_df, volume_df, 10)
