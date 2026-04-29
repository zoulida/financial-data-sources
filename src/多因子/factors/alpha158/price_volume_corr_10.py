from __future__ import annotations

import warnings

import pandas as pd


def compute_price_volume_corr_10(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    """10日价格与成交量相关系数。"""
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="invalid value encountered in divide", category=RuntimeWarning)
        return close_df.rolling(10, min_periods=10).corr(volume_df)

