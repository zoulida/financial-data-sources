from __future__ import annotations

import numpy as np
import pandas as pd


def compute_gap_ratio(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """(open / prev_close) - 1。"""
    if open_df.empty or close_df.empty:
        return close_df.copy()
    prev_close = close_df.shift(1).replace(0, np.nan)
    factor_df = open_df.divide(prev_close) - 1.0
    return factor_df.replace([np.inf, -np.inf], np.nan)
