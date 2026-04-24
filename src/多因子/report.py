from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def save_selection_results(
    selection_df: pd.DataFrame,
    score_df: pd.DataFrame,
    output_dir: str,
) -> None:
    """保存每期选股结果与综合分数。"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    selection_df.astype(int).to_csv(output_path / "selection_matrix.csv", encoding="utf-8-sig")
    score_df.to_csv(output_path / "score_matrix.csv", encoding="utf-8-sig")

    rows = []
    for dt in selection_df.index:
        selected_codes = selection_df.columns[selection_df.loc[dt].fillna(False)]
        for code in selected_codes:
            rows.append({
                "date": dt,
                "code": code,
                "score": score_df.loc[dt, code],
            })
    pd.DataFrame(rows).to_csv(output_path / "selected_stocks.csv", index=False, encoding="utf-8-sig")


def save_backtest_results(results: dict[str, Any], output_dir: str) -> None:
    """保存回测结果。"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    stats = results.get("stats")
    if stats is not None:
        if hasattr(stats, "to_frame"):
            stats.to_frame(name="value").to_csv(output_path / "portfolio_stats.csv", encoding="utf-8-sig")
        else:
            pd.DataFrame(stats).to_csv(output_path / "portfolio_stats.csv", encoding="utf-8-sig")

    equity_curve = results.get("equity_curve")
    if isinstance(equity_curve, pd.Series):
        equity_curve.to_frame(name="equity").to_csv(output_path / "equity_curve.csv", encoding="utf-8-sig")
    elif isinstance(equity_curve, pd.DataFrame):
        equity_curve.to_csv(output_path / "equity_curve.csv", encoding="utf-8-sig")

    returns = results.get("returns")
    if isinstance(returns, pd.Series):
        returns.to_frame(name="returns").to_csv(output_path / "returns.csv", encoding="utf-8-sig")
    elif isinstance(returns, pd.DataFrame):
        returns.to_csv(output_path / "returns.csv", encoding="utf-8-sig")

    positions = results.get("positions")
    if isinstance(positions, pd.Series):
        positions.to_frame(name="position").to_csv(output_path / "positions.csv", encoding="utf-8-sig")
    elif isinstance(positions, pd.DataFrame):
        positions.to_csv(output_path / "positions.csv", encoding="utf-8-sig")

    benchmark_close = results.get("benchmark_close")
    if isinstance(benchmark_close, pd.Series):
        benchmark_close.to_frame(name="benchmark_close").to_csv(output_path / "benchmark_close.csv", encoding="utf-8-sig")
    elif isinstance(benchmark_close, pd.DataFrame):
        benchmark_close.to_csv(output_path / "benchmark_close.csv", encoding="utf-8-sig")

    benchmark_returns = results.get("benchmark_returns")
    if isinstance(benchmark_returns, pd.Series):
        benchmark_returns.to_frame(name="benchmark_returns").to_csv(output_path / "benchmark_returns.csv", encoding="utf-8-sig")
    elif isinstance(benchmark_returns, pd.DataFrame):
        benchmark_returns.to_csv(output_path / "benchmark_returns.csv", encoding="utf-8-sig")


def save_stage_results(stage_results: dict[str, Any], output_dir: str) -> None:
    """保存选因各阶段结果。"""
    stage_dir = Path(output_dir) / "factor_selection"
    stage_dir.mkdir(parents=True, exist_ok=True)

    candidate_metrics = stage_results.get("candidate_metrics")
    if isinstance(candidate_metrics, pd.DataFrame):
        candidate_metrics.to_csv(stage_dir / "stage1_candidate_metrics.csv", index=False, encoding="utf-8-sig")

    candidate_status = stage_results.get("candidate_status")
    if isinstance(candidate_status, pd.DataFrame):
        candidate_status.to_csv(stage_dir / "stage1_candidate_status.csv", index=False, encoding="utf-8-sig")

    screened_metrics = stage_results.get("screened_metrics")
    if isinstance(screened_metrics, pd.DataFrame):
        screened_metrics.to_csv(stage_dir / "stage2_screened_metrics.csv", index=False, encoding="utf-8-sig")

    corr_matrix = stage_results.get("corr_matrix")
    if isinstance(corr_matrix, pd.DataFrame):
        corr_matrix.to_csv(stage_dir / "stage3_factor_score_corr.csv", encoding="utf-8-sig")

    corr_pairs = stage_results.get("corr_pairs")
    if isinstance(corr_pairs, pd.DataFrame):
        corr_pairs.to_csv(stage_dir / "stage3_high_corr_pairs.csv", index=False, encoding="utf-8-sig")

    final_selection = stage_results.get("final_selection")
    if isinstance(final_selection, pd.DataFrame):
        final_selection.to_csv(stage_dir / "stage4_final_factor_selection.csv", index=False, encoding="utf-8-sig")

    selected_score = stage_results.get("selected_score_matrix")
    if isinstance(selected_score, pd.DataFrame):
        selected_score.to_csv(stage_dir / "stage4_selected_factor_score_matrix.csv", encoding="utf-8-sig")
