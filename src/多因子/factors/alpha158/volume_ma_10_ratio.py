from __future__ import annotations

import numpy as np
import pandas as pd


def compute_volume_ma_10_ratio(volume_df: pd.DataFrame) -> pd.DataFrame:
    """volume / VMA10。"""
    if volume_df.empty:
        return volume_df.copy()
    ma_df = volume_df.rolling(10, min_periods=10).mean().replace(0, np.nan)
    factor_df = volume_df.divide(ma_df)
    return factor_df.replace([np.inf, -np.inf], np.nan)
