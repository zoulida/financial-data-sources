#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import logging
import os
import random
import sys
import threading
import time
import traceback
import warnings
from contextlib import redirect_stdout
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

_THIS_DIR = Path(__file__).resolve().parent
_SOURCE_DIR = _THIS_DIR.parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))
if str(_SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(_SOURCE_DIR))

from workflow_v2 import WorkflowConfigV2, WorkflowV2  # noqa: E402

try:
    from flask import Flask, jsonify, request, send_from_directory
except Exception:  # pragma: no cover
    Flask = None  # type: ignore[assignment]
    jsonify = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]
    send_from_directory = None  # type: ignore[assignment]

_CUSTOM_FACTOR_LOADER_PATH = _SOURCE_DIR / "custom-fa" / "custom_factor_loader.py"
_spec = importlib.util.spec_from_file_location("custom_factor_loader", _CUSTOM_FACTOR_LOADER_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"无法加载 custom factor loader: {_CUSTOM_FACTOR_LOADER_PATH}")
_custom_factor_loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_custom_factor_loader)
validate_factor_code = _custom_factor_loader.validate_factor_code
CUSTOM_DIR = _custom_factor_loader.CUSTOM_DIR

CONFIG_FILE = _THIS_DIR / "workflow_main_wave_event_ga_config.json"
V2_CONFIG_FILE = _THIS_DIR / "workflow_v2_config.json"


@dataclass
class WorkflowMainWaveEventGAConfig(WorkflowConfigV2):
    output_dir: str = "results_main_wave_event_ga"
    factor_cache_dir: str = ".factor_cache_mwega"
    use_step7_cache: bool = False
    signal_mode: str = "all"
    population_size: int = 60
    generations: int = 20
    max_depth: int = 5
    max_nodes: int = 28
    crossover_rate: float = 0.70
    mutation_rate: float = 0.25
    elite_keep: int = 6
    generation_elite_k: int = 12
    early_stop_rounds: int = 6
    window_choices: List[int] = field(default_factory=lambda: [3, 5, 10, 20, 30, 60])
    sequence_gap_choices: List[int] = field(default_factory=lambda: [1, 2, 3, 5, 10])
    count_threshold_choices: List[int] = field(default_factory=lambda: [1, 2, 3])
    export_topk: int = 10
    random_seed: int = 20260522
    export_prefix: str = "mwega"
    label_mode: str = "all"
    label_horizon: int = 20
    continuation_horizon: int = 10
    start_min_return: float = 0.18
    continuation_min_return: float = 0.06
    label_max_drawdown: float = -0.12
    fail_return_5d: float = -0.06
    fail_drawdown: float = -0.15
    limit_up_threshold: float = 0.095
    near_limit_up_threshold: float = 0.075
    big_up_threshold: float = 0.045
    big_down_threshold: float = -0.045
    volume_surge_ratio: float = 1.8
    shrink_volume_ratio: float = 0.8
    min_event_support: int = 200
    min_event_coverage: float = 0.001
    max_event_coverage: float = 0.25
    event_trigger_threshold: float = 0.50
    complexity_penalty: float = 0.003
    fail_penalty: float = 0.30
    sparsity_penalty: float = 0.20
    redundancy_penalty: float = 0.08
    jaccard_max: float = 0.80
    template_injection_ratio: float = 0.35


def load_saved_config() -> WorkflowMainWaveEventGAConfig:
    default = WorkflowMainWaveEventGAConfig()
    if not CONFIG_FILE.exists():
        cfg = _build_initial_config(default)
        save_config(cfg)
        return cfg
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        valid = set(asdict(default).keys())
        filtered = {k: v for k, v in raw.items() if k in valid and v not in ("", None)}
        for key in ("factor_libraries", "ml_model", "window_choices", "sequence_gap_choices", "count_threshold_choices"):
            if key in filtered and not isinstance(filtered[key], list):
                filtered[key] = [x.strip() for x in str(filtered[key]).split(",") if x.strip()]
        for key in ("window_choices", "sequence_gap_choices", "count_threshold_choices"):
            if key in filtered:
                filtered[key] = [int(x) for x in filtered[key]]
        return WorkflowMainWaveEventGAConfig(**{**asdict(_build_initial_config(default)), **filtered})
    except Exception as exc:
        print(f"⚠️ 读取主升浪事件 GA 配置失败，将使用默认参数: {exc}")
        return _build_initial_config(default)


def _build_initial_config(default: WorkflowMainWaveEventGAConfig) -> WorkflowMainWaveEventGAConfig:
    base = asdict(default)
    if V2_CONFIG_FILE.exists():
        try:
            raw = json.loads(V2_CONFIG_FILE.read_text(encoding="utf-8"))
            valid = set(base.keys())
            for key, value in raw.items():
                if key in valid and key not in {"output_dir", "factor_cache_dir", "use_step7_cache", "signal_mode"}:
                    base[key] = value
        except Exception as exc:
            print(f"⚠️ 读取 V2 配置失败，将使用主升浪事件 GA 默认值: {exc}")
    base.update(
        {
            "output_dir": "results_main_wave_event_ga",
            "factor_cache_dir": ".factor_cache_mwega",
            "use_step7_cache": False,
            "signal_mode": "all",
            "population_size": 60,
            "generations": 20,
            "max_depth": 5,
            "max_nodes": 28,
            "export_prefix": "mwega",
            "label_mode": "all",
            "random_seed": 20260522,
        }
    )
    return WorkflowMainWaveEventGAConfig(**base)


def save_config(config: WorkflowMainWaveEventGAConfig) -> None:
    CONFIG_FILE.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class EventExpr:
    op: str
    children: Tuple["EventExpr", ...] = ()
    value: Any = None

    def key(self) -> str:
        if self.op == "event":
            return str(self.value)
        args = ",".join(child.key() for child in self.children)
        return f"{self.op}[{self.value}]({args})" if self.value is not None else f"{self.op}({args})"

    def depth(self) -> int:
        return 1 if not self.children else 1 + max(child.depth() for child in self.children)

    def complexity(self) -> int:
        return 1 + sum(child.complexity() for child in self.children)

    def events(self) -> List[str]:
        if self.op == "event":
            return [str(self.value)]
        names: List[str] = []
        for child in self.children:
            names.extend(child.events())
        return sorted(set(names))

    def eval(self, engine: "MainWaveEventEngine") -> pd.DataFrame:
        if self.op == "event":
            return engine.events[str(self.value)].copy()
        args = [child.eval(engine) for child in self.children]
        if self.op == "AND":
            out = args[0].where(args[0] <= args[1], args[1])
        elif self.op == "OR":
            out = args[0].where(args[0] >= args[1], args[1])
        elif self.op == "NOT":
            out = 1.0 - engine.to_bool(args[0])
        elif self.op == "ANY":
            out = engine.any_event(args[0], int(self.value))
        elif self.op == "COUNT_GE":
            window, threshold = self.value
            out = (engine.to_bool(args[0]).rolling(int(window), min_periods=1).sum() >= int(threshold)).astype(float)
        elif self.op == "THEN":
            min_gap, max_gap = self.value
            out = engine.then_event(args[0], args[1], int(min_gap), int(max_gap))
        elif self.op == "WITHOUT":
            out = 1.0 - engine.any_event(args[0], int(self.value))
        elif self.op == "DECAY":
            out = engine.decay_event(args[0], int(self.value))
        else:
            raise ValueError(f"未知事件算子: {self.op}")
        return out.astype(float).replace([np.inf, -np.inf], np.nan)

    def to_code(self, event_vars: Dict[str, str]) -> str:
        if self.op == "event":
            return event_vars[str(self.value)]
        c = [x.to_code(event_vars) for x in self.children]
        if self.op == "AND":
            return f"(({c[0]}).where(({c[0]}) <= ({c[1]}), ({c[1]})))"
        if self.op == "OR":
            return f"(({c[0]}).where(({c[0]}) >= ({c[1]}), ({c[1]})))"
        if self.op == "NOT":
            return f"(1.0 - _b({c[0]}))"
        if self.op == "ANY":
            return f"_any({c[0]}, {int(self.value)})"
        if self.op == "COUNT_GE":
            window, threshold = self.value
            return f"_count_ge({c[0]}, {int(window)}, {int(threshold)})"
        if self.op == "THEN":
            min_gap, max_gap = self.value
            return f"_then({c[0]}, {c[1]}, {int(min_gap)}, {int(max_gap)})"
        if self.op == "WITHOUT":
            return f"(1.0 - _any({c[0]}, {int(self.value)}))"
        if self.op == "DECAY":
            return f"_decay({c[0]}, {int(self.value)})"
        raise ValueError(f"未知事件算子: {self.op}")


