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
from src.多因子.main import (
    Alpha101SelectionDialog,
    Alpha158SelectionDialog,
    Alpha191SelectionDialog,
    FACTOR_DIRECTIONS,
    FACTOR_LABELS,
    FACTOR_REGISTRY,
    _compute_registered_factor,
    _iter_factor_names,
    _load_last_run_config,
    _load_last_run_dates,
    _load_last_selected_factors,
    _make_label_text,
    _save_last_run_config,
)
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


class VisualizerDialog:
    """运行前弹出参数选择窗口。"""

    WINDOW_WIDTH = 860
    WINDOW_HEIGHT = 760
    MIN_WIDTH = 760
    MIN_HEIGHT = 680

    def __init__(self) -> None:
        self.result: dict[str, object] | None = None
        latest_start, latest_end, _ = get_strategy_date_range()
        self._latest_start = latest_start
        self._latest_end = latest_end
        last_start, last_end = _load_last_run_dates()
        default_start = last_start or latest_start
        default_end = last_end or latest_end
        last_run_config = _load_last_run_config()
        default_base_factors = _load_last_selected_factors("base", _iter_factor_names("base"))
        self.selected_alpha158_factors: list[str] = _load_last_selected_factors("alpha158")
        self.selected_alpha101_factors: list[str] = _load_last_selected_factors("alpha101")
        self.selected_alpha191_factors: list[str] = _load_last_selected_factors("alpha191")
        default_charts = last_run_config.get("visualizer_charts")
        if not isinstance(default_charts, list):
            default_charts = list(CHART_OPTIONS.keys())
        default_chart_set = {chart for chart in default_charts if isinstance(chart, str)}
        default_show_plots = bool(last_run_config.get("visualizer_show_plots", False))

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

        factor_hint = ttk.Label(factor_frame, text="与多因子主程序使用同一套因子注册和分组选择。", foreground="#666666")
        factor_hint.pack(anchor="w", pady=(0, 8))

        action_frame = ttk.Frame(factor_frame)
        action_frame.pack(anchor="w", pady=(0, 8))
        ttk.Button(action_frame, text="基础因子全选", command=self._select_all_factors).pack(side="left")
        ttk.Button(action_frame, text="基础因子全不选", command=self._clear_all_factors).pack(side="left", padx=(8, 0))
        ttk.Button(action_frame, text="基础因子反选", command=self._invert_factor_selection).pack(side="left", padx=(8, 0))

        base_frame = ttk.Frame(factor_frame)
        base_frame.pack(anchor="w", fill="x", pady=(0, 8))
        ttk.Label(base_frame, text="基础因子").grid(row=0, column=0, sticky="nw", padx=(0, 12))
        base_check_frame = ttk.Frame(base_frame)
        base_check_frame.grid(row=0, column=1, sticky="w")
        for row_index, factor_name in enumerate(_iter_factor_names("base")):
            var = tk.BooleanVar(value=factor_name in default_base_factors)
            self.factor_vars[factor_name] = var
            ttk.Checkbutton(base_check_frame, text=_make_label_text(factor_name), variable=var).grid(
                row=row_index,
                column=0,
                sticky="w",
                pady=2,
            )

        self.alpha158_summary_var = tk.StringVar(value="")
        self.alpha101_summary_var = tk.StringVar(value="")
        self.alpha191_summary_var = tk.StringVar(value="")
        self._build_group_selector(factor_frame, "Alpha158 因子", "启用 Alpha158", self.alpha158_summary_var, self._open_alpha158_dialog)
        self._build_group_selector(factor_frame, "Alpha101 因子", "启用 Alpha101", self.alpha101_summary_var, self._open_alpha101_dialog)
        self._build_group_selector(factor_frame, "国君朝阳191 因子", "启用 国君朝阳191", self.alpha191_summary_var, self._open_alpha191_dialog)
        self._refresh_group_summaries()

        date_frame = ttk.LabelFrame(self.container, text="2. 选择回测日期", padding=12)
        date_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(date_frame, text="开始日期（YYYYMMDD）").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Label(date_frame, text="结束日期（YYYYMMDD）").grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.start_entry = ttk.Entry(date_frame, width=20)
        self.start_entry.grid(row=0, column=1, sticky="w", pady=(0, 8))
        self.start_entry.insert(0, default_start)
        ttk.Button(date_frame, text="设为最新", command=self._reset_dates_to_latest).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(8, 0),
            pady=(0, 8),
        )
        self.end_entry = ttk.Entry(date_frame, width=20)
        self.end_entry.grid(row=1, column=1, sticky="w")
        self.end_entry.insert(0, default_end)
        self.date_hint_var = tk.StringVar(value=f"最新可用范围：{self._latest_start} ~ {self._latest_end}")
        ttk.Label(date_frame, textvariable=self.date_hint_var, foreground="#666666").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        chart_frame = ttk.LabelFrame(self.container, text="3. 选择要输出的图（默认全选）", padding=12)
        chart_frame.pack(fill="x", pady=(0, 10))
        self.chart_vars: dict[str, tk.BooleanVar] = {}
        for chart_key, chart_label in CHART_OPTIONS.items():
            var = tk.BooleanVar(value=chart_key in default_chart_set)
            self.chart_vars[chart_key] = var
            ttk.Checkbutton(chart_frame, text=chart_label, variable=var).pack(anchor="w", pady=2)

        display_frame = ttk.LabelFrame(self.container, text="4. 是否生成后直接弹图", padding=12)
        display_frame.pack(fill="x", pady=(0, 10))
        self.show_plots_var = tk.BooleanVar(value=default_show_plots)
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
        pass

    def _on_factor_canvas_configure(self, event: tk.Event) -> None:
        del event

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.main_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _select_all_factors(self) -> None:
        for var in self.factor_vars.values():
            var.set(True)

    def _clear_all_factors(self) -> None:
        for var in self.factor_vars.values():
            var.set(False)

    def _invert_factor_selection(self) -> None:
        for var in self.factor_vars.values():
            var.set(not var.get())

    def _build_group_selector(
        self,
        parent: ttk.Frame,
        title: str,
        check_text: str,
        summary_var: tk.StringVar,
        command: Callable[[], None],
    ) -> None:
        row_frame = ttk.Frame(parent)
        row_frame.pack(anchor="w", fill="x", pady=4)
        ttk.Label(row_frame, text=title, width=16).pack(side="left")
        ttk.Button(row_frame, text=f"选择 {title}...", command=command).pack(side="left", padx=(0, 10))
        ttk.Label(row_frame, text=check_text, foreground="#666666").pack(side="left")
        ttk.Label(row_frame, textvariable=summary_var, foreground="#666666").pack(side="left", padx=(10, 0))

    def _refresh_group_summaries(self) -> None:
        self.alpha158_summary_var.set(self._build_group_summary("alpha158", self.selected_alpha158_factors))
        self.alpha101_summary_var.set(self._build_group_summary("alpha101", self.selected_alpha101_factors))
        self.alpha191_summary_var.set(self._build_group_summary("alpha191", self.selected_alpha191_factors))

    def _build_group_summary(self, group: str, selected_factors: list[str]) -> str:
        return f"已选择 {len(selected_factors)} / {len(_iter_factor_names(group))} 个因子"

    def _open_alpha158_dialog(self) -> None:
        selected = Alpha158SelectionDialog(self.selected_alpha158_factors).show()
        if selected is not None:
            self.selected_alpha158_factors = selected
            self._refresh_group_summaries()

    def _open_alpha101_dialog(self) -> None:
        selected = Alpha101SelectionDialog(self.selected_alpha101_factors).show()
        if selected is not None:
            self.selected_alpha101_factors = selected
            self._refresh_group_summaries()

    def _open_alpha191_dialog(self) -> None:
        selected = Alpha191SelectionDialog(self.selected_alpha191_factors).show()
        if selected is not None:
            self.selected_alpha191_factors = selected
            self._refresh_group_summaries()

    def _reset_dates_to_latest(self) -> None:
        latest_start, latest_end, _ = get_strategy_date_range()
        self._latest_start = latest_start
        self._latest_end = latest_end
        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, latest_start)
        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(0, latest_end)
        self.date_hint_var.set(f"最新可用范围：{latest_start} ~ {latest_end}")

    def _cancel(self) -> None:
        self.result = None
        self.root.destroy()

    def _confirm(self) -> None:
        selected_base_factors = [name for name, var in self.factor_vars.items() if var.get()]
        selected_factors = (
            selected_base_factors
            + self.selected_alpha158_factors
            + self.selected_alpha101_factors
            + self.selected_alpha191_factors
        )
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
        last_run_config = _load_last_run_config()
        last_run_config.update(
            {
                "start_date": start_date,
                "end_date": end_date,
                "selected_factors": selected_factors,
                "visualizer_charts": selected_charts,
                "visualizer_show_plots": bool(self.show_plots_var.get()),
            }
        )
        _save_last_run_config(last_run_config)
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


