from __future__ import annotations

import pandas as pd


def compute_price_volume_corr_20(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    """20日价格与成交量相关系数。"""
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    return close_df.rolling(20, min_periods=20).corr(volume_df)

