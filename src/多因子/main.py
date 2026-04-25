from __future__ import annotations

import importlib
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import tkinter as tk
from tkinter import ttk

import pandas as pd

from src.多因子 import config
from src.多因子.backtest_vectorbt import (
    build_rebalance_mask,
    build_target_weights,
    extract_backtest_results,
    run_vectorbt_backtest,
)
from src.多因子.data_loader import build_data_bundle, get_strategy_date_range
from src.多因子.factor_evaluation import (
    build_forward_returns,
    calc_ic_series,
    calc_rank_ic_series,
    calc_rr_series,
    run_single_factor_backtest,
    save_factor_evaluation_results,
    summarize_factor_metrics,
)
from src.多因子.factors.momentum import compute_momentum_factor
from src.多因子.factors.risk_adjusted_momentum import compute_risk_adjusted_momentum
from src.多因子.factors.alpha101._base import returns as alpha101_returns, vwap as alpha101_vwap
from src.多因子.report import save_backtest_results, save_selection_results, save_stage_results
from src.多因子.scoring import combine_factor_scores, mask_factor, rank_score, select_top_n
from src.多因子.universe import build_tradable_mask


# 因子方向定义：
# False 表示“因子值越大越好”，横截面排名时按降序打分；
# True 表示“因子值越小越好”，横截面排名时按升序打分。
# 当前默认均按“越大越好”处理，如个别因子需要反向，可在此单独覆盖。
BASE_FACTOR_DIRECTIONS = {
    "momentum_20": False,
    "risk_adjusted_momentum_20": False,
}

BASE_FACTOR_LABELS = {
    "momentum_20": "20日动量",
    "risk_adjusted_momentum_20": "20日风险调整动量",
}


ALPHA158_FACTOR_SPECS = {
    "kbar_open_close_ratio": {"args": ["open", "close"], "label": "Alpha158 K线开收比"},
    "kbar_high_low_ratio": {"args": ["high", "low"], "label": "Alpha158 K线高低比"},
    "kbar_close_open_range_position": {
        "args": ["open", "high", "low", "close"],
        "label": "Alpha158 K线实体占日内振幅",
    },
    "kbar_upper_shadow_ratio": {"args": ["high", "open", "close"], "label": "Alpha158 上影线比例"},
    "kbar_lower_shadow_ratio": {"args": ["low", "open", "close"], "label": "Alpha158 下影线比例"},
    "kbar_body_ratio": {"args": ["open", "close"], "label": "Alpha158 实体比例"},
    "ret_1": {"args": ["close"], "label": "Alpha158 1日收益率"},
    "ret_2": {"args": ["close"], "label": "Alpha158 2日收益率"},
    "ret_3": {"args": ["close"], "label": "Alpha158 3日收益率"},
    "ret_4": {"args": ["close"], "label": "Alpha158 4日收益率"},
    "ret_5": {"args": ["close"], "label": "Alpha158 5日收益率"},
    "ret_10": {"args": ["close"], "label": "Alpha158 10日收益率"},
    "ret_20": {"args": ["close"], "label": "Alpha158 20日收益率"},
    "ret_30": {"args": ["close"], "label": "Alpha158 30日收益率"},
    "ret_60": {"args": ["close"], "label": "Alpha158 60日收益率"},
    "ret_120": {"args": ["close"], "label": "Alpha158 120日收益率"},
    "ret_240": {"args": ["close"], "label": "Alpha158 240日收益率"},
    "ma_5_ratio": {"args": ["close"], "label": "Alpha158 收盘价/MA5"},
    "ma_10_ratio": {"args": ["close"], "label": "Alpha158 收盘价/MA10"},
    "ma_20_ratio": {"args": ["close"], "label": "Alpha158 收盘价/MA20"},
    "ma_30_ratio": {"args": ["close"], "label": "Alpha158 收盘价/MA30"},
    "ma_60_ratio": {"args": ["close"], "label": "Alpha158 收盘价/MA60"},
    "ma_120_ratio": {"args": ["close"], "label": "Alpha158 收盘价/MA120"},
    "ma_240_ratio": {"args": ["close"], "label": "Alpha158 收盘价/MA240"},
    "std_5": {"args": ["close"], "label": "Alpha158 5日收益波动率"},
    "std_10": {"args": ["close"], "label": "Alpha158 10日收益波动率"},
    "std_20": {"args": ["close"], "label": "Alpha158 20日收益波动率"},
    "std_30": {"args": ["close"], "label": "Alpha158 30日收益波动率"},
    "std_60": {"args": ["close"], "label": "Alpha158 60日收益波动率"},
    "std_120": {"args": ["close"], "label": "Alpha158 120日收益波动率"},
    "std_240": {"args": ["close"], "label": "Alpha158 240日收益波动率"},
    "roc_rank_5": {"args": ["close"], "label": "Alpha158 5日收益时序排名"},
    "roc_rank_10": {"args": ["close"], "label": "Alpha158 10日收益时序排名"},
    "roc_rank_20": {"args": ["close"], "label": "Alpha158 20日收益时序排名"},
    "roc_rank_30": {"args": ["close"], "label": "Alpha158 30日收益时序排名"},
    "roc_rank_60": {"args": ["close"], "label": "Alpha158 60日收益时序排名"},
    "volume_ma_5_ratio": {"args": ["volume"], "label": "Alpha158 成交量/VMA5"},
    "volume_ma_10_ratio": {"args": ["volume"], "label": "Alpha158 成交量/VMA10"},
    "volume_ma_20_ratio": {"args": ["volume"], "label": "Alpha158 成交量/VMA20"},
    "volume_ma_30_ratio": {"args": ["volume"], "label": "Alpha158 成交量/VMA30"},
    "volume_std_5": {"args": ["volume"], "label": "Alpha158 5日量能波动率"},
    "volume_std_10": {"args": ["volume"], "label": "Alpha158 10日量能波动率"},
    "volume_std_20": {"args": ["volume"], "label": "Alpha158 20日量能波动率"},
    "volume_std_30": {"args": ["volume"], "label": "Alpha158 30日量能波动率"},
    "price_volume_corr_5": {"args": ["close", "volume"], "label": "Alpha158 5日价量相关"},
    "price_volume_corr_10": {"args": ["close", "volume"], "label": "Alpha158 10日价量相关"},
    "price_volume_corr_20": {"args": ["close", "volume"], "label": "Alpha158 20日价量相关"},
    "price_volume_corr_30": {"args": ["close", "volume"], "label": "Alpha158 30日价量相关"},
    "price_range_position_5": {"args": ["high", "low", "close"], "label": "Alpha158 5日区间位置"},
    "price_range_position_10": {"args": ["high", "low", "close"], "label": "Alpha158 10日区间位置"},
    "price_range_position_20": {"args": ["high", "low", "close"], "label": "Alpha158 20日区间位置"},
    "price_range_position_30": {"args": ["high", "low", "close"], "label": "Alpha158 30日区间位置"},
    "price_range_position_60": {"args": ["high", "low", "close"], "label": "Alpha158 60日区间位置"},
    "price_range_position_120": {"args": ["high", "low", "close"], "label": "Alpha158 120日区间位置"},
    "volume_position_5": {"args": ["volume"], "label": "Alpha158 5日量能位置"},
    "volume_position_10": {"args": ["volume"], "label": "Alpha158 10日量能位置"},
    "volume_position_20": {"args": ["volume"], "label": "Alpha158 20日量能位置"},
    "volume_position_30": {"args": ["volume"], "label": "Alpha158 30日量能位置"},
    "price_volume_ratio": {"args": ["high", "low", "close", "volume"], "label": "Alpha158 典型价/成交量"},
    "amount_mean_5_ratio": {"args": ["high", "low", "close", "amount"], "label": "Alpha158 5日均成交额/典型价"},
    "amount_mean_10_ratio": {"args": ["high", "low", "close", "amount"], "label": "Alpha158 10日均成交额/典型价"},
    "amount_mean_20_ratio": {"args": ["high", "low", "close", "amount"], "label": "Alpha158 20日均成交额/典型价"},
    "intraday_return": {"args": ["open", "close"], "label": "Alpha158 日内收益率"},
    "intraday_range_ratio": {"args": ["high", "low", "close"], "label": "Alpha158 日内振幅/收盘价"},
    "gap_ratio": {"args": ["open", "close"], "label": "Alpha158 跳空比例"},
    "amplitude_5": {"args": ["high", "low", "close"], "label": "Alpha158 5日平均振幅"},
    "amplitude_10": {"args": ["high", "low", "close"], "label": "Alpha158 10日平均振幅"},
    "amplitude_20": {"args": ["high", "low", "close"], "label": "Alpha158 20日平均振幅"},
    "amplitude_30": {"args": ["high", "low", "close"], "label": "Alpha158 30日平均振幅"},
    "amplitude_60": {"args": ["high", "low", "close"], "label": "Alpha158 60日平均振幅"},
    "return_mean_5": {"args": ["close"], "label": "Alpha158 5日日收益均值"},
    "return_mean_10": {"args": ["close"], "label": "Alpha158 10日日收益均值"},
    "return_mean_20": {"args": ["close"], "label": "Alpha158 20日日收益均值"},
    "return_mean_30": {"args": ["close"], "label": "Alpha158 30日日收益均值"},
    "return_mean_60": {"args": ["close"], "label": "Alpha158 60日日收益均值"},
    "downside_std_20": {"args": ["close"], "label": "Alpha158 20日下行波动率"},
    "downside_std_60": {"args": ["close"], "label": "Alpha158 60日下行波动率"},
    "turnover_amount_ratio": {"args": ["amount", "volume"], "label": "Alpha158 成交额/成交量"},
}


