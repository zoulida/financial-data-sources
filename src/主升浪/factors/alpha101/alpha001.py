from __future__ import annotations

import pandas as pd

from ._base import rank, stddev, ts_argmax, signedpower


def compute_alpha001(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    returns_df = close_df.pct_change()
    inner = close_df.where(~(returns_df < 0), stddev(returns_df, 20))
    return rank(ts_argmax(signedpower(inner, 2), 5)) - 0.5
