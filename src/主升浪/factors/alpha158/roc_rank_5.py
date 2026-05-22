from __future__ import annotations

import pandas as pd

from ._base import _rolling_rank_last


def compute_roc_rank_5(close_df: pd.DataFrame) -> pd.DataFrame:
    """5日收益率在过去5日内的时序排名百分位。"""
    if close_df.empty:
        return close_df.copy()
    return _rolling_rank_last(close_df.pct_change(), 5)

