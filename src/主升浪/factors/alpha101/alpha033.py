from __future__ import annotations

import pandas as pd

from ._base import rank


def compute_alpha033(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    if open_df.empty or close_df.empty:
        return close_df.copy()
    return rank(-(1 - open_df / close_df))
