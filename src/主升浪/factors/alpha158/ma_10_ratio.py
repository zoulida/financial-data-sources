from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ma_10_ratio(close_df: pd.DataFrame) -> pd.DataFrame:
    """close / MA10。"""
    if close_df.empty:
        return close_df.copy()
    ma_df = close_df.rolling(10, min_periods=10).mean().replace(0, np.nan)
    factor_df = close_df.divide(ma_df)
    return factor_df.replace([np.inf, -np.inf], np.nan)
