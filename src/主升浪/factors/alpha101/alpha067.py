from __future__ import annotations

import pandas as pd

from ._base import rank, ts_argmax, ts_argmin, ts_rank


def compute_alpha067(high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or low_df.empty or close_df.empty:
        return close_df.copy()
    price_pos = (close_df - low_df) / (high_df - low_df).replace(0, pd.NA)
    return rank(price_pos) + ts_rank(ts_argmax(high_df, 12) - ts_argmin(low_df, 12), 9)
