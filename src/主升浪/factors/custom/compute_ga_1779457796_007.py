from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ga_1779457796_007(close_df, low_df, open_df) -> pd.DataFrame:
    result = ((low_df).rolling(30, min_periods=30).corr(((open_df).where((open_df) >= (pd.DataFrame(-0.5, index=close_df.index, columns=close_df.columns)), (pd.DataFrame(-0.5, index=close_df.index, columns=close_df.columns)))))).sub(((low_df).rolling(30, min_periods=30).corr(((open_df).where((open_df) >= (pd.DataFrame(-0.5, index=close_df.index, columns=close_df.columns)), (pd.DataFrame(-0.5, index=close_df.index, columns=close_df.columns)))))).mean(axis=1), axis=0).div(((low_df).rolling(30, min_periods=30).corr(((open_df).where((open_df) >= (pd.DataFrame(-0.5, index=close_df.index, columns=close_df.columns)), (pd.DataFrame(-0.5, index=close_df.index, columns=close_df.columns)))))).std(axis=1).replace(0.0, np.nan), axis=0)
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
