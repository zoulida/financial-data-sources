from __future__ import annotations

import pandas as pd

from ._base import correlation, delta, log, rank, _safe_divide


def compute_alpha002(open_df: pd.DataFrame, close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or close_df.empty or volume_df.empty:
        return close_df.copy()
    volume_rank = rank(delta(log(volume_df), 2))
    intraday_rank = rank(_safe_divide(close_df - open_df, open_df))
    return -correlation(volume_rank, intraday_rank, 6)
