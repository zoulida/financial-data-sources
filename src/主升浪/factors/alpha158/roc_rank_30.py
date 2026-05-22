from __future__ import annotations

import pandas as pd

from ._base import _rolling_rank_last


def compute_roc_rank_30(close_df: pd.DataFrame) -> pd.DataFrame:
    """日收益率在过去30日内的时序排名百分位。"""
    if close_df.empty:
        return close_df.copy()
    return _rolling_rank_last(close_df.pct_change(), 30)

