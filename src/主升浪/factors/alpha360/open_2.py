from __future__ import annotations

import pandas as pd

from ._base import price_lag_ratio


def compute_open_2(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    return price_lag_ratio(open_df, close_df, 2)
