from __future__ import annotations

import pandas as pd

from ._base import decay_linear, delta, rank, scale, ts_rank


def compute_alpha090(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    return rank(scale(decay_linear(delta(close_df, 8), 15))) - ts_rank(close_df, 13)
