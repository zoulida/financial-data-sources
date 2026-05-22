from __future__ import annotations

import pandas as pd

from ._base import delta


def compute_alpha009(close_df: pd.DataFrame) -> pd.DataFrame:
    if close_df.empty:
        return close_df.copy()
    delta1 = delta(close_df, 1)
    cond = (delta1.rolling(5, min_periods=5).min() > 0) | (delta1.rolling(5, min_periods=5).max() < 0)
    return delta1.where(cond, -delta1)

