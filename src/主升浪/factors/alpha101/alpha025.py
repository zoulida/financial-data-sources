from __future__ import annotations

import pandas as pd

from ._base import adv, rank, returns, vwap


def compute_alpha025(high_df: pd.DataFrame, close_df: pd.DataFrame, volume_df: pd.DataFrame, amount_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or close_df.empty or volume_df.empty or amount_df.empty:
        return close_df.copy()
    return rank((-returns(close_df) * adv(volume_df, 20)) * vwap(amount_df, volume_df) * (high_df - close_df))
