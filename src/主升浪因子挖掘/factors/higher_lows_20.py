"""底部抬升因子：近 20 日低点逐步抬升的频率。

逻辑：
- 对 low 序列做 20 日滚动线性回归斜率；
- 斜率为正代表低点逐步抬升 → 多头试探、底部不断垫高；
- 直接以斜率作为因子值（值越大越好）。
"""
from __future__ import annotations

import pandas as pd

from src.主升浪因子挖掘.factors._base import linreg_slope


def compute_higher_lows_20(low_df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """计算低点抬升因子。"""
    if low_df.empty:
        return low_df.copy()
    return linreg_slope(low_df, window=window)
