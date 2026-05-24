"""技术指标因子：15 个（依赖 talib，若缺失则跳过该组）。"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ._helpers import HAS_TALIB

if HAS_TALIB:
    import talib


def _per_col(close: pd.DataFrame, func) -> pd.DataFrame:
    out = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
    for col in close.columns:
        try:
            out[col] = func(close[col].astype(float).to_numpy())
        except Exception:
            continue
    return out


def get_factors(panel: dict[str, pd.DataFrame], ctx: dict[str, Any]) -> dict[str, pd.DataFrame]:
    if not HAS_TALIB:
        print("⚠️ talib 不可用，indicator 组跳过")
        return {}
    close = panel["close"]
    high = panel.get("high", pd.DataFrame()).reindex_like(close).fillna(close)
    low = panel.get("low", pd.DataFrame()).reindex_like(close).fillna(close)
    out: dict[str, pd.DataFrame] = {}

    out["rsi_6"] = _per_col(close, lambda a: talib.RSI(a, timeperiod=6))
    out["rsi_14"] = _per_col(close, lambda a: talib.RSI(a, timeperiod=14))

    # MACD
    macd = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
    macd_signal = macd.copy()
    macd_hist = macd.copy()
    for col in close.columns:
        try:
            m, s, h = talib.MACD(close[col].astype(float).to_numpy(), 12, 26, 9)
            macd[col] = m
            macd_signal[col] = s
            macd_hist[col] = h
        except Exception:
            continue
    out["macd"] = macd
    out["macd_signal"] = macd_signal
    out["macd_hist"] = macd_hist

    # KDJ（用 STOCH 计算 k/d，再算 j = 3k - 2d）
    kdj_k = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
    kdj_d = kdj_k.copy()
    for col in close.columns:
        try:
            k, d = talib.STOCH(
                high[col].astype(float).to_numpy(),
                low[col].astype(float).to_numpy(),
                close[col].astype(float).to_numpy(),
                fastk_period=9, slowk_period=3, slowk_matype=0,
                slowd_period=3, slowd_matype=0,
            )
            kdj_k[col] = k
            kdj_d[col] = d
        except Exception:
            continue
    out["kdj_k"] = kdj_k
    out["kdj_d"] = kdj_d
    out["kdj_j"] = 3 * kdj_k - 2 * kdj_d

    # BOLL: %B 与 bandwidth
    boll_pct_b = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
    boll_bw = boll_pct_b.copy()
    for col in close.columns:
        try:
            up, mid, lo = talib.BBANDS(close[col].astype(float).to_numpy(), timeperiod=20, nbdevup=2, nbdevdn=2)
            band = up - lo
            boll_pct_b[col] = (close[col].to_numpy() - lo) / np.where(band == 0, np.nan, band)
            boll_bw[col] = band / np.where(mid == 0, np.nan, mid)
        except Exception:
            continue
    out["boll_pct_b"] = boll_pct_b
    out["boll_bandwidth"] = boll_bw

    # CCI / WR / CMO / TRIX
    out["cci_14"] = _hlc(close, high, low, lambda h, l, c: talib.CCI(h, l, c, timeperiod=14))
    out["wr_10"] = _hlc(close, high, low, lambda h, l, c: talib.WILLR(h, l, c, timeperiod=10))
    out["cmo_14"] = _per_col(close, lambda a: talib.CMO(a, timeperiod=14))
    out["trix_12"] = _per_col(close, lambda a: talib.TRIX(a, timeperiod=12))

    return out


def _hlc(close: pd.DataFrame, high: pd.DataFrame, low: pd.DataFrame, func) -> pd.DataFrame:
    out = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
    for col in close.columns:
        try:
            out[col] = func(
                high[col].astype(float).to_numpy(),
                low[col].astype(float).to_numpy(),
                close[col].astype(float).to_numpy(),
            )
        except Exception:
            continue
    return out
