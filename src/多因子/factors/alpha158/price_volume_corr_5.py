from __future__ import annotations

import warnings

import pandas as pd


def compute_price_volume_corr_5(close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    """5日价格与成交量相关系数。"""
    if close_df.empty or volume_df.empty:
        return close_df.copy()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="invalid value encountered in divide", category=RuntimeWarning)
        return close_df.rolling(5, min_periods=5).corr(volume_df)

