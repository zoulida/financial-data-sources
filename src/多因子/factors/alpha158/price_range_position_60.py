from __future__ import annotations

import pandas as pd

from src.多因子.factors.alpha158._base import _price_range_position


def compute_price_range_position_60(
    high_df: pd.DataFrame,
    low_df: pd.DataFrame,
    close_df: pd.DataFrame,
) -> pd.DataFrame:
    """收盘价位于过去60日区间的位置。"""
    if high_df.empty or low_df.empty or close_df.empty:
        return close_df.copy()
    return _price_range_position(high_df, low_df, close_df, 60)

