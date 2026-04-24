from __future__ import annotations

from pathlib import Path
from typing import Callable
import subprocess
import warnings
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

from src.多因子 import config
from src.多因子.backtest_vectorbt import build_rebalance_mask
from src.多因子.data_loader import build_data_bundle, get_strategy_date_range
from src.多因子.factor_evaluation import (
    build_forward_returns,
    calc_ic_series,
    calc_rank_ic_series,
    calc_rr_series,
    run_single_factor_backtest,
    summarize_factor_metrics,
)
from src.多因子.factors.momentum import compute_momentum_factor
from src.多因子.factors.risk_adjusted_momentum import compute_risk_adjusted_momentum
from src.多因子.scoring import mask_factor, rank_score
from src.多因子.universe import build_tradable_mask


_CJK_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    "KaiTi",
    "FangSong",
    "DengXian",
]

CHART_OPTIONS = {
    "factor_dashboard": "核心指标总览图（IC / RankIC / RR）",
    "group_avg_returns": "分组平均未来收益图",
    "group_cumulative_nav": "分组累计净值图",
    "single_factor_equity_vs_benchmark": "单因子净值 vs 基准图",
}


def _configure_plot_font() -> None:
    """配置 matplotlib 中文字体。"""
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in _CJK_FONT_CANDIDATES:
        if font_name in available_fonts:
            plt.rcParams["font.sans-serif"] = [font_name]
            plt.rcParams["axes.unicode_minus"] = False
            return
    raise RuntimeError(
        "未找到可用中文字体，无法生成中文可视化。请安装或启用以下任一字体："
        + ", ".join(_CJK_FONT_CANDIDATES)
    )


_configure_plot_font()


FACTOR_REGISTRY: dict[str, tuple[Callable[[pd.DataFrame], pd.DataFrame], bool, str]] = {
    "momentum_20": (
        lambda close_df: compute_momentum_factor(close_df, window=config.MOMENTUM_WINDOW),
        False,
        "20日动量",
    ),
    "risk_adjusted_momentum_20": (
        lambda close_df: compute_risk_adjusted_momentum(close_df, window=config.RISK_ADJUSTED_WINDOW),
        False,
        "20日风险调整动量",
    ),
}


