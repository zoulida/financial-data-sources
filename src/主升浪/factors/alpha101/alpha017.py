from __future__ import annotations

import pandas as pd

from ._base import rank, ts_rank, vwap as _unused, delta


def compute_alpha017(close_df: pd.DataFrame, vwap_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty or vwap_df.empty:
        return close_df.copy()
    return -rank(ts_rank(close_df, 10)) * rank(delta(delta(close_df, 1), 1)) * rank(ts_rank(vwap_df / close_df, 5))

