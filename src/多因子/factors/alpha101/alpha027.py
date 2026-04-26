from __future__ import annotations

import pandas as pd

from ._base import rank, correlation, ts_mean, vwap


def compute_alpha027(volume_df: pd.DataFrame, amount_df: pd.DataFrame) -> pd.DataFrame:
    if volume_df.empty or amount_df.empty:
        return volume_df.copy()
    signal = rank(ts_mean(correlation(rank(volume_df), rank(vwap(amount_df, volume_df)), 6), 2))
    return pd.DataFrame(-1.0, index=volume_df.index, columns=volume_df.columns).where(signal > 0.5, 1.0)
