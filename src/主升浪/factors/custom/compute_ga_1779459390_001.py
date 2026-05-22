from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779459390_001(close_df, low_df) -> pd.DataFrame:
    result = (((low_df).rolling(3, min_periods=3).mean()).shift(20)).rank(axis=1, pct=True)
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