class MainWaveEventEngine:
    logic_ops = ("AND", "OR")
    unary_ops = ("NOT", "ANY", "COUNT_GE", "WITHOUT", "DECAY")
    sequence_ops = ("THEN",)

    def __init__(self, config: WorkflowMainWaveEventGAConfig):
        self.config = config
        self.rng = random.Random(int(config.random_seed))
        self.events: Dict[str, pd.DataFrame] = {}
        self.expr_cache: Dict[str, pd.DataFrame] = {}

    @staticmethod
    def to_bool(df: pd.DataFrame) -> pd.DataFrame:
        return (df.astype(float).fillna(0.0) >= 0.5).astype(float)

    def any_event(self, df: pd.DataFrame, window: int) -> pd.DataFrame:
        return (self.to_bool(df).rolling(max(int(window), 1), min_periods=1).max() > 0).astype(float)

    def then_event(self, left: pd.DataFrame, right: pd.DataFrame, min_gap: int, max_gap: int) -> pd.DataFrame:
        left_bool = self.to_bool(left)
        prior = pd.DataFrame(0.0, index=left.index, columns=left.columns)
        for gap in range(max(int(min_gap), 0), max(int(max_gap), int(min_gap)) + 1):
            shifted = left_bool.shift(gap)
            prior = prior.where(prior >= shifted, shifted)
        return (prior * self.to_bool(right)).astype(float)

    def decay_event(self, df: pd.DataFrame, window: int) -> pd.DataFrame:
        base = self.to_bool(df)
        out = pd.DataFrame(0.0, index=base.index, columns=base.columns)
        w = max(int(window), 1)
        for gap in range(w):
            weight = float(w - gap) / float(w)
            shifted = base.shift(gap) * weight
            out = out.where(out >= shifted, shifted)
        return out.astype(float)

    def set_events(self, events: Dict[str, pd.DataFrame]) -> None:
        self.events = events
        self.expr_cache = {}

    def _window(self) -> int:
        values = [int(x) for x in self.config.window_choices if int(x) > 0]
        return self.rng.choice(values or [5, 10, 20])

    def _gap_pair(self) -> Tuple[int, int]:
        values = sorted({int(x) for x in self.config.sequence_gap_choices if int(x) >= 0}) or [1, 3, 5]
        a = self.rng.choice(values)
        b = self.rng.choice(values)
        return min(a, b), max(a, b)

    def _count_value(self) -> Tuple[int, int]:
        window = self._window()
        values = [int(x) for x in self.config.count_threshold_choices if int(x) > 0]
        threshold = min(self.rng.choice(values or [1, 2]), window)
        return window, threshold

    def random_expr(self, depth: int = 0) -> EventExpr:
        if depth >= self.config.max_depth or self.rng.random() < 0.30:
            return EventExpr("event", value=self.rng.choice(list(self.events.keys())))
        group = self.rng.choice(["logic", "unary", "sequence"])
        if group == "logic":
            return EventExpr(self.rng.choice(self.logic_ops), (self.random_expr(depth + 1), self.random_expr(depth + 1)))
        if group == "sequence":
            return EventExpr("THEN", (self.random_expr(depth + 1), self.random_expr(depth + 1)), self._gap_pair())
        op = self.rng.choice(self.unary_ops)
        if op in {"ANY", "WITHOUT", "DECAY"}:
            return EventExpr(op, (self.random_expr(depth + 1),), self._window())
        if op == "COUNT_GE":
            return EventExpr(op, (self.random_expr(depth + 1),), self._count_value())
        return EventExpr(op, (self.random_expr(depth + 1),))

    def template_exprs(self) -> List[EventExpr]:
        e = lambda name: EventExpr("event", value=name)
        return [
            EventExpr("THEN", (e("limit_up"), EventExpr("THEN", (e("shrink_volume_pullback"), e("restart_big_up")), (1, 5))), (1, 10)),
            EventExpr("THEN", (e("break_60d_high"), EventExpr("THEN", (e("pullback_not_break_ma20"), e("volume_breakout")), (1, 5))), (1, 10)),
            EventExpr("AND", (e("ma_bull_order"), EventExpr("AND", (EventExpr("COUNT_GE", (e("big_up"),), (20, 2)), EventExpr("WITHOUT", (e("big_down"),), 5))))),
            EventExpr("THEN", (e("big_bull_candle"), EventExpr("AND", (e("long_lower_shadow"), e("close_near_high")))), (1, 8)),
            EventExpr("AND", (EventExpr("DECAY", (e("near_limit_up"),), 10), EventExpr("WITHOUT", (e("long_upper_shadow_high_volume"),), 5))),
        ]

    def eval_expr(self, expr: EventExpr) -> pd.DataFrame:
        key = expr.key()
        if key not in self.expr_cache:
            self.expr_cache[key] = expr.eval(self)
        return self.expr_cache[key]

    def mutate(self, expr: EventExpr) -> EventExpr:
        if self.rng.random() < 0.25:
            return self.random_expr(0)
        if expr.op == "event":
            return EventExpr("event", value=self.rng.choice(list(self.events.keys())))
        children = list(expr.children)
        if children and self.rng.random() < 0.65:
            idx = self.rng.randrange(len(children))
            children[idx] = self.mutate(children[idx])
            return EventExpr(expr.op, tuple(children), expr.value)
        if expr.op in {"ANY", "WITHOUT", "DECAY"}:
            return EventExpr(expr.op, expr.children, self._window())
        if expr.op == "COUNT_GE":
            return EventExpr(expr.op, expr.children, self._count_value())
        if expr.op == "THEN":
            return EventExpr(expr.op, expr.children, self._gap_pair())
        if expr.op in self.logic_ops:
            return EventExpr(self.rng.choice(self.logic_ops), expr.children)
        return self.random_expr(0)

    def crossover(self, left: EventExpr, right: EventExpr) -> EventExpr:
        if self.rng.random() < 0.35 or not left.children:
            return right
        children = list(left.children)
        idx = self.rng.randrange(len(children))
        children[idx] = self.crossover(children[idx], right)
        return EventExpr(left.op, tuple(children), left.value)


