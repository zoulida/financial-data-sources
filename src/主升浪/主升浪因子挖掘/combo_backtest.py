"""多因子组合回测：相关性去冗余 + 等权合成 + vectorbt 回测 + 评价。

设计思路：
- 相关性筛选：在因子横截面 rank score 的 panel（堆叠成长表）上做 Pearson 相关；
  对绝对值超过阈值的因子对，保留优先级（main 流程传入）较高的一方。
- 等权合成：把保留下来的因子 rank score 取等权平均，作为综合分数。
- 等权回测：每个调仓日选综合分数前 N 名，等权配置；复用 src/多因子/backtest_vectorbt。
- 组合评价：核心收益/风险指标（Total Return、年化、夏普、最大回撤、超额）+ 主升浪 KPI（命中率/平均最大涨幅/盈亏比）。
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.主升浪因子挖掘.blastoff_evaluation import _topk_mask_per_row
from src.多因子.backtest_vectorbt import (
    build_target_weights,
    extract_backtest_results,
    run_vectorbt_backtest,
)
from src.多因子.scoring import select_top_n


def build_correlation_matrix(
    factor_scores: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """对各因子的 rank score 做横截面 Pearson 相关。

    实现方式：把每个因子矩阵 stack 成 (date, code) 索引的 Series，
    再横向拼成一张 panel，对 panel 求列相关。
    """
    if not factor_scores:
        return pd.DataFrame()

    flattened: dict[str, pd.Series] = {}
    for factor_name, score_df in factor_scores.items():
        if not isinstance(score_df, pd.DataFrame) or score_df.empty:
            continue
        flattened[factor_name] = score_df.stack(future_stack=True)

    if not flattened:
        return pd.DataFrame()

    panel = pd.DataFrame(flattened)
    # 排除取值常数列，避免 corr 出 NaN 警告
    valid_cols = [
        col for col in panel.columns
        if panel[col].dropna().nunique(dropna=True) > 1
    ]
    if not valid_cols:
        return pd.DataFrame(index=list(flattened.keys()), columns=list(flattened.keys()), dtype=float)
    return panel[valid_cols].corr()


def dedupe_by_correlation(
    factor_scores: dict[str, pd.DataFrame],
    priority: dict[str, float],
    threshold: float,
) -> tuple[list[str], pd.DataFrame, pd.DataFrame]:
    """按相关性阈值贪心去冗余。

    Args:
        factor_scores: {factor_name: rank_score_df}
        priority: {factor_name: 优先级分数}，越大越优先保留
        threshold: |corr| >= threshold 视为高相关。

    Returns:
        kept: 保留的因子列表（按 priority 降序）
        corr_matrix: 完整相关矩阵
        dropped_pairs_df: 触发去冗余的高相关因子对 [factor_a, factor_b, corr, dropped]
    """
    corr_matrix = build_correlation_matrix(factor_scores)
    kept = list(factor_scores.keys())
    dropped_rows: list[dict[str, Any]] = []

    if corr_matrix.empty or threshold >= 1.0:
        return kept, corr_matrix, pd.DataFrame(columns=["factor_a", "factor_b", "corr", "dropped"])

    # 收集所有高相关对，按 |corr| 降序处理
    pairs: list[tuple[str, str, float]] = []
    factor_names = [c for c in corr_matrix.columns if c in factor_scores]
    for i, a in enumerate(factor_names):
        for b in factor_names[i + 1:]:
            value = corr_matrix.loc[a, b]
            if pd.isna(value):
                continue
            corr_value = float(value)
            if abs(corr_value) >= threshold:
                pairs.append((a, b, corr_value))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)

    for a, b, corr_value in pairs:
        if a not in kept or b not in kept:
            continue
        priority_a = float(priority.get(a, 0.0))
        priority_b = float(priority.get(b, 0.0))
        if priority_a >= priority_b:
            dropped, retained = b, a
        else:
            dropped, retained = a, b
        kept.remove(dropped)
        dropped_rows.append({
            "factor_a": a,
            "factor_b": b,
            "corr": corr_value,
            "dropped": dropped,
            "retained": retained,
        })

    # 按优先级降序排列保留因子
    kept.sort(key=lambda name: priority.get(name, 0.0), reverse=True)
    dropped_pairs_df = pd.DataFrame(dropped_rows)
    return kept, corr_matrix, dropped_pairs_df


def equal_weight_combine(
    factor_scores: dict[str, pd.DataFrame],
    factor_names: list[str],
) -> pd.DataFrame:
    """对入选因子的 rank score 取等权平均。"""
    selected = [name for name in factor_names if name in factor_scores]
    if not selected:
        return pd.DataFrame()
    accumulator: pd.DataFrame | None = None
    for name in selected:
        score_df = factor_scores[name].astype(float)
        accumulator = score_df if accumulator is None else accumulator.add(score_df, fill_value=np.nan)
    if accumulator is None:
        return pd.DataFrame()
    return accumulator / float(len(selected))


def run_equal_weight_combo_backtest(
    combo_score_df: pd.DataFrame,
    close_df: pd.DataFrame,
    rebalance_mask: pd.Series,
    hold_num: int,
    benchmark_close: pd.Series | None,
    commission: float = 0.0,
    slippage: float = 0.0,
    init_cash: float = 1_000_000.0,
) -> dict[str, Any]:
    """对综合分数做等权 Top-N 组合的 vectorbt 回测。"""
    if combo_score_df.empty:
        return {}

    selection_df = select_top_n(combo_score_df, n=hold_num)
    weights_df = build_target_weights(selection_df, rebalance_mask)
    portfolio = run_vectorbt_backtest(
        close_df=close_df,
        target_weights=weights_df,
        commission=commission,
        slippage=slippage,
        init_cash=init_cash,
    )
    results = extract_backtest_results(portfolio, benchmark_close=benchmark_close)
    results["selection_df"] = selection_df
    results["weights_df"] = weights_df
    return results


def summarize_combo_metrics(
    backtest_results: dict[str, Any],
    periods_per_year: int = 252,
) -> pd.DataFrame:
    """汇总组合核心评价指标：总收益/年化/超额年化/波动/夏普/最大回撤。"""
    stats = backtest_results.get("stats")
    returns = backtest_results.get("returns")
    benchmark_returns = backtest_results.get("benchmark_returns")

    def _get(key: str) -> float:
        if stats is None or not hasattr(stats, "loc"):
            return float("nan")
        try:
            value = stats.loc[key]
            return float(value)
        except Exception:
            return float("nan")

    total_return = _get("Total Return [%]")
    benchmark_return = _get("Benchmark Return [%]")
    sharpe = _get("Sharpe Ratio")
    max_dd = _get("Max Drawdown [%]")

    # 年化收益（按日历日数）
    annualized = float("nan")
    excess_annualized = float("nan")
    volatility = float("nan")
    if isinstance(returns, pd.Series) and not returns.empty:
        try:
            idx = pd.to_datetime(returns.index)
            calendar_days = (idx[-1] - idx[0]).days
            if calendar_days > 0:
                annualized = ((1.0 + total_return / 100.0) ** (365.0 / calendar_days) - 1.0) * 100.0
        except Exception:
            pass
        valid = returns.dropna()
        if not valid.empty:
            volatility = float(valid.std(ddof=0) * np.sqrt(periods_per_year) * 100.0)
        if isinstance(benchmark_returns, pd.Series) and not benchmark_returns.empty:
            aligned = pd.concat(
                [returns, benchmark_returns.reindex(returns.index).fillna(0.0)],
                axis=1,
                keys=["strategy", "benchmark"],
            ).dropna()
            if not aligned.empty:
                excess_daily = aligned["strategy"] - aligned["benchmark"]
                try:
                    days = (pd.to_datetime(aligned.index[-1]) - pd.to_datetime(aligned.index[0])).days
                    if days > 0:
                        cum_excess = (1.0 + excess_daily).prod() - 1.0
                        excess_annualized = ((1.0 + cum_excess) ** (365.0 / days) - 1.0) * 100.0
                except Exception:
                    pass

    excess_total = total_return - benchmark_return if np.isfinite(total_return) and np.isfinite(benchmark_return) else float("nan")

    return pd.DataFrame([{
        "总收益率(%)": total_return,
        "基准收益率(%)": benchmark_return,
        "超额收益(%)": excess_total,
        "年化收益(%)": annualized,
        "超额年化(%)": excess_annualized,
        "波动率(%)": volatility,
        "夏普比率": sharpe,
        "最大回撤(%)": max_dd,
    }])


def evaluate_combo_blastoff_kpi(
    combo_score_df: pd.DataFrame,
    events: dict[str, Any],
    top_k_list: list[int],
) -> pd.DataFrame:
    """用主升浪 KPI 评价组合分数（命中率/平均最大涨幅/盈亏比/起爆速度）。"""
    if combo_score_df.empty:
        return pd.DataFrame()

    is_blastoff = events["is_blastoff"]
    forward_max_return = events["forward_max_return"]
    forward_drawdown = events["forward_drawdown"]
    time_to_peak = events["time_to_peak"]

    common_idx = combo_score_df.index.intersection(is_blastoff.index)
    common_cols = combo_score_df.columns.intersection(is_blastoff.columns)
    factor = combo_score_df.reindex(index=common_idx, columns=common_cols)
    is_blastoff = is_blastoff.reindex(index=common_idx, columns=common_cols).fillna(False)
    forward_max_return = forward_max_return.reindex(index=common_idx, columns=common_cols)
    forward_drawdown = forward_drawdown.reindex(index=common_idx, columns=common_cols)
    time_to_peak = time_to_peak.reindex(index=common_idx, columns=common_cols)

    rows: list[dict[str, Any]] = []
    for k in top_k_list:
        topk_mask = _topk_mask_per_row(factor, k)
        valid_rows = topk_mask.any(axis=1)
        if not valid_rows.any():
            rows.append({"TopK": k, "Precision@K": np.nan, "Recall@K": np.nan,
                         "平均最大涨幅": np.nan, "平均最大回撤": np.nan,
                         "平均起爆速度": np.nan, "盈亏比": np.nan})
            continue
        topk_mask_valid = topk_mask.loc[valid_rows]
        hits = (topk_mask_valid & is_blastoff.loc[valid_rows]).sum(axis=1)
        topk_size = topk_mask_valid.sum(axis=1).replace(0, np.nan)
        events_per_day = is_blastoff.loc[valid_rows].sum(axis=1).replace(0, np.nan)
        precision = float((hits / topk_size).mean())
        recall = float((hits / events_per_day).mean())
        topk_returns = forward_max_return.loc[valid_rows].where(topk_mask_valid)
        topk_drawdowns = forward_drawdown.loc[valid_rows].where(topk_mask_valid)
        topk_times = time_to_peak.loc[valid_rows].where(topk_mask_valid).replace(-1, np.nan)
        max_return_mean = float(topk_returns.stack().mean())
        drawdown_mean = float(topk_drawdowns.stack().mean())
        time_mean = float(pd.to_numeric(topk_times.stack(), errors="coerce").mean())
        pnl = float(max_return_mean / abs(drawdown_mean)) if np.isfinite(drawdown_mean) and abs(drawdown_mean) > 1e-9 else float("nan")
        rows.append({
            "TopK": k,
            "Precision@K": precision,
            "Recall@K": recall,
            "平均最大涨幅": max_return_mean,
            "平均最大回撤": drawdown_mean,
            "平均起爆速度": time_mean,
            "盈亏比": pnl,
        })
    return pd.DataFrame(rows)
