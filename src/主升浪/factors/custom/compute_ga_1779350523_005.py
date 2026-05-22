from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779350523_005(close_df, volume_df) -> pd.DataFrame:
    result = (volume_df).rank(axis=1, pct=True)
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
