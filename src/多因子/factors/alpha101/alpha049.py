from __future__ import annotations

import pandas as pd

from ._base import delay, delta


def compute_alpha049(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    cond = ((delay(close_df, 20) - delay(close_df, 10)) / 10 - (delay(close_df, 10) - close_df) / 10) < -0.1
    return (-delta(close_df, 1)).where(cond, 1.0)
