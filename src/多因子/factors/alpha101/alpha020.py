from __future__ import annotations

import pandas as pd

from ._base import delay, rank, _safe_divide


def compute_alpha020(open_df: pd.DataFrame, high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or high_df.empty or low_df.empty or close_df.empty:
        return close_df.copy()
    return -rank((open_df - delay(high_df, 1)) * rank((open_df - delay(close_df, 1))) * rank((open_df - delay(low_df, 1))))

