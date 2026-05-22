from __future__ import annotations

import pandas as pd

from ._base import price_lag_ratio


def compute_vwap_47(vwap_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    return price_lag_ratio(vwap_df, close_df, 47)
