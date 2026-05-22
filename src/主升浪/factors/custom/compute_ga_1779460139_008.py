from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779460139_008(close_df, amount_df, low_df) -> pd.DataFrame:
    result = (np.log(((amount_df).div((amount_df).abs().sum(axis=1).replace(0.0, np.nan), axis=0)).abs().replace(0.0, np.nan))).rolling(60, min_periods=60).cov(((low_df).rank(axis=1, pct=True)))
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
