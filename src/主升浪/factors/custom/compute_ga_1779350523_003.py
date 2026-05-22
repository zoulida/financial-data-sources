from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779350523_003(close_df, returns_df) -> pd.DataFrame:
    result = (returns_df).rolling(30, min_periods=30).cov((np.log((close_df).abs().replace(0.0, np.nan))))
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
