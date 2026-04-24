from __future__ import annotations

import numpy as np
import pandas as pd


def compute_kbar_high_low_ratio(high_df: pd.DataFrame, low_df: pd.DataFrame) -> pd.DataFrame:
    """(high - low) / low。"""
    if high_df.empty or low_df.empty:
        return high_df.copy()
    base = low_df.replace(0, np.nan)
    factor_df = (high_df - low_df).divide(base)
    return factor_df.replace([np.inf, -np.inf], np.nan)
