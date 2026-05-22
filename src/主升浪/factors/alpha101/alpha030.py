from __future__ import annotations

import pandas as pd

from ._base import adv, delta, rank, sign, sum_ts


def compute_alpha030(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    direction = 1.0 - rank((sign(delta(close_df, 1)) + sign(delta(close_df, 1).shift(1)) + sign(delta(close_df, 1).shift(2))))
    return direction * (sum_ts(volume_df, 5) / sum_ts(volume_df, 20))
