from __future__ import annotations

import pandas as pd

from ._base import delta, rank, returns, stddev


def compute_alpha034(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    return rank(2 - rank(stddev(returns(close_df), 2) / stddev(returns(close_df), 5)) - rank(delta(close_df, 1)))
