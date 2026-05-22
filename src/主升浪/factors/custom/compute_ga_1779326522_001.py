from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779326522_001(close_df, open_df) -> pd.DataFrame:
    result = (((open_df).rolling(60, min_periods=60).min()).rolling(10, min_periods=10).min()).rolling(60, min_periods=60).min()
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
