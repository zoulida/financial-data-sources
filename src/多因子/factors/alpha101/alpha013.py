from __future__ import annotations

import pandas as pd

from ._base import covariance, rank


def compute_alpha013(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    return -rank(covariance(rank(close_df), rank(volume_df), 5))

