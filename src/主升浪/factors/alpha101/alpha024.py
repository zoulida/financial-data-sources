from __future__ import annotations

import pandas as pd

from ._base import delay, delta, ts_mean, ts_min


def compute_alpha024(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    ma100 = ts_mean(close_df, 100)
    cond = delta(ma100, 100) / delay(close_df, 100).abs() <= 0.05
    return (-delta(close_df, 3)).where(cond, -(close_df - ts_min(close_df, 100)))
