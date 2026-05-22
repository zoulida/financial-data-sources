from __future__ import annotations

import pandas as pd

from ._base import rank, ts_rank


def compute_alpha004(low_df: pd.DataFrame) -> pd.DataFrame:
    if low_df.empty:
        return low_df.copy()
    return -ts_rank(rank(low_df), 9)
