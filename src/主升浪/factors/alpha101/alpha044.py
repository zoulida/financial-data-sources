from __future__ import annotations

import pandas as pd

from ._base import correlation, rank


def compute_alpha044(high_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or volume_df.empty:
        return high_df.copy()
    return -correlation(high_df, rank(volume_df), 5)
