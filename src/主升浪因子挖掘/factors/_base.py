"""主升浪因子库共享算子。

提供：
- rolling_zscore: 滚动 z-score
- linreg_slope: 滚动 OLS 斜率
- pct_rank: 时序分位排名
- ts_std / ts_mean / ts_max / ts_min: 滚动统计辅助
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_zscore(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """滚动 z-score：(x - mean) / std。"""
    mean = df.rolling(window=window, min_periods=window).mean()
    std = df.rolling(window=window, min_periods=window).std(ddof=0)
    return (df - mean) / std.replace(0.0, np.nan)


def linreg_slope(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """滚动窗口对每列做 OLS 线性回归，返回斜率。

    使用 cov(x, y) / var(x) 闭式解，x 取 1..window 等差序列。
    """
    if df.empty or window <= 1:
        return pd.DataFrame(np.nan, index=df.index, columns=df.columns)
    x = np.arange(1, window + 1, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    x_var = float((x_centered ** 2).sum())
    if x_var == 0:
        return pd.DataFrame(np.nan, index=df.index, columns=df.columns)

    def _slope(values: np.ndarray) -> float:
        if np.any(~np.isfinite(values)):
            return np.nan
        return float(((values - values.mean()) * x_centered).sum() / x_var)

    return df.rolling(window=window, min_periods=window).apply(_slope, raw=True)


def pct_rank(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """对每列做窗口内时序分位排名（值越大排名越高，归一化到 0..1）。"""
    return df.rolling(window=window, min_periods=window).apply(
        lambda x: (x.argsort().argsort()[-1] + 1) / len(x) if len(x) > 0 else np.nan,
        raw=True,
    )


def ts_std(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window=window, min_periods=window).std(ddof=0)


def ts_mean(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window=window, min_periods=window).mean()


def ts_max(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window=window, min_periods=window).max()


def ts_min(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window=window, min_periods=window).min()
