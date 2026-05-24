"""波动 / 振幅因子：8 个。"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ._helpers import HAS_TALIB, apply_per_column

if HAS_TALIB:
    import talib


def get_factors(panel: dict[str, pd.DataFrame], ctx: dict[str, Any]) -> dict[str, pd.DataFrame]:
    close = panel["close"]
    high = panel.get("high", pd.DataFrame()).reindex_like(close)
    low = panel.get("low", pd.DataFrame()).reindex_like(close)
    returns = close.pct_change(fill_method=None)
    out: dict[str, pd.DataFrame] = {}

    out["vol_5"] = returns.rolling(5).std()
    out["vol_20"] = returns.rolling(20).std()
    out["vol_60"] = returns.rolling(60).std()

    # 下行波动率：仅取负收益
    neg = returns.where(returns < 0)
    out["downside_vol_20"] = neg.rolling(20).std()

    # 平均振幅
    if not high.empty and not low.empty:
        out["amp_20"] = ((high - low) / close).rolling(20).mean()

        # 跳空频率：|open - prev_close| / prev_close > 1% 比例
        open_ = panel.get("open", pd.DataFrame()).reindex_like(close)
        if not open_.empty:
            gap = (open_ - close.shift(1)).abs() / close.shift(1)
            out["gap_freq_20"] = (gap > 0.01).astype(float).rolling(20).mean()

        # 20 日内最大回撤
        rolling_max = close.rolling(20).max()
        out["max_drawdown_20"] = close / rolling_max - 1.0

        # ATR_14
        if HAS_TALIB:
            def _atr(arr_close, arr_high, arr_low):
                return talib.ATR(arr_high, arr_low, arr_close, timeperiod=14)

            atr_df = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
            for col in close.columns:
                try:
                    atr_df[col] = talib.ATR(
                        high[col].astype(float).to_numpy(),
                        low[col].astype(float).to_numpy(),
                        close[col].astype(float).to_numpy(),
                        timeperiod=14,
                    )
                except Exception:
                    continue
            out["atr_14"] = atr_df / close

    return out
