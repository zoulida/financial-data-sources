from __future__ import annotations

import numpy as np
import pandas as pd


def compute_turnover_amount_ratio(amount_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    """amount / volume，可近似成交均价。"""
    if amount_df.empty or volume_df.empty:
        return amount_df.copy()
    base = volume_df.replace(0, np.nan)
    factor_df = amount_df.divide(base)
    return factor_df.replace([np.inf, -np.inf], np.nan)
