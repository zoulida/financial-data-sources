from __future__ import annotations

import pandas as pd

from src.多因子.factors.alpha158._base import _avg_price


def compute_amount_mean_5_ratio(
    high_df: pd.DataFrame,
    low_df: pd.DataFrame,
    close_df: pd.DataFrame,
    amount_df: pd.DataFrame,
) -> pd.DataFrame:
    """5日平均成交额 / 典型价格。"""
    if high_df.empty or low_df.empty or close_df.empty or amount_df.empty:
        return close_df.copy()
    typical_price = _avg_price(high_df, low_df, close_df).replace(0, pd.NA)
    mean_amount = amount_df.rolling(5, min_periods=5).mean()
    return (mean_amount / typical_price).astype(float)

