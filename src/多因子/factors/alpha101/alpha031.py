from __future__ import annotations

import pandas as pd

from ._base import decay_linear, delta, rank, ts_rank


def compute_alpha031(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    return rank(rank(rank(decay_linear(-rank(rank(delta(close_df, 10))), 10)))) + rank(-delta(close_df, 3))
