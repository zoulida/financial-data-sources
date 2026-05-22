"""主升浪 KPI 评估模块。

主指标：
- Precision@K：每日因子排名前 K 中，未来 N 日触发主升浪事件的比例（按时间均值）
- Recall@K：所有主升浪正样本中被排进前 K 的比例
- TopK 平均最大涨幅 / 中位最大涨幅
- TopK 平均最大回撤
- TopK 平均起爆速度（time_to_peak，越小越好）
- 盈亏比：max_return / |drawdown|

参考指标：调用 src/多因子/factor_evaluation 计算 IC / RankIC。
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.多因子.factor_evaluation import (
    build_forward_returns,
    calc_ic_series,
    calc_rank_ic_series,
)


def _topk_mask_per_row(factor_df: pd.DataFrame, k: int) -> pd.DataFrame:
    """对每一行，标记因子值最高的前 K 只为 True。"""
    if factor_df.empty or k <= 0:
        return pd.DataFrame(False, index=factor_df.index, columns=factor_df.columns)
    ranks = factor_df.rank(axis=1, ascending=False, method="first")
    return (ranks <= k) & factor_df.notna()


def evaluate_factor_blastoff(
    factor_df: pd.DataFrame,
    events: dict[str, Any],
    top_k_list: list[int],
) -> dict[str, Any]:
    """对单因子计算主升浪 KPI。

    Args:
        factor_df: T×N 因子矩阵（值越大越接近起爆前夜）。
        events: events.compute_blastoff_events 返回的字典。
        top_k_list: 多档 Top-K。

    Returns:
        dict: 包含 metrics_df / per_date_metrics / topk_picks。
    """
    is_blastoff: pd.DataFrame = events["is_blastoff"]
    forward_max_return: pd.DataFrame = events["forward_max_return"]
    forward_drawdown: pd.DataFrame = events["forward_drawdown"]
    time_to_peak: pd.DataFrame = events["time_to_peak"]

    # 对齐索引与列
    common_index = factor_df.index.intersection(is_blastoff.index)
    common_columns = factor_df.columns.intersection(is_blastoff.columns)
    factor_df = factor_df.reindex(index=common_index, columns=common_columns)
    is_blastoff = is_blastoff.reindex(index=common_index, columns=common_columns).fillna(False)
    forward_max_return = forward_max_return.reindex(index=common_index, columns=common_columns)
    forward_drawdown = forward_drawdown.reindex(index=common_index, columns=common_columns)
    time_to_peak = time_to_peak.reindex(index=common_index, columns=common_columns)

    metrics_rows = []
    for k in top_k_list:
        topk_mask = _topk_mask_per_row(factor_df, k)
        # 只统计 factor 有效的行
        valid_rows = topk_mask.any(axis=1)
        topk_mask_valid = topk_mask.loc[valid_rows]
        if topk_mask_valid.empty:
            metrics_rows.append({
                "TopK": k,
                "Precision@K": np.nan,
                "Recall@K": np.nan,
                "平均最大涨幅": np.nan,
                "中位最大涨幅": np.nan,
                "平均最大回撤": np.nan,
                "平均起爆速度": np.nan,
                "盈亏比": np.nan,
                "样本日数": 0,
            })
            continue

        # 命中率：每日 (TopK 内事件数 / K)，按时间求均值
        hits_per_day = (topk_mask_valid & is_blastoff.loc[valid_rows]).sum(axis=1)
        topk_size_per_day = topk_mask_valid.sum(axis=1).replace(0, np.nan)
        precision_series = hits_per_day / topk_size_per_day
        precision_at_k = float(precision_series.mean())

        # 召回率：所有事件里被排进前 K 的比例
        events_per_day = is_blastoff.loc[valid_rows].sum(axis=1).replace(0, np.nan)
        recall_series = hits_per_day / events_per_day
        recall_at_k = float(recall_series.mean())

        # TopK 内的实际未来收益统计
        topk_returns = forward_max_return.loc[valid_rows].where(topk_mask_valid)
        topk_drawdowns = forward_drawdown.loc[valid_rows].where(topk_mask_valid)
        topk_times = time_to_peak.loc[valid_rows].where(topk_mask_valid).replace(-1, np.nan)

        max_return_mean = float(topk_returns.stack().mean())
        max_return_median = float(topk_returns.stack().median())
        drawdown_mean = float(topk_drawdowns.stack().mean())
        time_to_peak_mean = float(pd.to_numeric(topk_times.stack(), errors="coerce").mean())

        if np.isfinite(drawdown_mean) and abs(drawdown_mean) > 1e-9:
            pnl_ratio = float(max_return_mean / abs(drawdown_mean))
        else:
            pnl_ratio = np.nan

        metrics_rows.append({
            "TopK": k,
            "Precision@K": precision_at_k,
            "Recall@K": recall_at_k,
            "平均最大涨幅": max_return_mean,
            "中位最大涨幅": max_return_median,
            "平均最大回撤": drawdown_mean,
            "平均起爆速度": time_to_peak_mean,
            "盈亏比": pnl_ratio,
            "样本日数": int(valid_rows.sum()),
        })

    metrics_df = pd.DataFrame(metrics_rows)

    # 末期 Top-K 个股清单（取最后一个有效因子日）
    topk_picks: dict[int, pd.DataFrame] = {}
    last_valid_dt = None
    for dt in reversed(factor_df.index):
        row = factor_df.loc[dt].dropna()
        if not row.empty:
            last_valid_dt = dt
            break
    if last_valid_dt is not None:
        last_row = factor_df.loc[last_valid_dt].dropna().sort_values(ascending=False)
        for k in top_k_list:
            top_codes = last_row.head(k)
            picks_df = pd.DataFrame({
                "code": top_codes.index,
                "factor_value": top_codes.values,
                "rank": range(1, len(top_codes) + 1),
            })
            picks_df.attrs["snapshot_date"] = str(last_valid_dt)
            topk_picks[k] = picks_df

    return {
        "metrics_df": metrics_df,
        "topk_picks": topk_picks,
        "snapshot_date": str(last_valid_dt) if last_valid_dt is not None else None,
    }


def evaluate_factor_ic_reference(
    factor_df: pd.DataFrame,
    close_df: pd.DataFrame,
    rebalance_mask: pd.Series,
) -> pd.DataFrame:
    """计算 IC / RankIC 作为参考指标。"""
    if factor_df.empty or close_df.empty:
        return pd.DataFrame()
    forward_returns = build_forward_returns(close_df, rebalance_mask)
    ic_series = calc_ic_series(factor_df, forward_returns)
    rank_ic_series = calc_rank_ic_series(factor_df, forward_returns)

    def _ir(series: pd.Series, periods_per_year: int = 52) -> float:
        valid = series.dropna()
        if valid.empty or valid.std(ddof=0) == 0:
            return float("nan")
        return float(valid.mean() / valid.std(ddof=0) * np.sqrt(periods_per_year))

    return pd.DataFrame([{
        "IC均值": float(ic_series.mean()),
        "ICIR": _ir(ic_series),
        "RankIC均值": float(rank_ic_series.mean()),
        "RankICIR": _ir(rank_ic_series),
    }])
