from __future__ import annotations

import numpy as np
import pandas as pd


def compute_intraday_range_ratio(high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """(high - low) / close。"""
    if high_df.empty or low_df.empty or close_df.empty:
        return close_df.copy()
    base = close_df.replace(0, np.nan)
    factor_df = (high_df - low_df).divide(base)
    return factor_df.replace([np.inf, -np.inf], np.nan)
