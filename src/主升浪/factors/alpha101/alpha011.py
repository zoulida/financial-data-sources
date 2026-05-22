from __future__ import annotations

import pandas as pd

from ._base import rank, ts_max, ts_min, vwap as _vwap_unused


def compute_alpha011(close_df: pd.DataFrame, vwap_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or vwap_df.empty or volume_df.empty:
        return close_df.copy()
    inner = rank(ts_max(vwap_df - close_df, 3)) + rank(ts_min(vwap_df - close_df, 3))
    return inner * rank(volume_df.diff(3))

