from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_smoke_1779439841_001(close_df, low_df) -> pd.DataFrame:
    result = low_df
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
