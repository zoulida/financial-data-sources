"""缩量盘整因子：近 20 日成交量逐步萎缩程度。

逻辑：
- 对成交量取 log 后，做 20 日滚动线性回归得到斜率；
- 斜率越负，代表成交量越在持续萎缩 → 越可能是吸筹末段；
- 因子方向统一为"值越大越接近起爆前夜"，因此最终取 -slope。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.主升浪因子挖掘.factors._base import linreg_slope


def compute_vol_shrink_20(volume_df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """计算缩量盘整因子。"""
    if volume_df.empty:
        return volume_df.copy()
    log_volume = np.log(volume_df.replace(0.0, np.nan))
    slope = linreg_slope(log_volume, window=window)
    return -slope
