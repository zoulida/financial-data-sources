from __future__ import annotations

import pandas as pd

from ._base import correlation, rank, ts_max, ts_rank


def compute_alpha026(high_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or volume_df.empty:
        return high_df.copy()
    return -ts_max(correlation(ts_rank(volume_df, 5), ts_rank(high_df, 5), 5), 3)
