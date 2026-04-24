from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_divide(numerator: pd.DataFrame, denominator: pd.DataFrame | float | int) -> pd.DataFrame:
    """安全除法，统一处理 0 和无穷值。"""
    if isinstance(denominator, pd.DataFrame):
        result = numerator.divide(denominator.replace(0, np.nan))
    else:
        if denominator == 0:
            return numerator * np.nan
        result = numerator / denominator
    return result.replace([np.inf, -np.inf], np.nan)


def _rolling_rank_last(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """返回滚动窗口内最后一个值的时序排名百分位。"""
    return df.rolling(window, min_periods=window).apply(
        lambda values: pd.Series(values).rank(pct=True).iloc[-1],
        raw=False,
    )


def _ts_minmax_position(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """计算当前值在过去窗口最小值与最大值之间的位置。"""
    rolling_min = df.rolling(window, min_periods=window).min()
    rolling_max = df.rolling(window, min_periods=window).max()
    return _safe_divide(df - rolling_min, (rolling_max - rolling_min))


def _avg_price(high_df: pd.DataFrame, low_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """典型价格。"""
    return (high_df + low_df + close_df) / 3.0


def _price_range_position(
    high_df: pd.DataFrame,
    low_df: pd.DataFrame,
    close_df: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """当前收盘价位于过去 N 日高低区间中的相对位置。"""
    rolling_high = high_df.rolling(window, min_periods=window).max()
    rolling_low = low_df.rolling(window, min_periods=window).min()
    return _safe_divide(close_df - rolling_low, (rolling_high - rolling_low))


def _intraday_return(open_df: pd.DataFrame, close_df: pd.DataFrame) -> pd.DataFrame:
    """日内收益率。"""
    return _safe_divide(close_df - open_df, open_df)

