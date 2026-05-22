from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_divide(numerator: pd.DataFrame, denominator: pd.DataFrame) -> pd.DataFrame:
    denominator = denominator.replace(0, np.nan)
    result = numerator.divide(denominator)
    return result.replace([np.inf, -np.inf], np.nan)


def price_lag_ratio(price_df: pd.DataFrame, close_df: pd.DataFrame, lag: int) -> pd.DataFrame:
    if price_df.empty or close_df.empty:
        return price_df.copy()
    return _safe_divide(price_df.shift(lag), close_df)


def volume_lag_ratio(volume_df: pd.DataFrame, lag: int) -> pd.DataFrame:
    if volume_df.empty:
        return volume_df.copy()
    return _safe_divide(volume_df.shift(lag), volume_df)
