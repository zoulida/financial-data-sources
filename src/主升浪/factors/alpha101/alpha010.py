from __future__ import annotations

import pandas as pd

from ._base import delta, rank, ts_max


def compute_alpha010(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    delta1 = delta(close_df, 1)
    signal = delta1.where(~((delta1.rolling(4, min_periods=4).max() < 0)), -delta1)
    signal = signal.where(~((delta1.rolling(4, min_periods=4).min() > 0)), delta1)
    return rank(signal)

