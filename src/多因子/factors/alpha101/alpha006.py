from __future__ import annotations

import pandas as pd

from ._base import correlation


def compute_alpha006(open_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or volume_df.empty:
        return open_df.copy()
    return -correlation(open_df, volume_df, 10)
