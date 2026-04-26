from __future__ import annotations

import pandas as pd

from ._base import delay, delta, log, min_df, product, rank, returns, scale, sign, ts_min, ts_rank


def compute_alpha029(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    inner = rank(rank(scale(log(ts_min(rank(rank(-rank(delta(close_df - 1, 5)))), 2)))))
    return min_df(product(inner, 1), 5) + ts_rank(delay(-returns(close_df), 6), 5)
