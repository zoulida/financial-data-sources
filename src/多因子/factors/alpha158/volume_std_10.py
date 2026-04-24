from __future__ import annotations

import pandas as pd


def compute_volume_std_10(volume_df: pd.DataFrame) -> pd.DataFrame:
    """10日成交量波动率。"""
    if volume_df.empty:
        return volume_df.copy()
    return volume_df.pct_change().rolling(10, min_periods=10).std()

