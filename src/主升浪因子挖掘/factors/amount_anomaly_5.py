"""资金异动因子：近 5 日成交额相对前 20 日均值的 z-score。

逻辑：
- 计算 5 日成交额均值；
- 对 20 日窗口的成交额做均值/标准差，对 5 日均值进行标准化；
- z-score 越大代表近期资金异常涌入 → 起爆前夜的"埋伏资金"信号。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_amount_anomaly_5(
    amount_df: pd.DataFrame,
    short_window: int = 5,
    long_window: int = 20,
) -> pd.DataFrame:
    """计算成交额异动因子。"""
    if amount_df.empty:
        return amount_df.copy()
    short_mean = amount_df.rolling(window=short_window, min_periods=short_window).mean()
    long_rolling = amount_df.rolling(window=long_window, min_periods=long_window)
    long_mean = long_rolling.mean()
    long_std = long_rolling.std(ddof=0)
    return (short_mean - long_mean) / long_std.replace(0.0, np.nan)
