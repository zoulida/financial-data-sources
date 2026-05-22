from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779459390_002(close_df, low_df) -> pd.DataFrame:
    result = ((np.log((close_df).abs().replace(0.0, np.nan))).sub((np.log((close_df).abs().replace(0.0, np.nan))).mean(axis=1), axis=0).div((np.log((close_df).abs().replace(0.0, np.nan))).std(axis=1).replace(0.0, np.nan), axis=0)).divide((np.log(((low_df).diff(10)).abs().replace(0.0, np.nan))).replace(0.0, np.nan))
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
