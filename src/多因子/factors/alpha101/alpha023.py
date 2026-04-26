from __future__ import annotations

import pandas as pd

from ._base import delta, ts_mean


def compute_alpha023(high_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or close_df.empty:
        return close_df.copy()
    cond = ts_mean(high_df, 20) < high_df
    return (-delta(high_df, 2)).where(cond, 0.0)
