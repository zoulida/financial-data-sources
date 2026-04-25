from __future__ import annotations

import pandas as pd

from ._base import _safe_divide, delay, rank, sum_ts


def compute_alpha008(open_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or returns_df.empty:
        return open_df.copy()
    left = sum_ts(open_df, 5) * sum_ts(returns_df, 5)
    return -rank(left - delay(left, 10))
