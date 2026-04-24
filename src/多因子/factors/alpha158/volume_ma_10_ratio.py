from __future__ import annotations

import pandas as pd


def compute_volume_ma_10_ratio(volume_df: pd.DataFrame) -> pd.DataFrame:
    """volume / VMA10。"""
    if volume_df.empty:
        return volume_df.copy()
    ma_df = volume_df.rolling(10, min_periods=10).mean().replace(0, pd.NA)
    return (volume_df / ma_df).astype(float)

