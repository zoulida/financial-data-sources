from __future__ import annotations

import numpy as np
import pandas as pd

from src.多因子.factors.alpha158._base import _avg_price


def compute_price_volume_ratio(high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    """典型价格 / 成交量。"""
    if high_df.empty or low_df.empty or close_df.empty or volume_df.empty:
        return close_df.copy()
    typical_price = _avg_price(high_df, low_df, close_df)
    base = volume_df.replace(0, np.nan)
    factor_df = typical_price.divide(base)
    return factor_df.replace([np.inf, -np.inf], np.nan)
