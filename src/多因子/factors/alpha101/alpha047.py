from __future__ import annotations

import pandas as pd

from ._base import adv, delay, rank, ts_max, ts_mean, vwap


def compute_alpha047(high_df: pd.DataFrame, close_df: pd.DataFrame, volume_df: pd.DataFrame, amount_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or close_df.empty or volume_df.empty or amount_df.empty:
        return close_df.copy()
    return rank(1 / close_df) * volume_df / adv(volume_df, 20) * high_df * rank(high_df - close_df) / ts_mean(high_df, 5) - rank(vwap(amount_df, volume_df) - delay(vwap(amount_df, volume_df), 5))
