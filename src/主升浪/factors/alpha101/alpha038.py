from __future__ import annotations

import pandas as pd

from ._base import rank, ts_rank


def compute_alpha038(open_df: pd.DataFrame, high_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or high_df.empty or close_df.empty:
        return close_df.copy()
    return -rank(ts_rank(close_df, 10)) * rank(close_df / open_df)