def _discover_alpha158_factors() -> dict[str, dict[str, object]]:
    """扫描 alpha158 子目录，构建可注册因子清单。"""
    alpha_dir = Path(__file__).resolve().parent / "factors" / "alpha158"
    if not alpha_dir.exists():
        return {}

    discovered: dict[str, dict[str, object]] = {}
    for file_path in sorted(alpha_dir.glob("*.py")):
        if file_path.stem.startswith("_"):
            continue
        factor_name = file_path.stem
        spec = ALPHA158_FACTOR_SPECS.get(factor_name)
        if spec is None:
            continue
        discovered[f"alpha158.{factor_name}"] = {
            "module": f"src.多因子.factors.alpha158.{factor_name}",
            "function": f"compute_{factor_name}",
            "args": list(spec["args"]),
            "label": str(spec["label"]),
            "ascending": False,
            "group": "alpha158",
        }
    return discovered


ALPHA101_FACTOR_SPECS = {
    "alpha001": {"args": ["close"], "label": "Alpha101 #001"},
    "alpha002": {"args": ["open", "close", "volume"], "label": "Alpha101 #002"},
    "alpha003": {"args": ["open", "volume"], "label": "Alpha101 #003"},
    "alpha004": {"args": ["low"], "label": "Alpha101 #004"},
    "alpha005": {"args": ["open", "close", "vwap"], "label": "Alpha101 #005"},
    "alpha006": {"args": ["open", "volume"], "label": "Alpha101 #006"},
    "alpha007": {"args": ["close", "volume"], "label": "Alpha101 #007"},
    "alpha008": {"args": ["open", "returns"], "label": "Alpha101 #008"},
    "alpha009": {"args": ["close"], "label": "Alpha101 #009"},
    "alpha010": {"args": ["close"], "label": "Alpha101 #010"},
    "alpha011": {"args": ["close", "vwap", "volume"], "label": "Alpha101 #011"},
    "alpha012": {"args": ["volume", "close"], "label": "Alpha101 #012"},
    "alpha013": {"args": ["close", "volume"], "label": "Alpha101 #013"},
    "alpha014": {"args": ["open", "volume", "returns"], "label": "Alpha101 #014"},
    "alpha015": {"args": ["high", "volume"], "label": "Alpha101 #015"},
    "alpha016": {"args": ["high", "volume"], "label": "Alpha101 #016"},
    "alpha017": {"args": ["close", "vwap"], "label": "Alpha101 #017"},
    "alpha018": {"args": ["open", "close"], "label": "Alpha101 #018"},
    "alpha019": {"args": ["close"], "label": "Alpha101 #019"},
    "alpha020": {"args": ["open", "high", "low", "close"], "label": "Alpha101 #020"},
}


def _discover_alpha101_factors() -> dict[str, dict[str, object]]:
    """扫描 alpha101 子目录，构建可注册因子清单。"""
    alpha_dir = Path(__file__).resolve().parent / "factors" / "alpha101"
    if not alpha_dir.exists():
        return {}

    discovered: dict[str, dict[str, object]] = {}
    for file_path in sorted(alpha_dir.glob("alpha*.py")):
        if file_path.stem.startswith("_"):
            continue
        factor_name = file_path.stem
        spec = ALPHA101_FACTOR_SPECS.get(factor_name)
        if spec is None:
            continue
        factor_key = f"alpha101.{factor_name}"
        discovered[factor_key] = {
            "module": f"src.多因子.factors.alpha101.{factor_name}",
            "function": f"compute_{factor_name}",
            "args": list(spec["args"]),
            "label": str(spec["label"]),
            "ascending": False,
            "group": "alpha101",
        }
    return discovered


FACTOR_REGISTRY: dict[str, dict[str, object]] = {
    "momentum_20": {
        "kind": "builtin",
        "label": BASE_FACTOR_LABELS["momentum_20"],
        "ascending": BASE_FACTOR_DIRECTIONS["momentum_20"],
        "group": "base",
    },
    "risk_adjusted_momentum_20": {
        "kind": "builtin",
        "label": BASE_FACTOR_LABELS["risk_adjusted_momentum_20"],
        "ascending": BASE_FACTOR_DIRECTIONS["risk_adjusted_momentum_20"],
        "group": "base",
    },
}
FACTOR_REGISTRY.update(_discover_alpha158_factors())
FACTOR_REGISTRY.update(_discover_alpha101_factors())

