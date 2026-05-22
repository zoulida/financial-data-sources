from __future__ import annotations

import pandas as pd

from ._base import adv, delay, rank, ts_mean


def compute_alpha021(open_df: pd.DataFrame, close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or close_df.empty or volume_df.empty:
        return close_df.copy()
    mean8 = ts_mean(close_df, 8)
    std8 = close_df.rolling(8, min_periods=8).std()
    cond1 = (mean8 + std8) < ts_mean(close_df, 2)
    cond2 = ts_mean(close_df, 2) < (mean8 - std8)
    cond3 = volume_df >= adv(volume_df, 20)
    result = pd.DataFrame(-1.0, index=close_df.index, columns=close_df.columns)
    result = result.where(~cond1, 1.0)
    result = result.where(~(~cond1 & cond2), -1.0)
    result = result.where(~(~cond1 & ~cond2 & cond3), 1.0)
    return result
