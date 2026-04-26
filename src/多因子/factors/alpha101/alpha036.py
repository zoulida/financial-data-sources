from __future__ import annotations

import pandas as pd

from ._base import adv, correlation, delay, rank, returns, ts_mean, ts_rank, vwap


def compute_alpha036(open_df: pd.DataFrame, close_df: pd.DataFrame, volume_df: pd.DataFrame, amount_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or close_df.empty or volume_df.empty or amount_df.empty:
        return close_df.copy()
    return 2.21 * rank(correlation(close_df - open_df, delay(volume_df, 1), 15)) + 0.7 * rank(open_df - close_df) + 0.73 * rank(ts_rank(delay(-returns(close_df), 6), 5)) + rank(abs(correlation(vwap(amount_df, volume_df), adv(volume_df, 20), 6))) + 0.6 * rank((ts_mean(close_df, 200) - open_df) * (close_df - open_df))