class VisualizerDialog:
    """运行前弹出参数选择窗口。"""

    WINDOW_WIDTH = 860
    WINDOW_HEIGHT = 760
    MIN_WIDTH = 760
    MIN_HEIGHT = 680

    def __init__(self) -> None:
        self.result: dict[str, object] | None = None
        default_start, default_end, _ = get_strategy_date_range()

        self.root = tk.Tk()
        self.root.title("因子可视化参数选择")
        self.root.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.root.resizable(True, True)
        self._center_window(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        outer = ttk.Frame(self.root)
        outer.pack(fill="both", expand=True)

        self.main_canvas = tk.Canvas(outer, highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.main_canvas.yview)
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)

        self.main_scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)

        self.container = ttk.Frame(self.main_canvas, padding=16)
        self.container_window = self.main_canvas.create_window((0, 0), window=self.container, anchor="nw")

        self.container.bind("<Configure>", self._on_container_configure)
        self.main_canvas.bind("<Configure>", self._on_canvas_configure)
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        title = ttk.Label(self.container, text="请选择因子可视化参数", font=("Microsoft YaHei", 16, "bold"))
        title.pack(anchor="w", pady=(0, 12))

        factor_frame = ttk.LabelFrame(self.container, text="1. 选择因子（可多选）", padding=12)
        factor_frame.pack(fill="both", expand=False, pady=(0, 10))
        self.factor_vars: dict[str, tk.BooleanVar] = {}

        factor_hint = ttk.Label(
            factor_frame,
            text="因子较多时可滚动查看，下方勾选框支持多行展示。",
            foreground="#666666",
        )
        factor_hint.pack(anchor="w", pady=(0, 8))

        factor_canvas_frame = ttk.Frame(factor_frame)
        factor_canvas_frame.pack(fill="both", expand=True)

        self.factor_canvas = tk.Canvas(factor_canvas_frame, height=220, highlightthickness=0)
        self.factor_scrollbar = ttk.Scrollbar(factor_canvas_frame, orient="vertical", command=self.factor_canvas.yview)
        self.factor_canvas.configure(yscrollcommand=self.factor_scrollbar.set)

        self.factor_scrollbar.pack(side="right", fill="y")
        self.factor_canvas.pack(side="left", fill="both", expand=True)

        self.factor_inner = ttk.Frame(self.factor_canvas)
        self.factor_inner_window = self.factor_canvas.create_window((0, 0), window=self.factor_inner, anchor="nw")

        self.factor_inner.bind("<Configure>", self._on_factor_inner_configure)
        self.factor_canvas.bind("<Configure>", self._on_factor_canvas_configure)

        for factor_name, (_, _, factor_label) in FACTOR_REGISTRY.items():
            var = tk.BooleanVar(value=True)
            self.factor_vars[factor_name] = var
            ttk.Checkbutton(self.factor_inner, text=f"{factor_name}（{factor_label}）", variable=var).pack(anchor="w", pady=2)

        date_frame = ttk.LabelFrame(self.container, text="2. 选择回测日期", padding=12)
        date_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(date_frame, text="开始日期（YYYYMMDD）").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Label(date_frame, text="结束日期（YYYYMMDD）").grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.start_entry = ttk.Entry(date_frame, width=20)
        self.start_entry.grid(row=0, column=1, sticky="w", pady=(0, 8))
        self.start_entry.insert(0, default_start)
        self.end_entry = ttk.Entry(date_frame, width=20)
        self.end_entry.grid(row=1, column=1, sticky="w")
        self.end_entry.insert(0, default_end)
        ttk.Label(date_frame, text="默认值来自统一日期函数，可直接修改。", foreground="#666666").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        chart_frame = ttk.LabelFrame(self.container, text="3. 选择要输出的图（默认全选）", padding=12)
        chart_frame.pack(fill="x", pady=(0, 10))
        self.chart_vars: dict[str, tk.BooleanVar] = {}
        for chart_key, chart_label in CHART_OPTIONS.items():
            var = tk.BooleanVar(value=True)
            self.chart_vars[chart_key] = var
            ttk.Checkbutton(chart_frame, text=chart_label, variable=var).pack(anchor="w", pady=2)

        display_frame = ttk.LabelFrame(self.container, text="4. 是否生成后直接弹图", padding=12)
        display_frame.pack(fill="x", pady=(0, 10))
        self.show_plots_var = tk.BooleanVar(value=False)
        ttk.Radiobutton(display_frame, text="不弹出（默认）", variable=self.show_plots_var, value=False).pack(anchor="w")
        ttk.Radiobutton(display_frame, text="弹出图片", variable=self.show_plots_var, value=True).pack(anchor="w")

        self.message_var = tk.StringVar(value="")
        ttk.Label(self.container, textvariable=self.message_var, foreground="#cc3333").pack(anchor="w", pady=(4, 12))

        button_frame = ttk.Frame(self.container)
        button_frame.pack(fill="x", pady=(0, 8))
        ttk.Button(button_frame, text="取消", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(button_frame, text="开始生成", command=self._confirm).pack(side="right")

    def _center_window(self, width: int, height: int) -> None:
        """让弹窗出现在屏幕正中间。"""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _on_container_configure(self, _event: tk.Event) -> None:
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.main_canvas.itemconfigure(self.container_window, width=event.width)

    def _on_factor_inner_configure(self, _event: tk.Event) -> None:
        self.factor_canvas.configure(scrollregion=self.factor_canvas.bbox("all"))

    def _on_factor_canvas_configure(self, event: tk.Event) -> None:
        self.factor_canvas.itemconfigure(self.factor_inner_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        widget = self.root.winfo_containing(self.root.winfo_pointerx(), self.root.winfo_pointery())
        if widget is None:
            return

        factor_widgets = {self.factor_canvas, self.factor_inner}
        parent = widget
        while parent is not None:
            if parent in factor_widgets:
                self.factor_canvas.yview_scroll(int(-event.delta / 120), "units")
                return
            parent = parent.master

        self.main_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _cancel(self) -> None:
        self.result = None
        self.root.destroy()

    def _confirm(self) -> None:
        selected_factors = [name for name, var in self.factor_vars.items() if var.get()]
        selected_charts = [name for name, var in self.chart_vars.items() if var.get()]
        start_date = self.start_entry.get().strip()
        end_date = self.end_entry.get().strip()

        if not selected_factors:
            self.message_var.set("请至少勾选一个因子。")
            return
        if not selected_charts:
            self.message_var.set("请至少勾选一种图表。")
            return
        if len(start_date) != 8 or not start_date.isdigit():
            self.message_var.set("开始日期格式必须为 YYYYMMDD。")
            return
        if len(end_date) != 8 or not end_date.isdigit():
            self.message_var.set("结束日期格式必须为 YYYYMMDD。")
            return
        if start_date > end_date:
            self.message_var.set("开始日期不能晚于结束日期。")
            return

        self.result = {
            "factors": selected_factors,
            "charts": selected_charts,
            "show_plots": bool(self.show_plots_var.get()),
            "start_date": start_date,
            "end_date": end_date,
        }
        self.root.destroy()

    def show(self) -> dict[str, object] | None:
        self.root.mainloop()
        return self.result


def _safe_savefig(path: Path) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        plt.tight_layout()
        plt.savefig(path, dpi=160)
        plt.close()


def _open_image(path: Path) -> None:
    try:
        subprocess.Popen(["cmd", "/c", "start", "", str(path)], shell=False)
    except Exception:
        pass


def _compute_group_returns(
    masked_factor_df: pd.DataFrame,
    forward_returns_df: pd.DataFrame,
    group_count: int = 5,
) -> pd.DataFrame:
    """按调仓期横截面分组，计算各组未来收益。"""
    result_rows: list[pd.Series] = []

    valid_dates = masked_factor_df.index.intersection(forward_returns_df.index)
    labels = [f"G{i}" for i in range(1, group_count + 1)]

    for dt in valid_dates:
        merged = pd.concat(
            [masked_factor_df.loc[dt], forward_returns_df.loc[dt]],
            axis=1,
            keys=["factor", "future_return"],
        ).dropna()
        if len(merged) < group_count:
            continue

        merged = merged.sort_values("factor", ascending=False).reset_index(drop=True)
        merged["group"] = pd.qcut(merged.index + 1, q=group_count, labels=labels)
        group_return = merged.groupby("group", observed=False)["future_return"].mean()
        group_return.name = dt
        result_rows.append(group_return)

    if not result_rows:
        return pd.DataFrame(columns=labels)

    return pd.DataFrame(result_rows).reindex(columns=labels)


def _save_group_return_plots(base_dir: Path, factor_label: str, group_return_df: pd.DataFrame) -> list[Path]:
    """保存分组收益的柱状图和累计净值图。"""
    saved_paths: list[Path] = []
    if group_return_df.empty:
        return saved_paths

    avg_group_return = group_return_df.mean()
    cumulative_group_nav = (1.0 + group_return_df.fillna(0.0)).cumprod()

    plt.figure(figsize=(12, 6))
    avg_group_return.plot(kind="bar", color=["#d65f5f", "#f2a65a", "#9cc17b", "#4d96ff", "#2d6cdf"])
    plt.axhline(0, color="black", linewidth=1)
    plt.title(f"{factor_label} 分组平均未来收益")
    plt.xlabel("分组（G1=最高因子组，G5=最低因子组）")
    plt.ylabel("平均未来收益")
    path = base_dir / "group_avg_returns.png"
    _safe_savefig(path)
    saved_paths.append(path)

    plt.figure(figsize=(12, 6))
    for column in cumulative_group_nav.columns:
        cumulative_group_nav[column].plot(label=column, linewidth=2)
    plt.title(f"{factor_label} 分组累计净值")
    plt.xlabel("调仓日期")
    plt.ylabel("累计净值")
    plt.legend()
    path = base_dir / "group_cumulative_nav.png"
    _safe_savefig(path)
    saved_paths.append(path)
    return saved_paths


def _save_metric_dashboard(
    base_dir: Path,
    factor_label: str,
    summary_df: pd.DataFrame,
    ic_series: pd.Series,
    rank_ic_series: pd.Series,
    rr_series: pd.Series,
) -> Path:
    """保存因子核心指标总览图。"""
    row = summary_df.iloc[0]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"{factor_label} 因子表现总览", fontsize=16)

    metric_names = ["IC均值", "ICIR", "RankIC均值", "RankICIR", "RR均值", "RR胜率"]
    metric_values = [float(row[name]) if pd.notna(row[name]) else 0.0 for name in metric_names]
    axes[0, 0].bar(metric_names, metric_values, color=["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b", "#e377c2"])
    axes[0, 0].axhline(0, color="black", linewidth=1)
    axes[0, 0].set_title("核心指标柱状图")
    axes[0, 0].tick_params(axis="x", rotation=20)

    axes[0, 1].plot(ic_series.dropna().index, ic_series.dropna().values, label="IC", linewidth=1.5)
    axes[0, 1].plot(rank_ic_series.dropna().index, rank_ic_series.dropna().values, label="RankIC", linewidth=1.5)
    axes[0, 1].axhline(0, color="black", linewidth=1)
    axes[0, 1].set_title("IC / RankIC 时序")
    axes[0, 1].legend()

    axes[1, 0].hist(ic_series.dropna(), bins=20, alpha=0.7, label="IC", color="#4d96ff")
    axes[1, 0].hist(rank_ic_series.dropna(), bins=20, alpha=0.5, label="RankIC", color="#f2a65a")
    axes[1, 0].axvline(0, color="black", linewidth=1)
    axes[1, 0].set_title("IC / RankIC 分布")
    axes[1, 0].legend()

    axes[1, 1].plot(rr_series.dropna().index, rr_series.dropna().values, color="#d65f5f", linewidth=1.5)
    axes[1, 1].axhline(0, color="black", linewidth=1)
    axes[1, 1].set_title("RR 时序")

    path = base_dir / "factor_dashboard.png"
    _safe_savefig(path)
    return path


def _save_group_return_table(base_dir: Path, group_return_df: pd.DataFrame) -> None:
    if group_return_df.empty:
        return

    group_return_df.to_csv(base_dir / "group_return_timeseries.csv", encoding="utf-8-sig")

    summary = pd.DataFrame(
        {
            "平均未来收益": group_return_df.mean(),
            "正收益占比": group_return_df.gt(0).mean(),
            "累计净值终值": (1.0 + group_return_df.fillna(0.0)).cumprod().iloc[-1],
        }
    )
    summary.to_csv(base_dir / "group_return_summary.csv", encoding="utf-8-sig")


def visualize_factor(
    factor_name: str,
    selected_charts: list[str],
    show_plots: bool,
    start_date: str,
    end_date: str,
) -> Path:
    """单独生成指定因子的可视化解释结果。"""
    if factor_name not in FACTOR_REGISTRY:
        raise ValueError(f"不支持的因子：{factor_name}，可选值：{', '.join(FACTOR_REGISTRY.keys())}")

    factor_builder, ascending, factor_label = FACTOR_REGISTRY[factor_name]

    data_bundle = build_data_bundle(
        max_price=config.MAX_PRICE,
        max_mcap=config.MAX_MCAP,
        need_download=config.NEED_DOWNLOAD,
        dividend_type=config.DIVIDEND_TYPE,
        start_date=start_date,
        end_date=end_date,
    )
    close_df = data_bundle.get("close")
    universe_df = data_bundle.get("universe")
    benchmark_close = data_bundle.get("benchmark_close")
    if close_df is None or universe_df is None or close_df.empty:
        raise ValueError("数据加载失败，无法生成因子可视化")

    tradable_mask = build_tradable_mask(universe_df=universe_df, close_df=close_df)
    rebalance_mask = build_rebalance_mask(close_df.index, freq=config.REBALANCE_FREQ)
    forward_returns_df = build_forward_returns(close_df, rebalance_mask)

    raw_factor_df = factor_builder(close_df)
    masked_factor_df = mask_factor(raw_factor_df, tradable_mask)
    factor_score_df = rank_score(masked_factor_df, ascending=ascending)

    ic_series = calc_ic_series(masked_factor_df, forward_returns_df)
    rank_ic_series = calc_rank_ic_series(masked_factor_df, forward_returns_df)
    rr_series = calc_rr_series(masked_factor_df, forward_returns_df, hold_num=config.HOLD_NUM)
    summary_df = summarize_factor_metrics(
        factor_name=factor_name,
        ic_series=ic_series,
        rank_ic_series=rank_ic_series,
        rr_series=rr_series,
        periods_per_year=config.IC_PERIODS_PER_YEAR,
    )
    backtest_results = run_single_factor_backtest(
        factor_df=raw_factor_df,
        tradable_mask=tradable_mask,
        close_df=close_df,
        rebalance_mask=rebalance_mask,
        benchmark_close=benchmark_close,
        hold_num=config.HOLD_NUM,
    )

    group_return_df = _compute_group_returns(masked_factor_df, forward_returns_df, group_count=5)

    output_dir = Path(__file__).resolve().parent / config.OUTPUT_DIR / "factor_visualization" / factor_name
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_df.to_csv(output_dir / "summary.csv", index=False, encoding="utf-8-sig")
    pd.concat([ic_series, rank_ic_series, rr_series], axis=1).to_csv(
        output_dir / "ic_rankic_rr_timeseries.csv", encoding="utf-8-sig"
    )
    factor_score_df.to_csv(output_dir / "factor_score_matrix.csv", encoding="utf-8-sig")
    _save_group_return_table(output_dir, group_return_df)

    opened_paths: list[Path] = []
    if "factor_dashboard" in selected_charts:
        opened_paths.append(_save_metric_dashboard(output_dir, factor_label, summary_df, ic_series, rank_ic_series, rr_series))
    if "group_avg_returns" in selected_charts or "group_cumulative_nav" in selected_charts:
        group_plot_paths = _save_group_return_plots(output_dir, factor_label, group_return_df)
        for path in group_plot_paths:
            if path.name == "group_avg_returns.png" and "group_avg_returns" in selected_charts:
                opened_paths.append(path)
            if path.name == "group_cumulative_nav.png" and "group_cumulative_nav" in selected_charts:
                opened_paths.append(path)

    equity_curve = backtest_results.get("equity_curve")
    if "single_factor_equity_vs_benchmark" in selected_charts and isinstance(equity_curve, pd.Series):
        plt.figure(figsize=(12, 6))
        equity_curve.plot(label=f"{factor_label} 单因子净值", linewidth=2)
        if isinstance(benchmark_close, pd.Series) and not benchmark_close.empty:
            benchmark_curve = benchmark_close.copy()
            benchmark_curve.index = pd.to_datetime(benchmark_curve.index.astype(str))
            benchmark_curve = benchmark_curve.reindex(equity_curve.index).ffill()
            if len(benchmark_curve) > 0 and pd.notna(benchmark_curve.iloc[0]) and benchmark_curve.iloc[0] != 0:
                benchmark_curve = benchmark_curve / benchmark_curve.iloc[0] * equity_curve.iloc[0]
                benchmark_curve.plot(label=config.BENCHMARK_NAME, linestyle="--")
        plt.title(f"{factor_label} 单因子净值 vs 基准")
        plt.xlabel("日期")
        plt.ylabel("净值")
        plt.legend()
        path = output_dir / "single_factor_equity_vs_benchmark.png"
        _safe_savefig(path)
        opened_paths.append(path)

    desc_text = [
        f"因子名称: {factor_label}",
        f"开始日期: {start_date}",
        f"结束日期: {end_date}",
        f"IC均值: {summary_df.iloc[0]['IC均值']:.6f}",
        f"ICIR: {summary_df.iloc[0]['ICIR']:.6f}",
        f"RankIC均值: {summary_df.iloc[0]['RankIC均值']:.6f}",
        f"RankICIR: {summary_df.iloc[0]['RankICIR']:.6f}",
        f"RR均值: {summary_df.iloc[0]['RR均值']:.6f}",
        f"RR胜率: {summary_df.iloc[0]['RR胜率']:.6f}",
        "说明: G1 为最高因子组，G5 为最低因子组；若分组收益呈阶梯状递减，说明因子分层较好。",
    ]
    (output_dir / "readme.txt").write_text("\n".join(desc_text), encoding="utf-8")

    if show_plots:
        for path in opened_paths:
            _open_image(path)

    print(f"因子可视化完成：{factor_name}")
    print(f"输出目录：{output_dir}")
    return output_dir


def main() -> None:
    dialog = VisualizerDialog()
    selected = dialog.show()
    if selected is None:
        print("已取消因子可视化。")
        return

    factors = selected["factors"]
    charts = selected["charts"]
    show_plots = bool(selected["show_plots"])
    start_date = str(selected["start_date"])
    end_date = str(selected["end_date"])

    for factor_name in factors:
        visualize_factor(
            factor_name=factor_name,
            selected_charts=charts,
            show_plots=show_plots,
            start_date=start_date,
            end_date=end_date,
        )


if __name__ == "__main__":
    main()
