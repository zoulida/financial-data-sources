from __future__ import annotations

import pandas as pd

from ._base import correlation, delay, delta, indneutralize, rank


def compute_alpha048(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    return indneutralize(correlation(delta(close_df, 1), delta(delay(close_df, 1), 1), 250) * delta(close_df, 1) / close_df)
