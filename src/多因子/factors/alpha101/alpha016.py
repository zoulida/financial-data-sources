from __future__ import annotations

import pandas as pd

from ._base import rank, ts_max, correlation, vwap as _unused


def compute_alpha016(high_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or volume_df.empty:
        return high_df.copy()
    return -rank(covariance := high_df.rolling(5, min_periods=5).cov(volume_df).pipe(rank))

