from __future__ import annotations

import pandas as pd

from ._base import _intraday_return


def compute_intraday_return(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """日内收益率。"""
    if open_df.empty or close_df.empty:
        return close_df.copy()
    return _intraday_return(open_df, close_df)

