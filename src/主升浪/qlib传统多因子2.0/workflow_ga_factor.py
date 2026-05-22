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

import factor_filter  # noqa: E402
from workflow_v2 import WorkflowConfigV2, WorkflowV2  # noqa: E402

try:
    from flask import Flask, jsonify, request, send_from_directory
except Exception:  # pragma: no cover
    Flask = None  # type: ignore[assignment]
    jsonify = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]

_CUSTOM_FACTOR_LOADER_PATH = _SOURCE_DIR / "custom-fa" / "custom_factor_loader.py"
_spec = importlib.util.spec_from_file_location("custom_factor_loader", _CUSTOM_FACTOR_LOADER_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"无法加载 custom factor loader: {_CUSTOM_FACTOR_LOADER_PATH}")
_custom_factor_loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_custom_factor_loader)
validate_factor_code = _custom_factor_loader.validate_factor_code
CUSTOM_DIR = _custom_factor_loader.CUSTOM_DIR

CONFIG_FILE = _THIS_DIR / "workflow_ga_factor_config.json"
V2_CONFIG_FILE = _THIS_DIR / "workflow_v2_config.json"


@dataclass
class WorkflowGAFactorConfig(WorkflowConfigV2):
    output_dir: str = "results_ga"
    factor_cache_dir: str = ".factor_cache_ga"
    use_step7_cache: bool = False
    signal_mode: str = "traditional"
    population_size: int = 50
    generations: int = 20
    max_depth: int = 4
    max_nodes: int = 24
    crossover_rate: float = 0.7
    mutation_rate: float = 0.2
    elite_keep: int = 5
    generation_elite_k: int = 10
    early_stop_rounds: int = 5
    window_choices: List[int] = field(default_factory=lambda: [3, 5, 10, 20, 30, 60])
    export_topk: int = 10
    random_seed: int = 20260520
    min_non_null_ratio: float = 0.35
    complexity_penalty: float = 0.002
    corr_penalty: float = 0.05
    export_prefix: str = "ga"


def load_saved_config() -> WorkflowGAFactorConfig:
    default = WorkflowGAFactorConfig()
    if not CONFIG_FILE.exists():
        cfg = _build_initial_config(default)
        save_config(cfg)
        return cfg
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        valid = set(asdict(default).keys())
        filtered = {k: v for k, v in raw.items() if k in valid and v not in ("", None)}
        for key in ("factor_libraries", "ml_model", "window_choices"):
            if key in filtered and not isinstance(filtered[key], list):
                filtered[key] = [x.strip() for x in str(filtered[key]).split(",") if x.strip()]
        if "window_choices" in filtered:
            filtered["window_choices"] = [int(x) for x in filtered["window_choices"]]
        return WorkflowGAFactorConfig(**{**asdict(_build_initial_config(default)), **filtered})
    except Exception as exc:
        print(f"⚠️ 读取 GA 配置失败，将使用默认参数: {exc}")
        return _build_initial_config(default)


def _build_initial_config(default: WorkflowGAFactorConfig) -> WorkflowGAFactorConfig:
    base = asdict(default)
    if V2_CONFIG_FILE.exists():
        try:
            raw = json.loads(V2_CONFIG_FILE.read_text(encoding="utf-8"))
            valid = set(base.keys())
            for key, value in raw.items():
                if key in valid and key not in {"output_dir", "factor_cache_dir", "use_step7_cache"}:
                    base[key] = value
        except Exception as exc:
            print(f"⚠️ 读取 V2 配置失败，将使用 GA 内置默认值: {exc}")
    base.update(
        {
            "output_dir": "results_ga",
            "factor_cache_dir": ".factor_cache_ga",
            "use_step7_cache": False,
            "population_size": 50,
            "generations": 20,
            "max_depth": 4,
            "max_nodes": 24,
            "crossover_rate": 0.7,
            "mutation_rate": 0.2,
            "elite_keep": 5,
            "generation_elite_k": 10,
            "early_stop_rounds": 5,
            "window_choices": [3, 5, 10, 20, 30, 60],
            "export_topk": 10,
            "random_seed": 20260520,
            "min_non_null_ratio": 0.35,
            "complexity_penalty": 0.002,
            "corr_penalty": 0.05,
            "export_prefix": "ga",
        }
    )
    return WorkflowGAFactorConfig(**base)


