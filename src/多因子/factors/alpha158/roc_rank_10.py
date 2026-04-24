from __future__ import annotations

import pandas as pd

from src.多因子.factors.alpha158._base import _rolling_rank_last


def compute_roc_rank_10(close_df: pd.DataFrame) -> pd.DataFrame:
    """日收益率在过去10日内的时序排名百分位。"""
    if close_df.empty:
        return close_df.copy()
    return _rolling_rank_last(close_df.pct_change(), 10)

