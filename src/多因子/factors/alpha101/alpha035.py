from __future__ import annotations

import pandas as pd

from ._base import rank, returns, ts_rank


def compute_alpha035(high_df: pd.DataFrame, low_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if high_df.empty or low_df.empty or volume_df.empty:
        return high_df.copy()
    return ts_rank(volume_df, 32) * (1 - ts_rank(close_df := (high_df + low_df) / 2, 16)) * (1 - ts_rank(returns(close_df), 32))
