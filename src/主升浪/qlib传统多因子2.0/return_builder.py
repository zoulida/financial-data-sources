#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore
"""未来收益构造器。

提供三种口径，统一返回 ``行=date, 列=instrument`` 的宽表 ``pd.DataFrame``：

- ``holding_close``：持有期 close-to-close 收益，``close[t+N] / close[t] - 1``。
- ``max_high``：未来 N 日内最高价 ``max(high[t+1..t+N]) / close[t] - 1``。
- ``max_close``：未来 N 日内最高收盘价 ``max(close[t+1..t+N]) / close[t] - 1``。

注意：
- ``max_high`` / ``max_close`` 只能用于因子评价与 ML 标签，不应用于回测净值（最高价通常无法实际成交）。
- 当 ``holding_period <= 0`` 时会抛 ``ValueError``。
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

VALID_MODES = ("holding_close", "max_high", "max_close")


def _validate(panel: Dict[str, pd.DataFrame], required_keys) -> None:
    missing = [key for key in required_keys if key not in panel or panel[key] is None]
    if missing:
        raise KeyError(f"panel 缺少必需字段: {missing}")


def _max_in_future_window(series_df: pd.DataFrame, holding_period: int) -> pd.DataFrame:
    """计算 ``[t+1, t+N]`` 区间的最大值（不含当日）。

    实现方式：对原序列向上 shift(-1)，再做长度 N 的 rolling.max()，再向上 shift(N-1)。
    等价于：``forward_max[t] = max(series[t+1], ..., series[t+N])``。
    """
    if holding_period <= 0:
        raise ValueError(f"holding_period 必须 > 0，当前为 {holding_period}")
    shifted = series_df.shift(-1)
    rolling_max = shifted.rolling(window=holding_period, min_periods=1).max()
    # rolling 默认在窗口右端记录结果，因此再向上 shift(N-1) 即可对齐到 t。
    return rolling_max.shift(-(holding_period - 1))


def build_future_return(
    panel: Dict[str, pd.DataFrame],
    mode: str,
    holding_period: int,
) -> pd.DataFrame:
    """根据指定模式计算未来收益矩阵。

    Args:
        panel: 行情宽表字典，需包含 ``close`` 字段；``max_high`` 模式还需 ``high``。
        mode: ``"holding_close"`` / ``"max_high"`` / ``"max_close"``。
        holding_period: 持有期 N。

    Returns:
        与 ``panel["close"]`` 同形状的 ``pd.DataFrame``。
    """
    if mode not in VALID_MODES:
        raise ValueError(f"mode 必须是 {VALID_MODES}，当前为 {mode}")
    if holding_period <= 0:
        raise ValueError(f"holding_period 必须 > 0，当前为 {holding_period}")

    _validate(panel, ["close"])
    close = panel["close"].astype(float)

    if mode == "holding_close":
        future_price = close.shift(-holding_period)
    elif mode == "max_close":
        future_price = _max_in_future_window(close, holding_period)
    elif mode == "max_high":
        _validate(panel, ["high"])
        future_price = _max_in_future_window(panel["high"].astype(float), holding_period)
    else:  # pragma: no cover
        raise AssertionError("unreachable")

    base = close.replace(0.0, np.nan)
    future_return = future_price.divide(base) - 1.0
    return future_return.replace([np.inf, -np.inf], np.nan)


def build_holding_period_return(
    panel: Dict[str, pd.DataFrame],
    holding_period: int,
) -> pd.DataFrame:
    """专用于回测净值的 close-to-close 收益矩阵。

    无论用户的 ``future_return_mode`` 是什么，回测净值统一使用此口径，避免
    最高价无法实际成交带来的失真。
    """
    return build_future_return(panel, "holding_close", holding_period)
