from __future__ import annotations

import numpy as np
import pandas as pd


def compute_mwega_1779417203_004(open_df, high_df, low_df, close_df, volume_df) -> pd.DataFrame:
    def _b(x):
        return (x.astype(float).fillna(0.0) >= 0.5).astype(float)
    def _any(x, window):
        return (_b(x).rolling(int(window), min_periods=1).max() > 0).astype(float)
    def _count_ge(x, window, threshold):
        return (_b(x).rolling(int(window), min_periods=1).sum() >= int(threshold)).astype(float)
    def _then(a, b, min_gap, max_gap):
        left = _b(a)
        prior = pd.DataFrame(0.0, index=left.index, columns=left.columns)
        for gap in range(int(min_gap), int(max_gap) + 1):
            shifted = left.shift(gap)
            prior = prior.where(prior >= shifted, shifted)
        return (prior * _b(b)).astype(float)
    def _decay(x, window):
        base = _b(x)
        out = pd.DataFrame(0.0, index=base.index, columns=base.columns)
        w = int(window)
        for gap in range(w):
            shifted = base.shift(gap) * (float(w - gap) / float(w))
            out = out.where(out >= shifted, shifted)
        return out.astype(float)
    ret1 = close_df / close_df.shift(1) - 1.0
    gap = open_df / close_df.shift(1) - 1.0
    body_high = close_df.where(close_df >= open_df, open_df)
    body_low = close_df.where(close_df <= open_df, open_df)
    day_range = (high_df - low_df).replace(0.0, np.nan)
    upper_shadow = (high_df - body_high) / day_range
    lower_shadow = (body_low - low_df) / day_range
    body_abs = (close_df - open_df).abs() / open_df.replace(0.0, np.nan)
    close_pos = (close_df - low_df) / day_range
    amount_proxy = close_df * volume_df
    ma5 = close_df.rolling(5, min_periods=5).mean()
    ma10 = close_df.rolling(10, min_periods=10).mean()
    ma20 = close_df.rolling(20, min_periods=20).mean()
    hh20 = close_df.rolling(20, min_periods=20).max()
    hh60 = close_df.rolling(60, min_periods=30).max()
    ll10 = close_df.rolling(10, min_periods=5).min()
    vol_ma5 = volume_df.rolling(5, min_periods=3).mean()
    vol_ma20 = volume_df.rolling(20, min_periods=5).mean()
    amt_ma20 = amount_proxy.rolling(20, min_periods=5).mean()
    ret3 = close_df / close_df.shift(3) - 1.0
    ret5 = close_df / close_df.shift(5) - 1.0
    ret20 = close_df / close_df.shift(20) - 1.0
    event_big_down = (ret1 <= -0.045).astype(float)
    event_big_up = (ret1 >= 0.045).astype(float)
    event_ma_bull_order = ((ma5 > ma10) & (ma10 >= ma20 * 0.995) & (close_df > ma20)).astype(float)
    result = ((event_ma_bull_order).where((event_ma_bull_order) <= (((_count_ge(event_big_up, 20, 2)).where((_count_ge(event_big_up, 20, 2)) <= ((1.0 - _any(event_big_down, 5))), ((1.0 - _any(event_big_down, 5)))))), (((_count_ge(event_big_up, 20, 2)).where((_count_ge(event_big_up, 20, 2)) <= ((1.0 - _any(event_big_down, 5))), ((1.0 - _any(event_big_down, 5))))))))
    return result.astype(float).replace([np.inf, -np.inf], np.nan)