def save_config(config: WorkflowGAFactorConfig) -> None:
    CONFIG_FILE.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class GAExpr:
    op: str
    children: Tuple["GAExpr", ...] = ()
    value: Any = None

    def key(self) -> str:
        if self.op == "field":
            return str(self.value)
        if self.op == "const":
            return f"{float(self.value):.4g}"
        args = ",".join(child.key() for child in self.children)
        return f"{self.op}[{self.value}]({args})" if self.value is not None else f"{self.op}({args})"

    def depth(self) -> int:
        return 1 if not self.children else 1 + max(child.depth() for child in self.children)

    def complexity(self) -> int:
        return 1 + sum(child.complexity() for child in self.children)

    def fields(self) -> List[str]:
        if self.op == "field":
            return [str(self.value)]
        values: List[str] = []
        for child in self.children:
            values.extend(child.fields())
        return sorted(set(values))

    def eval(self, panel: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if self.op == "field":
            return panel[str(self.value)].copy()
        if self.op == "const":
            base = panel["close"]
            return pd.DataFrame(float(self.value), index=base.index, columns=base.columns)
        args = [child.eval(panel) for child in self.children]
        with np.errstate(all="ignore"):
            if self.op == "add":
                out = args[0].add(args[1], fill_value=np.nan)
            elif self.op == "sub":
                out = args[0].sub(args[1], fill_value=np.nan)
            elif self.op == "mul":
                out = args[0] * args[1]
            elif self.op == "safe_div":
                out = args[0].divide(args[1].replace(0.0, np.nan))
            elif self.op == "rank":
                out = args[0].rank(axis=1, pct=True)
            elif self.op == "demean":
                out = args[0].sub(args[0].mean(axis=1), axis=0)
            elif self.op == "zscore_cs":
                out = args[0].sub(args[0].mean(axis=1), axis=0).div(args[0].std(axis=1).replace(0.0, np.nan), axis=0)
            elif self.op == "scale":
                out = args[0].div(args[0].abs().sum(axis=1).replace(0.0, np.nan), axis=0)
            elif self.op == "delay":
                out = args[0].shift(int(self.value))
            elif self.op == "delta":
                out = args[0].diff(int(self.value))
            elif self.op == "ts_mean":
                out = args[0].rolling(int(self.value), min_periods=int(self.value)).mean()
            elif self.op == "ts_std":
                out = args[0].rolling(int(self.value), min_periods=int(self.value)).std()
            elif self.op == "ts_min":
                out = args[0].rolling(int(self.value), min_periods=int(self.value)).min()
            elif self.op == "ts_max":
                out = args[0].rolling(int(self.value), min_periods=int(self.value)).max()
            elif self.op == "ts_rank":
                out = args[0].rolling(int(self.value), min_periods=int(self.value)).rank(pct=True)
            elif self.op == "correlation":
                out = args[0].rolling(int(self.value), min_periods=int(self.value)).corr(args[1])
            elif self.op == "covariance":
                out = args[0].rolling(int(self.value), min_periods=int(self.value)).cov(args[1])
            elif self.op == "log_abs":
                out = np.log(args[0].abs().replace(0.0, np.nan))
            elif self.op == "abs":
                out = args[0].abs()
            elif self.op == "sign":
                out = np.sign(args[0])
            elif self.op == "min":
                out = args[0].where(args[0] <= args[1], args[1])
            elif self.op == "max":
                out = args[0].where(args[0] >= args[1], args[1])
            else:
                raise ValueError(f"未知算子: {self.op}")
        return out.astype(float).replace([np.inf, -np.inf], np.nan)

    def to_code(self, names: Dict[str, str]) -> str:
        if self.op == "field":
            return names[str(self.value)]
        if self.op == "const":
            return f"pd.DataFrame({float(self.value)!r}, index=close_df.index, columns=close_df.columns)"
        c = [x.to_code(names) for x in self.children]
        if self.op == "add":
            return f"({c[0]}).add(({c[1]}), fill_value=np.nan)"
        if self.op == "sub":
            return f"({c[0]}).sub(({c[1]}), fill_value=np.nan)"
        if self.op == "mul":
            return f"(({c[0]}) * ({c[1]}))"
        if self.op == "safe_div":
            return f"({c[0]}).divide(({c[1]}).replace(0.0, np.nan))"
        if self.op == "rank":
            return f"({c[0]}).rank(axis=1, pct=True)"
        if self.op == "demean":
            return f"({c[0]}).sub(({c[0]}).mean(axis=1), axis=0)"
        if self.op == "zscore_cs":
            return f"({c[0]}).sub(({c[0]}).mean(axis=1), axis=0).div(({c[0]}).std(axis=1).replace(0.0, np.nan), axis=0)"
        if self.op == "scale":
            return f"({c[0]}).div(({c[0]}).abs().sum(axis=1).replace(0.0, np.nan), axis=0)"
        if self.op == "delay":
            return f"({c[0]}).shift({int(self.value)})"
        if self.op == "delta":
            return f"({c[0]}).diff({int(self.value)})"
        if self.op in {"ts_mean", "ts_std", "ts_min", "ts_max"}:
            method = {"ts_mean": "mean", "ts_std": "std", "ts_min": "min", "ts_max": "max"}[self.op]
            return f"({c[0]}).rolling({int(self.value)}, min_periods={int(self.value)}).{method}()"
        if self.op == "ts_rank":
            return f"({c[0]}).rolling({int(self.value)}, min_periods={int(self.value)}).rank(pct=True)"
        if self.op == "correlation":
            return f"({c[0]}).rolling({int(self.value)}, min_periods={int(self.value)}).corr(({c[1]}))"
        if self.op == "covariance":
            return f"({c[0]}).rolling({int(self.value)}, min_periods={int(self.value)}).cov(({c[1]}))"
        if self.op == "log_abs":
            return f"np.log(({c[0]}).abs().replace(0.0, np.nan))"
        if self.op == "abs":
            return f"({c[0]}).abs()"
        if self.op == "sign":
            return f"np.sign(({c[0]}))"
        if self.op == "min":
            return f"({c[0]}).where(({c[0]}) <= ({c[1]}), ({c[1]}))"
        if self.op == "max":
            return f"({c[0]}).where(({c[0]}) >= ({c[1]}), ({c[1]}))"
        raise ValueError(f"未知算子: {self.op}")


class GAFactorEngine:
    fields = ("open", "high", "low", "close", "volume", "amount", "vwap", "returns")
    unary_ops = ("rank", "demean", "zscore_cs", "scale", "log_abs", "abs", "sign")
    window_unary_ops = ("delay", "delta", "ts_mean", "ts_std", "ts_min", "ts_max", "ts_rank")
    binary_ops = ("add", "sub", "mul", "safe_div", "min", "max")
    window_binary_ops = ("correlation", "covariance")

    def __init__(self, config: WorkflowGAFactorConfig):
        self.config = config
        self.rng = random.Random(int(config.random_seed))
        self.expr_cache: Dict[str, pd.DataFrame] = {}

    def random_expr(self, depth: int = 0) -> GAExpr:
        if depth >= self.config.max_depth or self.rng.random() < 0.25:
            if self.rng.random() < 0.9:
                return GAExpr("field", value=self.rng.choice(self.fields))
            return GAExpr("const", value=self.rng.choice([-1.0, -0.5, 0.5, 1.0, 2.0]))
        group = self.rng.choice(["unary", "window_unary", "binary", "window_binary"])
        if group == "unary":
            return GAExpr(self.rng.choice(self.unary_ops), (self.random_expr(depth + 1),))
        if group == "window_unary":
            return GAExpr(self.rng.choice(self.window_unary_ops), (self.random_expr(depth + 1),), self._window())
        if group == "binary":
            return GAExpr(self.rng.choice(self.binary_ops), (self.random_expr(depth + 1), self.random_expr(depth + 1)))
        return GAExpr(self.rng.choice(self.window_binary_ops), (self.random_expr(depth + 1), self.random_expr(depth + 1)), self._window())

    def _window(self) -> int:
        values = [int(x) for x in self.config.window_choices if int(x) > 1]
        return self.rng.choice(values or [5, 10, 20])

    def eval_expr(self, expr: GAExpr, panel: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        key = expr.key()
        if key not in self.expr_cache:
            self.expr_cache[key] = expr.eval(panel)
        return self.expr_cache[key]

    def mutate(self, expr: GAExpr) -> GAExpr:
        if self.rng.random() < 0.25:
            return self.random_expr(0)
        if expr.op == "field":
            return GAExpr("field", value=self.rng.choice(self.fields))
        if expr.op == "const":
            return GAExpr("const", value=self.rng.choice([-1.0, -0.5, 0.5, 1.0, 2.0]))
        children = list(expr.children)
        if children and self.rng.random() < 0.65:
            idx = self.rng.randrange(len(children))
            children[idx] = self.mutate(children[idx])
            return GAExpr(expr.op, tuple(children), expr.value)
        if expr.op in self.window_unary_ops + self.window_binary_ops:
            return GAExpr(expr.op, expr.children, self._window())
        return self.random_expr(0)

    def crossover(self, left: GAExpr, right: GAExpr) -> GAExpr:
        if self.rng.random() < 0.35 or not left.children:
            return right
        children = list(left.children)
        idx = self.rng.randrange(len(children))
        children[idx] = self.crossover(children[idx], right)
        return GAExpr(left.op, tuple(children), left.value)


class WorkflowGAFactor(WorkflowV2):
    def __init__(self, config: WorkflowGAFactorConfig):
        super().__init__(config)
        self.config: WorkflowGAFactorConfig = config
        self.engine = GAFactorEngine(config)
        self.ga_generation_stats = pd.DataFrame()
        self.ga_population = pd.DataFrame()
        self.ga_elite_archive = pd.DataFrame()
        self.ga_lineage = pd.DataFrame()
        self.ga_diversity = pd.DataFrame()
        self.ga_lineage_top_text: str = ""
        self._expr_by_name: Dict[str, GAExpr] = {}
        # expr_key -> {first_generation, operation, parents, mutation_op, depth, complexity}
        self._lineage_map: Dict[str, Dict[str, Any]] = {}
        # 每次表达式在某代被评价后的详细记录，含 fitness / survived
        self._lineage_records: List[Dict[str, Any]] = []

    def run(self) -> Dict[str, Any]:
        print("🧬 workflow_ga_factor 启动：逐代生成 → 逐代评价 → 逐代进化")
        save_config(self.config)
        t0 = time.perf_counter()
        self._init_qlib()
        self._load_market_data()
        pool_report = self._filter_stock_pool()
        self._build_returns()

        final_exprs = self._evolve_factors()
        self._load_final_ga_factors(final_exprs)
        self._standardize_factors()
        eval_upper_bound = self.config.train_end_time if self.config.filter_use_train_only else None
        evaluation, rank_ic, quantile_returns, correlation = self._evaluate_factors(eval_upper_bound)
        selected, filter_report = self._filter_final_factors(evaluation, correlation)
        if not selected:
            raise RuntimeError("GA 最终过滤后剩余 0 个因子，请放宽过滤参数或增加代数。")
        exported = self._export_selected_factors(selected)
        factor_profile = self._profile_factors(evaluation, rank_ic, quantile_returns, eval_upper_bound)
        signals, ml_info = self._build_signals(selected, evaluation)
        benchmark = self._load_benchmark_returns()
        backtest, performance = self._run_backtests(signals, benchmark)

        results = {
            "factor_evaluation": evaluation,
            "factor_profile": factor_profile,
            "rank_ic": rank_ic,
            "quantile_returns": quantile_returns,
            "correlation": correlation,
            "filter_report": filter_report,
            "stock_pool_report": pool_report,
            "selected_factors": selected,
            "signals": signals,
            "backtest": backtest,
            "performance": performance,
            "ml_info": ml_info,
            "ga_generation_stats": self.ga_generation_stats,
            "ga_population": self.ga_population,
            "ga_elite_archive": self.ga_elite_archive,
            "ga_exported_factors": exported,
        }
        self._save_results(results)
        self._save_ga_results(results)
        self._plot_results(rank_ic, quantile_returns, backtest)
        self._plot_ga_results()
        print(f"🎉 GA workflow 完成，总耗时 {time.perf_counter() - t0:.2f}s")
        print(f"📁 结果目录: {self.output_dir}")
        return results

    def _evolve_factors(self) -> List[GAExpr]:
        cfg = self.config
        # 0 代初始种群：随机初始化
        init_pop = self._unique_exprs([self.engine.random_expr() for _ in range(cfg.population_size * 2)])[: cfg.population_size]
        for expr in init_pop:
            self._record_lineage(expr, generation=0, operation="random_init", parents=[], mutation_op=None)
        population: List[GAExpr] = init_pop
        archive: Dict[str, Dict[str, Any]] = {}
        population_rows: List[Dict[str, Any]] = []
        generation_rows: List[Dict[str, Any]] = []
        best_fitness = -1e18
        stale_rounds = 0
        last_completed_gen = -1

        for gen in range(int(cfg.generations)):
            print(f"\n🧬 第 {gen + 1}/{cfg.generations} 代：计算并评价 {len(population)} 个表达式")
            factors, expr_map, quality = self._compute_population(population, gen)
            if not factors:
                print("  ⚠️ 本代无有效表达式，随机重启种群")
                population = self._unique_exprs([self.engine.random_expr() for _ in range(cfg.population_size * 2)])[: cfg.population_size]
                for expr in population:
                    self._record_lineage(expr, generation=gen + 1, operation="random_restart", parents=[], mutation_op=None)
                continue
            self.factor_dict = factors
            self._standardize_factors()
            evaluation, _, quantile_returns, correlation = self._evaluate_factors(cfg.train_end_time if cfg.filter_use_train_only else None)
            scored = self._score_generation(evaluation, quantile_returns, correlation, quality, expr_map, gen)
            if scored.empty:
                population = self._unique_exprs([self.engine.random_expr() for _ in range(cfg.population_size * 2)])[: cfg.population_size]
                for expr in population:
                    self._record_lineage(expr, generation=gen + 1, operation="random_restart", parents=[], mutation_op=None)
                continue
            population_rows.extend(scored.to_dict(orient="records"))
            for row in scored.to_dict(orient="records"):
                rec = {
                    "generation": int(gen),
                    "factor": str(row.get("factor")),
                    "expr_key": str(row.get("expr_key")),
                    "operation": str(row.get("operation", "unknown")),
                    "parents": str(row.get("parents") or ""),
                    "mutation_op": str(row.get("mutation_op") or ""),
                    "first_generation": int(row.get("first_generation", gen) or gen),
                    "fitness": float(row.get("fitness", 0.0) or 0.0),
                    "rank_ic_mean": float(row.get("rank_ic_mean", 0.0) or 0.0),
                    "rank_ic_ir": float(row.get("rank_ic_ir", 0.0) or 0.0),
                    "depth": int(row.get("depth", 0) or 0),
                    "complexity": int(row.get("complexity", 0) or 0),
                    "survived": False,
                }
                self._lineage_records.append(rec)
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
            try:
                self._append_generation_markdown(gen, scored, top_n=5, gen_best=gen_best, gen_mean=gen_mean, archive_size=len(archive))
            except Exception as exc:
                print(f"  ⚠️ 写 ga_generations.md 失败: {type(exc).__name__}: {exc}")
            last_completed_gen = gen
            if gen_best > best_fitness + 1e-8:
                best_fitness = gen_best
                stale_rounds = 0
            else:
                stale_rounds += 1
                if stale_rounds >= int(cfg.early_stop_rounds):
                    print(f"  🛑 连续 {stale_rounds} 代未提升，提前停止")
                    break
            population = self._next_generation(scored, expr_map, gen + 1)

        # 标记下代仍存在的个体为 survived（限制在最后一成功代的记录上）
        if last_completed_gen >= 0:
            survived_keys = {self._lineage_map.get(expr.key(), {}).get("expr_key") or expr.key() for expr in population}
            for rec in self._lineage_records:
                if int(rec["generation"]) == int(last_completed_gen) and rec["expr_key"] in survived_keys:
                    rec["survived"] = True

        self.ga_population = pd.DataFrame(population_rows)
        self.ga_generation_stats = pd.DataFrame(generation_rows)
        self.ga_lineage = pd.DataFrame(self._lineage_records)
        self.ga_elite_archive = pd.DataFrame(list(archive.values()))
        if self.ga_elite_archive.empty or "fitness" not in self.ga_elite_archive.columns:
            raise RuntimeError("GA 未产生任何有效 elite 因子。")
        self.ga_elite_archive = self.ga_elite_archive.sort_values("fitness", ascending=False).reset_index(drop=True)
        self.ga_diversity = self._compute_diversity()
        self.ga_lineage_top_text = self._build_top_lineage_text(top_n=10)
        try:
            self._append_lineage_markdown_section()
        except Exception as exc:
            print(f"⚠️ 写 ga_generations.md 谱系章节失败: {type(exc).__name__}: {exc}")
        final_rows = self.ga_elite_archive.head(max(int(cfg.export_topk) * 5, int(cfg.export_topk))).to_dict(orient="records")
        return [self._expr_by_name[str(row["factor"])] for row in final_rows if str(row["factor"]) in self._expr_by_name]

    def _append_generation_markdown(
        self,
        gen: int,
        scored: pd.DataFrame,
        top_n: int,
        gen_best: float,
        gen_mean: float,
        archive_size: int,
    ) -> None:
        md_path = self.output_dir / "ga_generations.md"
        ranked = scored.sort_values("fitness", ascending=False).head(max(int(top_n), 1))
        lines: List[str] = []
        if not md_path.exists():
            cfg = self.config
            lines.append("# GA 因子工作流 进化报告\n")
            lines.append(
                f"种群={cfg.population_size}, 代数={cfg.generations}, 交叉率={cfg.crossover_rate}, 变异率={cfg.mutation_rate}, "
                f"精英保留={cfg.elite_keep}, 最大深度={cfg.max_depth}, 最大节点={cfg.max_nodes}\n"
            )
            lines.append(
                "\n说明：本文件逐代追加，可以在 GA 运行过程中随时查看。`operation` 含义："
                "`random_init` 初始随机, `random_inject` 本代随机注入, `random_restart` 本代重启, "
                "`elite` 从上代直接保留, `crossover` 交叉, `mutate` 变异, `crossover+mutate` 先交叉后变异, `reproduction` 原样复制。\n"
            )
        lines.append(f"\n## 第 {gen} 代  best={gen_best:.4f}  mean={gen_mean:.4f}  n_valid={len(scored)}  archive={archive_size}")
        if "operation" in scored.columns:
            op_counts = scored["operation"].value_counts().to_dict()
            if op_counts:
                op_str = " | ".join([f"{k}={int(v)}" for k, v in op_counts.items()])
                lines.append(f"- 本代有效个体操作分布：{op_str}")
        lines.append("")
        lines.append("| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for i, row in enumerate(ranked.to_dict(orient="records"), start=1):
            expr_key = str(row.get("expr_key", "") or "").replace("|", "\\|")
            if len(expr_key) > 140:
                expr_key = expr_key[:140] + "…"
            lines.append(
                f"| {i} | {row.get('factor')} | {row.get('operation','')} | {row.get('mutation_op','') or ''} | "
                f"{float(row.get('fitness',0.0) or 0.0):.4f} | {float(row.get('rank_ic_mean',0.0) or 0.0):.4f} | "
                f"{float(row.get('rank_ic_ir',0.0) or 0.0):.2f} | {int(row.get('depth',0) or 0)} | "
                f"{int(row.get('complexity',0) or 0)} | `{expr_key}` |"
            )
        # 展开 top 3 的父代表达式
        lines.append("")
        for i, row in enumerate(ranked.head(3).to_dict(orient="records"), start=1):
            op = str(row.get("operation", "") or "")
            parents_str = str(row.get("parents", "") or "")
            parents = [p for p in parents_str.split("|") if p]
            if op in ("random_init", "random_inject", "random_restart") or not parents:
                continue
            lines.append(f"- **#{i} {row.get('factor')}**  来源=`{op}`  变异点=`{row.get('mutation_op','') or '-'}`")
            for pi, pk in enumerate(parents):
                pk_show = pk if len(pk) <= 140 else pk[:140] + "…"
                lines.append(f"  - parent[{pi}] = `{pk_show}`")
        with md_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _append_lineage_markdown_section(self) -> None:
        md_path = self.output_dir / "ga_generations.md"
        if not md_path.exists() or self.ga_elite_archive.empty:
            return
        lines: List[str] = ["\n---\n\n## 🌳 最优 Top 10 因子血缘\n"]
        for rank, row in enumerate(self.ga_elite_archive.head(10).to_dict(orient="records"), start=1):
            factor = str(row.get("factor"))
            fitness = float(row.get("fitness", 0.0) or 0.0)
            expr_key = str(row.get("expr_key", ""))
            lines.append(f"\n**[{rank}] {factor}**  fitness=`{fitness:.4f}`  \n  expr = `{expr_key}`")
            tree_lines: List[str] = []
            self._append_lineage_chain(expr_key, tree_lines, depth=1, max_depth=6)
            if tree_lines:
                lines.append("```")
                lines.extend(tree_lines)
                lines.append("```")
        with md_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _record_lineage(
        self,
        expr: GAExpr,
        generation: int,
        operation: str,
        parents: List[GAExpr],
        mutation_op: Optional[str],
    ) -> None:
        key = expr.key()
        if key in self._lineage_map:
            return
        self._lineage_map[key] = {
            "expr_key": key,
            "first_generation": int(generation),
            "operation": str(operation),
            "parents": [p.key() for p in parents],
            "mutation_op": mutation_op,
            "depth": int(expr.depth()),
            "complexity": int(expr.complexity()),
        }

    def _compute_population(
        self, population: List[GAExpr], generation: int
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, GAExpr], Dict[str, Dict[str, Any]]]:
        factors: Dict[str, pd.DataFrame] = {}
        expr_map: Dict[str, GAExpr] = {}
        quality: Dict[str, Dict[str, Any]] = {}
        seen: set[str] = set()
        for i, expr in enumerate(population):
            key = expr.key()
            if key in seen or expr.depth() > self.config.max_depth or expr.complexity() > self.config.max_nodes:
                continue
            seen.add(key)
            name = f"ga_g{generation:03d}_{i:04d}"
            try:
                df = self.engine.eval_expr(expr, self.panel).reindex_like(self.future_return)
                non_null_ratio = float(df.notna().mean().mean())
                if non_null_ratio < float(self.config.min_non_null_ratio):
                    continue
                row_std = df.std(axis=1)
                if float((row_std.fillna(0.0) <= 1e-12).mean()) > 0.8:
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
                print(f"  ⚠️ 表达式计算失败: {key[:80]} | {type(exc).__name__}: {exc}")
        return factors, expr_map, quality

    def _build_top_lineage_text(self, top_n: int = 10) -> str:
        if self.ga_elite_archive.empty:
            return ""
        lines: List[str] = [f"# GA Lineage Top {top_n}\n"]
        for rank, row in enumerate(self.ga_elite_archive.head(top_n).to_dict(orient="records"), start=1):
            factor = str(row.get("factor"))
            fitness = float(row.get("fitness", 0.0) or 0.0)
            expr_key = str(row.get("expr_key", ""))
            lines.append(f"\n[{rank}] factor={factor} | fitness={fitness:.4f}\n    expr   = {expr_key}")
            self._append_lineage_chain(expr_key, lines, depth=1, max_depth=6)
        return "\n".join(lines)

    def _append_lineage_chain(self, expr_key: str, lines: List[str], depth: int, max_depth: int) -> None:
        if depth > max_depth:
            return
        info = self._lineage_map.get(expr_key)
        if not info:
            return
        indent = "    " * depth
        op = info.get("operation", "?")
        gen = info.get("first_generation", "?")
        muta = info.get("mutation_op") or ""
        muta_part = f" mutate={muta}" if muta else ""
        parents = list(info.get("parents") or [])
        if not parents:
            lines.append(f"{indent}└─ gen={gen} op={op}{muta_part} (root)")
            return
        lines.append(f"{indent}└─ gen={gen} op={op}{muta_part} parents={len(parents)}")
        for i, parent_key in enumerate(parents):
            lines.append(f"{indent}    parent[{i}] = {parent_key[:120]}")
            self._append_lineage_chain(parent_key, lines, depth + 1, max_depth)

    @staticmethod
    def _short_expr_label(expr_key: str, max_len: int = 36) -> str:
        text = str(expr_key or "")
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"

    def _collect_lineage_tree_nodes(
        self,
        expr_key: str,
        depth: int,
        max_depth: int,
        rows: List[Dict[str, Any]],
        edges: List[Tuple[str, str]],
        seen: set[str],
    ) -> None:
        if depth > max_depth or expr_key in seen:
            return
        seen.add(expr_key)
        info = self._lineage_map.get(expr_key, {})
        rows.append(
            {
                "expr_key": expr_key,
                "depth": int(depth),
                "operation": str(info.get("operation", "unknown")),
                "generation": info.get("first_generation", "?"),
                "mutation_op": info.get("mutation_op") or "",
                "parents": list(info.get("parents") or []),
            }
        )
        for parent_key in list(info.get("parents") or [])[:2]:
            edges.append((expr_key, parent_key))
            self._collect_lineage_tree_nodes(parent_key, depth + 1, max_depth, rows, edges, seen)

    def _plot_top_lineage_tree(self, ts: str, top_n: int = 10, max_depth: int = 5) -> None:
        if self.ga_elite_archive.empty or not self._lineage_map:
            return
        top_rows = self.ga_elite_archive.head(max(int(top_n), 1)).to_dict(orient="records")
        if not top_rows:
            return
        op_colors = {
            "random_init": "#D6EAF8",
            "random_inject": "#D5F5E3",
            "random_restart": "#FADBD8",
            "elite": "#FCF3CF",
            "crossover": "#D2B4DE",
            "mutate": "#F5CBA7",
            "crossover+mutate": "#F1948A",
            "reproduction": "#D7DBDD",
            "unknown": "#EAECEE",
        }
        n = len(top_rows)
        ncols = 2 if n > 1 else 1
        nrows = int(np.ceil(n / ncols))
        fig, axes = plt.subplots(nrows, ncols, figsize=(18, max(5, 4.5 * nrows)), squeeze=False)
        for ax in axes.ravel():
            ax.axis("off")
        for rank, row in enumerate(top_rows, start=1):
            ax = axes.ravel()[rank - 1]
            expr_key = str(row.get("expr_key", ""))
            factor = str(row.get("factor", ""))
            fitness = float(row.get("fitness", 0.0) or 0.0)
            nodes: List[Dict[str, Any]] = []
            edges: List[Tuple[str, str]] = []
            self._collect_lineage_tree_nodes(expr_key, 0, int(max_depth), nodes, edges, set())
            if not nodes:
                continue
            by_depth: Dict[int, List[Dict[str, Any]]] = {}
            for node in nodes:
                by_depth.setdefault(int(node["depth"]), []).append(node)
            positions: Dict[str, Tuple[float, float]] = {}
            max_width = max(len(v) for v in by_depth.values())
            for depth, level_nodes in by_depth.items():
                count = len(level_nodes)
                xs = np.linspace(0.08, 0.92, count) if count > 1 else np.array([0.5])
                y = 0.92 - depth * (0.80 / max(int(max_depth), 1))
                for x, node in zip(xs, level_nodes):
                    positions[str(node["expr_key"])] = (float(x), float(y))
            for child_key, parent_key in edges:
                if child_key not in positions or parent_key not in positions:
                    continue
                x0, y0 = positions[child_key]
                x1, y1 = positions[parent_key]
                ax.annotate(
                    "",
                    xy=(x1, y1 + 0.035),
                    xytext=(x0, y0 - 0.035),
                    arrowprops={"arrowstyle": "->", "color": "#566573", "lw": 1.0, "alpha": 0.75},
                )
            for node in nodes:
                key = str(node["expr_key"])
                x, y = positions[key]
                op = str(node.get("operation", "unknown"))
                mutation_op = str(node.get("mutation_op") or "")
                label = f"g{node.get('generation')} | {op}"
                if mutation_op:
                    label += f"\\nmut={mutation_op}"
                label += f"\\n{self._short_expr_label(key, 34)}"
                ax.text(
                    x,
                    y,
                    label,
                    ha="center",
                    va="center",
                    fontsize=7.5,
                    bbox={
                        "boxstyle": "round,pad=0.35",
                        "facecolor": op_colors.get(op, op_colors["unknown"]),
                        "edgecolor": "#34495E",
                        "linewidth": 0.8,
                        "alpha": 0.95,
                    },
                )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_title(f"Top {rank}: {factor} | fitness={fitness:.4f}", fontsize=10, pad=8)
            ax.text(0.01, 0.01, f"nodes={len(nodes)}, width={max_width}", fontsize=7, color="#7F8C8D", transform=ax.transAxes)
        legend_items = []
        for op, color in op_colors.items():
            legend_items.append(plt.Line2D([0], [0], marker="s", color="w", label=op, markerfacecolor=color, markeredgecolor="#34495E", markersize=9))
        fig.legend(handles=legend_items, loc="lower center", ncol=5, fontsize=8, frameon=False)
        fig.suptitle("GA Top 10 Lineage Inverted Trees", fontsize=16, y=0.995)
        fig.tight_layout(rect=[0, 0.04, 1, 0.97])
        fig.savefig(self.output_dir / f"ga_lineage_tree_{ts}.png", dpi=160)
        plt.close(fig)

    def _compute_diversity(self) -> pd.DataFrame:
        if not self._lineage_records:
            return pd.DataFrame()
        df = pd.DataFrame(self._lineage_records)
        rows: List[Dict[str, Any]] = []
        for gen, sub in df.groupby("generation"):
            ops_count = sub["operation"].value_counts().to_dict()
            rows.append(
                {
                    "generation": int(gen),
                    "n_evaluated": int(len(sub)),
                    "n_unique_expr": int(sub["expr_key"].nunique()),
                    "depth_mean": float(sub["depth"].mean()),
                    "complexity_mean": float(sub["complexity"].mean()),
                    "fitness_std": float(sub["fitness"].std() or 0.0),
                    "fitness_max": float(sub["fitness"].max()),
                    "fitness_mean": float(sub["fitness"].mean()),
                    "op_random_init": int(ops_count.get("random_init", 0)),
                    "op_random_inject": int(ops_count.get("random_inject", 0)),
                    "op_random_restart": int(ops_count.get("random_restart", 0)),
                    "op_elite": int(ops_count.get("elite", 0)),
                    "op_crossover": int(ops_count.get("crossover", 0)),
                    "op_mutate": int(ops_count.get("mutate", 0)),
                    "op_crossover_mutate": int(ops_count.get("crossover+mutate", 0)),
                    "op_reproduction": int(ops_count.get("reproduction", 0)),
                }
            )
        return pd.DataFrame(rows).sort_values("generation").reset_index(drop=True)

    def _score_generation(
        self,
        evaluation: pd.DataFrame,
        quantile_returns: pd.DataFrame,
        correlation: pd.DataFrame,
        quality: Dict[str, Dict[str, Any]],
        expr_map: Dict[str, GAExpr],
        generation: int,
    ) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        mono_map: Dict[str, float] = {}
        spread_map: Dict[str, float] = {}
        if not quantile_returns.empty:
            for factor, sub in quantile_returns.groupby("factor"):
                mean_q = sub.groupby("quantile")["ret"].mean().reindex(sorted(sub["quantile"].unique()))
                if len(mean_q) >= 2:
                    diffs = mean_q.diff().dropna()
                    mono_map[str(factor)] = float(max((diffs > 0).mean(), (diffs < 0).mean())) if not diffs.empty else 0.0
                    spread_map[str(factor)] = float(mean_q.iloc[-1] - mean_q.iloc[0])
        abs_corr_mean = correlation.abs().replace(1.0, np.nan).mean().fillna(0.0).to_dict() if not correlation.empty else {}
        for row in evaluation.to_dict(orient="records"):
            factor = str(row["factor"])
            q = quality.get(factor, {})
            if factor not in expr_map:
                continue
            rank_ic = abs(float(row.get("rank_ic_mean", 0.0) or 0.0))
            ir = abs(float(row.get("rank_ic_ir", 0.0) or 0.0))
            win_rate = float(row.get("ic_win_rate", 0.0) or 0.0)
            mono = abs(float(mono_map.get(factor, 0.0) or 0.0) - 0.5) * 2.0
            complexity = float(q.get("complexity", 1.0))
            corr_penalty = float(abs_corr_mean.get(factor, 0.0)) * float(self.config.corr_penalty)
            fitness = rank_ic + 0.4 * ir + 0.2 * win_rate + 0.1 * mono
            fitness -= float(self.config.complexity_penalty) * complexity + corr_penalty
            rows.append(
                {
                    **row,
                    **q,
                    "generation": generation,
                    "fitness": float(fitness),
                    "monotonicity_score": float(mono),
                    "top_bottom_spread": float(spread_map.get(factor, np.nan)),
                }
            )
        return pd.DataFrame(rows).sort_values("fitness", ascending=False).reset_index(drop=True)

    def _next_generation(self, scored: pd.DataFrame, expr_map: Dict[str, GAExpr], next_generation: int) -> List[GAExpr]:
        cfg = self.config
        ranked = scored.sort_values("fitness", ascending=False)
        elites = [expr_map[str(x)] for x in ranked.head(max(int(cfg.elite_keep), 1))["factor"] if str(x) in expr_map]
        parents = [expr_map[str(x)] for x in ranked.head(max(int(cfg.population_size // 2), 2))["factor"] if str(x) in expr_map]
        if not parents:
            parents = elites or [self.engine.random_expr()]
        next_pop: List[GAExpr] = []
        # 精英直接保留，记录为 elite
        for expr in elites:
            self._record_lineage(expr, generation=next_generation, operation="elite", parents=[expr], mutation_op=None)
            next_pop.append(expr)
        while len(next_pop) < int(cfg.population_size):
            ops_used: List[str] = []
            parent_exprs: List[GAExpr] = []
            if self.engine.rng.random() < float(cfg.crossover_rate) and len(parents) >= 2:
                pa = self.engine.rng.choice(parents)
                pb = self.engine.rng.choice(parents)
                child = self.engine.crossover(pa, pb)
                ops_used.append("crossover")
                parent_exprs = [pa, pb]
            else:
                pa = self.engine.rng.choice(parents)
                child = pa
                parent_exprs = [pa]
            mutation_op: Optional[str] = None
            if self.engine.rng.random() < float(cfg.mutation_rate):
                child = self.engine.mutate(child)
                ops_used.append("mutate")
                mutation_op = child.op
            if not ops_used:
                operation = "reproduction"
            else:
                operation = "+".join(ops_used)
            self._record_lineage(
                child,
                generation=next_generation,
                operation=operation,
                parents=parent_exprs,
                mutation_op=mutation_op,
            )
            next_pop.append(child)
        # 随机注入个体，保证多样性
        random_inject = [self.engine.random_expr() for _ in range(int(cfg.population_size))]
        for expr in random_inject:
            self._record_lineage(expr, generation=next_generation, operation="random_inject", parents=[], mutation_op=None)
        return self._unique_exprs(next_pop + random_inject)[: int(cfg.population_size)]

    @staticmethod
    def _unique_exprs(exprs: List[GAExpr]) -> List[GAExpr]:
        seen: set[str] = set()
        result: List[GAExpr] = []
        for expr in exprs:
            key = expr.key()
            if key in seen:
                continue
            seen.add(key)
            result.append(expr)
        return result

    def _load_final_ga_factors(self, exprs: List[GAExpr]) -> None:
        self.factor_dict = {}
        self._expr_by_name = {}
        for i, expr in enumerate(self._unique_exprs(exprs)):
            name = f"ga_final_{i:04d}"
            self.factor_dict[name] = self.engine.eval_expr(expr, self.panel).reindex_like(self.future_return)
            self._expr_by_name[name] = expr
        print(f"✅ 汇总历代 elite 后进入最终评价: {len(self.factor_dict)} 个因子")

    def _filter_final_factors(self, evaluation: pd.DataFrame, correlation: pd.DataFrame) -> Tuple[List[str], pd.DataFrame]:
        selected, report = factor_filter.apply(
            self.config.filter_method,
            evaluation,
            correlation=correlation,
            rank_ic_min=self.config.filter_rank_ic_min,
            rank_ic_ir_min=self.config.filter_rank_ic_ir_min,
            corr_max=self.config.filter_corr_max,
            topk=min(int(self.config.filter_topk), int(self.config.export_topk)),
        )
        selected = selected[: max(int(self.config.export_topk), 1)]
        print(f"✅ GA 最终过滤后保留 {len(selected)} / {len(evaluation)} 个因子")
        return selected, report

    def _export_selected_factors(self, selected: List[str]) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
        used_names: set[str] = set()
        for idx, factor_name in enumerate(selected, start=1):
            expr = self._expr_by_name.get(factor_name)
            if expr is None:
                continue
            fields = expr.fields()
            if "close" not in fields:
                fields = ["close"] + fields
            param_map = {
                "open": "open_df",
                "high": "high_df",
                "low": "low_df",
                "close": "close_df",
                "volume": "volume_df",
                "amount": "amount_df",
                "vwap": "vwap_df",
                "returns": "returns_df",
            }
            params = [param_map[x] for x in fields if x in param_map]
            func_name = f"compute_{self.config.export_prefix}_{int(time.time())}_{idx:03d}"
            while func_name in used_names or (CUSTOM_DIR / f"{func_name}.py").exists():
                idx += 1
                func_name = f"compute_{self.config.export_prefix}_{int(time.time())}_{idx:03d}"
            used_names.add(func_name)
            code_expr = expr.to_code(param_map)
            source = (
                "from __future__ import annotations\n\n"
                "import numpy as np\n"
                "import pandas as pd\n\n\n"
                f"def {func_name}({', '.join(params)}) -> pd.DataFrame:\n"
                f"    result = {code_expr}\n"
                "    return result.astype(float).replace([np.inf, -np.inf], np.nan)\n"
            )
            ok, msg = validate_factor_code(source, run_smoke_test=True)
            if not ok:
                print(f"  ⚠️ 因子 {factor_name} 导出校验失败: {msg}")
                continue
            target = CUSTOM_DIR / f"{func_name}.py"
            target.write_text(source, encoding="utf-8")
            rows.append({"factor": factor_name, "function": func_name, "path": str(target), "expression": expr.key()})
            print(f"  💾 已导出 GA 因子: {target.name}")
        return pd.DataFrame(rows)

    def _save_ga_results(self, results: Dict[str, Any]) -> None:
        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        self._latest_ga_timestamp = ts
        if not self.ga_generation_stats.empty:
            self.ga_generation_stats.to_csv(self.output_dir / f"ga_generation_stats_{ts}.csv", index=False, encoding="utf-8-sig")
        if not self.ga_population.empty:
            self.ga_population.to_csv(self.output_dir / f"ga_population_{ts}.csv", index=False, encoding="utf-8-sig")
        if not self.ga_elite_archive.empty:
            self.ga_elite_archive.to_csv(self.output_dir / f"ga_elite_archive_{ts}.csv", index=False, encoding="utf-8-sig")
        if not self.ga_lineage.empty:
            self.ga_lineage.to_csv(self.output_dir / f"ga_lineage_{ts}.csv", index=False, encoding="utf-8-sig")
        if not self.ga_diversity.empty:
            self.ga_diversity.to_csv(self.output_dir / f"ga_diversity_{ts}.csv", index=False, encoding="utf-8-sig")
        if self.ga_lineage_top_text:
            (self.output_dir / f"ga_lineage_top_{ts}.txt").write_text(self.ga_lineage_top_text, encoding="utf-8")
        exported = results.get("ga_exported_factors", pd.DataFrame())
        if isinstance(exported, pd.DataFrame) and not exported.empty:
            exported.to_csv(self.output_dir / f"ga_exported_factors_{ts}.csv", index=False, encoding="utf-8-sig")
        op_totals: Dict[str, int] = {}
        if not self.ga_lineage.empty and "operation" in self.ga_lineage.columns:
            op_totals = {str(k): int(v) for k, v in self.ga_lineage["operation"].value_counts().to_dict().items()}
        summary = {
            "population_size": self.config.population_size,
            "generations": self.config.generations,
            "archive_size": int(len(self.ga_elite_archive)),
            "lineage_records": int(len(self.ga_lineage)),
            "unique_expressions": int(len(self._lineage_map)),
            "operation_counts": op_totals,
            "exported": int(len(exported)) if isinstance(exported, pd.DataFrame) else 0,
            "selected_factors": results.get("selected_factors", []),
        }
        (self.output_dir / f"ga_summary_{ts}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    def _plot_ga_results(self) -> None:
        if self.ga_generation_stats.empty:
            return
        ts = getattr(self, "_latest_ga_timestamp", None) or pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(self.ga_generation_stats["generation"], self.ga_generation_stats["best_fitness"], label="best")
        ax.plot(self.ga_generation_stats["generation"], self.ga_generation_stats["mean_fitness"], label="mean")
        ax.set_title("GA Fitness by Generation")
        ax.set_xlabel("Generation")
        ax.set_ylabel("Fitness")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(self.output_dir / f"ga_fitness_{ts}.png", dpi=120)
        plt.close(fig)

        if not self.ga_diversity.empty:
            div = self.ga_diversity.set_index("generation")
            fig2, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
            axes[0].plot(div.index, div["n_unique_expr"], label="unique_expr", marker="o")
            axes[0].plot(div.index, div["complexity_mean"], label="mean_complexity", marker="s")
            axes[0].plot(div.index, div["depth_mean"], label="mean_depth", marker="^")
            axes[0].set_ylabel("Diversity / Structure")
            axes[0].grid(alpha=0.3)
            axes[0].legend(loc="best")
            axes[0].set_title("GA Diversity by Generation")
            op_cols = [
                "op_random_init",
                "op_random_inject",
                "op_random_restart",
                "op_elite",
                "op_crossover",
                "op_mutate",
                "op_crossover_mutate",
                "op_reproduction",
            ]
            present = [c for c in op_cols if c in div.columns and div[c].sum() > 0]
            if present:
                bottom = np.zeros(len(div.index), dtype=float)
                for col in present:
                    values = div[col].astype(float).values
                    axes[1].bar(div.index, values, bottom=bottom, label=col.replace("op_", ""))
                    bottom = bottom + values
                axes[1].set_ylabel("Population by Operation")
                axes[1].set_xlabel("Generation")
                axes[1].grid(alpha=0.3, axis="y")
                axes[1].legend(loc="upper right", fontsize=8, ncol=2)
            fig2.tight_layout()
            fig2.savefig(self.output_dir / f"ga_diversity_{ts}.png", dpi=120)
            plt.close(fig2)

        if not self.ga_lineage.empty:
            grouped = [sub["complexity"].astype(float).values for _, sub in self.ga_lineage.groupby("generation")]
            gens = sorted(self.ga_lineage["generation"].unique())
            if grouped and gens:
                fig3, ax3 = plt.subplots(figsize=(10, 5))
                ax3.boxplot(grouped, positions=gens, widths=0.6, showfliers=False)
                ax3.set_title("GA Complexity Distribution by Generation")
                ax3.set_xlabel("Generation")
                ax3.set_ylabel("Complexity")
                ax3.grid(alpha=0.3, axis="y")
                fig3.tight_layout()
                fig3.savefig(self.output_dir / f"ga_complexity_{ts}.png", dpi=120)
                plt.close(fig3)
            try:
                self._plot_top_lineage_tree(ts, top_n=10, max_depth=5)
            except Exception as exc:
                print(f"⚠️ 绘制 GA Top10 血缘倒树失败: {type(exc).__name__}: {exc}")


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


def _run_background(config: WorkflowGAFactorConfig) -> None:
    with _RUN_LOCK:
        _RUN_STATE.update({"running": True, "logs": [], "last_results": None, "error": None, "start_time": time.strftime("%Y-%m-%d %H:%M:%S"), "end_time": None})
    tee = _LogTee(sys.stdout)
    try:
        with redirect_stdout(tee):
            wf = WorkflowGAFactor(config)
            results = wf.run()
        perf = results["performance"].round(4).to_dict(orient="records")
        exported = results.get("ga_exported_factors", pd.DataFrame())
        # 按代切片 lineage（每代保留 fitness 最高的前 50 行，避免 web payload 过大）
        gen_buckets: Dict[int, List[Dict[str, Any]]] = {}
        if isinstance(wf.ga_lineage, pd.DataFrame) and not wf.ga_lineage.empty:
            for gen, sub in wf.ga_lineage.groupby("generation"):
                cols = [c for c in [
                    "factor", "expr_key", "operation", "parents", "mutation_op",
                    "first_generation", "fitness", "rank_ic_mean", "rank_ic_ir",
                    "depth", "complexity", "survived",
                ] if c in sub.columns]
                top = sub.sort_values("fitness", ascending=False).head(50)[cols]
                gen_buckets[int(gen)] = top.round(4).to_dict(orient="records")
        diversity_records = (
            wf.ga_diversity.round(4).to_dict(orient="records")
            if isinstance(wf.ga_diversity, pd.DataFrame) and not wf.ga_diversity.empty
            else []
        )
        latest_ts = getattr(wf, "_latest_ga_timestamp", "")
        lineage_tree_name = f"ga_lineage_tree_{latest_ts}.png" if latest_ts else ""
        lineage_tree_path = wf.output_dir / lineage_tree_name if lineage_tree_name else None
        lineage_tree_url = f"/api/result-file/{lineage_tree_name}" if lineage_tree_path is not None and lineage_tree_path.exists() else ""
        with _RUN_LOCK:
            _RUN_STATE["last_results"] = _json_safe(
                {
                    "performance": perf,
                    "selected_factors": results.get("selected_factors", []),
                    "exported": exported.to_dict(orient="records") if isinstance(exported, pd.DataFrame) else [],
                    "generation_stats": wf.ga_generation_stats.round(4).to_dict(orient="records"),
                    "diversity": diversity_records,
                    "lineage_by_generation": gen_buckets,
                    "lineage_top_text": wf.ga_lineage_top_text,
                    "lineage_tree_url": lineage_tree_url,
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


def _merge_config(payload: Dict[str, Any]) -> WorkflowGAFactorConfig:
    default = asdict(WorkflowGAFactorConfig())
    merged = asdict(load_saved_config())
    for key, value in (payload or {}).items():
        if key not in default:
            continue
        if value in ("", None):
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
                if key == "window_choices":
                    merged[key] = [int(x) for x in merged[key]]
            else:
                merged[key] = str(value)
        except Exception:
            continue
    return WorkflowGAFactorConfig(**merged)


def _build_flask_app() -> Any:
    if Flask is None:
        raise ImportError("缺少 flask，请先 pip install flask")
    from _workflow_ga_factor_html import render_index_html

    # 屏蔽 Flask/Werkzeug 的默认访问日志，避免 /api/status 轮询刷屏
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
                return jsonify({"ok": False, "error": "已有 GA 任务运行中"}), 409
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
        return send_from_directory(str(_THIS_DIR / "results_ga"), filename)

    return app


def main_cli() -> None:
    cfg = load_saved_config()
    save_config(cfg)
    WorkflowGAFactor(cfg).run()


def main_web(host: str = "127.0.0.1", port: int = 8001) -> None:
    app = _build_flask_app()
    print("=" * 80)
    print(f"GA 因子生成 Web 控制台已启动: http://{host}:{port}")
    print("=" * 80)
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="遗传算法因子生成 workflow")
    parser.add_argument("--cli", action="store_true", help="不启动 Web，直接命令行运行")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    if args.cli:
        main_cli()
    else:
        main_web(args.host, args.port)
