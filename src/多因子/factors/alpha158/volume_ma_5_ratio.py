from __future__ import annotations

import pandas as pd


def compute_volume_ma_5_ratio(volume_df: pd.DataFrame) -> pd.DataFrame:
    """volume / VMA5。"""
    if volume_df.empty:
        return volume_df.copy()
    ma_df = volume_df.rolling(5, min_periods=5).mean().replace(0, pd.NA)
    return (volume_df / ma_df).astype(float)

