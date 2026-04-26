from __future__ import annotations

import pandas as pd

from ._base import adv, delta, rank, ts_rank


def compute_alpha043(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    return ts_rank(volume_df / adv(volume_df, 20), 20) * ts_rank(-delta(close_df, 7), 8)
