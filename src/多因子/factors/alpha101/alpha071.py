from __future__ import annotations

import pandas as pd

from ._base import adv, correlation, delta, rank, ts_rank


def compute_alpha071(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    return -rank(delta(close_df, 3)) * ts_rank(volume_df / adv(volume_df, 20), 16) + correlation(close_df, volume_df, 6)
