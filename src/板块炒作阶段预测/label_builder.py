# -*- coding: utf-8 -*-
"""四阶段标签构造。

阶段定义（基于横截面分位 + 未来窗口表现）：
- 炒作末期：过去明显上涨且当前拥挤，未来超额收益转弱或回撤扩大。
- 正在炒作：过去强势、当前活跃，未来仍能延续超额收益。
- 预备炒作：过去未显著上涨，当前刚开始放量/扩散，未来明显走强。
- 冷门板块：过去与未来都缺乏超额收益和成交活跃度。

打标签优先级：炒作末期 > 正在炒作 > 预备炒作 > 冷门板块；不满足任一条件
的样本默认归为 ``中性``，可在配置中合并到冷门板块。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Mapping, Tuple

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

LABEL_PREP = "预备炒作"
LABEL_ACTIVE = "正在炒作"
LABEL_LATE = "炒作末期"
LABEL_COLD = "冷门板块"
LABEL_NEUTRAL = "中性板块"

LABEL_ORDER = (LABEL_PREP, LABEL_ACTIVE, LABEL_LATE, LABEL_COLD)
LABEL_TO_INT = {name: idx for idx, name in enumerate(LABEL_ORDER)}
INT_TO_LABEL = {idx: name for name, idx in LABEL_TO_INT.items()}


@dataclass
class LabelConfig:
    """标签构造配置。

    所有阈值均为横截面分位（每个交易日所有板块内部排名 0~1）。
    """

    horizon: int = 10
    short_horizon: int = 5
    long_horizon: int = 20
    # 共用：分位
    high_quantile: float = 0.75
    very_high_quantile: float = 0.85
    low_quantile: float = 0.5
    very_low_quantile: float = 0.4
    # 风险阈值（绝对值）
    drawdown_strong_negative: float = -0.10
    fail_future_excess: float = 0.0
    # 是否将"中性"合并到冷门板块（True=三/四分类；False=保留中性，输出 5 类）
    merge_neutral_to_cold: bool = True
    min_valid_samples_per_day: int = 10


def _rank_pct(df: pd.DataFrame) -> pd.DataFrame:
    return df.rank(axis=1, pct=True, method="average")


def _future_cum_return(daily_ret: pd.DataFrame, window: int) -> pd.DataFrame:
    """未来 ``[t+1, t+window]`` 的累计收益率（向后看 ``window`` 个交易日）。"""
    log_ret = np.log1p(daily_ret.fillna(0.0))
    cum_log = log_ret.cumsum()
    fwd_log = cum_log.shift(-window) - cum_log
    return np.expm1(fwd_log)


def _future_max_drawdown(daily_ret: pd.DataFrame, window: int) -> pd.DataFrame:
    """未来 ``window`` 日内的最大回撤（向后看）。

    实现：对每个 t，取 [t+1, t+window] 的累计净值序列，计算最大回撤。
    用循环逐板块计算（板块数量较少，约几百个，性能可接受）。
    """
    out = pd.DataFrame(index=daily_ret.index, columns=daily_ret.columns, dtype=float)
    log_ret = np.log1p(daily_ret.fillna(0.0)).values
    n = len(daily_ret)
    cols = daily_ret.columns
    for j, col in enumerate(cols):
        col_log = log_ret[:, j]
        col_dd = np.full(n, np.nan)
        for i in range(n - 1):
            end = min(n, i + 1 + window)
            window_log = col_log[i + 1:end]
            if window_log.size < 2:
                continue
            nav = np.exp(np.cumsum(window_log))
            running_max = np.maximum.accumulate(nav)
            dd = nav / running_max - 1.0
            col_dd[i] = float(np.min(dd))
        out[col] = col_dd
    return out


def build_labels(
    intermediates: Mapping[str, pd.DataFrame],
    config: LabelConfig | None = None,
) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """构造板块四阶段标签。

    Args:
        intermediates: ``feature_builder.build_sector_feature_table`` 返回的中间宽表。
        config: 标签配置。

    Returns:
        labels_long: ``MultiIndex(datetime, sector)`` 的 ``DataFrame``，
            包含 ``label`` 字符串列与 ``label_id`` 整数列，以及若干辅助列。
        debug_panels: 中间宽表（分位、未来收益等），便于检查标签质量。
    """
    config = config or LabelConfig()
    sector_excess = intermediates["sector_excess"]
    sector_ret = intermediates["sector_ret"]
    amount_share = intermediates["amount_share"]

    # 过去窗口分位
    past_excess_short = _rank_pct(
        sector_excess.rolling(config.short_horizon, min_periods=2).sum()
    )
    past_excess_main = _rank_pct(
        sector_excess.rolling(config.horizon, min_periods=2).sum()
    )
    past_excess_long = _rank_pct(
        sector_excess.rolling(config.long_horizon, min_periods=2).sum()
    )

    amount_share_rank = _rank_pct(amount_share)
    amount_share_short_rank = _rank_pct(
        amount_share.rolling(config.short_horizon, min_periods=2).mean()
    )

    # 未来窗口
    future_excess_main = _future_cum_return(sector_excess, config.horizon)
    future_excess_short = _future_cum_return(sector_excess, config.short_horizon)
    future_excess_long = _future_cum_return(sector_excess, config.long_horizon)
    future_excess_main_rank = _rank_pct(future_excess_main)
    future_excess_long_rank = _rank_pct(future_excess_long)
    future_drawdown_main = _future_max_drawdown(sector_ret, config.horizon)

    # 横截面有效样本数门槛：当日有效板块过少则该日不打标签
    valid_per_day = sector_excess.notna().sum(axis=1)
    valid_mask_day = valid_per_day >= config.min_valid_samples_per_day

    # 默认标签：中性（用 object 数组，避免字符串与 NaN 类型升级失败）
    label_array = np.full(sector_excess.shape, np.nan, dtype=object)
    valid_cell = valid_mask_day.values[:, None] & sector_excess.notna().values
    label_array[valid_cell] = LABEL_NEUTRAL
    label = pd.DataFrame(
        label_array, index=sector_excess.index, columns=sector_excess.columns
    )

    high = config.high_quantile
    very_high = config.very_high_quantile
    low = config.low_quantile
    very_low = config.very_low_quantile

    # 1) 炒作末期：过去强 + 当前拥挤 + 未来弱/回撤
    late_mask = (
        (past_excess_long >= very_high)
        & (amount_share_rank >= high)
        & (
            (future_excess_main_rank <= low)
            | (future_drawdown_main <= config.drawdown_strong_negative)
        )
    )

    # 2) 正在炒作：过去强 + 当前活跃 + 未来延续
    active_mask = (
        (past_excess_main >= high)
        & (amount_share_rank >= high)
        & (future_excess_short > config.fail_future_excess)
        & (future_excess_main_rank >= 0.5)
    )

    # 3) 预备炒作：过去不算高 + 当前刚活跃 + 未来明显强
    prep_mask = (
        (past_excess_main < high)
        & (past_excess_long < very_high)
        & (amount_share_short_rank >= 0.6)
        & (future_excess_main_rank >= very_high)
    )

    # 4) 冷门板块：过去弱 + 当前弱 + 未来弱
    cold_mask = (
        (past_excess_main <= low)
        & (amount_share_rank <= very_low)
        & (future_excess_main_rank <= low)
    )

    # 优先级：炒作末期 > 正在炒作 > 预备炒作 > 冷门板块
    label = label.mask(cold_mask, LABEL_COLD)
    label = label.mask(prep_mask, LABEL_PREP)
    label = label.mask(active_mask, LABEL_ACTIVE)
    label = label.mask(late_mask, LABEL_LATE)

    if config.merge_neutral_to_cold:
        label = label.where(label != LABEL_NEUTRAL, LABEL_COLD)

    label_long = label.stack(future_stack=True).dropna().rename("label")
    label_long.index.set_names(["datetime", "sector"], inplace=True)

    aux = pd.DataFrame({
        "future_excess_main": future_excess_main.stack(future_stack=True),
        "future_excess_long": future_excess_long.stack(future_stack=True),
        "future_drawdown_main": future_drawdown_main.stack(future_stack=True),
        "past_excess_main_rank": past_excess_main.stack(future_stack=True),
        "past_excess_long_rank": past_excess_long.stack(future_stack=True),
        "amount_share_rank": amount_share_rank.stack(future_stack=True),
    })
    aux.index.set_names(["datetime", "sector"], inplace=True)

    labels_long = label_long.to_frame().join(aux, how="left")
    labels_long["label_id"] = labels_long["label"].map(LABEL_TO_INT)

    debug_panels: Dict[str, pd.DataFrame] = {
        "past_excess_main_rank": past_excess_main,
        "past_excess_long_rank": past_excess_long,
        "amount_share_rank": amount_share_rank,
        "future_excess_main": future_excess_main,
        "future_excess_main_rank": future_excess_main_rank,
        "future_drawdown_main": future_drawdown_main,
        "label_wide": label,
    }

    counts = labels_long["label"].value_counts(dropna=True).to_dict()
    LOGGER.info("标签分布: %s", counts)
    return labels_long, debug_panels
