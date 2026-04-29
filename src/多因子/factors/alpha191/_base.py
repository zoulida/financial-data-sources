from __future__ import annotations

import warnings

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


def rank(df: pd.DataFrame) -> pd.DataFrame:
    return df.rank(axis=1, pct=True)


def ts_rank(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).apply(
        lambda values: pd.Series(values).rank(pct=True).iloc[-1],
        raw=False,
    )


def ts_mean(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).mean()


def ts_std(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).std()


def ts_min(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).min()


def ts_max(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).max()


def correlation(x_df: pd.DataFrame, y_df: pd.DataFrame, window: int) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="invalid value encountered in divide", category=RuntimeWarning)
        return x_df.rolling(window, min_periods=window).corr(y_df)


def delta(df: pd.DataFrame, period: int = 1) -> pd.DataFrame:
    return df.diff(period)


def delay(df: pd.DataFrame, period: int = 1) -> pd.DataFrame:
    return df.shift(period)


def scale(df: pd.DataFrame) -> pd.DataFrame:
    denom = df.abs().sum(axis=1).replace(0, np.nan)
    return df.div(denom, axis=0)


def vwap(amount_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    return _safe_divide(amount_df, volume_df)


def template_alpha191(
    alpha_id: int,
    open_df: pd.DataFrame,
    high_df: pd.DataFrame,
    low_df: pd.DataFrame,
    close_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    amount_df: pd.DataFrame,
) -> pd.DataFrame:
    windows = [3, 5, 8, 10, 13, 20, 30, 60]
    window = windows[(alpha_id - 1) % len(windows)]
    short_window = windows[(alpha_id + 1) % len(windows)]
    typical_price = (high_df + low_df + close_df) / 3
    vwap_df = vwap(amount_df, volume_df)
    returns_df = close_df.pct_change()
    pattern = (alpha_id - 1) % 12

    if pattern == 0:
        return rank(_safe_divide(close_df, ts_mean(close_df, window)) - 1)
    if pattern == 1:
        return -rank(ts_std(returns_df, window))
    if pattern == 2:
        return rank(_safe_divide(close_df - ts_min(low_df, window), ts_max(high_df, window) - ts_min(low_df, window)))
    if pattern == 3:
        return -rank(correlation(rank(close_df), rank(volume_df), window))
    if pattern == 4:
        return rank(_safe_divide(ts_mean(volume_df, short_window), ts_mean(volume_df, window)) - 1)
    if pattern == 5:
        return rank(_safe_divide(vwap_df, close_df) - 1)
    if pattern == 6:
        return rank(delta(close_df, max(1, short_window // 2)))
    if pattern == 7:
        return -rank(_safe_divide(high_df - low_df, close_df))
    if pattern == 8:
        return rank(_safe_divide(close_df - open_df, open_df))
    if pattern == 9:
        return rank(ts_rank(returns_df, window))
    if pattern == 10:
        return -rank(_safe_divide(ts_mean(amount_df, short_window), ts_mean(amount_df, window)) - 1)
    return scale(rank(typical_price - delay(typical_price, max(1, short_window // 2))))
