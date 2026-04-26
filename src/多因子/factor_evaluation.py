from __future__ import annotations

from pathlib import Path
from typing import Any
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

from src.多因子 import config
from src.多因子.backtest_vectorbt import extract_backtest_results, run_vectorbt_backtest
from src.多因子.scoring import mask_factor, rank_score, select_top_n

_CJK_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    "KaiTi",
    "FangSong",
    "DengXian",
]


def _configure_plot_font() -> str:
    """配置 matplotlib 中文字体。

    处理原则：
    - 如果系统存在可用中文字体，则显式指定，彻底消除中文 glyph warning；
    - 如果系统不存在可用中文字体，则直接抛错，而不是带 warning 继续跑。
    """
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in _CJK_FONT_CANDIDATES:
        if font_name in available_fonts:
            plt.rcParams["font.sans-serif"] = [font_name]
            plt.rcParams["axes.unicode_minus"] = False
            return font_name
    raise RuntimeError(
        "未找到可用中文字体，无法生成中文图表。请安装或启用以下任一字体："
        + ", ".join(_CJK_FONT_CANDIDATES)
    )


PLOT_FONT_NAME = _configure_plot_font()


def build_forward_returns(close_df: pd.DataFrame, rebalance_mask: pd.Series) -> pd.DataFrame:
    """构建与调仓周期一致的未来收益矩阵。

    说明：
    - 只在调仓日上计算未来一期收益；
    - 未来一期收益定义为：本次调仓日到下一次调仓日之间的区间收益；
    - 非调仓日保留为 NaN，不参与 IC / IR / RR 统计。
    """
    if close_df.empty:
        return close_df.copy()

    forward_returns = pd.DataFrame(np.nan, index=close_df.index, columns=close_df.columns, dtype=float)
    rebalance_dates = [dt for dt in close_df.index if bool(rebalance_mask.get(dt, False))]

    for idx in range(len(rebalance_dates) - 1):
        current_dt = rebalance_dates[idx]
        next_dt = rebalance_dates[idx + 1]
        current_close = close_df.loc[current_dt]
        next_close = close_df.loc[next_dt]
        forward_returns.loc[current_dt] = next_close.divide(current_close).subtract(1.0)

    return forward_returns


def _calc_cross_section_corr(
    factor_row: pd.Series,
    return_row: pd.Series,
    method: str,
) -> float:
    merged = pd.concat([factor_row, return_row], axis=1, keys=["factor", "future_return"]).dropna()
    merged["factor"] = pd.to_numeric(merged["factor"], errors="coerce")
    merged["future_return"] = pd.to_numeric(merged["future_return"], errors="coerce")
    merged = merged.replace([np.inf, -np.inf], np.nan).dropna()
    if len(merged) < 3:
        return np.nan
    return float(merged["factor"].corr(merged["future_return"], method=method))


def calc_ic_series(factor_df: pd.DataFrame, forward_returns_df: pd.DataFrame) -> pd.Series:
    """计算逐期 Pearson IC 序列。"""
    ic_values = {
        dt: _calc_cross_section_corr(factor_df.loc[dt], forward_returns_df.loc[dt], method="pearson")
        for dt in factor_df.index.intersection(forward_returns_df.index)
    }
    return pd.Series(ic_values, name="IC")


def calc_rank_ic_series(factor_df: pd.DataFrame, forward_returns_df: pd.DataFrame) -> pd.Series:
    """计算逐期 Spearman RankIC 序列。"""
    rank_ic_values = {
        dt: _calc_cross_section_corr(factor_df.loc[dt], forward_returns_df.loc[dt], method="spearman")
        for dt in factor_df.index.intersection(forward_returns_df.index)
    }
    return pd.Series(rank_ic_values, name="RankIC")


def calc_rr_series(
    factor_df: pd.DataFrame,
    forward_returns_df: pd.DataFrame,
    hold_num: int,
) -> pd.Series:
    """计算逐期 RR（这里定义为顶部组合收益减去底部组合收益）。

    说明：
    - RR 在这里取 Return Spread Rate 的含义；
    - 每期选因子值最高的前 N 只作为多头组；
    - 选因子值最低的前 N 只作为空头参考组；
    - RR = 多头组平均未来收益 - 空头组平均未来收益。
    """
    rr_dict: dict[object, float] = {}
    for dt in factor_df.index.intersection(forward_returns_df.index):
        merged = pd.concat(
            [factor_df.loc[dt], forward_returns_df.loc[dt]],
            axis=1,
            keys=["factor", "future_return"],
        ).dropna()
        merged["factor"] = pd.to_numeric(merged["factor"], errors="coerce")
        merged["future_return"] = pd.to_numeric(merged["future_return"], errors="coerce")
        merged = merged.replace([np.inf, -np.inf], np.nan).dropna()
        if merged.empty:
            rr_dict[dt] = np.nan
            continue

        top_group = merged.nlargest(hold_num, "factor")
        bottom_group = merged.nsmallest(hold_num, "factor")
        if top_group.empty or bottom_group.empty:
            rr_dict[dt] = np.nan
            continue

        rr_dict[dt] = float(top_group["future_return"].mean() - bottom_group["future_return"].mean())

    return pd.Series(rr_dict, name="RR")


