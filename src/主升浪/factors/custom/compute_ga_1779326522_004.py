from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779326522_004(close_df, volume_df) -> pd.DataFrame:
    result = volume_df
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
