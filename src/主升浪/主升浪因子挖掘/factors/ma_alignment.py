"""均线粘合度因子：5/10/20/60 日均线越粘合越接近起爆前夜。

逻辑：
- 计算 5/10/20/60 日均线；
- 对每个交易日，取 4 条均线的横向标准差除以均值，得到"相对发散度"；
- 发散度越小 → 均线粘合 → 越接近变盘临界点；
- 取 -divergence 让"越粘合"对应"因子值越大"。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_ma_alignment(close_df: pd.DataFrame) -> pd.DataFrame:
    """计算多周期均线粘合度因子。"""
    if close_df.empty:
        return close_df.copy()

    ma_windows = [5, 10, 20, 60]
    ma_list = [
        close_df.rolling(window=w, min_periods=w).mean()
        for w in ma_windows
    ]

    # 在第三个轴堆叠：(T, N, K)
    stacked = np.stack([ma.to_numpy(dtype=float) for ma in ma_list], axis=-1)
    mean_ma = np.nanmean(stacked, axis=-1)
    std_ma = np.nanstd(stacked, axis=-1, ddof=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        divergence = std_ma / np.where(mean_ma == 0, np.nan, mean_ma)

    factor = -divergence
    return pd.DataFrame(factor, index=close_df.index, columns=close_df.columns)
