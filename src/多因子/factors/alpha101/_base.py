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


def delta(df: pd.DataFrame, period: int = 1) -> pd.DataFrame:
    return df.diff(period)


def delay(df: pd.DataFrame, period: int = 1) -> pd.DataFrame:
    return df.shift(period)


def returns(close_df: pd.DataFrame) -> pd.DataFrame:
    return close_df.pct_change()


def rank(df: pd.DataFrame) -> pd.DataFrame:
    return df.rank(axis=1, pct=True)


def ts_rank(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).apply(
        lambda values: pd.Series(values).rank(pct=True).iloc[-1],
        raw=False,
    )


def ts_min(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).min()


def ts_max(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).max()


def stddev(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).std()


def correlation(x_df: pd.DataFrame, y_df: pd.DataFrame, window: int) -> pd.DataFrame:
    return x_df.rolling(window, min_periods=window).corr(y_df)


def covariance(x_df: pd.DataFrame, y_df: pd.DataFrame, window: int) -> pd.DataFrame:
    return x_df.rolling(window, min_periods=window).cov(y_df)


def signedpower(df: pd.DataFrame, power: float) -> pd.DataFrame:
    return np.sign(df) * np.power(np.abs(df), power)


def scale(df: pd.DataFrame, a: float = 1.0) -> pd.DataFrame:
    denom = df.abs().sum(axis=1).replace(0, np.nan)
    return df.mul(a).div(denom, axis=0)


def ts_argmax(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).apply(lambda values: float(np.argmax(values)) + 1.0, raw=True)


def ts_argmin(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).apply(lambda values: float(np.argmin(values)) + 1.0, raw=True)


def sum_ts(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).sum()


def product(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).apply(np.prod, raw=True)


def adv(volume_df: pd.DataFrame, window: int) -> pd.DataFrame:
    return volume_df.rolling(window, min_periods=window).mean()


def log(df: pd.DataFrame) -> pd.DataFrame:
    return np.log(df.replace(0, np.nan))


def sign(df: pd.DataFrame) -> pd.DataFrame:
    return np.sign(df)


def decay_linear(df: pd.DataFrame, window: int) -> pd.DataFrame:
    weights = np.arange(1, window + 1, dtype=float)
    weight_sum = weights.sum()
    return df.rolling(window, min_periods=window).apply(lambda values: float(np.dot(values, weights) / weight_sum), raw=True)


def ts_mean(df: pd.DataFrame, window: int) -> pd.DataFrame:
    return df.rolling(window, min_periods=window).mean()


def min_df(left: pd.DataFrame, right: pd.DataFrame | float) -> pd.DataFrame:
    if isinstance(right, pd.DataFrame):
        return left.combine(right, np.minimum)
    return left.clip(upper=right)


def max_df(left: pd.DataFrame, right: pd.DataFrame | float) -> pd.DataFrame:
    if isinstance(right, pd.DataFrame):
        return left.combine(right, np.maximum)
    return left.clip(lower=right)


def vwap(amount_df: pd.DataFrame, volume_df: pd.DataFrame) -> pd.DataFrame:
    return _safe_divide(amount_df, volume_df)
