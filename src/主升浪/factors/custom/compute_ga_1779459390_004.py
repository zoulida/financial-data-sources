from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779459390_004(close_df, returns_df) -> pd.DataFrame:
    result = ((returns_df).rank(axis=1, pct=True)).rolling(10, min_periods=10).std()
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
