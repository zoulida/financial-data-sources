from __future__ import annotations

import pandas as pd


def compute_volume_std_30(volume_df: pd.DataFrame) -> pd.DataFrame:
    """30日成交量波动率。"""
    if volume_df.empty:
        return volume_df.copy()
    return volume_df.pct_change().rolling(30, min_periods=30).std()

