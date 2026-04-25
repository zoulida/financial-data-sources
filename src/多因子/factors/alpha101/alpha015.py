from __future__ import annotations

import pandas as pd

from ._base import rank, correlation, sum_ts


def compute_alpha015(high_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or volume_df.empty:
        return high_df.copy()
    return -sum_ts(rank(correlation(rank(high_df), rank(volume_df), 3)), 3)

