from __future__ import annotations

import numpy as np
import pandas as pd


def compute_kbar_lower_shadow_ratio(low_df: pd.DataFrame, open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """(min(open, close) - low) / close。"""
    if low_df.empty or open_df.empty or close_df.empty:
        return close_df.copy()
    body_bottom = pd.DataFrame(index=close_df.index, columns=close_df.columns, data=open_df.where(open_df <= close_df, close_df))
    base = close_df.replace(0, np.nan)
    factor_df = (body_bottom - low_df).divide(base)
    return factor_df.replace([np.inf, -np.inf], np.nan)
