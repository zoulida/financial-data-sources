from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779459390_006(close_df, high_df) -> pd.DataFrame:
    result = (((high_df).sub((high_df).mean(axis=1), axis=0)).rank(axis=1, pct=True)).rolling(10, min_periods=10).std()
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
