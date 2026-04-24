from __future__ import annotations

import pandas as pd


def compute_downside_std_60(close_df: pd.DataFrame) -> pd.DataFrame:
    """60日下行收益波动率。"""
    if close_df.empty:
        return close_df.copy()
    returns = close_df.pct_change()
    downside = returns.where(returns < 0)
    return downside.rolling(60, min_periods=60).std()