FACTOR_DIRECTIONS = {name: bool(spec["ascending"]) for name, spec in FACTOR_REGISTRY.items()}
FACTOR_LABELS = {name: str(spec["label"]) for name, spec in FACTOR_REGISTRY.items()}


def _compute_registered_factor(factor_name: str, data_bundle: dict[str, object]) -> pd.DataFrame:
    """按注册表定义计算单个因子。"""
    if factor_name == "momentum_20":
        close_df = data_bundle.get("close")
        if not isinstance(close_df, pd.DataFrame):
            raise ValueError("缺少 close 数据，无法计算 momentum_20")
        return compute_momentum_factor(close_df, window=config.MOMENTUM_WINDOW)

    if factor_name == "risk_adjusted_momentum_20":
        close_df = data_bundle.get("close")
        if not isinstance(close_df, pd.DataFrame):
            raise ValueError("缺少 close 数据，无法计算 risk_adjusted_momentum_20")
        return compute_risk_adjusted_momentum(close_df, window=config.RISK_ADJUSTED_WINDOW)

    spec = FACTOR_REGISTRY.get(factor_name)
    if spec is None:
        raise ValueError(f"未注册的因子: {factor_name}")

    module_name = spec.get("module")
    function_name = spec.get("function")
    if not isinstance(module_name, str) or not isinstance(function_name, str):
        raise ValueError(f"因子 {factor_name} 的模块注册信息不完整")

    module = importlib.import_module(module_name)
    compute_func = getattr(module, function_name)
    args = []
    for field_name in spec.get("args", []):
        if field_name == "vwap":
            amount_df = data_bundle.get("amount")
            volume_df = data_bundle.get("volume")
            if not isinstance(amount_df, pd.DataFrame) or not isinstance(volume_df, pd.DataFrame):
                raise ValueError(f"计算因子 {factor_name} 时缺少字段: vwap")
            args.append(alpha101_vwap(amount_df, volume_df))
            continue
        if field_name == "returns":
            close_df = data_bundle.get("close")
            if not isinstance(close_df, pd.DataFrame):
                raise ValueError(f"计算因子 {factor_name} 时缺少字段: returns")
            args.append(alpha101_returns(close_df))
            continue
        field_df = data_bundle.get(str(field_name))
        if not isinstance(field_df, pd.DataFrame):
            raise ValueError(f"计算因子 {factor_name} 时缺少字段: {field_name}")
        args.append(field_df)
    return compute_func(*args)


def _configure_scrollable_frame(canvas: tk.Canvas, scroll_frame: ttk.Frame) -> None:
    """配置滚动容器，避免 lambda 捕获导致的类型告警。"""

    def _on_configure(event: tk.Event[tk.Misc]) -> None:
        del event
        canvas.configure(scrollregion=canvas.bbox("all"))

    scroll_frame.bind("<Configure>", _on_configure)


