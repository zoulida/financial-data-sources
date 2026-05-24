"""相对强度 / 形态因子：10 个。"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ._helpers import max_streak, safe_div


def get_factors(panel: dict[str, pd.DataFrame], ctx: dict[str, Any]) -> dict[str, pd.DataFrame]:
    close = panel["close"]
    returns = close.pct_change(fill_method=None)
    out: dict[str, pd.DataFrame] = {}

    index_close = ctx.get("index_close")  # pd.Series（索引 = 日期）
    if isinstance(index_close, pd.Series) and not index_close.empty:
        index_close = index_close.reindex(close.index).ffill()
        idx_ret = index_close.pct_change(fill_method=None)
        # 个股 - 指数 累计收益
        for w in (20, 60):
            stock_cum = close.pct_change(w, fill_method=None)
            idx_cum = (index_close / index_close.shift(w) - 1.0).reindex(close.index)
            out[f"rel_alpha_{w}"] = stock_cum.sub(idx_cum, axis=0)
        # Beta_60：逐列 corr，避免 rolling.corr(DataFrame, Series) 在某些 pandas 版本触发 Grouper 报错
        std_stock = returns.rolling(60).std()
        std_idx = idx_ret.rolling(60).std().reindex(close.index)
        corr60 = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
        idx_aligned = idx_ret.reindex(close.index)
        for col in close.columns:
            corr60[col] = returns[col].rolling(60).corr(idx_aligned)
        out["beta_60"] = corr60.mul(std_stock, axis=0).div(std_idx.replace(0.0, np.nan), axis=0)
        # 相对强度：个股 60 日累计 / 指数 60 日累计
        s_cum = close / close.shift(60) - 1.0
        i_cum = (index_close / index_close.shift(60) - 1.0).reindex(close.index)
        out["relative_strength_60"] = (1.0 + s_cum).div(1.0 + i_cum, axis=0)

    # 上涨天数（20 日）
    up = (returns > 0).astype(float)
    down = (returns < 0).astype(float)
    out["up_days_20"] = up.rolling(20).sum()
    out["green_red_diff_20"] = up.rolling(20).sum() - down.rolling(20).sum()

    # 最长连阳/连阴天数
    out["up_streak_max_20"] = max_streak(returns > 0, 20)
    out["down_streak_max_20"] = max_streak(returns < 0, 20)

    # 涨停/跌停近似（日涨幅 ≥ 9.5% / ≤ -9.5%）
    out["limit_up_count_20"] = (returns >= 0.095).astype(float).rolling(20).sum()
    out["limit_down_count_20"] = (returns <= -0.095).astype(float).rolling(20).sum()

    return out
