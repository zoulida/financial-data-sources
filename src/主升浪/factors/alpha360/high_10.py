from __future__ import annotations

import pandas as pd

from ._base import price_lag_ratio


def compute_high_10(high_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    return price_lag_ratio(high_df, close_df, 10)
