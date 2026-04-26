from __future__ import annotations

import pandas as pd

from ._base import correlation, rank, ts_mean, stddev


def compute_alpha079(high_df: pd.DataFrame, low_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or low_df.empty or volume_df.empty:
        return high_df.copy()
    mid = (high_df + low_df) / 2
    return rank(stddev(mid, 24)) * -correlation(rank(mid), rank(volume_df), 8)
