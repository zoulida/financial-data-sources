"""布林带宽度收窄因子：20 日布林带相对宽度越小越接近起爆前夜。

逻辑：
- 计算 20 日收盘价均值与标准差；
- bandwidth = (2 * std) / mean，作为相对宽度；
- 取 -bandwidth 让"越窄"对应"因子值越大"。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_range_squeeze_20(close_df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """计算布林带宽度收窄因子。"""
    if close_df.empty:
        return close_df.copy()
    rolling = close_df.rolling(window=window, min_periods=window)
    mean = rolling.mean()
    std = rolling.std(ddof=0)
    bandwidth = (2.0 * std) / mean.replace(0.0, np.nan)
    return -bandwidth
