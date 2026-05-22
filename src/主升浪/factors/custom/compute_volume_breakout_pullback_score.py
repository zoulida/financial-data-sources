"""放量突破前高 + 回踩 N 日——形态强度连续因子（不再约束缩量）。

在原"突破 + 缩量回踩"形态基础上做两点改动：
    1. 取消缩量条件：不再要求回踩期间成交量必须收缩到突破日的某比例以下。
    2. 回踩窗口缩短：从 5 日改为 3 日（``pullback_window`` 默认 3），让信号更贴近主升浪节奏。

强度由两个分量相乘得到：
    1. 突破幅度  s_breakout = clip(close_breakout / rolling_high_breakout - 1, 0)
    2. 放量倍数  s_volume   = clip(volume_breakout / volume_mean_breakout - 1.5, 0)
其中 *_breakout 后缀表示"该值取自最近一次放量突破日的当日值"，通过 ffill 延续到当前事件触发日。

事件触发日（突破后第 ``pullback_window`` 个交易日）的强度为两项之积；事件触发后再按
``decay_rate`` 指数衰减，窗口 ``decay_window`` 之外归 0；从未满足过形态的位置始终为 0。
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def compute_volume_breakout_pullback_score(
    close_df: pd.DataFrame,
    high_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    lookback_window: int = 60,
    breakout_window: int = 20,
    pullback_window: int = 3,
    decay_rate: float = 0.7,
    decay_window: int = 5,
) -> pd.DataFrame:
    """放量突破前高 + 回踩 N 日——形态强度连续因子（不约束缩量）。

    Args:
        close_df: 收盘价宽表（index=date, columns=code）。
        high_df: 最高价宽表，形状与 ``close_df`` 一致。
        volume_df: 成交量宽表，形状与 ``close_df`` 一致。
        lookback_window: 前高及成交量均值的回看窗口，默认 60 个交易日。
        breakout_window: 突破检测窗口（事件触发日距突破日的最大天数），默认 20。
        pullback_window: 回踩窗口（突破后等待 N 个交易日才作为事件触发日），默认 3。
        decay_rate: 事件触发后每过一日的强度衰减系数，默认 0.7。
        decay_window: 事件触发后强度延续天数，超过则归 0，默认 5。

    Returns:
        与 ``close_df`` 形状一致的强度矩阵，值域 ``[0, +∞)``。绝大多数位置为 0，
        事件触发当日及其后 ``decay_window`` 日内为正数。
    """
    if close_df.empty or high_df.empty or volume_df.empty:
        return close_df.copy() * 0.0

    assert close_df.shape == high_df.shape == volume_df.shape, "输入 DataFrame 形状不一致"

    # ---------------- 1. 还原放量突破日的判定 ----------------
    # 前高（不含当天）
    rolling_high = (
        high_df.rolling(window=lookback_window, min_periods=lookback_window).max().shift(1)
    )
    # 60 日均量（不含当天）
    volume_mean = (
        volume_df.rolling(window=lookback_window, min_periods=lookback_window).mean().shift(1)
    )

    # 放量突破：收盘 > 前高 且 成交量 > 1.5 × 60 日均量
    breakout = (close_df > rolling_high) & (volume_df > 1.5 * volume_mean)

    # 在突破日保留对应量，其余位置 NaN，再向后 ffill 延续到事件触发日
    breakout_close = close_df.where(breakout)
    breakout_rh = rolling_high.where(breakout)
    breakout_vol = volume_df.where(breakout)
    breakout_vmean = volume_mean.where(breakout)

    ff_close = breakout_close.ffill(limit=breakout_window)
    ff_rh = breakout_rh.ffill(limit=breakout_window)
    ff_vol = breakout_vol.ffill(limit=breakout_window)
    ff_vmean = breakout_vmean.ffill(limit=breakout_window)

    # 事件触发条件（去掉缩量约束）：
    #   1) 过去 breakout_window 天内有过突破
    #   2) 突破发生在 pullback_window 天之前（即"回踩 N 天"已经过去）
    has_breakout_recently = (
        breakout.astype(int).rolling(window=breakout_window, min_periods=1).max() > 0
    )
    has_breakout_before_pullback = (
        breakout.astype(int)
        .shift(pullback_window)
        .rolling(window=breakout_window, min_periods=1)
        .max()
        > 0
    )

    final_condition = (has_breakout_recently & has_breakout_before_pullback).fillna(False)

    # ---------------- 2. 形态强度两分量 ----------------
    s_breakout = (ff_close / ff_rh - 1.0).clip(lower=0.0)
    s_volume = (ff_vol / ff_vmean - 1.5).clip(lower=0.0)

    strength_raw = s_breakout * s_volume

    # 仅在事件触发日保留强度，其它位置 0
    strength_event = strength_raw.where(final_condition, other=0.0).fillna(0.0)

    # ---------------- 3. 事件后指数衰减 ----------------
    # 思路：把触发日的强度向后 ffill 至多 decay_window 日；再用"距最近触发日的天数"做指数衰减。
    trigger_mask = strength_event > 0

    # 触发日强度（NaN 表示非触发日），ffill 限制 decay_window
    trigger_strength = strength_event.where(trigger_mask)
    ff_strength = trigger_strength.ffill(limit=decay_window)

    # 距最近触发日的天数：用行号差实现向量化
    row_idx_1d = np.arange(len(close_df.index), dtype=float)
    row_idx_arr = np.broadcast_to(row_idx_1d[:, None], close_df.shape)
    row_idx_df = pd.DataFrame(
        row_idx_arr.copy(), index=close_df.index, columns=close_df.columns
    )
    trigger_row = row_idx_df.where(trigger_mask)
    ff_trigger_row = trigger_row.ffill(limit=decay_window)
    days_since = row_idx_df - ff_trigger_row  # 触发日为 0，其后递增；超出窗口为 NaN

    decay_factor = np.power(decay_rate, days_since)
    score = (ff_strength * decay_factor).fillna(0.0)

    # 与 close_df 严格对齐
    score = score.reindex_like(close_df).fillna(0.0)
    return score
