from __future__ import annotations

import pandas as pd

from ._base import price_lag_ratio


def compute_close_22(close_df: pd.DataFrame) -> pd.DataFrame:
    return price_lag_ratio(close_df, close_df, 22)
