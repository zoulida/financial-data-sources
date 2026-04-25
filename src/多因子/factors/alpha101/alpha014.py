from __future__ import annotations

import pandas as pd

from ._base import correlation, rank, returns, ts_rank


def compute_alpha014(open_df: pd.DataFrame, volume_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or volume_df.empty or returns_df.empty:
        return open_df.copy()
    return -(rank(delta := returns_df.diff(3)) * correlation(open_df, volume_df, 10))

