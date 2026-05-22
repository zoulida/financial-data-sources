from __future__ import annotations

import pandas as pd


def compute_volume_std_20(volume_df: pd.DataFrame) -> pd.DataFrame:
    """20日成交量波动率。"""
    if volume_df.empty:
        return volume_df.copy()
    return volume_df.pct_change().rolling(20, min_periods=20).std()

