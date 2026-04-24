from __future__ import annotations

import numpy as np
import pandas as pd


def compute_kbar_close_open_range_position(
    open_df: pd.DataFrame,
    high_df: pd.DataFrame,
    low_df: pd.DataFrame,
    close_df: pd.DataFrame,
) -> pd.DataFrame:
    """(close - open) / (high - low)。"""
    if open_df.empty or high_df.empty or low_df.empty or close_df.empty:
        return close_df.copy()

    intraday_range = (high_df - low_df).replace(0, np.nan)
    factor_df = (close_df - open_df).divide(intraday_range)
    return factor_df.replace([np.inf, -np.inf], np.nan)