class FactorGroupSelectionDialog:
    """分组因子单独选择窗口。"""

    def __init__(self, group: str, title: str, selected_factors: list[str] | None = None) -> None:
        self.result: list[str] | None = None
        self.selected_factors = set(selected_factors or [])
        self.group = group
        self.group_title = title
        self.group_factor_names = _iter_factor_names(group)

        self.root = tk.Toplevel()
        self.root.title(f"选择 {title} 因子")
        self.root.resizable(False, False)
        self._center_window(620, 680)
        self.root.transient()
        self.root.grab_set()

        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text=f"请选择要启用的 {title} 因子", font=("Microsoft YaHei", 13, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text=f"这些因子位于 factors/{group} 子目录，勾选后会参与回测。",
            foreground="#666666",
        ).pack(anchor="w", pady=(4, 10))

        action_frame = ttk.Frame(container)
        action_frame.pack(anchor="w", pady=(0, 8))
        ttk.Button(action_frame, text="全选", command=self._select_all).pack(side="left")
        ttk.Button(action_frame, text="全不选", command=self._clear_all).pack(side="left", padx=(8, 0))
        ttk.Button(action_frame, text="反选", command=self._invert_all).pack(side="left", padx=(8, 0))

        canvas = tk.Canvas(container, width=560, height=500, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        _configure_scrollable_frame(canvas, scroll_frame)
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.factor_vars: dict[str, tk.BooleanVar] = {}
        for row_index, factor_name in enumerate(self.group_factor_names):
            var = tk.BooleanVar(value=factor_name in self.selected_factors)
            self.factor_vars[factor_name] = var
            ttk.Checkbutton(
                scroll_frame,
                text=_make_label_text(factor_name),
                variable=var,
            ).grid(row=row_index, column=0, sticky="w", pady=2)

        self.message_var = tk.StringVar(value="")
        ttk.Label(container, textvariable=self.message_var, foreground="#cc3333").pack(anchor="w", pady=(10, 8))

        button_frame = ttk.Frame(container)
        button_frame.pack(anchor="e")
        ttk.Button(button_frame, text="取消", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(button_frame, text="确定", command=self._confirm).pack(side="right")

        self.root.protocol("WM_DELETE_WINDOW", self._cancel)

    def _center_window(self, width: int, height: int) -> None:
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _select_all(self) -> None:
        for var in self.factor_vars.values():
            var.set(True)

    def _clear_all(self) -> None:
        for var in self.factor_vars.values():
            var.set(False)

    def _invert_all(self) -> None:
        for var in self.factor_vars.values():
            var.set(not var.get())

    def _cancel(self) -> None:
        self.result = [name for name, var in self.factor_vars.items() if var.get()]
        self.root.destroy()

    def _confirm(self) -> None:
        self.result = [name for name, var in self.factor_vars.items() if var.get()]
        self.root.destroy()

    def show(self) -> list[str] | None:
        self.root.wait_window()
        return self.result


class Alpha158SelectionDialog(FactorGroupSelectionDialog):
    """Alpha158 因子单独选择窗口。"""

    def __init__(self, selected_factors: list[str] | None = None) -> None:
        super().__init__(group="alpha158", title="Alpha158", selected_factors=selected_factors)


class Alpha101SelectionDialog(FactorGroupSelectionDialog):
    """Alpha101 因子单独选择窗口。"""

    def __init__(self, selected_factors: list[str] | None = None) -> None:
        super().__init__(group="alpha101", title="Alpha101", selected_factors=selected_factors)


def _iter_factor_names(group: str | None = None) -> list[str]:
    """按分组返回注册因子名称列表。"""
    factor_names: list[str] = []
    for name, spec in FACTOR_REGISTRY.items():
        current_group = spec.get("group")
        if group is not None and current_group != group:
            continue
        factor_names.append(name)
    return factor_names


def _make_label_text(factor_name: str) -> str:
    """构造界面显示用的因子名称。"""
    return f"{factor_name}（{FACTOR_LABELS[factor_name]}）"


class StrategyRunDialog:
    """运行前弹出参数选择窗口。"""

    def __init__(self) -> None:
        self.result: dict[str, object] | None = None
        default_start, default_end, _ = get_strategy_date_range()
        self.selected_alpha158_factors: list[str] = []
        self.selected_alpha101_factors: list[str] = []

        self.root = tk.Tk()
        self.root.title("多因子运行参数")
        self.root.resizable(False, False)
        self._center_window(680, 560)

        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        title = ttk.Label(container, text="请选择本次运行参数", font=("Microsoft YaHei", 14, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        ttk.Label(container, text="开始日期（YYYYMMDD）").grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.start_entry = ttk.Entry(container, width=22)
        self.start_entry.grid(row=1, column=1, sticky="w", pady=(0, 8))
        self.start_entry.insert(0, default_start)

        ttk.Label(container, text="结束日期（YYYYMMDD）").grid(row=2, column=0, sticky="w", pady=(0, 12))
        self.end_entry = ttk.Entry(container, width=22)
        self.end_entry.grid(row=2, column=1, sticky="w", pady=(0, 12))
        self.end_entry.insert(0, default_end)

        ttk.Label(container, text="基础因子（可多选）").grid(row=3, column=0, sticky="nw", pady=(0, 10))
        factor_section = ttk.Frame(container)
        factor_section.grid(row=3, column=1, sticky="w", pady=(0, 10))

        factor_action_frame = ttk.Frame(factor_section)
        factor_action_frame.pack(anchor="w", pady=(0, 6))
        ttk.Button(factor_action_frame, text="全选", command=self._select_all_factors).pack(side="left")
        ttk.Button(factor_action_frame, text="全不选", command=self._clear_all_factors).pack(side="left", padx=(8, 0))
        ttk.Button(factor_action_frame, text="反选", command=self._invert_factor_selection).pack(side="left", padx=(8, 0))

        self.factor_vars: dict[str, tk.BooleanVar] = {}
        factor_check_frame = ttk.Frame(factor_section)
        factor_check_frame.pack(anchor="w")
        base_factor_names = _iter_factor_names("base")
        for row_index, factor_name in enumerate(base_factor_names):
            var = tk.BooleanVar(value=True)
            self.factor_vars[factor_name] = var
            factor_text = _make_label_text(factor_name)
            ttk.Checkbutton(factor_check_frame, text=factor_text, variable=var).grid(
                row=row_index,
                column=0,
                sticky="w",
                pady=2,
            )

        ttk.Label(container, text="Alpha158 因子").grid(row=4, column=0, sticky="nw", pady=(0, 12))
        alpha_frame = ttk.Frame(container)
        alpha_frame.grid(row=4, column=1, sticky="w", pady=(0, 12))
        self.alpha158_var = tk.IntVar(value=0)
        self.alpha158_check = tk.Checkbutton(
            alpha_frame,
            text="启用 Alpha158",
            variable=self.alpha158_var,
            onvalue=1,
            offvalue=0,
            tristatevalue=-1,
            indicatoron=True,
            selectcolor="#bfbfbf",
            command=self._toggle_alpha158_from_main,
        )
        self.alpha158_check.pack(side="left")
        ttk.Button(alpha_frame, text="选择 Alpha158 因子...", command=self._open_alpha158_dialog).pack(side="left", padx=(10, 0))
        self.alpha158_summary_var = tk.StringVar(value=self._build_alpha158_summary())
        ttk.Label(alpha_frame, textvariable=self.alpha158_summary_var, foreground="#666666").pack(side="left", padx=(10, 0))

        ttk.Label(container, text="Alpha101 因子").grid(row=5, column=0, sticky="nw", pady=(0, 12))
        alpha101_frame = ttk.Frame(container)
        alpha101_frame.grid(row=5, column=1, sticky="w", pady=(0, 12))
        self.alpha101_var = tk.IntVar(value=0)
        self.alpha101_check = tk.Checkbutton(
            alpha101_frame,
            text="启用 Alpha101",
            variable=self.alpha101_var,
            onvalue=1,
            offvalue=0,
            tristatevalue=-1,
            indicatoron=True,
            selectcolor="#bfbfbf",
            command=self._toggle_alpha101_from_main,
        )
        self.alpha101_check.pack(side="left")
        ttk.Button(alpha101_frame, text="选择 Alpha101 因子...", command=self._open_alpha101_dialog).pack(side="left", padx=(10, 0))
        self.alpha101_summary_var = tk.StringVar(value=self._build_alpha101_summary())
        ttk.Label(alpha101_frame, textvariable=self.alpha101_summary_var, foreground="#666666").pack(side="left", padx=(10, 0))

        ttk.Label(container, text="运行到第几阶段").grid(row=6, column=0, sticky="nw")
        self.max_stage_var = tk.IntVar(value=4)
        stage_frame = ttk.Frame(container)
        stage_frame.grid(row=6, column=1, sticky="w")
        for stage, label in [
            (1, "阶段1：单因子评估"),
            (2, "阶段2：指标初筛"),
            (3, "阶段3：相关性去冗余"),
            (4, "阶段4：组合构建与回测"),
        ]:
            ttk.Radiobutton(stage_frame, text=label, variable=self.max_stage_var, value=stage).pack(anchor="w", pady=1)

        ttk.Label(container, text="默认日期沿用当前策略原始范围，可直接修改。", foreground="#666666").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(12, 4)
        )

        self.message_var = tk.StringVar(value="")
        ttk.Label(container, textvariable=self.message_var, foreground="#cc3333").grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(4, 10)
        )

        button_frame = ttk.Frame(container)
        button_frame.grid(row=9, column=0, columnspan=2, sticky="e")
        ttk.Button(button_frame, text="取消", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(button_frame, text="开始运行", command=self._confirm).pack(side="right")

        container.columnconfigure(1, weight=1)
        self._sync_alpha158_main_state()
        self._sync_alpha101_main_state()
        self.root.protocol("WM_DELETE_WINDOW", self._cancel)

    def _center_window(self, width: int, height: int) -> None:
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _select_all_factors(self) -> None:
        for var in self.factor_vars.values():
            var.set(True)

    def _clear_all_factors(self) -> None:
        for var in self.factor_vars.values():
            var.set(False)

    def _invert_factor_selection(self) -> None:
        for var in self.factor_vars.values():
            var.set(not var.get())

    def _set_alpha158_state(self, state: str) -> None:
        """设置 Alpha158 主复选框状态。"""
        if state == "all":
            self.alpha158_var.set(1)
        elif state == "partial":
            self.alpha158_var.set(-1)
        else:
            self.alpha158_var.set(0)
        self.alpha158_check.update_idletasks()

    def _sync_alpha158_main_state(self) -> None:
        """根据已选数量同步主界面 Alpha158 复选框状态。"""
        total_count = len(_iter_factor_names("alpha158"))
        selected_count = len(self.selected_alpha158_factors)
        if selected_count <= 0:
            self._set_alpha158_state("none")
        elif selected_count >= total_count:
            self._set_alpha158_state("all")
        else:
            self._set_alpha158_state("partial")
        self.alpha158_summary_var.set(self._build_alpha158_summary())

    def _toggle_alpha158_from_main(self) -> None:
        """主界面切换 Alpha158 全选/全不选。"""
        if self.alpha158_var.get() == 1:
            self.selected_alpha158_factors = _iter_factor_names("alpha158")
        else:
            self.selected_alpha158_factors = []
        self._sync_alpha158_main_state()

    def _build_alpha158_summary(self) -> str:
        total_count = len(_iter_factor_names("alpha158"))
        selected_count = len(self.selected_alpha158_factors)
        return f"已选择 {selected_count} / {total_count} 个因子"

    def _set_alpha101_state(self, state: str) -> None:
        """设置 Alpha101 主复选框状态。"""
        if state == "all":
            self.alpha101_var.set(1)
        elif state == "partial":
            self.alpha101_var.set(-1)
        else:
            self.alpha101_var.set(0)
        self.alpha101_check.update_idletasks()

    def _sync_alpha101_main_state(self) -> None:
        """根据已选数量同步主界面 Alpha101 复选框状态。"""
        total_count = len(_iter_factor_names("alpha101"))
        selected_count = len(self.selected_alpha101_factors)
        if selected_count <= 0:
            self._set_alpha101_state("none")
        elif selected_count >= total_count:
            self._set_alpha101_state("all")
        else:
            self._set_alpha101_state("partial")
        self.alpha101_summary_var.set(self._build_alpha101_summary())

    def _toggle_alpha101_from_main(self) -> None:
        """主界面切换 Alpha101 全选/全不选。"""
        if self.alpha101_var.get() == 1:
            self.selected_alpha101_factors = _iter_factor_names("alpha101")
        else:
            self.selected_alpha101_factors = []
        self._sync_alpha101_main_state()

    def _build_alpha101_summary(self) -> str:
        total_count = len(_iter_factor_names("alpha101"))
        selected_count = len(self.selected_alpha101_factors)
        return f"已选择 {selected_count} / {total_count} 个因子"

    def _open_alpha158_dialog(self) -> None:
        dialog = Alpha158SelectionDialog(self.selected_alpha158_factors)
        selected = dialog.show()
        if selected is None:
            return
        self.selected_alpha158_factors = selected
        self._sync_alpha158_main_state()

    def _open_alpha101_dialog(self) -> None:
        dialog = Alpha101SelectionDialog(self.selected_alpha101_factors)
        selected = dialog.show()
        if selected is None:
            return
        self.selected_alpha101_factors = selected
        self._sync_alpha101_main_state()

    def _cancel(self) -> None:
        self.result = None
        self.root.destroy()

    def _confirm(self) -> None:
        start_date = self.start_entry.get().strip()
        end_date = self.end_entry.get().strip()
        if not (start_date.isdigit() and len(start_date) == 8):
            self.message_var.set("开始日期格式不正确，请输入 YYYYMMDD")
            return
        if not (end_date.isdigit() and len(end_date) == 8):
            self.message_var.set("结束日期格式不正确，请输入 YYYYMMDD")
            return
        if start_date > end_date:
            self.message_var.set("开始日期不能晚于结束日期")
            return

        selected_base_factors = [factor_name for factor_name, var in self.factor_vars.items() if var.get()]
        selected_factors = selected_base_factors + self.selected_alpha158_factors + self.selected_alpha101_factors
        if not selected_factors:
            self.message_var.set("请至少选择一个因子")
            return

        self.result = {
            "start_date": start_date,
            "end_date": end_date,
            "max_stage": int(self.max_stage_var.get()),
            "selected_factors": selected_factors,
        }
        self.root.destroy()

    def show(self) -> dict[str, object] | None:
        self.root.mainloop()
        return self.result


def _passes_threshold(value: float, threshold: float | None, *, use_abs: bool = False) -> bool:
    """判断单个指标是否通过阈值。"""
    if threshold is None:
        return True
    if pd.isna(value):
        return False
    metric_value = abs(float(value)) if use_abs else float(value)
    return bool(metric_value >= threshold)


def _infer_factor_direction(row: pd.Series) -> int:
    """根据候选因子指标推断后续组合使用方向。"""
    rank_ic_mean = row.get("RankIC均值")
    if pd.notna(rank_ic_mean) and float(rank_ic_mean) != 0.0:
        return 1 if float(rank_ic_mean) > 0 else -1

    ic_mean = row.get("IC均值")
    if pd.notna(ic_mean) and float(ic_mean) != 0.0:
        return 1 if float(ic_mean) > 0 else -1

    return 1


def _apply_factor_direction(score_df: pd.DataFrame, direction: int) -> pd.DataFrame:
    """按推断方向统一因子分数，保证分数越高越偏多。"""
    if direction >= 0:
        return score_df
    return score_df * -1


def _build_candidate_status(candidate_metrics_df: pd.DataFrame) -> pd.DataFrame:
    """根据候选因子指标总表，生成“阶段一：初筛状态表”。"""
    rows: list[dict[str, object]] = []
    for _, row in candidate_metrics_df.iterrows():
        direction = _infer_factor_direction(row)
        metric_checks = {
            "IC均值通过": _passes_threshold(row["IC均值"], config.MIN_IC_MEAN, use_abs=True),
            "ICIR通过": _passes_threshold(row["ICIR"], config.MIN_ICIR, use_abs=True),
            "RankIC均值通过": _passes_threshold(row["RankIC均值"], config.MIN_RANK_IC_MEAN, use_abs=True),
            "RankICIR通过": _passes_threshold(row["RankICIR"], config.MIN_RANK_ICIR, use_abs=True),
            "RR均值通过": _passes_threshold(row["RR均值"], config.MIN_RR_MEAN),
            "RR胜率通过": _passes_threshold(row["RR胜率"], config.MIN_RR_WIN_RATE),
        }
        rows.append(
            {
                "factor": row["factor"],
                "方向": direction,
                **metric_checks,
                "初筛是否通过": all(metric_checks.values()),
            }
        )
    return pd.DataFrame(rows)


def _calc_factor_priority(candidate_metrics_df: pd.DataFrame, factor_name: str) -> float:
    """在相关性去冗余阶段，为候选因子计算“保留优先级”。"""
    row = candidate_metrics_df.loc[candidate_metrics_df["factor"] == factor_name]
    if row.empty:
        return float("-inf")

    values = row.iloc[0]
    metrics = [abs(values["ICIR"]), abs(values["RankICIR"]), values["RR胜率"], values["RR均值"], abs(values["IC均值"])]
    score = 0.0
    for metric in metrics:
        if pd.notna(metric):
            score += float(metric)
    return score


def _build_correlation_artifacts(selected_factor_scores: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """构建“阶段二：因子相关性分析”所需的两个结果。"""
    if not selected_factor_scores:
        return pd.DataFrame(), pd.DataFrame(columns=["factor_a", "factor_b", "corr"])

    flattened: dict[str, pd.Series] = {}
    for factor_name, score_df in selected_factor_scores.items():
        flattened[factor_name] = score_df.stack(future_stack=True)

    score_panel = pd.DataFrame(flattened)
    corr_matrix = score_panel.corr()

    corr_rows: list[dict[str, object]] = []
    factor_names = list(corr_matrix.columns)
    for i, factor_a in enumerate(factor_names):
        for factor_b in factor_names[i + 1 :]:
            corr_value = corr_matrix.loc[factor_a, factor_b]
            if pd.isna(corr_value):
                continue
            if abs(float(corr_value)) >= config.FACTOR_CORR_THRESHOLD:
                corr_rows.append({"factor_a": factor_a, "factor_b": factor_b, "corr": float(corr_value)})

    corr_pairs_df = pd.DataFrame(corr_rows)
    if not corr_pairs_df.empty:
        corr_pairs_df = corr_pairs_df.sort_values("corr", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)
    return corr_matrix, corr_pairs_df


def _deduplicate_by_correlation(
    screened_factor_scores: dict[str, pd.DataFrame],
    screened_metrics_df: pd.DataFrame,
) -> tuple[list[str], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """执行“阶段二：因子去相关”。"""
    corr_matrix, corr_pairs_df = _build_correlation_artifacts(screened_factor_scores)
    selected = list(screened_factor_scores.keys())

    for _, row in corr_pairs_df.iterrows():
        factor_a = row["factor_a"]
        factor_b = row["factor_b"]
        if factor_a not in selected or factor_b not in selected:
            continue

        priority_a = _calc_factor_priority(screened_metrics_df, factor_a)
        priority_b = _calc_factor_priority(screened_metrics_df, factor_b)
        if priority_a >= priority_b:
            selected.remove(factor_b)
        else:
            selected.remove(factor_a)

    final_rows = []
    for factor_name in screened_metrics_df["factor"].tolist():
        final_rows.append(
            {
                "factor": factor_name,
                "是否入选最终组合": factor_name in selected,
                "组合权重": 1.0 / len(selected) if factor_name in selected and selected else 0.0,
            }
        )
    return selected, corr_matrix, corr_pairs_df, pd.DataFrame(final_rows)


def _print_separator(char: str = "=", length: int = 90) -> None:
    """打印分隔线，让控制台阶段输出更清晰。"""
    print(char * length)


def _print_factor_evaluation(factor_name: str, summary_df: pd.DataFrame) -> None:
    """打印单因子评估结果。"""
    row = summary_df.iloc[0]
    _print_separator("-", 90)
    print(f"[单因子评估] {factor_name}")
    _print_separator("-", 90)
    print(
        "  "
        f"IC均值={row['IC均值']:.6f}, "
        f"ICIR={row['ICIR']:.6f}, "
        f"RankIC均值={row['RankIC均值']:.6f}, "
        f"RankICIR={row['RankICIR']:.6f}, "
        f"RR均值={row['RR均值']:.6f}, "
        f"RR胜率={row['RR胜率']:.6f}"
    )
    _print_separator("-", 90)


def _print_stage_table(title: str, df: pd.DataFrame) -> None:
    """统一打印阶段性表格结果。"""
    _print_separator("-", 90)
    print(f"[{title}]")
    _print_separator("-", 90)
    if df.empty:
        print("  当前阶段结果为空")
        _print_separator("-", 90)
        return
    print(df.to_string(index=False))
    _print_separator("-", 90)


class StrategyProgressDialog:
    """运行开始前的提示窗口。"""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("多因子运行提示")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self._center_window(520, 180)

        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="配置已确认，准备开始运行", font=("Microsoft YaHei", 14, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text="运行进度将打印到控制台，请查看终端输出。此提示窗口会自动关闭。",
            foreground="#666666",
        ).pack(anchor="w", pady=(10, 12))

        self.progress = ttk.Progressbar(container, mode="indeterminate", length=460)
        self.progress.pack(anchor="w")
        self.progress.start(12)

    def _center_window(self, width: int, height: int) -> None:
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def close(self) -> None:
        self.progress.stop()
        self.root.destroy()


def _print_console_progress(
    title: str,
    detail: str,
    current: int | None = None,
    total: int | None = None,
) -> None:
    """把运行进度打印到控制台。"""
    if current is not None and total is not None and total > 0:
        bar_length = 24
        filled = int(bar_length * current / total)
        bar = "#" * filled + "-" * (bar_length - filled)
        percent = current / total * 100
        message = f"[进度] {title} | [{bar}] {current}/{total} ({percent:.1f}%) | {detail}"
    else:
        message = f"[进度] {title} | {detail}"
    print(message)
    sys.stdout.flush()


def _get_run_params() -> dict[str, object] | None:
    """弹出运行参数窗口，返回用户选择结果。"""
    dialog = StrategyRunDialog()
    return dialog.show()


def run_strategy(
    start_date: str | None = None,
    end_date: str | None = None,
    max_stage: int = 4,
    selected_factors: list[str] | None = None,
    progress_callback: Callable[[str, str, int | None, int | None], None] | None = None,
) -> dict[str, object]:
    """运行多因子研究与回测主流程。"""
    if max_stage < 1 or max_stage > 4:
        raise ValueError("max_stage 必须在 1 到 4 之间")

    if selected_factors is None:
        selected_factors = list(FACTOR_LABELS.keys())
    if not selected_factors:
        raise ValueError("selected_factors 不能为空")

    def report_progress(
        title: str,
        detail: str,
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        _print_console_progress(title, detail, current, total)
        if progress_callback is not None:
            progress_callback(title, detail, current, total)

    report_progress("阶段0：加载数据", "正在加载股票池、行情和基准数据...")

    _print_separator("=", 90)
    print("[阶段0] 开始加载数据与准备基础输入...")
    _print_separator("=", 90)
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
    if close_df is None or universe_df is None:
        raise ValueError("数据加载失败，缺少必要字段")
    if close_df.empty:
        raise ValueError("未获取到有效行情数据")

    tradable_mask = build_tradable_mask(
        universe_df=universe_df,
        close_df=close_df,
    )

    print(
        f"[阶段0] 数据准备完成：股票池={len(universe_df)}，"
        f"价格矩阵形状={close_df.shape}，"
        f"基准={'有' if benchmark_close is not None else '无'}"
    )

    all_factor_dict = {}
    total_factors = len(selected_factors)
    for factor_index, factor_name in enumerate(selected_factors, start=1):
        report_progress(
            "阶段0：计算候选因子",
            f"正在计算 {factor_name} ...",
            factor_index,
            total_factors,
        )
        all_factor_dict[factor_name] = _compute_registered_factor(factor_name, data_bundle)
    raw_factor_dict = {name: all_factor_dict[name] for name in selected_factors if name in all_factor_dict}
    if not raw_factor_dict:
        raise ValueError("所选因子未注册，无法运行")
    print(f"[阶段0] 候选因子列表：{', '.join(raw_factor_dict.keys())}")

    rebalance_mask = build_rebalance_mask(close_df.index, freq=config.REBALANCE_FREQ)
    forward_returns_df = build_forward_returns(close_df, rebalance_mask)

    _print_separator("=", 90)
    print("[阶段1] 开始逐个评估候选因子...")
    _print_separator("=", 90)
    report_progress("阶段1：评估候选因子", "正在计算 IC / RankIC / RR 和单因子回测...", 0, len(raw_factor_dict))
    factor_analysis: dict[str, dict[str, object]] = {}
    candidate_metrics_list: list[pd.DataFrame] = []
    candidate_factor_scores: dict[str, pd.DataFrame] = {}

    for factor_index, (factor_name, raw_factor_df) in enumerate(raw_factor_dict.items(), start=1):
        report_progress(
            "阶段1：评估候选因子",
            f"正在评估 {factor_name} ...",
            factor_index,
            len(raw_factor_dict),
        )
        masked_factor_df = mask_factor(raw_factor_df, tradable_mask)
        factor_score_df = rank_score(masked_factor_df, ascending=FACTOR_DIRECTIONS.get(factor_name, False))

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

        single_factor_results = run_single_factor_backtest(
            factor_df=raw_factor_df,
            tradable_mask=tradable_mask,
            close_df=close_df,
            rebalance_mask=rebalance_mask,
            benchmark_close=benchmark_close,
            hold_num=config.HOLD_NUM,
        )

        factor_analysis[factor_name] = {
            "raw_factor_df": raw_factor_df,
            "masked_factor_df": masked_factor_df,
            "factor_score_df": factor_score_df,
            "ic_series": ic_series,
            "rank_ic_series": rank_ic_series,
            "rr_series": rr_series,
            "summary_df": summary_df,
            "single_factor_results": single_factor_results,
        }
        candidate_metrics_list.append(summary_df)
        candidate_factor_scores[factor_name] = factor_score_df
        _print_factor_evaluation(factor_name, summary_df)

    candidate_metrics_df = pd.concat(candidate_metrics_list, ignore_index=True)
    _print_stage_table("阶段1结果：候选因子指标总表", candidate_metrics_df)

    stage_results = {
        "candidate_metrics": candidate_metrics_df,
        "candidate_status": pd.DataFrame(),
        "screened_metrics": pd.DataFrame(),
        "corr_matrix": pd.DataFrame(),
        "corr_pairs": pd.DataFrame(),
        "final_selection": pd.DataFrame(),
        "selected_score_matrix": pd.DataFrame(),
    }

    output_dir = Path(__file__).resolve().parent / config.OUTPUT_DIR
    save_stage_results(stage_results, str(output_dir))
    stage1_metrics_path = output_dir / "factor_selection" / "stage1_candidate_metrics.csv"
    print(f"[阶段1] 已保存候选因子指标总表：{stage1_metrics_path}")

    if max_stage == 1:
        summary = {
            "start_date": data_bundle["start_date"],
            "end_date": data_bundle["end_date"],
            "date_reason": data_bundle["date_reason"],
            "benchmark_name": config.BENCHMARK_NAME,
            "benchmark_code": config.BENCHMARK_CODE,
            "stock_count": len(universe_df),
            "bar_count": len(data_bundle.get("bars", {})),
            "output_dir": str(output_dir),
            "portfolio": None,
            "results": None,
            "factor_analysis": factor_analysis,
            "stage_results": stage_results,
            "selected_factors": [],
            "selected_factor_weights": {},
            "completed_stage": 1,
        }
        print("[阶段1] 已按要求在阶段1结束。")
        return summary

    _print_separator("=", 90)
    print("[阶段2] 开始根据 IC / IR / RR 阈值做初筛...")
    _print_separator("=", 90)
    report_progress("阶段2：指标初筛", "正在根据阈值筛选候选因子...")
    candidate_status_df = _build_candidate_status(candidate_metrics_df)
    if "备注" not in candidate_status_df.columns:
        candidate_status_df["备注"] = ""
    screened_factors = candidate_status_df.loc[candidate_status_df["初筛是否通过"], "factor"].tolist()

    if not screened_factors:
        candidate_status_df["初筛是否通过"] = True
        candidate_status_df["备注"] = "当前阈值导致无因子通过，已回退为保留全部候选因子"
        screened_factors = candidate_status_df["factor"].tolist()

    factor_directions = {
        row["factor"]: int(row["方向"])
        for _, row in candidate_status_df.iterrows()
    }
    adjusted_factor_scores = {
        factor_name: _apply_factor_direction(candidate_factor_scores[factor_name], factor_directions.get(factor_name, 1))
        for factor_name in screened_factors
    }
    screened_metrics_df = candidate_metrics_df[candidate_metrics_df["factor"].isin(screened_factors)].reset_index(drop=True)
    screened_metrics_df["方向"] = screened_metrics_df["factor"].map(factor_directions).fillna(1).astype(int)

    _print_stage_table("阶段2结果：初筛状态表", candidate_status_df)
    _print_stage_table("阶段2结果：进入相关性分析的因子", screened_metrics_df)
    stage_results["candidate_status"] = candidate_status_df
    stage_results["screened_metrics"] = screened_metrics_df

    if max_stage == 2:
        summary = {
            "start_date": data_bundle["start_date"],
            "end_date": data_bundle["end_date"],
            "date_reason": data_bundle["date_reason"],
            "benchmark_name": config.BENCHMARK_NAME,
            "benchmark_code": config.BENCHMARK_CODE,
            "stock_count": len(universe_df),
            "bar_count": len(data_bundle.get("bars", {})),
            "output_dir": None,
            "portfolio": None,
            "results": None,
            "factor_analysis": factor_analysis,
            "stage_results": stage_results,
            "selected_factors": screened_factors,
            "selected_factor_weights": {},
            "completed_stage": 2,
        }
        print("[阶段2] 已按要求在阶段2结束。")
        return summary

    _print_separator("=", 90)
    print("[阶段3] 开始做因子相关性分析与去冗余...")
    _print_separator("=", 90)
    report_progress("阶段3：相关性去冗余", "正在分析因子相关性并保留优先级更高的因子...")
    final_factor_names, corr_matrix_df, corr_pairs_df, final_selection_df = _deduplicate_by_correlation(
        screened_factor_scores=adjusted_factor_scores,
        screened_metrics_df=screened_metrics_df,
    )
    if not final_factor_names:
        raise ValueError("相关性去冗余后没有剩余因子，请调整相关性阈值")

    _print_stage_table("阶段3结果：因子分数相关性矩阵", corr_matrix_df)
    _print_stage_table("阶段3结果：高相关因子对", corr_pairs_df)
    _print_stage_table("阶段3结果：最终入选因子", final_selection_df)
    stage_results["corr_matrix"] = corr_matrix_df
    stage_results["corr_pairs"] = corr_pairs_df
    stage_results["final_selection"] = final_selection_df

    if max_stage == 3:
        summary = {
            "start_date": data_bundle["start_date"],
            "end_date": data_bundle["end_date"],
            "date_reason": data_bundle["date_reason"],
            "benchmark_name": config.BENCHMARK_NAME,
            "benchmark_code": config.BENCHMARK_CODE,
            "stock_count": len(universe_df),
            "bar_count": len(data_bundle.get("bars", {})),
            "output_dir": None,
            "portfolio": None,
            "results": None,
            "factor_analysis": factor_analysis,
            "stage_results": stage_results,
            "selected_factors": final_factor_names,
            "selected_factor_weights": {},
            "completed_stage": 3,
        }
        print("[阶段3] 已按要求在阶段3结束。")
        return summary

    _print_separator("=", 90)
    print("[阶段4] 开始构建最终多因子组合并回测...")
    _print_separator("=", 90)
    report_progress("阶段4：组合构建与回测", "正在合成最终分数并运行回测...")
    final_weights = {factor_name: 1.0 / len(final_factor_names) for factor_name in final_factor_names}
    selected_factor_scores = {name: adjusted_factor_scores[name] for name in final_factor_names}
    score_df = combine_factor_scores(selected_factor_scores, final_weights)
    selection_df = select_top_n(score_df, n=config.HOLD_NUM)
    target_weights = build_target_weights(selection_df, rebalance_mask)

    portfolio = run_vectorbt_backtest(
        close_df=close_df,
        target_weights=target_weights,
        commission=config.COMMISSION,
        slippage=config.SLIPPAGE,
        init_cash=config.INITIAL_CASH,
    )
    results = extract_backtest_results(
        portfolio,
        benchmark_close=benchmark_close,
    )

    stage_results = {
        "candidate_metrics": candidate_metrics_df,
        "candidate_status": candidate_status_df,
        "screened_metrics": screened_metrics_df,
        "corr_matrix": corr_matrix_df,
        "corr_pairs": corr_pairs_df,
        "final_selection": final_selection_df,
        "selected_score_matrix": score_df,
    }

    output_dir = Path(__file__).resolve().parent / config.OUTPUT_DIR
    save_stage_results(stage_results, str(output_dir))
    save_selection_results(selection_df, score_df, str(output_dir))
    save_backtest_results(results, str(output_dir))
    print(f"[阶段4] 已保存阶段结果目录：{output_dir / 'factor_selection'}")
    print(f"[阶段4] 已保存选股矩阵 CSV：{output_dir / 'selection_matrix.csv'}")
    print(f"[阶段4] 已保存综合分数 CSV：{output_dir / 'score_matrix.csv'}")
    print(f"[阶段4] 已保存入选股票 CSV：{output_dir / 'selected_stocks.csv'}")
    print(f"[阶段4] 已保存组合统计 CSV：{output_dir / 'portfolio_stats.csv'}")
    print(f"[阶段4] 已保存净值曲线 CSV：{output_dir / 'equity_curve.csv'}")
    print(f"[阶段4] 已保存收益序列 CSV：{output_dir / 'returns.csv'}")
    for factor_name, factor_result in factor_analysis.items():
        save_factor_evaluation_results(
            output_dir=str(output_dir),
            factor_name=factor_name,
            ic_series=factor_result["ic_series"],
            rank_ic_series=factor_result["rank_ic_series"],
            rr_series=factor_result["rr_series"],
            summary_df=factor_result["summary_df"],
            backtest_results=factor_result["single_factor_results"],
        )
        factor_output_dir = output_dir / "factor_analysis" / factor_name / "latest"
        print(f"[阶段4] 已保存单因子分析目录：{factor_output_dir}")
        print(f"[阶段4]   - 指标汇总 CSV：{factor_output_dir / 'summary.csv'}")
        print(f"[阶段4]   - IC/RR 时序 CSV：{factor_output_dir / 'ic_ir_rr_timeseries.csv'}")
        print(f"[阶段4]   - 单因子统计 CSV：{factor_output_dir / 'single_factor_stats.csv'}")

    print(f"[阶段4] 组合构建完成：最终因子={', '.join(final_factor_names)}")
    print(f"[阶段4] 对应权重：{final_weights}")
    if hasattr(results.get("stats"), "loc") and "Total Return [%]" in results["stats"].index:
        print(f"[阶段4] 组合总收益率：{results['stats'].loc['Total Return [%]']:.6f}%")

    summary = {
        "start_date": data_bundle["start_date"],
        "end_date": data_bundle["end_date"],
        "date_reason": data_bundle["date_reason"],
        "benchmark_name": config.BENCHMARK_NAME,
        "benchmark_code": config.BENCHMARK_CODE,
        "stock_count": len(universe_df),
        "bar_count": len(data_bundle.get("bars", {})),
        "output_dir": str(output_dir),
        "portfolio": portfolio,
        "results": results,
        "factor_analysis": factor_analysis,
        "stage_results": stage_results,
        "selected_factors": final_factor_names,
        "selected_factor_weights": final_weights,
        "completed_stage": 4,
    }
    return summary


if __name__ == "__main__":
    run_params = _get_run_params()
    if run_params is None:
        print("已取消本次运行")
    else:
        progress_dialog = StrategyProgressDialog()
        progress_dialog.root.after(800, progress_dialog.close)
        progress_dialog.root.mainloop()

        run_result: dict[str, object] = {}
        run_error_holder: list[Exception] = []

        def _run_task() -> None:
            try:
                run_result["summary"] = run_strategy(
                    start_date=str(run_params["start_date"]),
                    end_date=str(run_params["end_date"]),
                    max_stage=int(run_params["max_stage"]),
                    selected_factors=list(run_params["selected_factors"]),
                    progress_callback=None,
                )
            except Exception as exc:  # pragma: no cover - 运行期异常展示
                run_error_holder.append(exc)

        worker = threading.Thread(target=_run_task, daemon=True)
        worker.start()
        worker.join()

        if run_error_holder:
            raise run_error_holder[0]

        summary = run_result["summary"]
        _print_separator("=", 90)
        print("多因子回测完成")
        _print_separator("=", 90)
        print(f"时间范围: {summary['start_date']} -> {summary['end_date']} ({summary['date_reason']})")
        print(f"基准: {summary['benchmark_name']} ({summary['benchmark_code']})")
        print(f"股票池数量: {summary['stock_count']}")
        print(f"成功加载行情数量: {summary['bar_count']}")
        print(f"运行结束阶段: {summary['completed_stage']}")
        if summary["selected_factors"]:
            print(f"当前入选因子: {', '.join(summary['selected_factors'])}")
        if summary["output_dir"]:
            print(f"输出目录: {summary['output_dir']}")
