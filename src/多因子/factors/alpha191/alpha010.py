from __future__ import annotations

import numpy as np
import pandas as pd

from ._gtja import alpha191_010


def compute_alpha010(
    open_df: pd.DataFrame,
    high_df: pd.DataFrame,
    low_df: pd.DataFrame,
    close_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    amount_df: pd.DataFrame,
) -> pd.DataFrame:
    """国君朝阳191 #010。"""
    if open_df.empty or high_df.empty or low_df.empty or close_df.empty or volume_df.empty or amount_df.empty:
        return close_df.copy()
    vwap_df = amount_df.divide(volume_df.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    turnover_df = amount_df.divide((close_df * volume_df).replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    data = {
        "open": open_df,
        "high": high_df,
        "low": low_df,
        "close": close_df,
        "volume": volume_df,
        "amount": amount_df,
        "vwap": vwap_df,
        "turn": turnover_df,
        "liquidity_value": close_df * volume_df,
    }
    result = alpha191_010(data)
    if result is None:
        raise NotImplementedError("Alpha191 #010 暂无可靠真实公式实现")
    return result