def _calc_group_monotonicity(factor_name: str, group_return_df: pd.DataFrame) -> pd.DataFrame:
    if group_return_df.empty:
        return pd.DataFrame(
            [
                {
                    "factor": factor_name,
                    "direction": "none",
                    "strict_decreasing": False,
                    "strict_increasing": False,
                    "decreasing_score": np.nan,
                    "increasing_score": np.nan,
                    "best_monotonic_score": np.nan,
                    "spearman": np.nan,
                    "top_bottom_spread": np.nan,
                    "abs_top_bottom_spread": np.nan,
                    "g1_return": np.nan,
                    "g2_return": np.nan,
                    "g3_return": np.nan,
                    "g4_return": np.nan,
                    "g5_return": np.nan,
                }
            ]
        )

    avg_returns = group_return_df.mean().reindex(["G1", "G2", "G3", "G4", "G5"])
    values = avg_returns.to_numpy(dtype=float)
    valid_values = values[~np.isnan(values)]
    if len(valid_values) < 2:
        spearman = np.nan
        diffs = np.array([], dtype=float)
    else:
        spearman = pd.Series(values).corr(pd.Series(np.arange(1, len(values) + 1)), method="spearman")
        diffs = np.diff(values)

    valid_diffs = diffs[~np.isnan(diffs)]
    if len(valid_diffs) == 0:
        decreasing_score = np.nan
        increasing_score = np.nan
        strict_decreasing = False
        strict_increasing = False
    else:
        decreasing_score = float((valid_diffs < 0).sum() / len(valid_diffs))
        increasing_score = float((valid_diffs > 0).sum() / len(valid_diffs))
        strict_decreasing = bool((valid_diffs < 0).all())
        strict_increasing = bool((valid_diffs > 0).all())

    if pd.isna(spearman):
        direction = "none"
    elif spearman < 0:
        direction = "decreasing"
    elif spearman > 0:
        direction = "increasing"
    else:
        direction = "flat"

    top_bottom_spread = values[0] - values[-1] if not np.isnan(values[0]) and not np.isnan(values[-1]) else np.nan
    return pd.DataFrame(
        [
            {
                "factor": factor_name,
                "direction": direction,
                "strict_decreasing": strict_decreasing,
                "strict_increasing": strict_increasing,
                "decreasing_score": decreasing_score,
                "increasing_score": increasing_score,
                "best_monotonic_score": np.nanmax([decreasing_score, increasing_score]),
                "spearman": spearman,
                "top_bottom_spread": top_bottom_spread,
                "abs_top_bottom_spread": abs(top_bottom_spread) if not np.isnan(top_bottom_spread) else np.nan,
                "g1_return": values[0],
                "g2_return": values[1],
                "g3_return": values[2],
                "g4_return": values[3],
                "g5_return": values[4],
            }
        ]
    )


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

    ascending = FACTOR_DIRECTIONS[factor_name]
    factor_label = FACTOR_LABELS[factor_name]

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

    raw_factor_df = _compute_registered_factor(factor_name, data_bundle)
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
    monotonicity_df = _calc_group_monotonicity(factor_name, group_return_df)
    monotonicity_df.to_csv(output_dir / "group_monotonicity_summary.csv", index=False, encoding="utf-8-sig")

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

    output_dirs: list[Path] = []
    for factor_name in factors:
        output_dirs.append(
            visualize_factor(
                factor_name=factor_name,
                selected_charts=charts,
                show_plots=show_plots,
                start_date=start_date,
                end_date=end_date,
            )
        )

    monotonicity_rows: list[pd.DataFrame] = []
    for output_dir in output_dirs:
        summary_path = output_dir / "group_monotonicity_summary.csv"
        if summary_path.exists():
            monotonicity_rows.append(pd.read_csv(summary_path))
    if monotonicity_rows:
        batch_summary = pd.concat(monotonicity_rows, ignore_index=True)
        batch_summary = batch_summary.sort_values(
            by=["best_monotonic_score", "abs_top_bottom_spread", "spearman"],
            ascending=[False, False, False],
        )
        summary_dir = Path(__file__).resolve().parent / config.OUTPUT_DIR / "factor_visualization"
        batch_summary_path = summary_dir / "all_factor_monotonicity_summary.csv"
        batch_summary.to_csv(batch_summary_path, index=False, encoding="utf-8-sig")
        print(f"全因子单调性汇总：{batch_summary_path}")


if __name__ == "__main__":
    main()
