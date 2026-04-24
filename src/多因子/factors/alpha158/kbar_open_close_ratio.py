from __future__ import annotations

import numpy as np
import pandas as pd


def compute_kbar_open_close_ratio(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """(close - open) / open。"""
    if open_df.empty or close_df.empty:
        return close_df.copy()
    base = open_df.replace(0, np.nan)
    factor_df = (close_df - open_df).divide(base)
    return factor_df.replace([np.inf, -np.inf], np.nan)
