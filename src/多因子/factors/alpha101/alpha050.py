from __future__ import annotations

import pandas as pd

from ._base import correlation, rank, ts_max, vwap


def compute_alpha050(volume_df: pd.DataFrame, amount_df: pd.DataFrame) -> pd.DataFrame:
    if volume_df.empty or amount_df.empty:
        return volume_df.copy()
    return -ts_max(rank(correlation(rank(volume_df), rank(vwap(amount_df, volume_df)), 5)), 5)
