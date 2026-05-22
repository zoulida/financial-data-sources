from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779326522_003(close_df, returns_df) -> pd.DataFrame:
    result = ((returns_df).rolling(10, min_periods=10).std()).rolling(3, min_periods=3).min()
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
