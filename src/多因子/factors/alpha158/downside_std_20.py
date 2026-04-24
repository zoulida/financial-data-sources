from __future__ import annotations

import pandas as pd


def compute_downside_std_20(close_df: pd.DataFrame) -> pd.DataFrame:
    """20日下行收益波动率。"""
    if close_df.empty:
        return close_df.copy()
    returns = close_df.pct_change()
    downside = returns.where(returns < 0)
    return downside.rolling(20, min_periods=20).std()

