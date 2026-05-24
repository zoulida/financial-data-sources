"""量价相关性因子：8 个。"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ._helpers import HAS_TALIB

if HAS_TALIB:
    import talib


def get_factors(panel: dict[str, pd.DataFrame], ctx: dict[str, Any]) -> dict[str, pd.DataFrame]:
    close = panel["close"]
    high = panel.get("high", pd.DataFrame()).reindex_like(close)
    low = panel.get("low", pd.DataFrame()).reindex_like(close)
    vol = panel.get("vol", pd.DataFrame()).reindex_like(close)
    amount = panel.get("amount", pd.DataFrame()).reindex_like(close)
    returns = close.pct_change(fill_method=None)
    out: dict[str, pd.DataFrame] = {}

    # 滚动相关性：rolling.corr 接受 DataFrame 时按列对齐
    if not vol.empty:
        out["corr_close_vol_20"] = close.rolling(20).corr(vol)
        out["corr_ret_vol_20"] = returns.rolling(20).corr(vol)
        out["corr_close_vol_60"] = close.rolling(60).corr(vol)
    if not amount.empty:
        out["corr_close_amt_20"] = close.rolling(20).corr(amount)
        out["corr_ret_amt_20"] = returns.rolling(20).corr(amount)

    # 量价背离：sign(ret) * sign(Δvol) 反向比例（即两者反号的比例）
    if not vol.empty:
        sign_ret = np.sign(returns)
        sign_dvol = np.sign(vol.diff())
        diverge = (sign_ret * sign_dvol < 0).astype(float)
        out["vp_div_20"] = diverge.rolling(20).mean()

    # OBV 20 日斜率
    if HAS_TALIB and not vol.empty:
        obv = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
        for col in close.columns:
            try:
                obv[col] = talib.OBV(
                    close[col].astype(float).to_numpy(),
                    vol[col].astype(float).to_numpy(),
                )
            except Exception:
                continue
        # 简单斜率：OBV - OBV.shift(20)
        out["obv_slope_20"] = (obv - obv.shift(20)) / obv.rolling(20).std().replace(0.0, np.nan)

    # MFI_14
    if HAS_TALIB and not high.empty and not low.empty and not vol.empty:
        mfi = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
        for col in close.columns:
            try:
                mfi[col] = talib.MFI(
                    high[col].astype(float).to_numpy(),
                    low[col].astype(float).to_numpy(),
                    close[col].astype(float).to_numpy(),
                    vol[col].astype(float).to_numpy(),
                    timeperiod=14,
                )
            except Exception:
                continue
        out["mfi_14"] = mfi

    return out
