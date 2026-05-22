from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_smoke_1779439841_002(close_df) -> pd.DataFrame:
    result = close_df
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
