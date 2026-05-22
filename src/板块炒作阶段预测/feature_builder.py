# -*- coding: utf-8 -*-
"""板块特征工程。

输入：
- ``panel``：``{字段: DataFrame(index=datetime, columns=qlib_code)}``，由
  ``qlib_market_loader.load_market_panel`` 提供。
- ``universe``：``{板块名: [XtQuant 代码列表]}``。

输出：
- ``feature_panel``：``MultiIndex(datetime, sector)`` 的长表 ``DataFrame``，
  包含若干板块级特征列。
- 同时返回若干中间宽表，便于标签构造与解释。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from .code_utils import xt_to_qlib

LOGGER = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """板块特征工程配置。"""

    short_windows: Sequence[int] = field(default_factory=lambda: [3, 5, 10])
    mid_windows: Sequence[int] = field(default_factory=lambda: [20, 60])
    amount_baseline_window: int = 20
    big_up_threshold: float = 0.05
    big_down_threshold: float = -0.05
    near_limit_up_threshold: float = 0.085
    top_contrib_k: int = 5
    min_members_for_feature: int = 5


def _members_to_qlib(members: Iterable[str]) -> List[str]:
    return [xt_to_qlib(c) for c in members]


def _safe_sub_panel(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """安全地按列子集化，缺失列填充 NaN。"""
    valid = [c for c in columns if c in df.columns]
    if not valid:
        return pd.DataFrame(index=df.index)
    return df[valid]


def compute_returns_panel(panel: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """股票级日度收益率宽表。"""
    close = panel["close"]
    returns = close.pct_change(fill_method=None)
    return returns.replace([np.inf, -np.inf], np.nan)


def compute_market_return(returns: pd.DataFrame) -> pd.Series:
    """全市场等权日收益率（剔除 NaN 后横截面均值）。"""
    return returns.mean(axis=1, skipna=True)


def compute_sector_return(
    returns: pd.DataFrame,
    members_qlib: Sequence[str],
) -> pd.Series:
    """单个板块的等权日收益率。"""
    sub = _safe_sub_panel(returns, members_qlib)
    if sub.empty:
        return pd.Series(dtype=float, index=returns.index)
    return sub.mean(axis=1, skipna=True)


def compute_sector_amount(
    amount: pd.DataFrame,
    members_qlib: Sequence[str],
) -> pd.Series:
    """单个板块的日成交额（成分股之和）。"""
    sub = _safe_sub_panel(amount, members_qlib)
    if sub.empty:
        return pd.Series(dtype=float, index=amount.index)
    return sub.sum(axis=1, min_count=1)


def _rolling_cum_return(daily_ret: pd.Series, window: int) -> pd.Series:
    log_ret = np.log1p(daily_ret.fillna(0.0))
    cum = log_ret.rolling(window, min_periods=max(2, window // 2)).sum()
    return np.expm1(cum)


def _rolling_max_drawdown(daily_ret: pd.Series, window: int) -> pd.Series:
    log_ret = np.log1p(daily_ret.fillna(0.0))
    nav = np.exp(log_ret.cumsum())
    rolling_max = nav.rolling(window, min_periods=2).max()
    dd = nav / rolling_max - 1.0
    return dd.rolling(window, min_periods=2).min()


def _rolling_amount_ratio(amount: pd.Series, baseline_window: int) -> pd.Series:
    base = amount.rolling(baseline_window, min_periods=max(5, baseline_window // 2)).mean()
    return amount / base.replace(0.0, np.nan)


def _up_ratio(returns_sub: pd.DataFrame) -> pd.Series:
    if returns_sub.empty:
        return pd.Series(dtype=float)
    valid = returns_sub.notna().sum(axis=1)
    up = (returns_sub > 0).sum(axis=1)
    return up / valid.replace(0, np.nan)


def _ratio_above(returns_sub: pd.DataFrame, threshold: float) -> pd.Series:
    if returns_sub.empty:
        return pd.Series(dtype=float)
    valid = returns_sub.notna().sum(axis=1)
    cnt = (returns_sub >= threshold).sum(axis=1)
    return cnt / valid.replace(0, np.nan)


def _ratio_below(returns_sub: pd.DataFrame, threshold: float) -> pd.Series:
    if returns_sub.empty:
        return pd.Series(dtype=float)
    valid = returns_sub.notna().sum(axis=1)
    cnt = (returns_sub <= threshold).sum(axis=1)
    return cnt / valid.replace(0, np.nan)


def _outperform_ratio(returns_sub: pd.DataFrame, market_ret: pd.Series) -> pd.Series:
    if returns_sub.empty:
        return pd.Series(dtype=float)
    diff = returns_sub.sub(market_ret, axis=0)
    valid = diff.notna().sum(axis=1)
    win = (diff > 0).sum(axis=1)
    return win / valid.replace(0, np.nan)


def _top_contribution(returns_sub: pd.DataFrame, top_k: int) -> pd.Series:
    """近似计算板块涨幅由 Top-k 个股贡献的占比（绝对值法）。"""
    if returns_sub.empty:
        return pd.Series(dtype=float)
    abs_ret = returns_sub.abs()
    total = abs_ret.sum(axis=1, min_count=1)

    def _row_top_share(row: pd.Series) -> float:
        clean = row.dropna()
        if clean.empty:
            return np.nan
        k = min(top_k, len(clean))
        top_sum = clean.nlargest(k).sum()
        denom = clean.sum()
        if denom == 0:
            return np.nan
        return float(top_sum / denom)

    share = abs_ret.apply(_row_top_share, axis=1)
    return share.where(total.notna())


def build_sector_feature_table(
    panel: Mapping[str, pd.DataFrame],
    universe: Mapping[str, Sequence[str]],
    config: FeatureConfig | None = None,
) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """构造板块特征长表。

    Returns:
        feature_long: ``MultiIndex(datetime, sector)`` 的特征 ``DataFrame``。
        intermediates: 中间宽表，键包括
            ``sector_ret``、``sector_excess``、``sector_amount``、
            ``market_ret``、``amount_share``。
    """
    config = config or FeatureConfig()
    returns = compute_returns_panel(panel)
    market_ret = compute_market_return(returns)
    market_amount = panel["amount"].sum(axis=1, min_count=1)

    sector_ret_dict: Dict[str, pd.Series] = {}
    sector_amount_dict: Dict[str, pd.Series] = {}
    rows: List[pd.DataFrame] = []

    for sector_name, members_xt in universe.items():
        members_qlib = _members_to_qlib(members_xt)
        members_in_panel = [c for c in members_qlib if c in returns.columns]
        if len(members_in_panel) < config.min_members_for_feature:
            LOGGER.debug("跳过 %s（覆盖成分 %d）", sector_name, len(members_in_panel))
            continue

        sub_ret = returns[members_in_panel]
        sub_amount = panel["amount"][members_in_panel] if "amount" in panel else None

        sector_ret = sub_ret.mean(axis=1, skipna=True)
        sector_excess = sector_ret - market_ret
        sector_amount = sub_amount.sum(axis=1, min_count=1) if sub_amount is not None else pd.Series(index=returns.index, dtype=float)
        amount_share = sector_amount / market_amount.replace(0.0, np.nan)
        amount_ratio = _rolling_amount_ratio(sector_amount, config.amount_baseline_window)

        feats: Dict[str, pd.Series] = {}

        # 过去收益强度
        for w in list(config.short_windows) + list(config.mid_windows):
            feats[f"past_ret_{w}d"] = _rolling_cum_return(sector_ret, w)
            feats[f"past_excess_{w}d"] = _rolling_cum_return(sector_excess, w)

        # 成交活跃度
        feats["amount_share"] = amount_share
        feats[f"amount_ratio_{config.amount_baseline_window}d"] = amount_ratio
        for w in config.short_windows:
            feats[f"amount_share_mean_{w}d"] = amount_share.rolling(w, min_periods=2).mean()
            feats[f"amount_ratio_mean_{w}d"] = amount_ratio.rolling(w, min_periods=2).mean()

        # 扩散度
        for w in config.short_windows:
            window_ret = sub_ret.rolling(w, min_periods=max(2, w // 2)).mean()
            feats[f"up_ratio_{w}d"] = _up_ratio(window_ret)
            feats[f"big_up_ratio_{w}d"] = _ratio_above(window_ret, config.big_up_threshold / w)
            feats[f"near_limit_up_ratio_{w}d"] = _ratio_above(window_ret, config.near_limit_up_threshold / w)
            feats[f"outperform_ratio_{w}d"] = _outperform_ratio(window_ret, market_ret.rolling(w, min_periods=max(2, w // 2)).mean())

        # 趋势/拥挤
        for w in config.short_windows + list(config.mid_windows):
            feats[f"volatility_{w}d"] = sector_ret.rolling(w, min_periods=max(3, w // 2)).std()
            feats[f"max_drawdown_{w}d"] = _rolling_max_drawdown(sector_ret, w)
        feats[f"top{config.top_contrib_k}_contribution_5d"] = _top_contribution(
            sub_ret.rolling(5, min_periods=2).sum(), config.top_contrib_k
        )

        # 当日点估计
        feats["sector_ret_1d"] = sector_ret
        feats["sector_excess_1d"] = sector_excess
        feats["market_ret_1d"] = market_ret
        feats["n_members"] = pd.Series(len(members_in_panel), index=sector_ret.index, dtype=float)

        feat_df = pd.DataFrame(feats)
        feat_df["sector"] = sector_name
        feat_df = feat_df.set_index("sector", append=True)
        feat_df.index.set_names(["datetime", "sector"], inplace=True)
        rows.append(feat_df)

        sector_ret_dict[sector_name] = sector_ret
        sector_amount_dict[sector_name] = sector_amount

    if not rows:
        raise ValueError("没有任何板块通过最小成分数过滤，无法构造特征")

    feature_long = pd.concat(rows).sort_index()
    feature_long = feature_long.replace([np.inf, -np.inf], np.nan)

    sector_ret_wide = pd.DataFrame(sector_ret_dict)
    sector_amount_wide = pd.DataFrame(sector_amount_dict)
    sector_excess_wide = sector_ret_wide.sub(market_ret, axis=0)
    amount_share_wide = sector_amount_wide.div(market_amount.replace(0.0, np.nan), axis=0)

    intermediates = {
        "sector_ret": sector_ret_wide,
        "sector_excess": sector_excess_wide,
        "sector_amount": sector_amount_wide,
        "amount_share": amount_share_wide,
        "market_ret": market_ret.to_frame(name="market_ret"),
        "market_amount": market_amount.to_frame(name="market_amount"),
    }

    LOGGER.info(
        "板块特征构造完成：%d 个板块，特征 %d 列，长表 %d 行",
        len(rows), feature_long.shape[1], feature_long.shape[0],
    )
    return feature_long, intermediates
