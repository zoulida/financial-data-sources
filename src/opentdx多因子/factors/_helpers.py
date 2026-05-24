"""共享工具：talib 包装、滚动相关性、安全除法等。"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

try:
    import talib as _talib
    HAS_TALIB = True
except Exception:
    _talib = None
    HAS_TALIB = False


def safe_div(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    """逐元素安全除法：分母为 0/NaN 时输出 NaN。"""
    return a.div(b.replace(0.0, np.nan))


def apply_per_column(df: pd.DataFrame, func: Callable[[np.ndarray], np.ndarray], min_periods: int = 0) -> pd.DataFrame:
    """对 DataFrame 每一列应用一个 (1D ndarray -> 1D ndarray) 函数，结果对齐索引返回。"""
    out = pd.DataFrame(np.nan, index=df.index, columns=df.columns, dtype=float)
    for col in df.columns:
        s = df[col].astype(float).to_numpy()
        if np.isfinite(s).sum() <= min_periods:
            continue
        try:
            res = func(s)
        except Exception:
            continue
        if res is None:
            continue
        arr = np.asarray(res, dtype=float)
        if arr.shape[0] == out.shape[0]:
            out[col] = arr
    return out


def rolling_corr(a: pd.DataFrame, b: pd.DataFrame, window: int) -> pd.DataFrame:
    """逐列做 a 与 b 的滚动相关系数；要求 a/b 形状一致。"""
    a, b = a.align(b, join="inner")
    return a.rolling(window).corr(b)


def rolling_zscore(df: pd.DataFrame, window: int) -> pd.DataFrame:
    mean = df.rolling(window).mean()
    std = df.rolling(window).std().replace(0.0, np.nan)
    return (df - mean) / std


def streak(condition: pd.DataFrame) -> pd.DataFrame:
    """对 bool DataFrame 计算"当前连续为 True 的天数"，纯向量化（按列独立）。"""
    cond = condition.fillna(False).astype(int)
    # 标准技巧：累计求和 - 每次断开时记录的累计值
    cum = cond.cumsum()
    # 在 cond=0 处保留累计值，其余 NaN，向前填充得到"上一次断开时的累计"
    reset = cum.where(cond == 0).ffill().fillna(0)
    return cum - reset


def max_streak(condition: pd.DataFrame, window: int) -> pd.DataFrame:
    """N 日内连续为 True 的最大天数。"""
    s = streak(condition)
    return s.rolling(window).max()
