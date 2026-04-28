from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.多因子 import config
from src.多因子.backtest_vectorbt import (
    build_rebalance_mask,
    build_target_weights,
    extract_backtest_results,
    run_vectorbt_backtest,
)
from src.多因子.data_loader import build_data_bundle
from src.多因子.main import FACTOR_LABELS, FACTOR_REGISTRY, _compute_registered_factor
from src.多因子.scoring import mask_factor
from src.多因子.universe import build_tradable_mask


FACTOR_NAME = "alpha158.amount_mean_20_ratio"
START_DATE = "20241101"
END_DATE = "20260424"
EXCLUDED_CODES = {"601003.SH"}
GROUP_LABELS = ["G1", "G2", "G3", "G4", "G5"]


def _build_group_selection(masked_factor_df: pd.DataFrame, group_count: int = 5) -> dict[str, pd.DataFrame]:
    selections = {
        label: pd.DataFrame(False, index=masked_factor_df.index, columns=masked_factor_df.columns)
        for label in GROUP_LABELS[:group_count]
    }
    for dt, row in masked_factor_df.iterrows():
        valid = row.dropna().sort_values(ascending=False)
        if len(valid) < group_count:
            continue
        group_ids = pd.qcut(
            np.arange(1, len(valid) + 1),
            q=group_count,
            labels=GROUP_LABELS[:group_count],
        )
        grouped_codes = pd.Series(group_ids, index=valid.index)
        for label in GROUP_LABELS[:group_count]:
            codes = grouped_codes.index[grouped_codes.eq(label)].tolist()
            if codes:
                selections[label].loc[dt, codes] = True
    return selections


def main() -> None:
    start_date = START_DATE
    end_date = END_DATE
    factor_label = FACTOR_LABELS.get(FACTOR_NAME, FACTOR_NAME)
    if FACTOR_NAME not in FACTOR_REGISTRY:
        raise ValueError(f"因子未注册：{FACTOR_NAME}")

    print("=" * 90)
    print("[单因子阶段4逻辑回测] 开始")
    print(f"因子：{FACTOR_NAME}（{factor_label}）")
    print(f"日期：{start_date} ~ {end_date}")
    print("分组：按因子值从大到小分 5 组，G1=最大因子组，G5=最小因子组")
    print(f"排除代码：{', '.join(sorted(EXCLUDED_CODES))}")
    print("=" * 90)

    data_bundle = build_data_bundle(
        max_price=config.MAX_PRICE,
        max_mcap=config.MAX_MCAP,
        need_download=0,
        dividend_type=config.DIVIDEND_TYPE,
        start_date=start_date,
        end_date=end_date,
    )
    close_df = data_bundle.get("close")
    universe_df = data_bundle.get("universe")
    benchmark_close = data_bundle.get("benchmark_close")
    if close_df is None or universe_df is None or close_df.empty:
        raise ValueError("数据加载失败，无法回测")

    close_df = close_df.drop(columns=[code for code in EXCLUDED_CODES if code in close_df.columns], errors="ignore")
    if isinstance(universe_df, pd.DataFrame) and "code" in universe_df.columns:
        universe_df = universe_df[~universe_df["code"].isin(EXCLUDED_CODES)].reset_index(drop=True)
    if benchmark_close is not None and isinstance(benchmark_close, pd.Series) and benchmark_close.name in EXCLUDED_CODES:
        benchmark_close = None

    tradable_mask = build_tradable_mask(universe_df=universe_df, close_df=close_df)
    rebalance_mask = build_rebalance_mask(close_df.index, freq=config.REBALANCE_FREQ)

    raw_factor_df = _compute_registered_factor(FACTOR_NAME, data_bundle)
    raw_factor_df = raw_factor_df.drop(columns=[code for code in EXCLUDED_CODES if code in raw_factor_df.columns], errors="ignore")
    masked_factor_df = mask_factor(raw_factor_df, tradable_mask)
    group_selection_dict = _build_group_selection(masked_factor_df, group_count=5)

    output_dir = Path(__file__).resolve().parent / config.OUTPUT_DIR / "single_factor_stage4_logic_group_backtest" / FACTOR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    equity_curves: dict[str, pd.Series] = {}
    summary_rows: list[dict[str, object]] = []

    for label, selection_df in group_selection_dict.items():
        target_weights = build_target_weights(selection_df, rebalance_mask)
        portfolio = run_vectorbt_backtest(
            close_df=close_df,
            target_weights=target_weights,
            commission=config.COMMISSION,
            slippage=config.SLIPPAGE,
            init_cash=config.INITIAL_CASH,
        )
        results = extract_backtest_results(portfolio, benchmark_close=benchmark_close)
        equity_curve = results["equity_curve"]
        total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0)
        selected_counts = selection_df.sum(axis=1)
        rebalance_counts = selected_counts[rebalance_mask.reindex(selected_counts.index).fillna(False)]

        equity_curves[label] = equity_curve
        selection_df.to_csv(output_dir / f"selection_{label}.csv", encoding="utf-8-sig")
        target_weights.to_csv(output_dir / f"target_weights_{label}.csv", encoding="utf-8-sig")
        stats = results.get("stats")
        if stats is not None and hasattr(stats, "to_frame"):
            stats.to_frame(name="value").to_csv(output_dir / f"stats_{label}.csv", encoding="utf-8-sig")

        summary_rows.append(
            {
                "factor": FACTOR_NAME,
                "factor_label": factor_label,
                "start_date": start_date,
                "end_date": end_date,
                "group": label,
                "group_meaning": "因子最大组" if label == "G1" else "因子最小组" if label == "G5" else "中间组",
                "initial_equity": float(equity_curve.iloc[0]),
                "final_equity": float(equity_curve.iloc[-1]),
                "total_return": total_return,
                "total_return_pct": total_return * 100.0,
                "rebalance_count_min": int(rebalance_counts.min()) if not rebalance_counts.empty else 0,
                "rebalance_count_max": int(rebalance_counts.max()) if not rebalance_counts.empty else 0,
            }
        )

    equity_df = pd.DataFrame(equity_curves)
    equity_df.to_csv(output_dir / "group_equity_curves.csv", encoding="utf-8-sig")
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "group_summary.csv", index=False, encoding="utf-8-sig")

    plt.figure(figsize=(12, 6))
    for label in GROUP_LABELS:
        if label in equity_df.columns:
            equity_df[label].plot(label=label, linewidth=2)
    plt.title(f"{factor_label} 阶段4逻辑分组累计净值（G1=最大因子组，G5=最小因子组）")
    plt.xlabel("日期")
    plt.ylabel("累计净值")
    plt.legend()
    plt.tight_layout()
    chart_path = output_dir / "group_equity_curves.png"
    plt.savefig(chart_path, dpi=150)
    plt.close()

    print("[回测完成]")
    for row in summary_rows:
        print(
            f"{row['group']}（{row['group_meaning']}）："
            f"总收益率={float(row['total_return_pct']):.6f}%，"
            f"调仓日持仓数量={row['rebalance_count_min']}~{row['rebalance_count_max']}"
        )
    print(f"分组累计净值图：{chart_path}")
    print(f"结果目录：{output_dir}")


if __name__ == "__main__":
    main()
