"""主升浪因子挖掘入口。

流程：
1. 弹出对话框收集运行参数；
2. 通过 src/多因子/data_loader 加载日线数据包；
3. 计算主升浪事件标注；
4. 对每个勾选因子计算因子矩阵 + 主升浪 KPI + IC 参考；
5. 输出 CSV/PNG 到 outputs/<run_id>/<factor>/。

运行：
    python -m src.主升浪因子挖掘.main
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

import pandas as pd

from src.主升浪因子挖掘 import config
from src.主升浪因子挖掘.blastoff_evaluation import (
    evaluate_factor_blastoff,
    evaluate_factor_ic_reference,
)
from src.主升浪因子挖掘.dialogs import BlastoffRunDialog, save_last_run_config
from src.主升浪因子挖掘.events import compute_blastoff_events, summarize_events
from src.主升浪因子挖掘.factor_registry import FACTOR_REGISTRY, compute_factor
from src.主升浪因子挖掘.report import save_factor_blastoff_report, save_overall_summary
from src.主升浪因子挖掘.combo_backtest import (
    dedupe_by_correlation,
    equal_weight_combine,
    evaluate_combo_blastoff_kpi,
    run_equal_weight_combo_backtest,
    summarize_combo_metrics,
)
from src.多因子.backtest_vectorbt import build_rebalance_mask
from src.多因子.data_loader import build_data_bundle
from src.多因子.scoring import mask_factor, rank_score
from src.多因子.universe import build_tradable_mask


def _build_run_id(start_date: str, end_date: str) -> str:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return f"{start_date}_{end_date}__{timestamp}"


def run(run_config: dict) -> None:
    """根据对话框参数运行一次完整评估。"""
    start_date = str(run_config["start_date"])
    end_date = str(run_config["end_date"])
    forward_days = int(run_config["forward_days"])
    return_threshold = float(run_config["return_threshold"])
    max_drawdown = float(run_config["max_drawdown"])
    top_k_list = list(run_config["top_k_list"])
    selected_factors = list(run_config["selected_factors"])
    use_event_cache = bool(run_config["use_event_cache"])
    use_batch_data_cache = bool(run_config["use_batch_data_cache"])
    enable_combo_backtest = bool(run_config.get("enable_combo_backtest", False))
    corr_threshold = float(run_config.get("corr_threshold", 0.8))
    hold_num = int(run_config.get("hold_num", 26))

    print("=" * 60)
    print(f"[运行] 日期范围：{start_date} ~ {end_date}")
    print(f"[运行] 事件参数：N={forward_days}, 涨幅≥{return_threshold:.0%}, 最大回撤≤{max_drawdown:.0%}")
    print(f"[运行] Top-K 列表：{top_k_list}")
    print(f"[运行] 因子数：{len(selected_factors)}")
    print("=" * 60)

    # 1. 加载数据
    print("[数据] 调用 build_data_bundle...")
    data_bundle = build_data_bundle(
        start_date=start_date,
        end_date=end_date,
        use_batch_data_cache=use_batch_data_cache,
    )
    close_df = data_bundle.get("close")
    if not isinstance(close_df, pd.DataFrame) or close_df.empty:
        print("[数据] 收盘价数据为空，无法继续。")
        return

    # 2. 可交易掩码
    universe_df = data_bundle.get("universe")
    if not isinstance(universe_df, pd.DataFrame):
        universe_df = pd.DataFrame(columns=["code"])
    tradable_mask = build_tradable_mask(universe_df=universe_df, close_df=close_df)

    # 3. 主升浪事件标注
    print("[事件] 计算主升浪事件标注...")
    events = compute_blastoff_events(
        close_df=close_df,
        forward_days=forward_days,
        return_threshold=return_threshold,
        max_drawdown=max_drawdown,
        use_cache=use_event_cache,
    )
    events_summary = summarize_events(events)
    if not events_summary.empty:
        print("[事件] 总览：")
        print(events_summary.to_string(index=False))

    # 4. 调仓掩码（用于 IC 参考指标）
    rebalance_mask = build_rebalance_mask(close_df.index, freq=config.REBALANCE_FREQ)

    # 5. 输出根目录
    run_id = _build_run_id(start_date, end_date)
    output_root = config.OUTPUT_DIR / run_id
    output_root.mkdir(parents=True, exist_ok=True)
    print(f"[输出] 结果目录：{output_root}")

    overall_rows = []
    factor_rank_scores: dict[str, pd.DataFrame] = {}
    factor_priority: dict[str, float] = {}

    for factor_name in selected_factors:
        if factor_name not in FACTOR_REGISTRY:
            print(f"[跳过] 未注册因子：{factor_name}")
            continue
        print("-" * 60)
        print(f"[因子] {factor_name}")
        try:
            factor_df = compute_factor(factor_name, data_bundle)
        except Exception as exc:
            print(f"[因子] 计算失败：{exc}")
            traceback.print_exc()
            continue

        # 应用可交易掩码
        factor_df = mask_factor(factor_df, tradable_mask)

        # 提前计算 rank score（值越大越好），后续组合回测复用
        factor_score_df = rank_score(factor_df, ascending=False)
        factor_rank_scores[factor_name] = factor_score_df

        # 主升浪 KPI
        evaluation = evaluate_factor_blastoff(
            factor_df=factor_df,
            events=events,
            top_k_list=top_k_list,
        )
        metrics_df = evaluation["metrics_df"]
        if not metrics_df.empty:
            print(metrics_df.to_string(index=False))

        # IC 参考
        ic_summary = evaluate_factor_ic_reference(
            factor_df=factor_df,
            close_df=close_df,
            rebalance_mask=rebalance_mask,
        )
        if not ic_summary.empty:
            print("[参考 IC]")
            print(ic_summary.to_string(index=False))

        save_factor_blastoff_report(
            output_root=output_root,
            factor_name=factor_name,
            metrics_df=metrics_df,
            topk_picks=evaluation["topk_picks"],
            snapshot_date=evaluation.get("snapshot_date"),
            ic_summary_df=ic_summary,
            events_summary_df=events_summary,
        )

        # 汇总：取最大 K 档作为总排名指标（可在后续根据需要调整）
        if not metrics_df.empty:
            best_row = metrics_df.iloc[-1]
            precision_at_top = float(best_row.get("Precision@K", float("nan")))
            ic_mean = float(ic_summary["IC均值"].iloc[0]) if not ic_summary.empty else float("nan")
            overall_rows.append({
                "factor": factor_name,
                "label": str(FACTOR_REGISTRY[factor_name].get("label", factor_name)),
                "TopK": int(best_row.get("TopK", 0)) if pd.notna(best_row.get("TopK")) else 0,
                "Precision@K": precision_at_top,
                "Recall@K": float(best_row.get("Recall@K", float("nan"))),
                "平均最大涨幅": float(best_row.get("平均最大涨幅", float("nan"))),
                "平均最大回撤": float(best_row.get("平均最大回撤", float("nan"))),
                "盈亏比": float(best_row.get("盈亏比", float("nan"))),
                "IC均值": ic_mean,
                "RankIC均值": float(ic_summary["RankIC均值"].iloc[0]) if not ic_summary.empty else float("nan"),
            })

            # 优先级：以 Precision@K 为主，IC 兜底（确保两个 NaN 时仍有可比序）
            primary = precision_at_top if pd.notna(precision_at_top) else 0.0
            fallback = ic_mean if pd.notna(ic_mean) else 0.0
            factor_priority[factor_name] = primary + 1e-6 * fallback

    save_overall_summary(output_root, overall_rows)

    # ========== 多因子组合回测（可选） ==========
    if enable_combo_backtest and len(factor_rank_scores) >= 1:
        _run_combo_backtest_block(
            output_root=output_root,
            factor_rank_scores=factor_rank_scores,
            factor_priority=factor_priority,
            corr_threshold=corr_threshold,
            hold_num=hold_num,
            close_df=close_df,
            rebalance_mask=rebalance_mask,
            benchmark_close=data_bundle.get("benchmark_close"),
            events=events,
            top_k_list=top_k_list,
        )
    elif enable_combo_backtest:
        print("[组合] 没有可用的因子 rank score，跳过组合回测。")

    print("=" * 60)
    print(f"[完成] 评估结果已写入 {output_root}")


def _run_combo_backtest_block(
    output_root,
    factor_rank_scores: dict[str, pd.DataFrame],
    factor_priority: dict[str, float],
    corr_threshold: float,
    hold_num: int,
    close_df: pd.DataFrame,
    rebalance_mask: pd.Series,
    benchmark_close,
    events: dict,
    top_k_list: list[int],
) -> None:
    """单因子评估完成后，追加运行多因子组合回测。"""
    print("=" * 60)
    print(f"[组合] 启动多因子组合回测（候选因子数={len(factor_rank_scores)}, |corr|≥{corr_threshold}, 持仓={hold_num}）")

    # 1. 相关性筛选
    kept, corr_matrix, dropped_pairs = dedupe_by_correlation(
        factor_scores=factor_rank_scores,
        priority=factor_priority,
        threshold=corr_threshold,
    )
    combo_dir = output_root / "_combo_backtest"
    combo_dir.mkdir(parents=True, exist_ok=True)

    if not corr_matrix.empty:
        corr_matrix.to_csv(combo_dir / "correlation_matrix.csv", encoding="utf-8-sig")
        print("[组合] 相关性矩阵：")
        print(corr_matrix.round(3).to_string())
    if not dropped_pairs.empty:
        dropped_pairs.to_csv(combo_dir / "dropped_pairs.csv", index=False, encoding="utf-8-sig")
        print(f"[组合] 触发去冗余的因子对（{len(dropped_pairs)} 组）：")
        print(dropped_pairs.to_string(index=False))
    print(f"[组合] 保留因子（按优先级降序）: {kept}")
    pd.DataFrame({"factor": kept, "priority": [factor_priority.get(name, float('nan')) for name in kept]}).to_csv(
        combo_dir / "kept_factors.csv", index=False, encoding="utf-8-sig"
    )

    if not kept:
        print("[组合] 去相关后无保留因子，跳过等权回测。")
        return

    # 2. 等权合成
    combo_score = equal_weight_combine(factor_rank_scores, kept)
    if combo_score.empty:
        print("[组合] 等权合成结果为空，跳过回测。")
        return
    combo_score.to_csv(combo_dir / "combo_score.csv", encoding="utf-8-sig")

    # 3. 等权 vectorbt 回测
    print(f"[组合] 启动 vectorbt 等权回测，每期持有 Top-{hold_num}...")
    backtest_results = run_equal_weight_combo_backtest(
        combo_score_df=combo_score,
        close_df=close_df,
        rebalance_mask=rebalance_mask,
        hold_num=hold_num,
        benchmark_close=benchmark_close if isinstance(benchmark_close, pd.Series) else None,
    )
    if not backtest_results:
        print("[组合] 回测结果为空。")
        return

    # 4. 评价
    perf_df = summarize_combo_metrics(backtest_results)
    if not perf_df.empty:
        perf_df.to_csv(combo_dir / "combo_performance.csv", index=False, encoding="utf-8-sig")
        print("[组合] 组合核心指标：")
        print(perf_df.round(4).to_string(index=False))

    # 净值曲线
    equity_curve = backtest_results.get("equity_curve")
    if isinstance(equity_curve, pd.Series) and not equity_curve.empty:
        equity_curve.to_frame(name="equity").to_csv(
            combo_dir / "combo_equity_curve.csv", encoding="utf-8-sig"
        )

    # 5. 组合分数的主升浪 KPI
    combo_kpi_df = evaluate_combo_blastoff_kpi(combo_score, events, top_k_list)
    if not combo_kpi_df.empty:
        combo_kpi_df.to_csv(combo_dir / "combo_blastoff_kpi.csv", index=False, encoding="utf-8-sig")
        print("[组合] 综合分数主升浪 KPI：")
        print(combo_kpi_df.round(4).to_string(index=False))

    print(f"[组合] 结果已写入 {combo_dir}")


def main() -> int:
    dialog = BlastoffRunDialog()
    run_config = dialog.show()
    if run_config is None:
        print("[取消] 未启动评估。")
        return 0
    save_last_run_config(run_config)
    try:
        run(run_config)
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
