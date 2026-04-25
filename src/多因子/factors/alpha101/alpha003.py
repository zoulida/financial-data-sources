from __future__ import annotations

import pandas as pd

from ._base import correlation, rank


def compute_alpha003(open_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or volume_df.empty:
        return open_df.copy()
    return -correlation(rank(open_df), rank(volume_df), 10)