def summarize_factor_metrics(
    factor_name: str,
    ic_series: pd.Series,
    rank_ic_series: pd.Series,
    rr_series: pd.Series,
    periods_per_year: int = 52,
) -> pd.DataFrame:
    """汇总单因子的 IC / IR / RR 指标。"""

    def _calc_ir(series: pd.Series) -> float:
        valid = series.dropna()
        if valid.empty or valid.std(ddof=0) == 0:
            return np.nan
        return float(valid.mean() / valid.std(ddof=0) * np.sqrt(periods_per_year))

    summary = pd.DataFrame(
        [
            {
                "factor": factor_name,
                "IC均值": ic_series.mean(),
                "ICIR": _calc_ir(ic_series),
                "RankIC均值": rank_ic_series.mean(),
                "RankICIR": _calc_ir(rank_ic_series),
                "RR均值": rr_series.mean(),
                "RR胜率": rr_series.dropna().gt(0).mean() if not rr_series.dropna().empty else np.nan,
            }
        ]
    )
    return summary


def run_single_factor_backtest(
    factor_df: pd.DataFrame,
    tradable_mask: pd.DataFrame,
    close_df: pd.DataFrame,
    rebalance_mask: pd.Series,
    benchmark_close: pd.Series | None,
    hold_num: int,
    factor_ascending: bool = False,
) -> dict[str, Any]:
    """运行单因子回测。"""
    factor_score = rank_score(mask_factor(factor_df, tradable_mask), ascending=factor_ascending)
    selection_df = select_top_n(factor_score, n=hold_num)

    weights = pd.DataFrame(0.0, index=selection_df.index, columns=selection_df.columns)
    last_weights = pd.Series(0.0, index=selection_df.columns)
    for dt in selection_df.index:
        if bool(rebalance_mask.get(dt, False)):
            selected = selection_df.loc[dt].fillna(False)
            count = int(selected.sum())
            last_weights = selected.astype(float) / count if count > 0 else pd.Series(0.0, index=selection_df.columns)
        weights.loc[dt] = last_weights.values

    portfolio = run_vectorbt_backtest(
        close_df=close_df,
        target_weights=weights,
        commission=config.COMMISSION,
        slippage=config.SLIPPAGE,
        init_cash=config.INITIAL_CASH,
    )
    results = extract_backtest_results(portfolio, benchmark_close=benchmark_close)
    results["selection_df"] = selection_df
    results["score_df"] = factor_score
    return results


def save_factor_evaluation_results(
    output_dir: str,
    factor_name: str,
    ic_series: pd.Series,
    rank_ic_series: pd.Series,
    rr_series: pd.Series,
    summary_df: pd.DataFrame,
    backtest_results: dict[str, Any],
) -> None:
    """保存单因子评估结果与图表。"""
    base_dir = Path(output_dir) / "factor_analysis" / factor_name
    run_dir = base_dir / "latest"
    run_dir.mkdir(parents=True, exist_ok=True)

    pd.concat([ic_series, rank_ic_series, rr_series], axis=1).to_csv(
        run_dir / "ic_ir_rr_timeseries.csv", encoding="utf-8-sig"
    )
    summary_df.to_csv(run_dir / "summary.csv", index=False, encoding="utf-8-sig")

    stats = backtest_results.get("stats")
    if stats is not None and hasattr(stats, "to_frame"):
        stats.to_frame(name="value").to_csv(run_dir / "single_factor_stats.csv", encoding="utf-8-sig")

    equity_curve = backtest_results.get("equity_curve")
    benchmark_close = backtest_results.get("benchmark_close")
    if isinstance(equity_curve, pd.Series):
        equity_curve.to_frame(name="equity").to_csv(run_dir / "single_factor_equity.csv", encoding="utf-8-sig")

    if isinstance(equity_curve, pd.Series):
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            plt.figure(figsize=(12, 6))
            equity_curve.plot(label=f"{factor_name} 单因子净值", linewidth=2)
            if isinstance(benchmark_close, pd.Series) and not benchmark_close.empty:
                benchmark_curve = benchmark_close.copy()
                benchmark_curve.index = pd.to_datetime(benchmark_curve.index.astype(str))
                benchmark_curve = benchmark_curve.reindex(equity_curve.index).ffill()
                if len(benchmark_curve) > 0 and pd.notna(benchmark_curve.iloc[0]) and benchmark_curve.iloc[0] != 0:
                    benchmark_curve = benchmark_curve / benchmark_curve.iloc[0] * equity_curve.iloc[0]
                    benchmark_curve.plot(label=config.BENCHMARK_NAME, linestyle="--")
            plt.title(f"{factor_name} 单因子回测净值")
            plt.xlabel("日期")
            plt.ylabel("净值")
            plt.legend()
            plt.tight_layout()
            plt.savefig(run_dir / "single_factor_equity.png", dpi=150)
            plt.close()

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        plt.figure(figsize=(12, 6))
        ic_series.dropna().plot(label="IC", alpha=0.7)
        rank_ic_series.dropna().plot(label="RankIC", alpha=0.7)
        plt.axhline(0, color="black", linewidth=1)
        plt.title(f"{factor_name} IC / RankIC 时序")
        plt.xlabel("日期")
        plt.ylabel("相关系数")
        plt.legend()
        plt.tight_layout()
        plt.savefig(run_dir / "ic_rankic.png", dpi=150)
        plt.close()

