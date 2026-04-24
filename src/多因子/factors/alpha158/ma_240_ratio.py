from __future__ import annotations

import pandas as pd


def compute_ma_240_ratio(close_df: pd.DataFrame) -> pd.DataFrame:
    """close / MA240。"""
    if close_df.empty:
        return close_df.copy()
    ma_df = close_df.rolling(240, min_periods=240).mean().replace(0, pd.NA)
    return (close_df / ma_df).astype(float)