class WorkflowMainWaveEventGA(WorkflowV2):
    def __init__(self, config: WorkflowMainWaveEventGAConfig):
        super().__init__(config)
        self.config: WorkflowMainWaveEventGAConfig = config
        self.engine = MainWaveEventEngine(config)
        self.event_library: Dict[str, pd.DataFrame] = {}
        self.label_data: Dict[str, pd.DataFrame] = {}
        self.mwega_generation_stats = pd.DataFrame()
        self.mwega_population = pd.DataFrame()
        self.mwega_elite_archive = pd.DataFrame()
        self.mwega_lineage = pd.DataFrame()
        self._expr_by_name: Dict[str, EventExpr] = {}
        self._lineage_map: Dict[str, Dict[str, Any]] = {}
        self._lineage_records: List[Dict[str, Any]] = []

    def run(self) -> Dict[str, Any]:
        print("🌊 workflow_main_wave_event_ga 启动：事件库 → 主升浪标签 → 序列进化 → 导出回测")
        save_config(self.config)
        t0 = time.perf_counter()
        self._init_qlib()
        self._load_market_data()
        pool_report = self._filter_stock_pool()
        self._build_returns()
        self._build_main_wave_labels()
        self._build_event_library()
        final_exprs = self._evolve_events()
        self._load_final_event_factors(final_exprs)
        evaluation = self._evaluate_final_events()
        selected, filter_report = self._filter_final_events(evaluation)
        if not selected:
            raise RuntimeError("主升浪事件 GA 最终过滤后剩余 0 个事件因子，请放宽覆盖率/命中率参数或增加代数。")
        exported = self._export_selected_factors(selected)
        signals, signal_info = self._build_event_signals(selected)
        benchmark = self._load_benchmark_returns()
        backtest, performance = self._run_backtests(signals, benchmark)
        results = {
            "event_evaluation": evaluation,
            "filter_report": filter_report,
            "stock_pool_report": pool_report,
            "selected_factors": selected,
            "signals": signals,
            "signal_info": signal_info,
            "backtest": backtest,
            "performance": performance,
            "mwega_generation_stats": self.mwega_generation_stats,
            "mwega_population": self.mwega_population,
            "mwega_elite_archive": self.mwega_elite_archive,
            "mwega_exported_factors": exported,
        }
        self._save_mwega_results(results, time.perf_counter() - t0)
        self._plot_mwega_results(backtest)
        print(f"🎉 主升浪事件 GA 完成，总耗时 {time.perf_counter() - t0:.2f}s")
        print(f"📁 结果目录: {self.output_dir}")
        return results

    @staticmethod
    def _future_rolling_max(df: pd.DataFrame, window: int) -> pd.DataFrame:
        return df.shift(-1).iloc[::-1].rolling(max(int(window), 1), min_periods=1).max().iloc[::-1]

    @staticmethod
    def _future_rolling_min(df: pd.DataFrame, window: int) -> pd.DataFrame:
        return df.shift(-1).iloc[::-1].rolling(max(int(window), 1), min_periods=1).min().iloc[::-1]

    def _build_main_wave_labels(self) -> None:
        cfg = self.config
        panel = self.panel
        close = panel["close"]
        high = panel["high"]
        low = panel["low"]
        h = max(int(cfg.label_horizon), 2)
        ch = max(int(cfg.continuation_horizon), 2)
        future_close_h = close.shift(-h)
        future_close_ch = close.shift(-ch)
        future_ret_5d = close.shift(-5) / close - 1.0
        future_ret_10d = close.shift(-10) / close - 1.0
        future_ret_20d = future_close_h / close - 1.0
        future_ret_cont = future_close_ch / close - 1.0
        future_max_high = self._future_rolling_max(high, h)
        future_min_low = self._future_rolling_min(low, h)
        future_max_up = future_max_high / close - 1.0
        future_max_drawdown = future_min_low / close - 1.0
        ma5 = close.rolling(5, min_periods=5).mean()
        ma10 = close.rolling(10, min_periods=10).mean()
        ma20 = close.rolling(20, min_periods=20).mean()
        hh20 = close.rolling(20, min_periods=20).max()
        trend_now = (close > ma20) & (ma5 > ma10) & (ma10 >= ma20 * 0.995) & (close >= hh20 * 0.90)
        start_label = (
            (future_max_up >= float(cfg.start_min_return))
            & (future_max_drawdown >= float(cfg.label_max_drawdown))
            & (future_ret_5d >= float(cfg.fail_return_5d))
        ).astype(float)
        continuation_label = (
            trend_now
            & (future_ret_cont >= float(cfg.continuation_min_return))
            & (future_max_drawdown >= float(cfg.label_max_drawdown))
        ).astype(float)
        fail_label = ((future_ret_5d <= float(cfg.fail_return_5d)) | (future_max_drawdown <= float(cfg.fail_drawdown))).astype(float)
        if cfg.label_mode == "start":
            target = start_label
        elif cfg.label_mode == "continuation":
            target = continuation_label
        else:
            target = ((start_label > 0) | (continuation_label > 0)).astype(float)
        self.label_data = {
            "target": target.reindex_like(close),
            "start": start_label.reindex_like(close),
            "continuation": continuation_label.reindex_like(close),
            "fail": fail_label.reindex_like(close),
            "future_ret_5d": future_ret_5d.reindex_like(close),
            "future_ret_10d": future_ret_10d.reindex_like(close),
            "future_ret_20d": future_ret_20d.reindex_like(close),
            "future_max_up_20d": future_max_up.reindex_like(close),
            "future_max_drawdown_20d": future_max_drawdown.reindex_like(close),
        }
        baseline = float(target.stack(dropna=True).mean()) if not target.empty else 0.0
        print(f"✅ 主升浪标签完成: mode={cfg.label_mode}, baseline_hit_rate={baseline:.4f}")

    def _build_event_library(self) -> None:
        cfg = self.config
        panel = self.panel
        close = panel["close"]
        open_df = panel["open"]
        high = panel["high"]
        low = panel["low"]
        volume = panel["volume"]
        amount = panel.get("amount", close * volume)
        ret1 = close / close.shift(1) - 1.0
        gap = open_df / close.shift(1) - 1.0
        body_high = close.where(close >= open_df, open_df)
        body_low = close.where(close <= open_df, open_df)
        day_range = (high - low).replace(0.0, np.nan)
        upper_shadow = (high - body_high) / day_range
        lower_shadow = (body_low - low) / day_range
        body_abs = (close - open_df).abs() / open_df.replace(0.0, np.nan)
        close_pos = (close - low) / day_range
        ma5 = close.rolling(5, min_periods=5).mean()
        ma10 = close.rolling(10, min_periods=10).mean()
        ma20 = close.rolling(20, min_periods=20).mean()
        hh20 = close.rolling(20, min_periods=20).max()
        hh60 = close.rolling(60, min_periods=30).max()
        ll10 = close.rolling(10, min_periods=5).min()
        vol_ma5 = volume.rolling(5, min_periods=3).mean()
        vol_ma20 = volume.rolling(20, min_periods=5).mean()
        amt_ma5 = amount.rolling(5, min_periods=3).mean()
        amt_ma20 = amount.rolling(20, min_periods=5).mean()
        ret3 = close / close.shift(3) - 1.0
        ret5 = close / close.shift(5) - 1.0
        ret20 = close / close.shift(20) - 1.0
        events = {
            "limit_up": ret1 >= float(cfg.limit_up_threshold),
            "near_limit_up": ret1 >= float(cfg.near_limit_up_threshold),
            "big_up": ret1 >= float(cfg.big_up_threshold),
            "restart_big_up": (ret1 >= float(cfg.big_up_threshold)) & (close_pos >= 0.70),
            "gap_up_big": gap >= 0.03,
            "close_near_high": close_pos >= 0.80,
            "break_20d_high": close >= hh20.shift(1) * 1.005,
            "break_60d_high": close >= hh60.shift(1) * 1.005,
            "volume_surge": volume >= vol_ma20 * float(cfg.volume_surge_ratio),
            "amount_surge": amount >= amt_ma20 * float(cfg.volume_surge_ratio),
            "volume_double": volume >= vol_ma20 * 2.0,
            "shrink_volume_pullback": (ret3 <= 0.03) & (ret5 <= 0.06) & (volume <= vol_ma5 * float(cfg.shrink_volume_ratio)) & (close >= ma20 * 0.98),
            "volume_price_confirm": (ret1 > 0.02) & (volume >= vol_ma20 * 1.3),
            "big_amount_breakout": (close >= hh20.shift(1) * 1.003) & (amount >= amt_ma20 * 1.5),
            "volume_breakout": (close >= hh20.shift(1) * 1.003) & (volume >= vol_ma20 * 1.4),
            "long_upper_shadow": upper_shadow >= 0.45,
            "long_lower_shadow": lower_shadow >= 0.40,
            "big_bull_candle": (ret1 >= 0.035) & (body_abs >= 0.025) & (close > open_df),
            "big_bear_candle": (ret1 <= -0.035) & (body_abs >= 0.025) & (close < open_df),
            "doji_like": body_abs <= 0.008,
            "close_above_mid": close_pos >= 0.50,
            "ma5_above_ma10": ma5 > ma10,
            "ma10_above_ma20": ma10 >= ma20 * 0.995,
            "ma_bull_order": (ma5 > ma10) & (ma10 >= ma20 * 0.995) & (close > ma20),
            "close_above_ma20": close > ma20,
            "ma20_slope_up": ma20 > ma20.shift(5),
            "higher_high": high >= high.shift(1).rolling(5, min_periods=3).max(),
            "higher_low": low >= low.shift(1).rolling(5, min_periods=3).min(),
            "pullback_to_ma5": (close <= ma5 * 1.025) & (close >= ma5 * 0.975),
            "pullback_to_ma10": (close <= ma10 * 1.03) & (close >= ma10 * 0.97),
            "pullback_not_break_ma20": (low <= ma20 * 1.03) & (close >= ma20 * 0.99),
            "small_pullback_after_big_up": (ret5 <= 0.05) & ((ret20 >= 0.08) | (self.engine.any_event((ret1 >= cfg.big_up_threshold).astype(float), 10) > 0)),
            "lower_shadow_on_ma": (lower_shadow >= 0.30) & (low <= ma10 * 1.03) & (close >= ma20 * 0.98),
            "pullback_depth_ok": (close >= ll10 * 1.02) & (ret5 <= 0.06) & (ret20 >= 0.00),
            "long_upper_shadow_high_volume": (upper_shadow >= 0.40) & (volume >= vol_ma20 * 1.5),
            "high_open_low_close": (gap >= 0.02) & (close < open_df) & (close_pos <= 0.35),
            "big_down": ret1 <= float(cfg.big_down_threshold),
            "volume_down_break": (ret1 <= -0.03) & (volume >= vol_ma20 * 1.4),
            "break_ma20_down": close < ma20 * 0.98,
            "consecutive_down": (ret1 < 0).rolling(3, min_periods=3).sum() >= 3,
        }
        self.event_library = {name: df.astype(float).reindex_like(close).replace([np.inf, -np.inf], np.nan) for name, df in events.items()}
        self.engine.set_events(self.event_library)
        print(f"✅ 基础事件库完成: {len(self.event_library)} 个事件")

    def _evolve_events(self) -> List[EventExpr]:
        cfg = self.config
        template_count = int(max(0, min(1.0, float(cfg.template_injection_ratio))) * int(cfg.population_size))
        templates = self.engine.template_exprs()[:template_count]
        random_count = max(int(cfg.population_size) * 2 - len(templates), 1)
        population = self._unique_exprs(templates + [self.engine.random_expr() for _ in range(random_count)])[: int(cfg.population_size)]
        for expr in population:
            self._record_lineage(expr, 0, "template_or_random", [], None)
        archive: Dict[str, Dict[str, Any]] = {}
        population_rows: List[Dict[str, Any]] = []
        generation_rows: List[Dict[str, Any]] = []
        best_fitness = -1e18
        stale_rounds = 0
        for gen in range(int(cfg.generations)):
            print(f"\n🌊 第 {gen + 1}/{cfg.generations} 代：计算并评价 {len(population)} 个事件序列")
            factors, expr_map, quality = self._compute_population(population, gen)
            if not factors:
                print("  ⚠️ 本代无有效事件序列，随机重启")
                population = self._unique_exprs([self.engine.random_expr() for _ in range(int(cfg.population_size) * 2)])[: int(cfg.population_size)]
                for expr in population:
                    self._record_lineage(expr, gen + 1, "random_restart", [], None)
                continue
            scored = self._score_population(factors, expr_map, quality, gen)
            if scored.empty:
                population = self._unique_exprs([self.engine.random_expr() for _ in range(int(cfg.population_size) * 2)])[: int(cfg.population_size)]
                for expr in population:
                    self._record_lineage(expr, gen + 1, "random_restart", [], None)
                continue
            population_rows.extend(scored.to_dict(orient="records"))
            for row in scored.to_dict(orient="records"):
                self._lineage_records.append(
                    {
                        "generation": int(gen),
                        "factor": str(row.get("factor")),
                        "expr_key": str(row.get("expr_key")),
                        "operation": str(row.get("operation", "unknown")),
                        "parents": str(row.get("parents") or ""),
                        "mutation_op": str(row.get("mutation_op") or ""),
                        "fitness": float(row.get("fitness", 0.0) or 0.0),
                        "hit_rate": float(row.get("hit_rate", 0.0) or 0.0),
                        "uplift": float(row.get("uplift", 0.0) or 0.0),
                        "coverage": float(row.get("coverage", 0.0) or 0.0),
                        "depth": int(row.get("depth", 0) or 0),
                        "complexity": int(row.get("complexity", 0) or 0),
                    }
                )
            elites = scored.sort_values("fitness", ascending=False).head(max(int(cfg.generation_elite_k), 1))
            for row in elites.to_dict(orient="records"):
                key = str(row["expr_key"])
                old = archive.get(key)
                if old is None or float(row["fitness"]) > float(old["fitness"]):
                    archive[key] = row
            gen_best = float(scored["fitness"].max())
            gen_mean = float(scored["fitness"].mean())
            generation_rows.append(
                {
                    "generation": gen,
                    "n_valid": int(len(scored)),
                    "best_fitness": gen_best,
                    "mean_fitness": gen_mean,
                    "best_factor": str(scored.sort_values("fitness", ascending=False).iloc[0]["factor"]),
                }
            )
            print(f"  ✅ 本代 best_fitness={gen_best:.4f}, mean={gen_mean:.4f}, archive={len(archive)}")
            self._append_generation_markdown(gen, scored, gen_best, gen_mean, len(archive))
            if gen_best > best_fitness + 1e-8:
                best_fitness = gen_best
                stale_rounds = 0
            else:
                stale_rounds += 1
                if stale_rounds >= int(cfg.early_stop_rounds):
                    print(f"  🛑 连续 {stale_rounds} 代未提升，提前停止")
                    break
            population = self._next_generation(scored, expr_map, gen + 1)
        self.mwega_population = pd.DataFrame(population_rows)
        self.mwega_generation_stats = pd.DataFrame(generation_rows)
        self.mwega_lineage = pd.DataFrame(self._lineage_records)
        self.mwega_elite_archive = pd.DataFrame(list(archive.values()))
        if self.mwega_elite_archive.empty:
            raise RuntimeError("主升浪事件 GA 未产生任何有效 elite。")
        self.mwega_elite_archive = self.mwega_elite_archive.sort_values("fitness", ascending=False).reset_index(drop=True)
        final_rows = self.mwega_elite_archive.head(max(int(cfg.export_topk) * 5, int(cfg.export_topk))).to_dict(orient="records")
        return [self._expr_by_name[str(row["factor"])] for row in final_rows if str(row["factor"]) in self._expr_by_name]

    def _record_lineage(self, expr: EventExpr, generation: int, operation: str, parents: List[EventExpr], mutation_op: Optional[str]) -> None:
        key = expr.key()
        if key in self._lineage_map:
            return
        self._lineage_map[key] = {
            "expr_key": key,
            "first_generation": int(generation),
            "operation": operation,
            "parents": [p.key() for p in parents],
            "mutation_op": mutation_op or "",
            "depth": int(expr.depth()),
            "complexity": int(expr.complexity()),
        }

    def _compute_population(self, population: List[EventExpr], generation: int) -> Tuple[Dict[str, pd.DataFrame], Dict[str, EventExpr], Dict[str, Dict[str, Any]]]:
        factors: Dict[str, pd.DataFrame] = {}
        expr_map: Dict[str, EventExpr] = {}
        quality: Dict[str, Dict[str, Any]] = {}
        seen: set[str] = set()
        close = self.panel["close"]
        for i, expr in enumerate(population):
            key = expr.key()
            if key in seen or expr.depth() > self.config.max_depth or expr.complexity() > self.config.max_nodes:
                continue
            seen.add(key)
            name = f"mwega_g{generation:03d}_{i:04d}"
            try:
                df = self.engine.eval_expr(expr).reindex_like(close)
                non_null_ratio = float(df.notna().mean().mean())
                if non_null_ratio < 0.50:
                    continue
                factors[name] = df
                expr_map[name] = expr
                self._expr_by_name[name] = expr
                lineage = self._lineage_map.get(key, {})
                quality[name] = {
                    "expr_key": key,
                    "expression": key,
                    "complexity": expr.complexity(),
                    "depth": expr.depth(),
                    "non_null_ratio": non_null_ratio,
                    "operation": lineage.get("operation", "unknown"),
                    "parents": "|".join(lineage.get("parents", []) or []),
                    "mutation_op": lineage.get("mutation_op") or "",
                    "first_generation": int(lineage.get("first_generation", generation)),
                }
            except Exception as exc:
                print(f"  ⚠️ 事件序列计算失败: {key[:100]} | {type(exc).__name__}: {exc}")
        return factors, expr_map, quality

    def _score_population(self, factors: Dict[str, pd.DataFrame], expr_map: Dict[str, EventExpr], quality: Dict[str, Dict[str, Any]], generation: int) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for name, df in factors.items():
            metrics = self._evaluate_event_factor(name, df)
            if not metrics.get("valid", False):
                continue
            q = quality.get(name, {})
            complexity = float(q.get("complexity", 1.0))
            coverage = float(metrics.get("coverage", 0.0) or 0.0)
            uplift = float(metrics.get("uplift", 0.0) or 0.0)
            hit_rate = float(metrics.get("hit_rate", 0.0) or 0.0)
            ret_mean = float(metrics.get("future_ret_20d_mean", 0.0) or 0.0)
            drawdown = abs(float(metrics.get("future_max_drawdown_20d_mean", 0.0) or 0.0))
            fail_rate = float(metrics.get("fail_rate", 0.0) or 0.0)
            stability = float(metrics.get("stability", 0.0) or 0.0)
            coverage_mid = max(np.sqrt(float(self.config.min_event_coverage) * float(self.config.max_event_coverage)), 1e-6)
            coverage_score = max(0.0, 1.0 - abs(np.log(max(coverage, 1e-9) / coverage_mid)) / 5.0)
            ret_score = np.tanh(ret_mean / max(abs(float(self.config.start_min_return)), 1e-6))
            dd_score = np.tanh(ret_mean / max(drawdown, 1e-6)) if ret_mean > 0 else ret_score
            uplift_score = np.tanh(max(uplift - 1.0, 0.0) / 2.0)
            fitness = 0.30 * uplift_score + 0.20 * hit_rate + 0.20 * ret_score + 0.15 * dd_score + 0.10 * stability + 0.05 * coverage_score
            fitness -= float(self.config.fail_penalty) * fail_rate
            fitness -= float(self.config.complexity_penalty) * complexity
            if coverage < float(self.config.min_event_coverage) or coverage > float(self.config.max_event_coverage):
                fitness -= float(self.config.sparsity_penalty)
            rows.append({**metrics, **q, "factor": name, "generation": generation, "fitness": float(fitness)})
        return pd.DataFrame(rows).sort_values("fitness", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()

    def _evaluate_event_factor(self, name: str, factor_df: pd.DataFrame) -> Dict[str, Any]:
        cfg = self.config
        target = self.label_data["target"].reindex_like(factor_df)
        fail = self.label_data["fail"].reindex_like(factor_df)
        future_ret = self.label_data["future_ret_20d"].reindex_like(factor_df)
        future_up = self.label_data["future_max_up_20d"].reindex_like(factor_df)
        future_dd = self.label_data["future_max_drawdown_20d"].reindex_like(factor_df)
        trigger = (factor_df >= float(cfg.event_trigger_threshold)).astype(float)
        train_mask = pd.DataFrame(True, index=factor_df.index, columns=factor_df.columns)
        valid_mask = pd.DataFrame(False, index=factor_df.index, columns=factor_df.columns)
        if cfg.train_end_time:
            train_mask.loc[train_mask.index > pd.Timestamp(cfg.train_end_time), :] = False
        if cfg.valid_end_time and cfg.train_end_time:
            valid_mask.loc[(valid_mask.index > pd.Timestamp(cfg.train_end_time)) & (valid_mask.index <= pd.Timestamp(cfg.valid_end_time)), :] = True
        base = self._segment_metrics(trigger, target, fail, future_ret, future_up, future_dd, train_mask)
        valid = self._segment_metrics(trigger, target, fail, future_ret, future_up, future_dd, valid_mask)
        stability = 0.0
        if valid["support"] > 0 and base["hit_rate"] > 0 and valid["hit_rate"] > 0:
            stability = float(min(base["hit_rate"], valid["hit_rate"]) / max(base["hit_rate"], valid["hit_rate"]))
        elif valid["support"] == 0:
            stability = 0.5
        valid_flag = base["support"] >= int(cfg.min_event_support) and base["coverage"] >= float(cfg.min_event_coverage) and base["coverage"] <= float(cfg.max_event_coverage)
        return {
            "factor": name,
            "valid": bool(valid_flag),
            "support": int(base["support"]),
            "coverage": float(base["coverage"]),
            "baseline_hit_rate": float(base["baseline_hit_rate"]),
            "hit_rate": float(base["hit_rate"]),
            "uplift": float(base["uplift"]),
            "fail_rate": float(base["fail_rate"]),
            "future_ret_20d_mean": float(base["future_ret_mean"]),
            "future_ret_20d_median": float(base["future_ret_median"]),
            "future_max_up_20d_mean": float(base["future_up_mean"]),
            "future_max_drawdown_20d_mean": float(base["future_dd_mean"]),
            "valid_support": int(valid["support"]),
            "valid_hit_rate": float(valid["hit_rate"]),
            "valid_uplift": float(valid["uplift"]),
            "stability": float(stability),
        }

    @staticmethod
    def _segment_metrics(trigger: pd.DataFrame, target: pd.DataFrame, fail: pd.DataFrame, future_ret: pd.DataFrame, future_up: pd.DataFrame, future_dd: pd.DataFrame, segment_mask: pd.DataFrame) -> Dict[str, float]:
        mask = segment_mask & target.notna() & future_ret.notna()
        total = int(mask.sum().sum())
        if total <= 0:
            return {"support": 0, "coverage": 0.0, "baseline_hit_rate": 0.0, "hit_rate": 0.0, "uplift": 0.0, "fail_rate": 0.0, "future_ret_mean": 0.0, "future_ret_median": 0.0, "future_up_mean": 0.0, "future_dd_mean": 0.0}
        trig = (trigger > 0.5) & mask
        support = int(trig.sum().sum())
        baseline = float(target.where(mask).stack(dropna=True).mean())
        if support <= 0:
            return {"support": 0, "coverage": 0.0, "baseline_hit_rate": baseline, "hit_rate": 0.0, "uplift": 0.0, "fail_rate": 0.0, "future_ret_mean": 0.0, "future_ret_median": 0.0, "future_up_mean": 0.0, "future_dd_mean": 0.0}
        hit_values = target.where(trig).stack(dropna=True)
        fail_values = fail.where(trig).stack(dropna=True)
        ret_values = future_ret.where(trig).stack(dropna=True)
        up_values = future_up.where(trig).stack(dropna=True)
        dd_values = future_dd.where(trig).stack(dropna=True)
        hit_rate = float(hit_values.mean()) if not hit_values.empty else 0.0
        return {
            "support": float(support),
            "coverage": float(support / max(total, 1)),
            "baseline_hit_rate": baseline,
            "hit_rate": hit_rate,
            "uplift": float(hit_rate / max(baseline, 1e-9)),
            "fail_rate": float(fail_values.mean()) if not fail_values.empty else 0.0,
            "future_ret_mean": float(ret_values.mean()) if not ret_values.empty else 0.0,
            "future_ret_median": float(ret_values.median()) if not ret_values.empty else 0.0,
            "future_up_mean": float(up_values.mean()) if not up_values.empty else 0.0,
            "future_dd_mean": float(dd_values.mean()) if not dd_values.empty else 0.0,
        }

    def _next_generation(self, scored: pd.DataFrame, expr_map: Dict[str, EventExpr], next_generation: int) -> List[EventExpr]:
        cfg = self.config
        ranked = scored.sort_values("fitness", ascending=False)
        elites = [expr_map[str(x)] for x in ranked.head(max(int(cfg.elite_keep), 1))["factor"] if str(x) in expr_map]
        parents = [expr_map[str(x)] for x in ranked.head(max(int(cfg.population_size // 2), 2))["factor"] if str(x) in expr_map]
        if not parents:
            parents = elites or [self.engine.random_expr()]
        next_pop: List[EventExpr] = []
        for expr in elites:
            self._record_lineage(expr, next_generation, "elite", [expr], None)
            next_pop.append(expr)
        while len(next_pop) < int(cfg.population_size):
            ops: List[str] = []
            parent_exprs: List[EventExpr] = []
            if self.engine.rng.random() < float(cfg.crossover_rate) and len(parents) >= 2:
                pa = self.engine.rng.choice(parents)
                pb = self.engine.rng.choice(parents)
                child = self.engine.crossover(pa, pb)
                parent_exprs = [pa, pb]
                ops.append("crossover")
            else:
                pa = self.engine.rng.choice(parents)
                child = pa
                parent_exprs = [pa]
            mutation_op: Optional[str] = None
            if self.engine.rng.random() < float(cfg.mutation_rate):
                child = self.engine.mutate(child)
                mutation_op = child.op
                ops.append("mutate")
            operation = "+".join(ops) if ops else "reproduction"
            self._record_lineage(child, next_generation, operation, parent_exprs, mutation_op)
            next_pop.append(child)
        random_inject = [self.engine.random_expr() for _ in range(int(cfg.population_size))]
        for expr in random_inject:
            self._record_lineage(expr, next_generation, "random_inject", [], None)
        return self._unique_exprs(next_pop + random_inject)[: int(cfg.population_size)]

    @staticmethod
    def _unique_exprs(exprs: List[EventExpr]) -> List[EventExpr]:
        seen: set[str] = set()
        out: List[EventExpr] = []
        for expr in exprs:
            key = expr.key()
            if key in seen:
                continue
            seen.add(key)
            out.append(expr)
        return out

    def _load_final_event_factors(self, exprs: List[EventExpr]) -> None:
        self.factor_dict = {}
        self._expr_by_name = {}
        close = self.panel["close"]
        for i, expr in enumerate(self._unique_exprs(exprs)):
            name = f"mwega_final_{i:04d}"
            self.factor_dict[name] = self.engine.eval_expr(expr).reindex_like(close)
            self._expr_by_name[name] = expr
        print(f"✅ 汇总历代 elite 后进入最终评价: {len(self.factor_dict)} 个事件因子")

    def _evaluate_final_events(self) -> pd.DataFrame:
        rows = []
        for name, df in self.factor_dict.items():
            expr = self._expr_by_name.get(name)
            metrics = self._evaluate_event_factor(name, df)
            metrics["expr_key"] = expr.key() if expr else ""
            metrics["complexity"] = expr.complexity() if expr else 0
            metrics["depth"] = expr.depth() if expr else 0
            rows.append(metrics)
        out = pd.DataFrame(rows)
        if out.empty:
            return out
        out = out.sort_values(["valid", "uplift", "hit_rate", "future_ret_20d_mean"], ascending=[False, False, False, False]).reset_index(drop=True)
        print(f"✅ 最终事件评价完成: {len(out)} 个")
        return out

    def _filter_final_events(self, evaluation: pd.DataFrame) -> Tuple[List[str], pd.DataFrame]:
        if evaluation.empty:
            return [], pd.DataFrame()
        report = evaluation.copy()
        report["selected"] = False
        report["drop_reason"] = ""
        candidates = report[report["valid"]].sort_values("fitness" if "fitness" in report.columns else "uplift", ascending=False)
        if candidates.empty:
            candidates = report.sort_values("uplift", ascending=False).head(max(int(self.config.export_topk), 1))
        selected: List[str] = []
        selected_triggers: Dict[str, pd.DataFrame] = {}
        for _, row in candidates.iterrows():
            factor = str(row["factor"])
            trigger = (self.factor_dict[factor] >= float(self.config.event_trigger_threshold)).astype(float)
            too_close = False
            for old_name, old_trigger in selected_triggers.items():
                jaccard = self._jaccard(trigger, old_trigger)
                if jaccard > float(self.config.jaccard_max):
                    too_close = True
                    report.loc[report["factor"] == factor, "drop_reason"] = f"与 {old_name} 触发重合度过高 jaccard={jaccard:.3f}"
                    break
            if too_close:
                continue
            selected.append(factor)
            selected_triggers[factor] = trigger
            report.loc[report["factor"] == factor, "selected"] = True
            if len(selected) >= int(self.config.export_topk):
                break
        report.loc[(~report["selected"]) & (report["drop_reason"] == ""), "drop_reason"] = "未进入最终 TopK 或质量过滤未通过"
        print(f"✅ 主升浪事件 GA 最终过滤后保留 {len(selected)} / {len(evaluation)} 个事件因子")
        return selected, report

    @staticmethod
    def _jaccard(a: pd.DataFrame, b: pd.DataFrame) -> float:
        aa = a.astype(bool)
        bb = b.reindex_like(a).astype(bool)
        inter = float((aa & bb).sum().sum())
        union = float((aa | bb).sum().sum())
        return inter / union if union > 0 else 0.0

    def _build_event_signals(self, selected: List[str]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        mode = str(getattr(self.config, "signal_mode", "all") or "all").lower()
        if mode not in {"traditional", "ml", "all"}:
            print(f"  ⚠️ 未知 signal_mode={mode!r}，回退为 all")
            mode = "all"
        pieces = []
        trigger_pieces = []
        for name in selected:
            df = self.factor_dict[name]
            pieces.append(df.rank(axis=1, pct=True))
            trigger_pieces.append((df >= float(self.config.event_trigger_threshold)).astype(float))
        signals: Dict[str, pd.DataFrame] = {}
        signal_info: Dict[str, Any] = {"mode": mode, "n_factors": len(selected)}
        if pieces and mode in {"traditional", "all"}:
            score = pd.concat(pieces, keys=range(len(pieces)), names=["factor", "date"]).groupby(level="date").mean()
            trigger_score = pd.concat(trigger_pieces, keys=range(len(trigger_pieces)), names=["factor", "date"]).groupby(level="date").sum()
            signals.update({"score_mwega_equal": score, "score_mwega_trigger_count": trigger_score})
        if selected and mode in {"ml", "all"}:
            try:
                original_standardized = dict(self.standardized_factors)
                self.standardized_factors = {
                    name: self.factor_dict[name].replace([np.inf, -np.inf], np.nan).fillna(0.0)
                    for name in selected
                    if name in self.factor_dict
                }
                ml_signals, ml_info = self._ml_signals(selected)
                renamed_ml_signals = {}
                for name, score in ml_signals.items():
                    renamed_ml_signals[name.replace("score_ml_", "score_mwega_ml_")] = score
                signals.update(renamed_ml_signals)
                signal_info["ml"] = ml_info
                print(f"  ✅ ML 回测信号完成: {', '.join(renamed_ml_signals.keys())}")
            except Exception as exc:
                signal_info["ml_error"] = f"{type(exc).__name__}: {exc}"
                print(f"  ⚠️ ML 回测信号构造失败，已跳过: {type(exc).__name__}: {exc}")
            finally:
                self.standardized_factors = original_standardized if "original_standardized" in locals() else self.standardized_factors
        return signals, signal_info

    def _export_selected_factors(self, selected: List[str]) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
        used_names: set[str] = set()
        for idx, factor_name in enumerate(selected, start=1):
            expr = self._expr_by_name.get(factor_name)
            if expr is None:
                continue
            func_name = f"compute_{self.config.export_prefix}_{int(time.time())}_{idx:03d}"
            while func_name in used_names or (CUSTOM_DIR / f"{func_name}.py").exists():
                idx += 1
                func_name = f"compute_{self.config.export_prefix}_{int(time.time())}_{idx:03d}"
            used_names.add(func_name)
            source = self._build_export_source(func_name, expr)
            ok, msg = validate_factor_code(source, run_smoke_test=True)
            if not ok:
                print(f"  ⚠️ 事件因子 {factor_name} 导出校验失败: {msg}")
                continue
            target = CUSTOM_DIR / f"{func_name}.py"
            target.write_text(source, encoding="utf-8")
            rows.append({"factor": factor_name, "function": func_name, "path": str(target), "expression": expr.key()})
            print(f"  💾 已导出主升浪事件因子: {target.name}")
        return pd.DataFrame(rows)

    def _build_export_source(self, func_name: str, expr: EventExpr) -> str:
        event_vars = {name: f"event_{name}" for name in sorted(expr.events())}
        expr_code = expr.to_code(event_vars)
        event_code = self._export_event_code(event_vars)
        return (
            "from __future__ import annotations\n\n"
            "import numpy as np\n"
            "import pandas as pd\n\n\n"
            f"def {func_name}(open_df, high_df, low_df, close_df, volume_df) -> pd.DataFrame:\n"
            "    def _b(x):\n"
            "        return (x.astype(float).fillna(0.0) >= 0.5).astype(float)\n"
            "    def _any(x, window):\n"
            "        return (_b(x).rolling(int(window), min_periods=1).max() > 0).astype(float)\n"
            "    def _count_ge(x, window, threshold):\n"
            "        return (_b(x).rolling(int(window), min_periods=1).sum() >= int(threshold)).astype(float)\n"
            "    def _then(a, b, min_gap, max_gap):\n"
            "        left = _b(a)\n"
            "        prior = pd.DataFrame(0.0, index=left.index, columns=left.columns)\n"
            "        for gap in range(int(min_gap), int(max_gap) + 1):\n"
            "            shifted = left.shift(gap)\n"
            "            prior = prior.where(prior >= shifted, shifted)\n"
            "        return (prior * _b(b)).astype(float)\n"
            "    def _decay(x, window):\n"
            "        base = _b(x)\n"
            "        out = pd.DataFrame(0.0, index=base.index, columns=base.columns)\n"
            "        w = int(window)\n"
            "        for gap in range(w):\n"
            "            shifted = base.shift(gap) * (float(w - gap) / float(w))\n"
            "            out = out.where(out >= shifted, shifted)\n"
            "        return out.astype(float)\n"
            "    ret1 = close_df / close_df.shift(1) - 1.0\n"
            "    gap = open_df / close_df.shift(1) - 1.0\n"
            "    body_high = close_df.where(close_df >= open_df, open_df)\n"
            "    body_low = close_df.where(close_df <= open_df, open_df)\n"
            "    day_range = (high_df - low_df).replace(0.0, np.nan)\n"
            "    upper_shadow = (high_df - body_high) / day_range\n"
            "    lower_shadow = (body_low - low_df) / day_range\n"
            "    body_abs = (close_df - open_df).abs() / open_df.replace(0.0, np.nan)\n"
            "    close_pos = (close_df - low_df) / day_range\n"
            "    amount_proxy = close_df * volume_df\n"
            "    ma5 = close_df.rolling(5, min_periods=5).mean()\n"
            "    ma10 = close_df.rolling(10, min_periods=10).mean()\n"
            "    ma20 = close_df.rolling(20, min_periods=20).mean()\n"
            "    hh20 = close_df.rolling(20, min_periods=20).max()\n"
            "    hh60 = close_df.rolling(60, min_periods=30).max()\n"
            "    ll10 = close_df.rolling(10, min_periods=5).min()\n"
            "    vol_ma5 = volume_df.rolling(5, min_periods=3).mean()\n"
            "    vol_ma20 = volume_df.rolling(20, min_periods=5).mean()\n"
            "    amt_ma20 = amount_proxy.rolling(20, min_periods=5).mean()\n"
            "    ret3 = close_df / close_df.shift(3) - 1.0\n"
            "    ret5 = close_df / close_df.shift(5) - 1.0\n"
            "    ret20 = close_df / close_df.shift(20) - 1.0\n"
            f"{event_code}"
            f"    result = {expr_code}\n"
            "    return result.astype(float).replace([np.inf, -np.inf], np.nan)\n"
        )

    def _export_event_code(self, event_vars: Dict[str, str]) -> str:
        threshold = {
            "limit_up": float(self.config.limit_up_threshold),
            "near_limit_up": float(self.config.near_limit_up_threshold),
            "big_up": float(self.config.big_up_threshold),
            "big_down": float(self.config.big_down_threshold),
            "volume_surge_ratio": float(self.config.volume_surge_ratio),
            "shrink_volume_ratio": float(self.config.shrink_volume_ratio),
        }
        formulas = {
            "limit_up": f"(ret1 >= {threshold['limit_up']!r}).astype(float)",
            "near_limit_up": f"(ret1 >= {threshold['near_limit_up']!r}).astype(float)",
            "big_up": f"(ret1 >= {threshold['big_up']!r}).astype(float)",
            "restart_big_up": f"((ret1 >= {threshold['big_up']!r}) & (close_pos >= 0.70)).astype(float)",
            "gap_up_big": "(gap >= 0.03).astype(float)",
            "close_near_high": "(close_pos >= 0.80).astype(float)",
            "break_20d_high": "(close_df >= hh20.shift(1) * 1.005).astype(float)",
            "break_60d_high": "(close_df >= hh60.shift(1) * 1.005).astype(float)",
            "volume_surge": f"(volume_df >= vol_ma20 * {threshold['volume_surge_ratio']!r}).astype(float)",
            "amount_surge": f"(amount_proxy >= amt_ma20 * {threshold['volume_surge_ratio']!r}).astype(float)",
            "volume_double": "(volume_df >= vol_ma20 * 2.0).astype(float)",
            "shrink_volume_pullback": f"((ret3 <= 0.03) & (ret5 <= 0.06) & (volume_df <= vol_ma5 * {threshold['shrink_volume_ratio']!r}) & (close_df >= ma20 * 0.98)).astype(float)",
            "volume_price_confirm": "((ret1 > 0.02) & (volume_df >= vol_ma20 * 1.3)).astype(float)",
            "big_amount_breakout": "((close_df >= hh20.shift(1) * 1.003) & (amount_proxy >= amt_ma20 * 1.5)).astype(float)",
            "volume_breakout": "((close_df >= hh20.shift(1) * 1.003) & (volume_df >= vol_ma20 * 1.4)).astype(float)",
            "long_upper_shadow": "(upper_shadow >= 0.45).astype(float)",
            "long_lower_shadow": "(lower_shadow >= 0.40).astype(float)",
            "big_bull_candle": "((ret1 >= 0.035) & (body_abs >= 0.025) & (close_df > open_df)).astype(float)",
            "big_bear_candle": "((ret1 <= -0.035) & (body_abs >= 0.025) & (close_df < open_df)).astype(float)",
            "doji_like": "(body_abs <= 0.008).astype(float)",
            "close_above_mid": "(close_pos >= 0.50).astype(float)",
            "ma5_above_ma10": "(ma5 > ma10).astype(float)",
            "ma10_above_ma20": "(ma10 >= ma20 * 0.995).astype(float)",
            "ma_bull_order": "((ma5 > ma10) & (ma10 >= ma20 * 0.995) & (close_df > ma20)).astype(float)",
            "close_above_ma20": "(close_df > ma20).astype(float)",
            "ma20_slope_up": "(ma20 > ma20.shift(5)).astype(float)",
            "higher_high": "(high_df >= high_df.shift(1).rolling(5, min_periods=3).max()).astype(float)",
            "higher_low": "(low_df >= low_df.shift(1).rolling(5, min_periods=3).min()).astype(float)",
            "pullback_to_ma5": "((close_df <= ma5 * 1.025) & (close_df >= ma5 * 0.975)).astype(float)",
            "pullback_to_ma10": "((close_df <= ma10 * 1.03) & (close_df >= ma10 * 0.97)).astype(float)",
            "pullback_not_break_ma20": "((low_df <= ma20 * 1.03) & (close_df >= ma20 * 0.99)).astype(float)",
            "small_pullback_after_big_up": f"((ret5 <= 0.05) & ((ret20 >= 0.08) | (_any((ret1 >= {threshold['big_up']!r}).astype(float), 10) > 0))).astype(float)",
            "lower_shadow_on_ma": "((lower_shadow >= 0.30) & (low_df <= ma10 * 1.03) & (close_df >= ma20 * 0.98)).astype(float)",
            "pullback_depth_ok": "((close_df >= ll10 * 1.02) & (ret5 <= 0.06) & (ret20 >= 0.00)).astype(float)",
            "long_upper_shadow_high_volume": "((upper_shadow >= 0.40) & (volume_df >= vol_ma20 * 1.5)).astype(float)",
            "high_open_low_close": "((gap >= 0.02) & (close_df < open_df) & (close_pos <= 0.35)).astype(float)",
            "big_down": f"(ret1 <= {threshold['big_down']!r}).astype(float)",
            "volume_down_break": "((ret1 <= -0.03) & (volume_df >= vol_ma20 * 1.4)).astype(float)",
            "break_ma20_down": "(close_df < ma20 * 0.98).astype(float)",
            "consecutive_down": "((ret1 < 0).rolling(3, min_periods=3).sum() >= 3).astype(float)",
        }
        lines = []
        for name, var in event_vars.items():
            lines.append(f"    {var} = {formulas[name]}\n")
        return "".join(lines)

    def _append_generation_markdown(self, gen: int, scored: pd.DataFrame, gen_best: float, gen_mean: float, archive_size: int) -> None:
        md_path = self.output_dir / "mwega_generations.md"
        if gen == 0 and md_path.exists():
            md_path.unlink()
        lines = [f"\n## Generation {gen}\n", f"best_fitness={gen_best:.6f}, mean_fitness={gen_mean:.6f}, archive={archive_size}\n"]
        cols = ["factor", "fitness", "hit_rate", "uplift", "coverage", "fail_rate", "expr_key"]
        top = scored.head(10)
        for _, row in top.iterrows():
            parts = []
            for col in cols:
                if col not in row:
                    continue
                val = row[col]
                if isinstance(val, float):
                    parts.append(f"{col}={val:.4f}")
                else:
                    parts.append(f"{col}={val}")
            lines.append("- " + " | ".join(parts))
        with md_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _save_mwega_results(self, results: Dict[str, Any], elapsed: float) -> None:
        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        self._latest_mwega_timestamp = ts
        out = self.output_dir
        results["event_evaluation"].to_csv(out / f"mwega_event_evaluation_{ts}.csv", index=False, encoding="utf-8-sig")
        results["filter_report"].to_csv(out / f"mwega_filter_report_{ts}.csv", index=False, encoding="utf-8-sig")
        results["stock_pool_report"].to_csv(out / f"mwega_stock_pool_report_{ts}.csv", index=False, encoding="utf-8-sig")
        results["backtest"].to_csv(out / f"mwega_backtest_returns_{ts}.csv", encoding="utf-8-sig")
        results["performance"].to_csv(out / f"mwega_performance_{ts}.csv", index=False, encoding="utf-8-sig")
        if not self.mwega_generation_stats.empty:
            self.mwega_generation_stats.to_csv(out / f"mwega_generation_stats_{ts}.csv", index=False, encoding="utf-8-sig")
        if not self.mwega_population.empty:
            self.mwega_population.to_csv(out / f"mwega_population_{ts}.csv", index=False, encoding="utf-8-sig")
        if not self.mwega_elite_archive.empty:
            self.mwega_elite_archive.to_csv(out / f"mwega_elite_archive_{ts}.csv", index=False, encoding="utf-8-sig")
        if not self.mwega_lineage.empty:
            self.mwega_lineage.to_csv(out / f"mwega_lineage_{ts}.csv", index=False, encoding="utf-8-sig")
        exported = results.get("mwega_exported_factors", pd.DataFrame())
        if isinstance(exported, pd.DataFrame) and not exported.empty:
            exported.to_csv(out / f"mwega_exported_factors_{ts}.csv", index=False, encoding="utf-8-sig")
        summary = {
            "elapsed_seconds": float(elapsed),
            "population_size": int(self.config.population_size),
            "generations": int(self.config.generations),
            "label_mode": self.config.label_mode,
            "signal_mode": self.config.signal_mode,
            "event_count": int(len(self.event_library)),
            "archive_size": int(len(self.mwega_elite_archive)),
            "selected_factors": results.get("selected_factors", []),
            "signal_info": results.get("signal_info", {}),
            "exported": int(len(exported)) if isinstance(exported, pd.DataFrame) else 0,
        }
        (out / f"mwega_summary_{ts}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    def _plot_mwega_results(self, backtest: pd.DataFrame) -> None:
        ts = getattr(self, "_latest_mwega_timestamp", None) or pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        if not self.mwega_generation_stats.empty:
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(self.mwega_generation_stats["generation"], self.mwega_generation_stats["best_fitness"], label="best")
            ax.plot(self.mwega_generation_stats["generation"], self.mwega_generation_stats["mean_fitness"], label="mean")
            ax.set_title("Main Wave Event GA Fitness")
            ax.set_xlabel("Generation")
            ax.set_ylabel("Fitness")
            ax.grid(alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(self.output_dir / f"mwega_fitness_{ts}.png", dpi=120)
            plt.close(fig)
        if not backtest.empty:
            fig2, ax2 = plt.subplots(figsize=(11, 6))
            cumulative = (1.0 + backtest.fillna(0.0)).cumprod()
            for col in cumulative.columns:
                ax2.plot(cumulative.index, cumulative[col], label=col, linewidth=1.4)
            ax2.set_title("Main Wave Event GA Backtest")
            ax2.set_xlabel("Date")
            ax2.set_ylabel("Cumulative Return")
            ax2.grid(alpha=0.3)
            ax2.legend(loc="best", fontsize=9)
            fig2.tight_layout()
            fig2.savefig(self.output_dir / f"mwega_cumulative_return_{ts}.png", dpi=120)
            plt.close(fig2)


_RUN_LOCK = threading.Lock()
_RUN_STATE: Dict[str, Any] = {"running": False, "logs": [], "last_results": None, "error": None, "start_time": None, "end_time": None}


class _LogTee(io.StringIO):
    def __init__(self, original):
        super().__init__()
        self.original = original

    def write(self, s):
        try:
            self.original.write(s)
        except Exception:
            pass
        if s and s.strip():
            with _RUN_LOCK:
                _RUN_STATE["logs"].append(s.rstrip("\n"))
                _RUN_STATE["logs"] = _RUN_STATE["logs"][-1000:]
        return len(s)

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass


def _json_safe(value: Any) -> Any:
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        v = float(value)
        return v if np.isfinite(v) else None
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _run_background(config: WorkflowMainWaveEventGAConfig) -> None:
    with _RUN_LOCK:
        _RUN_STATE.update({"running": True, "logs": [], "last_results": None, "error": None, "start_time": time.strftime("%Y-%m-%d %H:%M:%S"), "end_time": None})
    tee = _LogTee(sys.stdout)
    try:
        with redirect_stdout(tee):
            wf = WorkflowMainWaveEventGA(config)
            results = wf.run()
        exported = results.get("mwega_exported_factors", pd.DataFrame())
        latest_ts = getattr(wf, "_latest_mwega_timestamp", "")
        fitness_name = f"mwega_fitness_{latest_ts}.png" if latest_ts else ""
        cumulative_name = f"mwega_cumulative_return_{latest_ts}.png" if latest_ts else ""
        with _RUN_LOCK:
            _RUN_STATE["last_results"] = _json_safe(
                {
                    "performance": results["performance"].round(4).to_dict(orient="records"),
                    "selected_factors": results.get("selected_factors", []),
                    "signal_info": results.get("signal_info", {}),
                    "exported": exported.to_dict(orient="records") if isinstance(exported, pd.DataFrame) else [],
                    "generation_stats": wf.mwega_generation_stats.round(4).to_dict(orient="records"),
                    "elite": wf.mwega_elite_archive.head(30).round(4).to_dict(orient="records"),
                    "fitness_url": f"/api/result-file/{fitness_name}" if fitness_name and (wf.output_dir / fitness_name).exists() else "",
                    "cumulative_url": f"/api/result-file/{cumulative_name}" if cumulative_name and (wf.output_dir / cumulative_name).exists() else "",
                    "output_dir": str(wf.output_dir),
                }
            )
    except Exception as exc:
        with _RUN_LOCK:
            _RUN_STATE["error"] = f"{type(exc).__name__}: {exc}"
            _RUN_STATE["logs"].extend(traceback.format_exc().splitlines())
    finally:
        with _RUN_LOCK:
            _RUN_STATE["running"] = False
            _RUN_STATE["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")


def _merge_config(payload: Dict[str, Any]) -> WorkflowMainWaveEventGAConfig:
    default = asdict(WorkflowMainWaveEventGAConfig())
    merged = asdict(load_saved_config())
    for key, value in (payload or {}).items():
        if key not in default or value in ("", None):
            continue
        target = default[key]
        try:
            if isinstance(target, bool):
                merged[key] = bool(value) if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
            elif isinstance(target, int):
                merged[key] = int(value)
            elif isinstance(target, float):
                merged[key] = float(value)
            elif isinstance(target, list):
                merged[key] = value if isinstance(value, list) else [x.strip() for x in str(value).split(",") if x.strip()]
                if key in {"window_choices", "sequence_gap_choices", "count_threshold_choices", "ml_model"} and key != "ml_model":
                    merged[key] = [int(x) for x in merged[key]]
            else:
                merged[key] = str(value)
        except Exception:
            continue
    return WorkflowMainWaveEventGAConfig(**merged)


def _build_flask_app() -> Any:
    if Flask is None:
        raise ImportError("缺少 flask，请先 pip install flask")
    from _workflow_main_wave_event_ga_html import render_index_html

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = Flask(__name__, static_folder=None)
    index_html = render_index_html()

    @app.route("/")
    def index():
        return index_html

    @app.route("/api/config", methods=["GET"])
    def api_config_get():
        return jsonify(asdict(load_saved_config()))

    @app.route("/api/config", methods=["POST"])
    def api_config_post():
        cfg = _merge_config(request.get_json(silent=True) or {})
        save_config(cfg)
        return jsonify({"ok": True, "config": asdict(cfg)})

    @app.route("/api/run", methods=["POST"])
    def api_run():
        with _RUN_LOCK:
            if _RUN_STATE["running"]:
                return jsonify({"ok": False, "error": "已有主升浪事件 GA 任务运行中"}), 409
        cfg = _merge_config(request.get_json(silent=True) or {})
        save_config(cfg)
        threading.Thread(target=_run_background, args=(cfg,), daemon=True).start()
        return jsonify({"ok": True, "config": asdict(cfg)})

    @app.route("/api/status")
    def api_status():
        with _RUN_LOCK:
            return jsonify(dict(_RUN_STATE))

    @app.route("/api/result-file/<path:filename>")
    def api_result_file(filename: str):
        if not filename.endswith((".png", ".jpg", ".jpeg", ".svg")):
            return jsonify({"ok": False, "error": "只允许访问结果图片文件"}), 400
        return send_from_directory(str(_THIS_DIR / "results_main_wave_event_ga"), filename)

    return app


def main_cli() -> None:
    cfg = load_saved_config()
    save_config(cfg)
    WorkflowMainWaveEventGA(cfg).run()


def main_web(host: str = "127.0.0.1", port: int = 8002) -> None:
    app = _build_flask_app()
    print("=" * 80)
    print(f"主升浪事件 GA Web 控制台已启动: http://{host}:{port}")
    print("=" * 80)
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="主升浪事件序列遗传挖掘 workflow")
    parser.add_argument("--cli", action="store_true", help="不启动 Web，直接命令行运行")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()
    if args.cli:
        main_cli()
    else:
        main_web(args.host, args.port)
