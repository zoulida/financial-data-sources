#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore
# pyright: reportMissingImports=false, reportMissingModuleSource=false, reportGeneralTypeIssues=false, reportOptionalMemberAccess=false
"""QLib 传统多因子 2.0 主流程。

相对 1.0 的扩展：

1. 任意选择因子库目录（_root / alpha101 / alpha158 / alpha191）。
2. 三种未来收益口径（持有期 close / 区间 max(high) / 区间 max(close)）。
3. 三种因子过滤策略（none / threshold / topk）。
4. 传统打分回测 与 ML 信号回测（LightGBM / Ridge / Lasso）。

运行方式：

- ``python workflow_v2.py`` 启动 Flask Web 控制台（端口 7778）。
- ``python workflow_v2.py --cli`` 直接命令行运行。
"""

from __future__ import annotations

import argparse
import json
import logging
import hashlib
import os
import sys
import threading
import time
import traceback
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
matplotlib.use("Agg")

# Windows 默认 stdout 编码可能是 GBK，无法输出 emoji 与中文。强制改为 UTF-8。
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import factor_cache  # noqa: E402
import factor_filter  # noqa: E402
import factor_loader  # noqa: E402
import return_builder  # noqa: E402
import stock_pool_filter  # noqa: E402
from ml_pipeline import MLConfig, train_predict  # noqa: E402

import qlib  # noqa: E402
from qlib.constant import REG_CN  # noqa: E402
from qlib.data import D  # noqa: E402
from qlib.utils import exists_qlib_data  # noqa: E402

# Flask 是 Web 控制台依赖，未安装时降级为 None，仅在启动 Web 时才报错（CLI 模式仍可用）。
try:
    from flask import Flask, jsonify, request  # noqa: E402
except ImportError:  # pragma: no cover
    Flask = None  # type: ignore[assignment]
    jsonify = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]

CONFIG_FILE = _THIS_DIR / "workflow_v2_config.json"
LOGGER = logging.getLogger(__name__)


# ============================================================================
# 配置
# ============================================================================


@dataclass
class WorkflowConfigV2:
    # ---- 沿用 1.0 ----
    provider_uri: str = "d:/pythonProject/sdufe-qlib/source/qlib-data数据下载/cn_data"
    market: str = "csi300"
    benchmark: str = "SH000300"
    start_time: str = "2024-11-01"
    end_time: str = "2026-04-30"
    topn: int = 50
    quantiles: int = 5
    ic_window: int = 60
    initial_account: float = 100000000.0
    open_cost: float = 0.0
    close_cost: float = 0.0
    output_dir: str = "results"
    # ---- 因子库 ----
    factor_libraries: List[str] = field(default_factory=lambda: ["_root"])
    # ---- 未来收益 ----
    future_return_mode: str = "holding_close"  # holding_close | max_high | max_close
    holding_period: int = 1
    # ---- 过滤 ----
    filter_method: str = "threshold"  # none | threshold | topk
    filter_rank_ic_min: float = 0.02
    filter_rank_ic_ir_min: float = 0.3
    filter_corr_max: float = 0.7
    filter_topk: int = 20
    # ---- 信号 ----
    signal_mode: str = "traditional"  # traditional | ml | all
    # ---- ML ----
    ml_model: List[str] = field(default_factory=lambda: ["lightgbm"])
    train_end_time: str = "2025-06-30"
    valid_end_time: str = "2025-09-30"
    test_start_time: str = "2025-10-01"
    ml_min_non_null_ratio: float = 0.3
    walk_forward_enable: bool = False
    walk_forward_n_windows: int = 5
    walk_forward_step_days: int = 30
    walk_forward_train_days: int = 730
    walk_forward_valid_days: int = 90
    use_step7_cache: bool = True
    # ---- 防未来函数 ----
    # direction_method:
    #   train_only  - 因子方向 / IC 加权权重仅用 train_end_time 之前的数据估算（默认，最干净）
    #   rolling     - 用 rolling_ic_window 个交易日的滚动 RankIC 决定方向 / 权重（时变，最严格）
    #   full_sample - 用全期 IC 估算（已知存在 look-ahead，仅用于对照验证）
    direction_method: str = "train_only"
    rolling_ic_window: int = 60
    # 第七步因子过滤是否仅用 train_end_time 之前的数据评估 IC/IR/分层（避免 in-sample 特征筛选）
    filter_use_train_only: bool = True
    # 回测净值与 performance 是否仅统计 >= test_start_time 之后的部分（与 ML 的 OOS 期对齐）
    backtest_test_period_only: bool = True
    enable_factor_profile: bool = True
    factor_profile_past_windows: List[int] = field(default_factory=lambda: [1, 3, 5, 10])
    factor_profile_future_window: int = 3
    # ---- 股票池过滤（akshare 市值 + 静态股价区间） ----
    enable_price_filter: bool = True
    min_close_price: float = 2.0
    max_close_price: float = 15.0
    price_filter_mode: str = "last"  # last | mean | median
    enable_market_cap_filter: bool = True
    min_market_cap_yi: float = 20.0
    max_market_cap_yi: float = 150.0
    market_cap_kind: str = "total"  # total | float
    market_cap_cache_max_age_days: int = 30
    force_refresh_market_cap_cache: bool = False
    # ---- 因子结果缓存（按 时间范围 + 股票池 + 因子源码 做 key）----
    enable_factor_cache: bool = True
    factor_cache_dir: str = ".factor_cache"


def load_saved_config() -> WorkflowConfigV2:
    default = WorkflowConfigV2()
    if not CONFIG_FILE.exists():
        return default
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)
        valid = set(asdict(default).keys())
        filtered = {k: v for k, v in saved.items() if k in valid}
        if "factor_libraries" in filtered and not isinstance(filtered["factor_libraries"], list):
            filtered["factor_libraries"] = [str(filtered["factor_libraries"])]
        if "ml_model" in filtered and not isinstance(filtered["ml_model"], list):
            filtered["ml_model"] = [str(filtered["ml_model"])]
        merged = {**asdict(default), **filtered}
        return WorkflowConfigV2(**merged)
    except Exception as exc:
        print(f"⚠️ 读取上次参数失败，将使用默认参数: {exc}")
        return default


def save_config(config: WorkflowConfigV2) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(asdict(config), file, ensure_ascii=False, indent=2)
        print(f"💾 已保存本次运行参数: {CONFIG_FILE}")
    except Exception as exc:
        print(f"⚠️ 保存运行参数失败: {exc}")


def _step7_cache_key(cfg: WorkflowConfigV2) -> str:
    payload = {
        "provider_uri": cfg.provider_uri,
        "market": cfg.market,
        "start_time": cfg.start_time,
        "end_time": cfg.end_time,
        "factor_libraries": list(cfg.factor_libraries),
        "future_return_mode": cfg.future_return_mode,
        "holding_period": int(cfg.holding_period),
        "filter_method": cfg.filter_method,
        "filter_rank_ic_min": float(cfg.filter_rank_ic_min),
        "filter_rank_ic_ir_min": float(cfg.filter_rank_ic_ir_min),
        "filter_corr_max": float(cfg.filter_corr_max),
        "filter_topk": int(cfg.filter_topk),
        "enable_price_filter": bool(cfg.enable_price_filter),
        "min_close_price": float(cfg.min_close_price),
        "max_close_price": float(cfg.max_close_price),
        "price_filter_mode": cfg.price_filter_mode,
        "enable_market_cap_filter": bool(cfg.enable_market_cap_filter),
        "min_market_cap_yi": float(cfg.min_market_cap_yi),
        "max_market_cap_yi": float(cfg.max_market_cap_yi),
        "market_cap_kind": cfg.market_cap_kind,
        # 防未来函数相关：会改变第六/七步的 evaluation 结果，所以必须纳入 key
        "filter_use_train_only": bool(cfg.filter_use_train_only),
        "train_end_time": cfg.train_end_time,
        "enable_factor_profile": bool(cfg.enable_factor_profile),
        "factor_profile_past_windows": list(cfg.factor_profile_past_windows),
        "factor_profile_future_window": int(cfg.factor_profile_future_window),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def _step7_cache_path(cfg: WorkflowConfigV2) -> Path:
    cache_dir = _THIS_DIR / ".step_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"step7_{_step7_cache_key(cfg)}.pkl"


# ============================================================================
# 工作流主类
# ============================================================================


class WorkflowV2:
    def __init__(self, config: WorkflowConfigV2):
        self.config = config
        self.output_dir = _THIS_DIR / config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.panel: Dict[str, pd.DataFrame] = {}
        self.future_return: Optional[pd.DataFrame] = None
        self.holding_return: Optional[pd.DataFrame] = None
        self.factor_dict: Dict[str, pd.DataFrame] = {}
        self.standardized_factors: Dict[str, pd.DataFrame] = {}

    # ---- 主流程 ----
    def run(self) -> Dict[str, Any]:
        print("🚀 QLib 传统多因子 2.0 workflow 启动")
        print("=" * 80)

        # 单步耗时记录
        step_times: List[Tuple[str, float]] = []

        def _timed(name: str, func, *args, **kwargs):
            t0 = time.perf_counter()
            result = func(*args, **kwargs)
            dt = time.perf_counter() - t0
            step_times.append((name, dt))
            print(f"⏱  [{name}] 耗时 {dt:.2f}s")
            return result

        run_t0 = time.perf_counter()

        cache_path = _step7_cache_path(self.config)
        cached_step7: Optional[Dict[str, Any]] = None
        if self.config.use_step7_cache and cache_path.exists():
            try:
                import pickle

                with open(cache_path, "rb") as fp:
                    cached_step7 = pickle.load(fp)
                print(f"♻️ 命中第七步缓存: {cache_path}")
            except Exception as exc:
                print(f"⚠️ 读取第七步缓存失败，将重新计算: {exc}")
                cached_step7 = None

        _timed("第一步:初始化QLib", self._init_qlib)
        if cached_step7 is None:
            _timed("第二步:加载行情", self._load_market_data)
            pool_report = _timed("第二点五步:股票池过滤", self._filter_stock_pool)
            _timed("第三步:构造未来收益", self._build_returns)
            _timed("第四步:加载因子库", self._load_factors)
            if not self.factor_dict:
                raise RuntimeError("加载到 0 个因子，请检查 factor_libraries 与行情数据。")

            _timed("第五步:标准化", self._standardize_factors)
            # 防未来函数：默认仅用 train_end_time 之前的数据评价因子，避免 in-sample 特征筛选
            eval_upper_bound: Optional[str] = (
                self.config.train_end_time
                if (self.config.filter_use_train_only and self.config.train_end_time)
                else None
            )
            evaluation, rank_ic, quantile_returns, correlation = _timed(
                "第六步:单因子评价", self._evaluate_factors, eval_upper_bound
            )
            factor_profile = _timed(
                "第六点五步:因子画像分类",
                self._profile_factors,
                evaluation,
                rank_ic,
                quantile_returns,
                eval_upper_bound,
            )
            selected, filter_report = _timed(
                "第七步:因子过滤", self._filter_factors, evaluation, correlation
            )
            if not selected:
                raise RuntimeError("过滤后剩余 0 个因子，请放宽过滤参数。")
            print(f"✅ 过滤后保留 {len(selected)} / {len(evaluation)} 个因子")

            try:
                import pickle

                cache_payload = {
                    "key": _step7_cache_key(self.config),
                    "pool_report": pool_report,
                    "evaluation": evaluation,
                    "factor_profile": factor_profile,
                    "rank_ic": rank_ic,
                    "quantile_returns": quantile_returns,
                    "correlation": correlation,
                    "selected": selected,
                    "filter_report": filter_report,
                    "future_return": self.future_return,
                    "holding_return": self.holding_return,
                    "standardized_factors": self.standardized_factors,
                }
                with open(cache_path, "wb") as fp:
                    pickle.dump(cache_payload, fp, protocol=pickle.HIGHEST_PROTOCOL)
                print(f"💾 已保存第七步缓存: {cache_path}")
            except Exception as exc:
                print(f"⚠️ 保存第七步缓存失败（不影响本次运行）: {exc}")
        else:
            pool_report = cached_step7.get("pool_report", pd.DataFrame())
            evaluation = cached_step7["evaluation"]
            factor_profile = cached_step7.get("factor_profile", pd.DataFrame())
            rank_ic = cached_step7.get("rank_ic", pd.DataFrame())
            quantile_returns = cached_step7.get("quantile_returns", pd.DataFrame())
            correlation = cached_step7.get("correlation", pd.DataFrame())
            selected = cached_step7["selected"]
            filter_report = cached_step7.get("filter_report", pd.DataFrame())
            self.future_return = cached_step7.get("future_return")
            self.holding_return = cached_step7.get("holding_return")
            self.standardized_factors = cached_step7.get("standardized_factors", {})
            if not selected:
                raise RuntimeError("第七步缓存中 selected 为空，请删除缓存或重新跑一遍前置步骤。")

        signals, ml_info = _timed(
            "第八步:构造信号", self._build_signals, selected, evaluation
        )
        benchmark = _timed("第九步:加载基准", self._load_benchmark_returns)
        backtest, performance = _timed(
            "第十步:回测", self._run_backtests, signals, benchmark
        )

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
        }
        _timed("第十一步:保存结果", self._save_results, results)
        _timed("第十二步:生成图表", self._plot_results, rank_ic, quantile_returns, backtest)

        total = time.perf_counter() - run_t0
        print("\n" + "=" * 80)
        print("⏲  各步骤耗时统计：")
        for name, dt in step_times:
            pct = (dt / total * 100.0) if total > 0 else 0.0
            print(f"   - {name:<22s} {dt:7.2f}s  ({pct:5.1f}%)")
        print(f"   {'总耗时':<22s} {total:7.2f}s")
        print("=" * 80)

        print("\n🎉 workflow 完成")
        print(f"📁 结果目录: {self.output_dir}")
        return results

    # ---- 步骤 1: QLib 初始化 ----
    def _init_qlib(self) -> None:
        print("\n第一步：初始化 QLib 数据环境")
        provider_uri = os.path.expanduser(self.config.provider_uri)
        if not exists_qlib_data(provider_uri):
            raise FileNotFoundError(f"QLib 数据不存在: {provider_uri}")
        # 重要：在 Windows + 中文目录下，joblib 的默认 multiprocessing 后端
        # 会让子进程通过 spawn 重新加载脚本路径，路径乱码会导致子进程反复失败、整个流程卡死。
        # 因此强制使用 threading 后端 + 单进程 kernels。
        qlib.init(
            provider_uri=provider_uri,
            region=REG_CN,
            joblib_backend="threading",
            kernels=1,
        )
        print(f"✅ QLib 初始化成功: {provider_uri}")

    # ---- 步骤 2: 行情数据 ----
    def _load_market_data(self) -> None:
        print("\n第二步：读取股票池行情数据")
        instruments = D.instruments(market=self.config.market)
        base_fields = ["$open", "$high", "$low", "$close", "$volume", "$vwap"]
        try:
            data = D.features(
                instruments=instruments,
                fields=base_fields + ["$amount"],
                start_time=self.config.start_time,
                end_time=self.config.end_time,
                freq="day",
            )
            data.columns = ["open", "high", "low", "close", "volume", "vwap", "amount"]
            has_amount = True
        except Exception as exc:
            print(f"⚠️ 无 $amount 字段（{exc}），将以 close*volume 近似")
            data = D.features(
                instruments=instruments,
                fields=base_fields,
                start_time=self.config.start_time,
                end_time=self.config.end_time,
                freq="day",
            )
            data.columns = ["open", "high", "low", "close", "volume", "vwap"]
            data["amount"] = data["close"] * data["volume"]
            has_amount = False

        if data.empty:
            raise ValueError(f"未读取到行情数据: market={self.config.market}")
        data = data.replace([np.inf, -np.inf], np.nan).sort_index()

        # 兼容 QLib 不同版本：MultiIndex 的两级名称未必为 ('instrument', 'datetime')
        index_names = list(data.index.names)
        if "instrument" in index_names:
            inst_level: Any = "instrument"
        elif "code" in index_names:
            inst_level = "code"
        else:
            inst_level = 0  # 默认第一级是 instrument

        # 长表 → 宽表字典 panel
        panel: Dict[str, pd.DataFrame] = {}
        for col in ["open", "high", "low", "close", "volume", "vwap", "amount"]:
            wide = data[col].unstack(inst_level)
            wide.index = pd.to_datetime(wide.index)
            wide = wide.sort_index()
            panel[col] = wide.astype(float)

        # 由 close 派生 returns，供 alpha101 部分因子使用
        panel["returns"] = panel["close"].pct_change(fill_method=None)

        n_days, n_codes = panel["close"].shape
        print(
            f"✅ 行情读取完成: {n_days} 个交易日, {n_codes} 只标的"
            f"（amount={'真实' if has_amount else '近似'}）"
        )
        self.panel = panel

    # ---- 步骤 2.5: 股票池过滤（市值 / 股价） ----
    def _filter_stock_pool(self) -> pd.DataFrame:
        cfg = self.config
        if not (cfg.enable_market_cap_filter or cfg.enable_price_filter):
            print("\n第二点五步：股票池过滤（已全部禁用，跳过）")
            return pd.DataFrame(columns=["step", "kept", "dropped", "examples"])

        print("\n第二点五步：股票池过滤（市值 / 股价）")
        pool_cfg = stock_pool_filter.StockPoolFilterConfig(
            enable_price=cfg.enable_price_filter,
            min_close_price=cfg.min_close_price,
            max_close_price=cfg.max_close_price,
            price_mode=cfg.price_filter_mode,
            enable_market_cap=cfg.enable_market_cap_filter,
            min_market_cap_yi=cfg.min_market_cap_yi,
            max_market_cap_yi=cfg.max_market_cap_yi,
            market_cap_kind=cfg.market_cap_kind,
            cache_max_age_days=cfg.market_cap_cache_max_age_days,
            force_refresh_cache=cfg.force_refresh_market_cap_cache,
        )
        before = self.panel["close"].shape[1]
        self.panel, report = stock_pool_filter.apply(self.panel, pool_cfg)
        after = self.panel["close"].shape[1]
        print(f"✅ 股票池过滤完成: {before} → {after} 只标的")
        return report

    # ---- 步骤 3: 未来收益 ----
    def _build_returns(self) -> None:
        cfg = self.config
        print(
            f"\n第三步：构造未来收益 mode={cfg.future_return_mode}, "
            f"holding_period={cfg.holding_period}"
        )
        self.future_return = return_builder.build_future_return(
            self.panel, cfg.future_return_mode, cfg.holding_period
        )
        # 回测净值用 close-to-close（即使用户选择了 max_* 模式，也强制 close-to-close）
        if cfg.future_return_mode == "holding_close":
            self.holding_return = self.future_return
        else:
            self.holding_return = return_builder.build_holding_period_return(
                self.panel, cfg.holding_period
            )
        print(f"✅ future_return 形状: {self.future_return.shape}")

    # ---- 步骤 4: 因子加载 ----
    def _load_factors(self) -> None:
        cfg = self.config
        print(f"\n第四步：加载因子库 {cfg.factor_libraries}")

        cache_dir: Optional[str] = None
        panel_sig: Optional[str] = None
        legacy_panel_sig: Optional[str] = None
        if cfg.enable_factor_cache:
            cache_path = Path(cfg.factor_cache_dir)
            if not cache_path.is_absolute():
                cache_path = _THIS_DIR / cache_path
            cache_dir = str(cache_path)
            panel_sig = factor_cache.panel_signature(self.panel)
            legacy_panel_sig = factor_cache.legacy_panel_signature(self.panel)
            stats = factor_cache.stats(cache_dir)
            print(
                f"  📦 因子缓存：启用 (dir={cache_dir}, "
                f"已有 {stats['count']} 个文件 / {stats['size_bytes']/1024/1024:.2f} MB, "
                f"panel_sig={panel_sig[:10]})"
            )
        else:
            print("  📦 因子缓存：已禁用")

        self.factor_dict = factor_loader.load_libraries(
            cfg.factor_libraries,
            self.panel,
            cache_dir=cache_dir,
            panel_sig=panel_sig,
            legacy_panel_sig=legacy_panel_sig,
        )
        print(f"✅ 共加载 {len(self.factor_dict)} 个因子")

    # ---- 步骤 5: 横截面去极值与标准化 ----
    @staticmethod
    def _winsorize_zscore(df: pd.DataFrame, limit: float = 5.0) -> pd.DataFrame:
        # 按行（每个交易日横截面）做 MAD 去极值 + Z-Score 标准化
        median = df.median(axis=1)
        mad = (df.sub(median, axis=0)).abs().median(axis=1)
        # MAD=0（稀疏因子或常值横截面）时，上下界=median 会把全部值裁成同一个数，
        # 导致 std=0、标准化结果全 NaN。把 MAD=0 的边界设为 NaN，
        # pandas.clip 对 NaN 边界视为不裁剪，保留原始值进入下游 z-score。
        mad_safe = mad.replace(0.0, np.nan)
        upper = median + limit * 1.4826 * mad_safe
        lower = median - limit * 1.4826 * mad_safe
        clipped = df.clip(lower=lower, upper=upper, axis=0)
        mean = clipped.mean(axis=1)
        std = clipped.std(axis=1).replace(0.0, np.nan)
        return clipped.sub(mean, axis=0).div(std, axis=0)

    def _standardize_factors(self) -> None:
        print("\n第五步：横截面去极值 + Z-Score 标准化")
        self.standardized_factors = {
            name: self._winsorize_zscore(df) for name, df in self.factor_dict.items()
        }
        print(f"✅ 标准化完成: {len(self.standardized_factors)} 个因子")

    # ---- 步骤 6: 单因子评价 ----
    def _evaluate_factors(
        self, upper_bound_date: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """单因子评价。

        Args:
            upper_bound_date: 仅用 ``date <= upper_bound_date`` 的 future_return 来估算
                IC/RankIC/IR/分层收益/相关性。设为 ``None`` 则用全期数据（旧行为）。
                启用此参数等价于"仅用训练期评价因子"，避免下游过滤 / 方向选择
                出现 in-sample look-ahead bias。
        """
        print("\n第六步：单因子评价（IC / RankIC / 分层 / 相关性）")
        future = self.future_return
        if upper_bound_date is not None:
            cutoff = pd.Timestamp(upper_bound_date)
            future = future.loc[future.index <= cutoff]
            if future.empty:
                raise ValueError(
                    f"训练期截断 upper_bound_date={upper_bound_date} 之后 future_return 为空，"
                    "请确认 train_end_time 在 start_time / end_time 之间。"
                )
            print(
                f"  🛡️  训练期评价：仅使用 <= {upper_bound_date} 的数据估算 IC/IR/分层/相关性 "
                f"({len(future)} 个交易日)，避免 look-ahead 偏差"
            )
        else:
            print(
                f"  ⚠️  全样本评价（filter_use_train_only=False）："
                f"使用全部 {len(future)} 个交易日的 future_return，可能引入 in-sample 偏差"
            )
        rows: List[Dict[str, float]] = []
        rank_ic_table = pd.DataFrame(index=future.index)
        quantile_pieces: List[pd.DataFrame] = []
        total = len(self.standardized_factors)

        for idx, (name, factor_df) in enumerate(self.standardized_factors.items(), start=1):
            aligned = factor_df.reindex_like(future)
            # 每日横截面 IC / RankIC
            ic_series = aligned.corrwith(future, axis=1, method="pearson")
            rank_ic_series = aligned.corrwith(future, axis=1, method="spearman")

            ic_mean = float(ic_series.mean())
            ic_std = float(ic_series.std())
            rank_ic_mean = float(rank_ic_series.mean())
            rank_ic_std = float(rank_ic_series.std())

            rows.append(
                {
                    "factor": name,
                    "ic_mean": ic_mean,
                    "ic_std": ic_std,
                    "ic_ir": ic_mean / ic_std if ic_std > 0 else 0.0,
                    "rank_ic_mean": rank_ic_mean,
                    "rank_ic_std": rank_ic_std,
                    "rank_ic_ir": rank_ic_mean / rank_ic_std if rank_ic_std > 0 else 0.0,
                    "ic_win_rate": float((ic_series > 0).mean()),
                }
            )
            rank_ic_table[name] = rank_ic_series
            quantile_pieces.append(self._quantile_returns_vectorized(name, aligned, future))

            if idx == 1 or idx == total or idx % max(total // 10, 1) == 0:
                print(f"  评价进度 {idx}/{total} | rank_ic_ir={rows[-1]['rank_ic_ir']:.3f}", flush=True)

        evaluation = pd.DataFrame(rows).sort_values(
            "rank_ic_ir", key=lambda s: s.abs(), ascending=False, na_position="last"
        ).reset_index(drop=True)
        quantile_returns = pd.concat(quantile_pieces, ignore_index=True) if quantile_pieces else pd.DataFrame(
            columns=["factor", "date", "quantile", "ret"]
        )

        # 因子相关性（按时间-横截面拼接成长向量做相关性）
        print("  计算因子相关性矩阵...", flush=True)
        flat_data = {
            name: df.reindex_like(future).values.ravel()
            for name, df in self.standardized_factors.items()
        }
        flat_df = pd.DataFrame(flat_data)
        correlation = flat_df.corr().fillna(0.0)

        print(f"✅ 评价完成: {len(evaluation)} 个因子")
        return evaluation, rank_ic_table, quantile_returns, correlation

    def _quantile_returns_vectorized(
        self, factor_name: str, factor_df: pd.DataFrame, future: pd.DataFrame
    ) -> pd.DataFrame:
        """向量化的分层收益计算：一次性处理所有日期。"""
        q = max(int(self.config.quantiles), 2)
        ranks = factor_df.rank(axis=1, pct=True)
        # 通过 pd.cut 按行分箱（向量化）
        bins = np.linspace(0.0, 1.0, q + 1)
        labels = [f"Q{i+1}" for i in range(q)]

        # 拉成长表 (date, code, rank, ret)
        rank_long = ranks.stack(dropna=True).rename("rank")
        ret_long = future.reindex_like(factor_df).stack(dropna=True).rename("ret")
        merged = pd.concat([rank_long, ret_long], axis=1, join="inner")
        if merged.empty:
            return pd.DataFrame(columns=["factor", "date", "quantile", "ret"])

        merged["quantile"] = pd.cut(merged["rank"], bins=bins, labels=labels, include_lowest=True)
        merged = merged.dropna(subset=["quantile"])
        if merged.empty:
            return pd.DataFrame(columns=["factor", "date", "quantile", "ret"])
        # 按 (date, quantile) 求平均收益
        date_level = merged.index.get_level_values(0)
        grouped = (
            merged.groupby([date_level, merged["quantile"]], observed=True)["ret"].mean().reset_index()
        )
        grouped.columns = ["date", "quantile", "ret"]
        grouped["factor"] = factor_name
        grouped["quantile"] = grouped["quantile"].astype(str)
        return grouped[["factor", "date", "quantile", "ret"]]

    @staticmethod
    def _mean_rank_corr(left: pd.DataFrame, right: pd.DataFrame) -> float:
        series = left.reindex_like(right).corrwith(right, axis=1, method="spearman")
        return float(series.mean()) if not series.empty else np.nan

    @staticmethod
    def _quantile_monotonicity(values: pd.Series) -> float:
        clean = values.dropna()
        if len(clean) < 2:
            return 0.0
        diffs = clean.diff().dropna()
        if diffs.empty:
            return 0.0
        pos_ratio = float((diffs > 0).mean())
        neg_ratio = float((diffs < 0).mean())
        return max(pos_ratio, neg_ratio)

    @staticmethod
    def _classify_factor_profile(
        ic_future: float,
        ic_past: float,
        ic_risk: float,
        stability: float,
        monotonicity: float,
    ) -> Tuple[str, str]:
        abs_future = abs(ic_future) if np.isfinite(ic_future) else 0.0
        past = ic_past if np.isfinite(ic_past) else 0.0
        risk = ic_risk if np.isfinite(ic_risk) else 0.0
        stable = stability if np.isfinite(stability) else 0.0
        mono = monotonicity if np.isfinite(monotonicity) else 0.0

        if abs_future < 0.005 or stable < 0.45:
            label = "noise_unclear"
            usage = "discard"
        elif ic_future > 0 and past > 0:
            label = "trend"
            usage = "alpha_core"
        elif ic_future > 0 and past < 0:
            label = "reversal"
            usage = "conditional_alpha"
        elif ic_future < 0 and past > 0:
            label = "overheat_risk"
            usage = "risk_filter"
        elif ic_future < 0 and past < 0:
            label = "negative_trend"
            usage = "risk_filter"
        else:
            label = "noise_unclear"
            usage = "discard"

        if risk > 0.05 and abs_future < 0.02:
            label = "risk"
            usage = "risk_filter"
        if mono < 0.5 and usage == "alpha_core":
            usage = "conditional_alpha"
        return label, usage

    def _profile_factors(
        self,
        evaluation: pd.DataFrame,
        rank_ic: pd.DataFrame,
        quantile_returns: pd.DataFrame,
        upper_bound_date: Optional[str] = None,
    ) -> pd.DataFrame:
        if not bool(getattr(self.config, "enable_factor_profile", True)):
            print("\n第六点五步：因子画像分类（已禁用）")
            return pd.DataFrame()
        if self.future_return is None or "close" not in self.panel:
            return pd.DataFrame()

        print("\n第六点五步：因子画像分类（趋势 / 反转 / 风险）")
        close = self.panel["close"].copy()
        target_future = self.future_return
        if upper_bound_date is not None:
            cutoff = pd.Timestamp(upper_bound_date)
            close = close.loc[close.index <= cutoff]
            target_future = target_future.loc[target_future.index <= cutoff]
            print(f"  🛡️  因子画像仅使用 <= {upper_bound_date} 的训练期样本")

        windows = sorted({int(w) for w in getattr(self.config, "factor_profile_past_windows", [1, 3, 5, 10]) if int(w) > 0})
        if not windows:
            windows = [1, 3, 5, 10]
        main_past_window = 5 if 5 in windows else windows[min(len(windows) - 1, 0)]
        future_window = max(int(getattr(self.config, "factor_profile_future_window", 3)), 1)

        past_returns = {w: close / close.shift(w) - 1.0 for w in windows}
        next_daily = [close.shift(-i) / close.shift(-(i - 1)) - 1.0 for i in range(1, future_window + 1)]
        future_volatility = pd.concat(next_daily).groupby(level=0).std() if next_daily else pd.DataFrame()
        future_path = [close.shift(-i) / close - 1.0 for i in range(1, future_window + 1)]
        future_min_return = pd.concat(future_path).groupby(level=0).min() if future_path else pd.DataFrame()
        future_drawdown = -future_min_return

        eval_map = evaluation.set_index("factor") if "factor" in evaluation.columns else pd.DataFrame()
        quantile_map: Dict[str, Tuple[float, float]] = {}
        if not quantile_returns.empty:
            for factor_name, sub in quantile_returns.groupby("factor"):
                mean_by_q = sub.groupby("quantile")["ret"].mean()
                ordered = mean_by_q.reindex(sorted(mean_by_q.index))
                top_bottom = float(ordered.iloc[-1] - ordered.iloc[0]) if len(ordered) >= 2 else np.nan
                quantile_map[str(factor_name)] = (top_bottom, self._quantile_monotonicity(ordered))

        rows: List[Dict[str, Any]] = []
        for factor_name, factor_df in self.standardized_factors.items():
            factor_for_profile = factor_df.reindex(index=target_future.index, columns=target_future.columns)
            ic_future = float(eval_map.loc[factor_name, "rank_ic_mean"]) if factor_name in eval_map.index else np.nan
            ic_series = rank_ic[factor_name].dropna() if factor_name in rank_ic.columns else pd.Series(dtype=float)
            direction = np.sign(ic_future) if np.isfinite(ic_future) and ic_future != 0 else 1.0
            stability = float((ic_series * direction > 0).mean()) if not ic_series.empty else np.nan

            past_metrics = {
                f"ic_past_{w}d": self._mean_rank_corr(
                    factor_for_profile, past_returns[w].reindex_like(target_future)
                )
                for w in windows
            }
            ic_past = past_metrics.get(f"ic_past_{main_past_window}d", np.nan)
            ic_future_vol = self._mean_rank_corr(
                factor_for_profile, future_volatility.reindex_like(target_future)
            )
            ic_future_drawdown = self._mean_rank_corr(
                factor_for_profile, future_drawdown.reindex_like(target_future)
            )
            ic_risk = float(np.nanmean([ic_future_vol, ic_future_drawdown]))
            top_bottom, monotonicity = quantile_map.get(factor_name, (np.nan, np.nan))
            label, usage = self._classify_factor_profile(
                ic_future, ic_past, ic_risk, stability, monotonicity
            )

            row: Dict[str, Any] = {
                "factor": factor_name,
                "auto_label": label,
                "usage": usage,
                "ic_future": ic_future,
                "ic_stability": stability,
                "ic_future_vol": ic_future_vol,
                "ic_future_drawdown": ic_future_drawdown,
                "ic_risk": ic_risk,
                "top_bottom_spread": top_bottom,
                "monotonicity": monotonicity,
            }
            row.update(past_metrics)
            rows.append(row)

        profile = pd.DataFrame(rows)
        if profile.empty:
            return profile
        order_cols = [
            "factor", "auto_label", "usage", "ic_future", f"ic_past_{main_past_window}d",
            "ic_risk", "ic_stability", "monotonicity", "top_bottom_spread",
            "ic_future_vol", "ic_future_drawdown",
        ]
        order_cols += [c for c in profile.columns if c.startswith("ic_past_") and c not in order_cols]
        profile = profile[[c for c in order_cols if c in profile.columns]]
        profile = profile.sort_values(
            ["usage", "auto_label", "ic_stability", "ic_future"],
            ascending=[True, True, False, False],
            na_position="last",
        ).reset_index(drop=True)
        label_counts = profile["auto_label"].value_counts().to_dict()
        usage_counts = profile["usage"].value_counts().to_dict()
        print(f"✅ 因子画像完成: label={label_counts}, usage={usage_counts}")
        return profile

    # ---- 步骤 7: 因子过滤 ----
    def _filter_factors(
        self, evaluation: pd.DataFrame, correlation: pd.DataFrame
    ) -> Tuple[List[str], pd.DataFrame]:
        cfg = self.config
        print(f"\n第七步：因子过滤 method={cfg.filter_method}")
        selected, report = factor_filter.apply(
            cfg.filter_method,
            evaluation,
            correlation=correlation,
            rank_ic_min=cfg.filter_rank_ic_min,
            rank_ic_ir_min=cfg.filter_rank_ic_ir_min,
            corr_max=cfg.filter_corr_max,
            topk=cfg.filter_topk,
        )
        return selected, report

    # ---- 步骤 8: 信号构造 ----
    def _build_signals(
        self, selected: List[str], evaluation: pd.DataFrame
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        cfg = self.config
        print(f"\n第八步：构造信号 mode={cfg.signal_mode}")
        if cfg.signal_mode == "traditional":
            signals = self._traditional_signals(selected, evaluation)
            return signals, {"mode": "traditional", "n_factors": len(selected)}
        if cfg.signal_mode == "ml":
            return self._ml_signals(selected)
        if cfg.signal_mode == "all":
            signals = self._traditional_signals(selected, evaluation)
            ml_signals, ml_info = self._ml_signals(selected)
            signals.update(ml_signals)
            return signals, {"mode": "all", "n_factors": len(selected), "ml": ml_info}
        raise ValueError(f"未知的 signal_mode: {cfg.signal_mode}")

    def _traditional_signals(
        self, selected: List[str], evaluation: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """构造传统打分信号。

        旧实现的致命缺陷是：用全样本（含未来）future_return 估算每个因子的 IC 符号
        来翻转因子方向，再用全样本 IR 加权——这会使样本内表现被严重高估
        （典型现象：score_ic_weighted 年化 100%+、Sharpe 12+）。

        现在支持三种方向 / 权重估计模式（由 ``config.direction_method`` 控制）：

        - ``train_only``：方向 / IR 权重 = 用 ``<= train_end_time`` 的数据估算（默认）。
          整段时间使用同一组 multiplier，干净简单。
        - ``rolling``：方向 / 权重时变。每个交易日 ``T`` 用 ``[T-window, T-1]`` 的滚动
          RankIC 决定 ``T`` 日因子方向，``shift(1)`` 严格避免泄漏当天。
        - ``full_sample``：保留旧行为，用全期 IC 估算（已知 look-ahead，仅用于对照）。

        ``score_rule_based`` 改成基于横截面 ``rank``（pct - 0.5）的等权信号，
        与 z-score 等权（``score_equal_weight``）形成对照，对极值更鲁棒。
        """
        from functools import reduce

        method = str(getattr(self.config, "direction_method", "train_only") or "train_only").lower()
        if method not in ("train_only", "rolling", "full_sample"):
            print(f"  ⚠️ 未知 direction_method={method!r}，回退为 train_only")
            method = "train_only"
        print(f"  🛡️  传统信号方向估计模式: {method}")

        # 评价基准：用持有期 close-to-close 的真实回报（与回测口径一致）
        target_full = self.holding_return if self.holding_return is not None else self.future_return

        if method == "rolling":
            return self._traditional_signals_rolling(selected, target_full)

        # ---- train_only / full_sample：估算一组静态 multiplier ----
        if method == "train_only":
            train_end = self.config.train_end_time
            if not train_end:
                print("  ⚠️ direction_method=train_only 但未配置 train_end_time，回退为 full_sample")
                target_for_dir = target_full
                effective_method = "full_sample(fallback)"
            else:
                cutoff = pd.Timestamp(train_end)
                target_for_dir = target_full.loc[target_full.index <= cutoff]
                if target_for_dir.empty:
                    raise ValueError(
                        f"direction_method=train_only 时，<= {train_end} 没有数据，无法估计因子方向"
                    )
                effective_method = "train_only"
                print(
                    f"  🛡️  方向估计仅用 <= {train_end} 的 {len(target_for_dir)} 个交易日 "
                    f"(共 {len(target_full)} 天)"
                )
        else:
            target_for_dir = target_full
            effective_method = "full_sample"
            print(f"  ⚠️  full_sample 模式：方向用全期估计，存在 look-ahead，仅供对照！")

        direction_rows: List[Dict[str, float]] = []
        for name in selected:
            aligned = self.standardized_factors[name].reindex_like(target_for_dir)
            rank_ic_series = aligned.corrwith(target_for_dir, axis=1, method="spearman")
            rank_ic_mean = float(rank_ic_series.mean())
            rank_ic_std = float(rank_ic_series.std())
            direction_rows.append(
                {
                    "factor": name,
                    "rank_ic_mean": rank_ic_mean,
                    "rank_ic_ir": rank_ic_mean / rank_ic_std if rank_ic_std > 0 else 0.0,
                }
            )
        direction_eval = pd.DataFrame(direction_rows).set_index("factor")
        rank_ic_mean_map = direction_eval["rank_ic_mean"].to_dict()
        ir_map = direction_eval["rank_ic_ir"].to_dict()
        higher_is_better = {
            n: float(np.sign(rank_ic_mean_map.get(n, 0.0)) or np.sign(ir_map.get(n, 0.0)) or 1.0) > 0
            for n in selected
        }
        direction_multiplier = {n: 1.0 if higher_is_better[n] else -1.0 for n in selected}

        # 因子 z-score 等权累加
        frames = [self.standardized_factors[n] * direction_multiplier[n] for n in selected]
        equal_weight = reduce(lambda a, b: a.add(b, fill_value=0.0), frames) / float(len(selected))

        # 因子 z-score 按 |IR| 加权累加（IR 已仅用训练期估计）
        weights = {n: abs(float(ir_map.get(n, 0.0))) for n in selected}
        total_abs = sum(abs(w) for w in weights.values())
        if total_abs <= 1e-12:
            ic_weighted = equal_weight.copy()
        else:
            weighted_frames = [
                self.standardized_factors[n] * direction_multiplier[n] * (weights[n] / total_abs)
                for n in selected
            ]
            ic_weighted = reduce(lambda a, b: a.add(b, fill_value=0.0), weighted_frames)

        # 横截面 rank 等权（每日把每个因子转成 [-0.5, 0.5] 的 rank-pct，再累加）
        # 与 z-score 等权形成对照：对异常值更鲁棒，避免单个因子极值主导
        rank_frames = [
            self.standardized_factors[n].rank(axis=1, pct=True).sub(0.5) * direction_multiplier[n]
            for n in selected
        ]
        rule_based = reduce(lambda a, b: a.add(b, fill_value=0.0), rank_frames) / float(len(selected))

        n_pos = sum(1 for v in direction_multiplier.values() if v > 0)
        n_neg = len(direction_multiplier) - n_pos
        print(
            f"  ✅ 静态方向估计完成 ({effective_method}): "
            f"正向因子 {n_pos} 个, 反向因子 {n_neg} 个"
        )

        return {
            "score_equal_weight": equal_weight,
            "score_ic_weighted": ic_weighted,
            "score_rule_based": rule_based,
        }

    def _traditional_signals_rolling(
        self, selected: List[str], target_full: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """rolling 模式：每个交易日 T 的方向 / 权重 = 用 [T-window, T-1] 的 RankIC 估计。

        ``shift(1)`` 严格保证 T 日只用截止 T-1 的信息，不存在 look-ahead。
        早期窗口不足的天数（前 ``window`` 个交易日）会被 NaN 掩盖、不参与组合。
        """
        from functools import reduce

        window = max(int(getattr(self.config, "rolling_ic_window", 60) or 60), 5)
        print(f"  🔁 rolling 方向估计：window={window} 个交易日，shift(1) 防泄漏")

        # 1. 每个因子的逐日 RankIC（用整段 future_return）
        daily_rank_ic: Dict[str, pd.Series] = {}
        for name in selected:
            aligned = self.standardized_factors[name].reindex_like(target_full)
            daily_rank_ic[name] = aligned.corrwith(target_full, axis=1, method="spearman")

        rank_ic_df = pd.DataFrame(daily_rank_ic)  # index=date, columns=factor

        # 2. 滚动 RankIC 均值 / 标准差 → 方向 sign 与 IR；shift(1) 保证 T 日不看 T 日的 IC
        rolling_mean = rank_ic_df.rolling(window, min_periods=max(window // 3, 5)).mean().shift(1)
        rolling_std = rank_ic_df.rolling(window, min_periods=max(window // 3, 5)).std().shift(1)
        rolling_ir = rolling_mean.divide(rolling_std.replace(0.0, np.nan))
        # 方向 multiplier ∈ {-1, +1}：sign(rolling_mean)，NaN（窗口未填满）→ 0 不参与
        direction_series = np.sign(rolling_mean.fillna(0.0)).astype(float)
        # |rolling_ir| 作为加权权重，NaN → 0
        weight_series = rolling_ir.abs().fillna(0.0)

        # 3. 组装信号：每个因子的标准化值 * direction_series[T]，然后累加
        equal_frames: List[pd.DataFrame] = []
        rank_frames: List[pd.DataFrame] = []
        ic_weighted_num: Optional[pd.DataFrame] = None  # 分子 sum(z * dir * |IR|)
        ic_weighted_den: Optional[pd.DataFrame] = None  # 分母 sum(|IR|)
        for name in selected:
            z = self.standardized_factors[name]
            dir_col = direction_series[name].reindex(z.index).fillna(0.0)
            w_col = weight_series[name].reindex(z.index).fillna(0.0)
            # 用列向量广播：每行（每天）乘以一个标量方向 / 权重
            z_dir = z.mul(dir_col, axis=0)
            r_dir = z.rank(axis=1, pct=True).sub(0.5).mul(dir_col, axis=0)
            equal_frames.append(z_dir)
            rank_frames.append(r_dir)
            # ic_weighted 数值化：weighted = z_dir * w_col (= z * dir * |IR|)
            weighted = z_dir.mul(w_col, axis=0)
            # 分母：跟随因子是否非空 + 权重；用 z 是否 NaN 作为参与标记
            den_mask = z.notna().mul(w_col, axis=0)
            if ic_weighted_num is None:
                ic_weighted_num = weighted
                ic_weighted_den = den_mask
            else:
                ic_weighted_num = ic_weighted_num.add(weighted, fill_value=0.0)
                ic_weighted_den = ic_weighted_den.add(den_mask, fill_value=0.0)

        equal_weight = reduce(lambda a, b: a.add(b, fill_value=0.0), equal_frames) / float(len(selected))
        rule_based = reduce(lambda a, b: a.add(b, fill_value=0.0), rank_frames) / float(len(selected))
        if ic_weighted_num is None or ic_weighted_den is None:
            ic_weighted = equal_weight.copy()
        else:
            ic_weighted = ic_weighted_num.divide(ic_weighted_den.replace(0.0, np.nan))

        # rolling 模式下早期窗口未填满的日期 multiplier=0，会让信号全为 0；mask 成 NaN
        warmup_mask = direction_series.eq(0.0).all(axis=1)
        if warmup_mask.any():
            equal_weight.loc[warmup_mask] = np.nan
            ic_weighted.loc[warmup_mask] = np.nan
            rule_based.loc[warmup_mask] = np.nan
            print(
                f"  🛡️  rolling 预热期 {int(warmup_mask.sum())} 天信号 mask 为 NaN（不参与回测）"
            )
        return {
            "score_equal_weight": equal_weight,
            "score_ic_weighted": ic_weighted,
            "score_rule_based": rule_based,
        }

    def _ml_signal(self, selected: List[str]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        # 拼成长表：MultiIndex(datetime, instrument)，列= factor1..K + future_return
        long_data: Dict[str, pd.Series] = {}
        for name in selected:
            stacked = self.standardized_factors[name].stack(dropna=False)
            stacked = stacked.rename_axis(["datetime", "instrument"])
            long_data[name] = stacked
        future_long = self.future_return.stack(dropna=False).rename_axis(["datetime", "instrument"])
        future_long.name = "future_return"
        df = pd.DataFrame(long_data)
        df = df.join(future_long, how="inner")

        cfg = self.config
        feature_cols = list(selected)
        try:
            if feature_cols:
                non_null_ratio_all = (1.0 - df[feature_cols].isna().mean()).replace([np.inf, -np.inf], np.nan)
                threshold = float(getattr(cfg, "ml_min_non_null_ratio", 0.0) or 0.0)
                kept = non_null_ratio_all[non_null_ratio_all >= threshold].index.tolist()
                removed = [c for c in feature_cols if c not in set(kept)]
                feature_cols = kept
                if removed:
                    print(
                        f"  🧹 ML特征过滤: 阈值={threshold:.2f}, 保留={len(kept)}/{len(selected)}, 剔除={len(removed)}"
                    )
                    for name in removed[:20]:
                        r = float(non_null_ratio_all.get(name, np.nan))
                        if np.isnan(r):
                            continue
                        print(f"     - {name}: {r*100:.2f}%")
                if not feature_cols:
                    raise ValueError(f"ML 特征过滤后剩余 0 个因子（阈值={threshold}），请降低阈值或检查因子覆盖度")
        except Exception as exc:
            print(f"  ⚠️ ML特征过滤失败，将使用全部因子: {exc}")
            feature_cols = list(selected)

        try:
            total_rows = int(len(df))
            label_non_null = int(df["future_return"].notna().sum())
            label_ratio = (label_non_null / total_rows) if total_rows > 0 else 0.0
            print(
                f"  🧪 ML数据诊断: 总行数={total_rows}, future_return非空={label_non_null} ({label_ratio*100:.2f}%)"
            )
            non_null_ratio = (1.0 - df[feature_cols].isna().mean()).replace([np.inf, -np.inf], np.nan)
            worst = non_null_ratio.sort_values().head(8)
            best = non_null_ratio.sort_values(ascending=False).head(8)
            print("  🧪 因子非空比例 最低Top8:")
            for k, v in worst.items():
                print(f"     - {k}: {float(v)*100:.2f}%")
            print("  🧪 因子非空比例 最高Top8:")
            for k, v in best.items():
                print(f"     - {k}: {float(v)*100:.2f}%")

            dates = pd.to_datetime(df.index.get_level_values("datetime"))
            train_mask = dates <= pd.Timestamp(cfg.train_end_time)
            valid_mask = (dates > pd.Timestamp(cfg.train_end_time)) & (dates <= pd.Timestamp(cfg.valid_end_time))
            test_mask = dates >= pd.Timestamp(cfg.test_start_time)
            train_label = int(df.loc[train_mask, "future_return"].notna().sum())
            valid_label = int(df.loc[valid_mask, "future_return"].notna().sum())
            test_label = int(df.loc[test_mask, "future_return"].notna().sum())
            print(
                "  🧪 标签非空行数(按时间切分): "
                f"train={train_label}, valid={valid_label}, test={test_label}"
            )
        except Exception as exc:
            print(f"  ⚠️ ML数据诊断失败: {exc}")

        model = cfg.ml_model[0] if isinstance(cfg.ml_model, list) else cfg.ml_model

        if bool(getattr(cfg, "walk_forward_enable", False)):
            step_days = max(int(getattr(cfg, "walk_forward_step_days", 30) or 30), 1)
            n_windows = max(int(getattr(cfg, "walk_forward_n_windows", 5) or 5), 1)
            train_days = max(int(getattr(cfg, "walk_forward_train_days", 730) or 730), 30)
            valid_days = max(int(getattr(cfg, "walk_forward_valid_days", 90) or 90), 10)

            base_test_start = pd.Timestamp(cfg.test_start_time)
            global_end = pd.Timestamp(cfg.end_time)
            try:
                data_min_date = pd.to_datetime(df.index.get_level_values("datetime")).min().normalize()
            except Exception:
                data_min_date = None

            combined_wide: Optional[pd.DataFrame] = None
            wf_windows: List[Dict[str, Any]] = []
            last_info: Dict[str, Any] = {}
            print(
                "  🔁 Walk-Forward: "
                f"n_windows={n_windows}, step_days={step_days}, train_days={train_days}, valid_days={valid_days}"
            )

            for i in range(n_windows):
                win_test_start = base_test_start + pd.Timedelta(days=i * step_days)
                if win_test_start > global_end:
                    break
                win_test_end = min(global_end, win_test_start + pd.Timedelta(days=step_days - 1))
                win_valid_end = win_test_start - pd.Timedelta(days=1)
                win_train_end = win_valid_end - pd.Timedelta(days=valid_days)
                win_train_start = win_train_end - pd.Timedelta(days=train_days)
                if data_min_date is not None and win_train_start < data_min_date:
                    win_train_start = data_min_date

                ml_config = MLConfig(
                    model=model,
                    train_end=str(win_train_end.date()),
                    valid_end=str(win_valid_end.date()),
                    test_start=str(win_test_start.date()),
                )
                print(
                    f"  🔁 WF窗口{i+1}: train~{win_train_start.date()}..{win_train_end.date()} "
                    f"valid~{(win_train_end + pd.Timedelta(days=1)).date()}..{win_valid_end.date()} "
                    f"test~{win_test_start.date()}..{win_test_end.date()}"
                )
                prediction, info = train_predict(df, feature_cols, "future_return", ml_config)
                last_info = info
                wide = prediction.unstack("instrument").sort_index()
                wide.index = pd.to_datetime(wide.index)
                wide = wide.loc[(wide.index >= win_test_start) & (wide.index <= win_test_end)]

                if combined_wide is None:
                    combined_wide = wide.copy()
                else:
                    combined_wide = pd.concat([combined_wide, wide], axis=0)

                wf_windows.append(
                    {
                        "window": int(i + 1),
                        "train_start": str(win_train_start.date()),
                        "train_end": str(win_train_end.date()),
                        "valid_end": str(win_valid_end.date()),
                        "test_start": str(win_test_start.date()),
                        "test_end": str(win_test_end.date()),
                        "data_min_date": str(data_min_date.date()) if data_min_date is not None else None,
                        "n_train": int(info.get("n_train", 0)),
                        "n_valid": int(info.get("n_valid", 0)),
                        "n_test": int(info.get("n_test", 0)),
                    }
                )

            if combined_wide is None or combined_wide.empty:
                raise ValueError("Walk-Forward 未生成任何测试期预测，请检查 test_start_time 与 end_time")
            combined_wide = combined_wide.sort_index().loc[~combined_wide.index.duplicated(keep="first")]

            last_info["walk_forward"] = {
                "enabled": True,
                "n_windows": int(len(wf_windows)),
                "step_days": int(step_days),
                "train_days": int(train_days),
                "valid_days": int(valid_days),
                "windows": wf_windows,
            }
            last_info["n_features_after_filter"] = int(len(feature_cols))
            last_info["min_non_null_ratio"] = float(getattr(cfg, "ml_min_non_null_ratio", 0.0) or 0.0)
            return combined_wide, last_info

        ml_config = MLConfig(
            model=model,
            train_end=cfg.train_end_time,
            valid_end=cfg.valid_end_time,
            test_start=cfg.test_start_time,
        )
        prediction, info = train_predict(df, feature_cols, "future_return", ml_config)
        info["n_features_after_filter"] = int(len(feature_cols))
        info["min_non_null_ratio"] = float(getattr(cfg, "ml_min_non_null_ratio", 0.0) or 0.0)

        # 转为宽表 (date x instrument)
        wide = prediction.unstack("instrument").sort_index()
        wide.index = pd.to_datetime(wide.index)
        return wide, info

    def _ml_signals(self, selected: List[str]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
        models = self.config.ml_model
        if isinstance(models, str):
            models = [models]
        models = [str(model).strip() for model in models if str(model).strip()]
        if not models:
            raise ValueError("至少选择一个 ml_model")

        original_model = self.config.ml_model
        signals: Dict[str, pd.DataFrame] = {}
        model_info: Dict[str, Any] = {}
        try:
            for model in models:
                print(f"  🤖 训练 ML 模型: {model}")
                self.config.ml_model = [model]
                score, info = self._ml_signal(selected)
                signals[f"score_ml_{model}"] = score
                model_info[model] = info
        finally:
            self.config.ml_model = original_model
        return signals, {"mode": "ml", "models": models, "by_model": model_info}

    # ---- 步骤 9: 基准 ----
    def _load_benchmark_returns(self) -> pd.Series:
        try:
            data = D.features(
                instruments=[self.config.benchmark],
                fields=["$close"],
                start_time=self.config.start_time,
                end_time=self.config.end_time,
                freq="day",
            )
            data.columns = ["close"]
            index_names = list(data.index.names)
            if "instrument" in index_names:
                inst_level: Any = "instrument"
            elif "code" in index_names:
                inst_level = "code"
            else:
                inst_level = 0
            wide = data["close"].unstack(inst_level).sort_index()
            close = wide.iloc[:, 0]  # 只有一只基准
            close.index = pd.to_datetime(close.index)
            return close.pct_change().fillna(0.0)
        except Exception as exc:
            print(f"⚠️ 基准 {self.config.benchmark} 读取失败 ({exc})，将使用 0 收益基准")
            idx = self.holding_return.index if self.holding_return is not None else self.future_return.index
            return pd.Series(0.0, index=idx)

    # ---- 步骤 10: 回测 ----
    def _run_backtests(
        self, signals: Dict[str, pd.DataFrame], benchmark: pd.Series
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        cfg = self.config
        # 防未来函数：默认仅在 test_start_time 之后统计净值与 performance，
        # 与 ML 信号的 OOS 期保持一致，避免传统信号被"训练期"高表现拖出虚高均值。
        test_start: Optional[pd.Timestamp] = None
        if bool(getattr(cfg, "backtest_test_period_only", True)) and cfg.test_start_time:
            try:
                test_start = pd.Timestamp(cfg.test_start_time)
            except Exception:
                test_start = None

        if test_start is not None:
            print(
                f"\n第十步：TopN={cfg.topn} 回测（OOS 模式：仅统计 >= {test_start.date()} 的净值）"
            )
            bm_for_perf = benchmark.loc[benchmark.index >= test_start] if not benchmark.empty else benchmark
        else:
            print(f"\n第十步：TopN={cfg.topn} 回测（全期模式：包含训练期，绩效可能偏高）")
            bm_for_perf = benchmark

        records: Dict[str, pd.Series] = {"benchmark": bm_for_perf}
        perf_rows: List[Dict[str, Any]] = []

        for sig_name, score_df in signals.items():
            daily_ret = self._topn_daily_returns(score_df)
            if test_start is not None and not daily_ret.empty:
                daily_ret = daily_ret.loc[daily_ret.index >= test_start]
            records[sig_name] = daily_ret
            perf_rows.append(self._summarize_performance(sig_name, daily_ret, bm_for_perf))

        # 对齐索引
        backtest = pd.DataFrame(records).sort_index()
        backtest = backtest.reindex(backtest.index.dropna())
        backtest = backtest.dropna(how="all")
        performance = pd.DataFrame(perf_rows)
        return backtest, performance

    def _topn_daily_returns(self, score_df: pd.DataFrame) -> pd.Series:
        topn = max(int(self.config.topn), 1)
        period = max(int(self.config.holding_period), 1)
        future_ret = self.holding_return  # close-to-close 持有期收益
        # 每隔 period 天调仓一次：T 选股，T+period 兑现持有期收益
        common_index = score_df.index.intersection(future_ret.index)
        score_df = score_df.loc[common_index].sort_index()
        future_ret = future_ret.loc[common_index].sort_index()

        rebalance_dates = score_df.index[::period]
        per_period_returns: List[Tuple[pd.Timestamp, float]] = []
        for date in rebalance_dates:
            scores = score_df.loc[date].dropna()
            if scores.empty:
                continue
            top_codes = scores.sort_values(ascending=False).head(topn).index
            future_row = future_ret.loc[date]
            ret_value = float(future_row.reindex(top_codes).mean())
            if not np.isnan(ret_value):
                per_period_returns.append((date, ret_value))

        if not per_period_returns:
            return pd.Series(dtype=float)

        # 把 N 天持有期收益均分到这 N 天上，便于和 benchmark 日度对齐画图
        result = pd.Series(0.0, index=common_index, dtype=float)
        for i, (date, total_ret) in enumerate(per_period_returns):
            try:
                start_pos = common_index.get_loc(date)
            except KeyError:
                continue
            end_pos = min(start_pos + period, len(common_index))
            if end_pos <= start_pos:
                continue
            daily_ret = (1.0 + total_ret) ** (1.0 / (end_pos - start_pos)) - 1.0
            result.iloc[start_pos:end_pos] = daily_ret
        return result

    @staticmethod
    def _summarize_performance(
        name: str, daily_ret: pd.Series, benchmark: pd.Series
    ) -> Dict[str, Any]:
        if daily_ret.empty:
            return {"signal": name, "annual_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0,
                    "excess_return": 0.0, "ic_periods": 0}
        cumulative = (1.0 + daily_ret).cumprod()
        ann_ret = cumulative.iloc[-1] ** (252.0 / max(len(daily_ret), 1)) - 1.0
        std = daily_ret.std()
        sharpe = (daily_ret.mean() / std * np.sqrt(252.0)) if std > 0 else 0.0
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        max_dd = float(drawdown.min())
        common = daily_ret.index.intersection(benchmark.index)
        if len(common) > 0:
            excess = (daily_ret.loc[common] - benchmark.loc[common]).mean() * 252.0
        else:
            excess = 0.0
        return {
            "signal": name,
            "annual_return": float(ann_ret),
            "sharpe": float(sharpe),
            "max_drawdown": max_dd,
            "excess_return": float(excess),
            "ic_periods": int(len(daily_ret)),
        }

    # ---- 步骤 11: 保存 / 画图 ----
    def _save_results(self, results: Dict[str, Any]) -> None:
        out = self.output_dir
        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        results["factor_evaluation"].to_csv(out / f"factor_evaluation_{ts}.csv", index=False, encoding="utf-8-sig")
        if not results.get("factor_profile", pd.DataFrame()).empty:
            results["factor_profile"].to_csv(out / f"factor_profile_{ts}.csv", index=False, encoding="utf-8-sig")
        results["filter_report"].to_csv(out / f"filter_report_{ts}.csv", index=False, encoding="utf-8-sig")
        results["stock_pool_report"].to_csv(out / f"stock_pool_report_{ts}.csv", index=False, encoding="utf-8-sig")
        results["correlation"].to_csv(out / f"correlation_{ts}.csv", encoding="utf-8-sig")
        results["rank_ic"].to_csv(out / f"rank_ic_{ts}.csv", encoding="utf-8-sig")
        results["quantile_returns"].to_csv(out / f"quantile_returns_{ts}.csv", index=False, encoding="utf-8-sig")
        results["backtest"].to_csv(out / f"backtest_returns_{ts}.csv", encoding="utf-8-sig")
        results["performance"].to_csv(out / f"performance_{ts}.csv", index=False, encoding="utf-8-sig")
        with open(out / f"selected_factors_{ts}.json", "w", encoding="utf-8") as fp:
            json.dump(results["selected_factors"], fp, ensure_ascii=False, indent=2)
        with open(out / f"ml_info_{ts}.json", "w", encoding="utf-8") as fp:
            json.dump({k: v for k, v in results["ml_info"].items() if k != "feature_columns"},
                      fp, ensure_ascii=False, indent=2, default=str)

    def _plot_results(
        self,
        rank_ic: pd.DataFrame,
        quantile_returns: pd.DataFrame,
        backtest: pd.DataFrame,
    ) -> None:
        out = self.output_dir
        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

        # 累计净值
        if not backtest.empty:
            fig, ax = plt.subplots(figsize=(11, 6))
            cumulative = (1.0 + backtest.fillna(0.0)).cumprod()
            for col in cumulative.columns:
                ax.plot(cumulative.index, cumulative[col], label=col, linewidth=1.5)
            ax.set_title("Strategy Cumulative Return")
            ax.set_xlabel("Date")
            ax.set_ylabel("Cumulative Return (1.0 = start)")
            ax.legend(loc="best", fontsize=9)
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            fig.savefig(out / f"cumulative_return_{ts}.png", dpi=120)
            plt.close(fig)

        # RankIC 时序（取前 5 个因子）
        if not rank_ic.empty:
            top_cols = rank_ic.abs().mean().sort_values(ascending=False).head(5).index
            fig, ax = plt.subplots(figsize=(11, 5))
            for col in top_cols:
                ax.plot(rank_ic.index, rank_ic[col].rolling(self.config.ic_window).mean(),
                        label=str(col), linewidth=1.0)
            ax.set_title(f"Rolling Rank IC (window={self.config.ic_window})")
            ax.axhline(0.0, color="grey", linewidth=0.8)
            ax.legend(loc="best", fontsize=8)
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            fig.savefig(out / f"rank_ic_rolling_{ts}.png", dpi=120)
            plt.close(fig)

        # 分层收益（取最强因子）
        if not quantile_returns.empty:
            best_factor = quantile_returns.groupby("factor")["ret"].mean().abs().idxmax()
            sub = quantile_returns[quantile_returns["factor"] == best_factor]
            mean_by_q = sub.groupby("quantile")["ret"].mean().reindex(sorted(sub["quantile"].unique()))
            fig, ax = plt.subplots(figsize=(8, 5))
            mean_by_q.plot(kind="bar", ax=ax, color="steelblue")
            ax.set_title(f"Quantile Returns of Best Factor: {best_factor}")
            ax.set_xlabel("Quantile")
            ax.set_ylabel("Average Future Return")
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            fig.savefig(out / f"quantile_returns_{ts}.png", dpi=120)
            plt.close(fig)


# ============================================================================
# Flask Web 控制台
# ============================================================================


_RUN_STATE: Dict[str, Any] = {
    "running": False,
    "logs": [],
    "last_results": None,
    "error": None,
    "start_time": None,
    "end_time": None,
}
_RUN_LOCK = threading.Lock()


def _append_log(msg: str) -> None:
    with _RUN_LOCK:
        _RUN_STATE["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        if len(_RUN_STATE["logs"]) > 2000:
            _RUN_STATE["logs"] = _RUN_STATE["logs"][-1000:]


class _StreamToLog:
    def __init__(self, original):
        self.original = original

    def write(self, text: str) -> None:
        try:
            self.original.write(text)
        except Exception:
            pass
        if text and text.strip():
            for line in text.rstrip().splitlines():
                _append_log(line)

    def flush(self) -> None:
        try:
            self.original.flush()
        except Exception:
            pass


def _run_workflow_background(config: WorkflowConfigV2) -> None:
    with _RUN_LOCK:
        _RUN_STATE["running"] = True
        _RUN_STATE["logs"] = []
        _RUN_STATE["last_results"] = None
        _RUN_STATE["error"] = None
        _RUN_STATE["start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _RUN_STATE["end_time"] = None

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = _StreamToLog(original_stdout)
    sys.stderr = _StreamToLog(original_stderr)
    try:
        save_config(config)
        wf = WorkflowV2(config)
        results = wf.run()
        factor_profile = results.get("factor_profile", pd.DataFrame())
        profile_summary = {}
        if isinstance(factor_profile, pd.DataFrame) and not factor_profile.empty:
            profile_summary = {
                "label_counts": factor_profile["auto_label"].value_counts().to_dict()
                if "auto_label" in factor_profile.columns else {},
                "usage_counts": factor_profile["usage"].value_counts().to_dict()
                if "usage" in factor_profile.columns else {},
            }
        with _RUN_LOCK:
            _RUN_STATE["last_results"] = {
                "performance": results["performance"].to_dict(orient="records"),
                "factor_evaluation_head": results["factor_evaluation"].head(20).to_dict(orient="records"),
                "factor_profile_head": factor_profile.head(30).to_dict(orient="records")
                if isinstance(factor_profile, pd.DataFrame) and not factor_profile.empty else [],
                "factor_profile_summary": profile_summary,
                "selected_factors": results["selected_factors"],
                "n_factors_total": int(len(results["factor_evaluation"])),
                "ml_info": {k: v for k, v in results["ml_info"].items() if k != "feature_columns"},
            }
    except Exception as exc:
        traceback.print_exc()
        with _RUN_LOCK:
            _RUN_STATE["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        with _RUN_LOCK:
            _RUN_STATE["running"] = False
            _RUN_STATE["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")


def _build_flask_app() -> Any:
    if Flask is None:
        raise ImportError("缺少 flask，请先 pip install flask")

    app = Flask(__name__, static_folder=None)
    INDEX_HTML = _render_index_html()

    @app.route("/")
    def index():
        return INDEX_HTML

    @app.route("/api/libraries")
    def api_libraries():
        return jsonify({"libraries": factor_loader.list_libraries()})

    def _resolve_cache_dir(cfg_dir: str) -> Path:
        p = Path(cfg_dir) if cfg_dir else Path(".factor_cache")
        if not p.is_absolute():
            p = _THIS_DIR / p
        return p

    @app.route("/api/factor_cache/stats")
    def api_factor_cache_stats():
        cfg = load_saved_config()
        cache_dir = _resolve_cache_dir(cfg.factor_cache_dir)
        info = factor_cache.stats(str(cache_dir))
        return jsonify({"dir": str(cache_dir), **info})

    @app.route("/api/factor_cache/clear", methods=["POST"])
    def api_factor_cache_clear():
        cfg = load_saved_config()
        cache_dir = _resolve_cache_dir(cfg.factor_cache_dir)
        deleted = factor_cache.clear(str(cache_dir))
        return jsonify({"ok": True, "deleted": deleted, "dir": str(cache_dir)})

    @app.route("/api/config", methods=["GET"])
    def api_get_config():
        cfg = load_saved_config()
        return jsonify(asdict(cfg))

    @app.route("/api/run", methods=["POST"])
    def api_run():
        with _RUN_LOCK:
            if _RUN_STATE["running"]:
                return jsonify({"ok": False, "msg": "已有运行中的任务，请稍候"}), 400
        payload = request.get_json(force=True, silent=True) or {}
        try:
            cfg = _coerce_config(payload)
        except ValueError as exc:
            return jsonify({"ok": False, "msg": str(exc)}), 400
        thread = threading.Thread(target=_run_workflow_background, args=(cfg,), daemon=True)
        thread.start()
        return jsonify({"ok": True})

    @app.route("/api/status")
    def api_status():
        with _RUN_LOCK:
            return jsonify(
                {
                    "running": _RUN_STATE["running"],
                    "logs": list(_RUN_STATE["logs"][-300:]),
                    "error": _RUN_STATE["error"],
                    "last_results": _RUN_STATE["last_results"],
                    "start_time": _RUN_STATE["start_time"],
                    "end_time": _RUN_STATE["end_time"],
                }
            )

    return app


def _coerce_config(payload: Dict[str, Any]) -> WorkflowConfigV2:
    default = asdict(WorkflowConfigV2())
    merged = {**default}
    for key, value in payload.items():
        if key not in default:
            continue
        target_type = type(default[key])
        try:
            if target_type is bool:
                merged[key] = bool(value)
            elif target_type is int:
                merged[key] = int(value)
            elif target_type is float:
                merged[key] = float(value)
            elif target_type is list:
                if isinstance(value, list):
                    merged[key] = [str(v) for v in value]
                else:
                    merged[key] = [x.strip() for x in str(value).split(",") if x.strip()]
            else:
                merged[key] = str(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"参数 {key} 无法转为 {target_type.__name__}: {exc}") from exc
    return WorkflowConfigV2(**merged)


def _render_index_html() -> str:
    libraries = factor_loader.list_libraries()
    lib_options_html = "".join(
        f'<label class="lib-opt"><input type="checkbox" name="factor_libraries" value="{lib}"> {lib}</label>'
        for lib in libraries
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><title>QLib 传统多因子 2.0 控制台</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "Microsoft Yahei", sans-serif; margin: 0; padding: 20px; background:#f5f6fa; }}
  h1 {{ font-size: 22px; margin-bottom: 12px; }}
  .layout {{ display: grid; grid-template-columns: 460px 1fr; gap: 16px; }}
  .panel {{ background:#fff; border-radius:8px; padding:16px; box-shadow:0 2px 6px rgba(0,0,0,.06); }}
  .panel h2 {{ font-size: 16px; margin: 0 0 10px; border-left: 3px solid #4a90e2; padding-left: 8px; }}
  fieldset {{ border:1px solid #e1e4e8; border-radius:6px; margin-bottom:12px; padding:10px 12px; }}
  legend {{ color:#4a90e2; font-weight:600; font-size:13px; padding:0 6px; }}
  .row {{ display:flex; gap:8px; margin-bottom:6px; flex-wrap:wrap; }}
  .row label {{ flex: 1; min-width: 130px; font-size:12px; color:#444; }}
  .row label > div {{ color:#888; font-size:11px; margin-bottom:2px; }}
  input[type=text], input[type=number], input[type=date], select {{ width:100%; padding:5px 7px; border:1px solid #d0d7de; border-radius:4px; font-size:12px; box-sizing: border-box; }}
  .lib-opt, .ml-opt {{ display:inline-block; margin:4px 8px 4px 0; font-size:12px; }}
  button {{ padding:8px 16px; border:none; border-radius:5px; cursor:pointer; font-size:13px; font-weight:600; }}
  .btn-primary {{ background:#4a90e2; color:#fff; }}
  .btn-primary:hover {{ background:#3577c5; }}
  .btn-primary:disabled {{ background:#a4bfdf; cursor:not-allowed; }}
  pre.logs {{ background:#1e1e2e; color:#d6e2f0; padding:10px; border-radius:6px; height:380px; overflow:auto; font-size:12px; }}
  table {{ border-collapse:collapse; width:100%; font-size:12px; }}
  th, td {{ border:1px solid #e1e4e8; padding:5px 8px; text-align:right; }}
  th {{ background:#f1f4f9; }}
  td:first-child, th:first-child {{ text-align:left; }}
  .status {{ font-size:13px; padding:6px 10px; border-radius:5px; margin-bottom:10px; }}
  .status.idle {{ background:#e9ecef; color:#444; }}
  .status.run  {{ background:#fff3cd; color:#856404; }}
  .status.err  {{ background:#f8d7da; color:#721c24; }}
  .status.ok   {{ background:#d4edda; color:#155724; }}
</style></head>
<body>
<h1>📊 QLib 传统多因子 2.0 控制台</h1>
<div class="layout">
  <form id="cfg-form" class="panel">
    <h2>运行参数</h2>
    <fieldset><legend>1. 数据与股票池</legend>
      <div class="row"><label><div>provider_uri</div><input name="provider_uri" type="text"></label></div>
      <div class="row">
        <label><div>market（成分股池）</div>
          <select name="market">
            <option value="csi300">csi300 — 沪深 300，大盘股池子</option>
            <option value="csi500">csi500 — 中证 500，中盘股池子</option>
            <option value="csi800">csi800 — 中证 800（300+500）</option>
            <option value="csi1000">csi1000 — 中证 1000，中小盘</option>
            <option value="all">all — 全 A 股（最彻底）</option>
            <option value="csi100">csi100 — 中证 100</option>
            <option value="sse50">sse50 — 上证 50</option>
          </select>
        </label>
        <label><div>benchmark</div>
          <select name="benchmark">
            <option value="SH000300">SH000300 — 沪深 300 指数</option>
            <option value="SH000905">SH000905 — 中证 500 指数</option>
            <option value="SH000852">SH000852 — 中证 1000 指数</option>
            <option value="SH000016">SH000016 — 上证 50 指数</option>
            <option value="SH000001">SH000001 — 上证综指</option>
            <option value="SZ399001">SZ399001 — 深证成指</option>
            <option value="SZ399006">SZ399006 — 创业板指</option>
          </select>
        </label>
      </div>
      <div class="row">
        <label><div>start_time</div><input name="start_time" type="text"></label>
        <label><div>end_time</div><input name="end_time" type="text"></label>
      </div>
    </fieldset>

    <fieldset><legend>1.5 股票池过滤（akshare 市值 + 股价区间）</legend>
      <div class="row">
        <label><div><input name="enable_market_cap_filter" type="checkbox"> 启用市值过滤</div></label>
        <label><div>市值下限（亿元）</div><input name="min_market_cap_yi" type="number" step="1" min="0"></label>
        <label><div>市值上限（亿元）</div><input name="max_market_cap_yi" type="number" step="1" min="0"></label>
        <label><div>市值口径</div>
          <select name="market_cap_kind">
            <option value="total">total（总市值）</option>
            <option value="float">float（流通市值）</option>
          </select>
        </label>
      </div>
      <div class="row">
        <label><div><input name="enable_price_filter" type="checkbox"> 启用股价过滤</div></label>
        <label><div>股价下限（元）</div><input name="min_close_price" type="number" step="0.1" min="0"></label>
        <label><div>股价上限（元）</div><input name="max_close_price" type="number" step="0.1" min="0"></label>
        <label><div>参考价取法</div>
          <select name="price_filter_mode">
            <option value="last">last（最后一日）</option>
            <option value="mean">mean（全期均值）</option>
            <option value="median">median（全期中位数）</option>
          </select>
        </label>
      </div>
      <div class="row">
        <label><div>市值缓存有效期（天）</div><input name="market_cap_cache_max_age_days" type="number" step="1" min="0"></label>
        <label><div><input name="force_refresh_market_cap_cache" type="checkbox"> 强制刷新缓存</div></label>
      </div>
    </fieldset>

    <fieldset><legend>2. 因子库（可多选）</legend>
      <div id="lib-options">{lib_options_html}</div>
      <div class="row" style="margin-top:8px; align-items:center;">
        <label style="flex:0 0 auto;"><div>&nbsp;</div>
          <input name="enable_factor_cache" type="checkbox"> 启用因子缓存（按 时间范围 + 股票池 + 因子源码 命中）
        </label>
        <label style="flex:1;"><div>缓存目录（相对本脚本）</div>
          <input name="factor_cache_dir" type="text" placeholder=".factor_cache">
        </label>
        <label style="flex:0 0 auto;"><div>&nbsp;</div>
          <button type="button" id="btn-clear-cache" class="btn-primary"
            style="background:#c0504d;">清空因子缓存</button>
        </label>
        <label style="flex:1;"><div>缓存状态</div>
          <span id="cache-stats" style="font-size:12px;color:#666;">—</span>
        </label>
      </div>
    </fieldset>

    <fieldset><legend>3. 未来收益</legend>
      <div class="row">
        <label><div>future_return_mode</div>
          <select name="future_return_mode">
            <option value="holding_close">holding_close</option>
            <option value="max_high">max_high</option>
            <option value="max_close">max_close</option>
          </select>
        </label>
        <label><div>holding_period (N)</div><input name="holding_period" type="number" min="1"></label>
      </div>
    </fieldset>

    <fieldset><legend>4. 因子过滤</legend>
      <div class="row">
        <label><div>filter_method</div>
          <select name="filter_method">
            <option value="none">none</option>
            <option value="threshold">threshold</option>
            <option value="topk">topk</option>
          </select>
        </label>
        <label><div>topk</div><input name="filter_topk" type="number" min="1"></label>
      </div>
      <div class="row">
        <label><div>|RankIC mean| ></div><input name="filter_rank_ic_min" type="number" step="0.001"></label>
        <label><div>|RankIC IR| ></div><input name="filter_rank_ic_ir_min" type="number" step="0.01"></label>
        <label><div>|corr| 最大</div><input name="filter_corr_max" type="number" step="0.05"></label>
      </div>
    </fieldset>

    <fieldset><legend>4.5 因子画像 / 自动分类</legend>
      <div class="row">
        <label style="flex:1;"><div>&nbsp;</div>
          <input name="enable_factor_profile" type="checkbox"> 启用因子画像分类（趋势 / 反转 / 风险 / 噪声）
        </label>
        <label><div>过去收益窗口（逗号分隔）</div><input name="factor_profile_past_windows" type="text" placeholder="1,3,5,10"></label>
        <label><div>未来风险窗口</div><input name="factor_profile_future_window" type="number" min="1" step="1"></label>
      </div>
    </fieldset>

    <fieldset><legend>5. 信号 / ML</legend>
      <div class="row">
        <label><div>signal_mode</div>
          <select name="signal_mode">
            <option value="traditional">traditional</option>
            <option value="ml">ml</option>
            <option value="all">all</option>
          </select>
        </label>
        <label><div>ml_model</div>
          <label class="ml-opt"><input type="checkbox" name="ml_model" value="lightgbm"> lightgbm</label>
          <label class="ml-opt"><input type="checkbox" name="ml_model" value="ridge"> ridge</label>
          <label class="ml-opt"><input type="checkbox" name="ml_model" value="lasso"> lasso</label>
        </label>
      </div>
      <div class="row">
        <label><div>训练集结束 train_end_time</div><input name="train_end_time" type="date"></label>
        <label><div>验证集结束 valid_end_time</div><input name="valid_end_time" type="date"></label>
        <label><div>测试集开始 test_start_time</div><input name="test_start_time" type="date"></label>
      </div>
      <div class="row">
        <label><div>ML 因子非空比例阈值（>= 才用于训练）</div><input name="ml_min_non_null_ratio" type="number" step="0.05" min="0" max="1"></label>
      </div>
      <div class="row">
        <label style="flex:1;"><div>&nbsp;</div>
          <input name="walk_forward_enable" type="checkbox"> 启用 Walk-Forward 滚动训练（按窗口逐段训练+测试，拼接 OOS 预测）
        </label>
      </div>
      <div class="row">
        <label><div>窗口数 walk_forward_n_windows</div><input name="walk_forward_n_windows" type="number" min="1" step="1"></label>
        <label><div>窗口步长（天）walk_forward_step_days</div><input name="walk_forward_step_days" type="number" min="1" step="1"></label>
      </div>
      <div class="row">
        <label><div>训练回看（天）walk_forward_train_days</div><input name="walk_forward_train_days" type="number" min="30" step="30"></label>
        <label><div>验证期（天）walk_forward_valid_days</div><input name="walk_forward_valid_days" type="number" min="10" step="10"></label>
      </div>
      <div class="row">
        <label style="flex:1;"><div>&nbsp;</div>
          <input name="use_step7_cache" type="checkbox"> 使用第七步缓存（命中则跳过 1-7 步，直接从 ML/信号开始）
        </label>
      </div>
      <div id="ml-date-hint" style="font-size:12px;color:#666;margin-top:4px;"></div>
    </fieldset>

    <fieldset><legend>5.5 防未来函数（强烈建议保持默认勾选）</legend>
      <div class="row">
        <label><div>direction_method（传统信号方向估计）</div>
          <select name="direction_method">
            <option value="train_only">train_only — 仅用训练期估计方向/IR 权重（默认，干净）</option>
            <option value="rolling">rolling — 滚动窗口，shift(1) 防泄漏（最严格，时变）</option>
            <option value="full_sample">full_sample — 全样本估计（已知有 look-ahead，仅供对照！）</option>
          </select>
        </label>
        <label><div>rolling_ic_window（rolling 模式回看窗口）</div>
          <input name="rolling_ic_window" type="number" min="5" step="5">
        </label>
      </div>
      <div class="row">
        <label style="flex:1;"><div>&nbsp;</div>
          <input name="filter_use_train_only" type="checkbox">
          第六/七步因子评价 / 过滤仅用训练期（避免 in-sample 特征筛选）
        </label>
        <label style="flex:1;"><div>&nbsp;</div>
          <input name="backtest_test_period_only" type="checkbox">
          回测净值与 performance 仅统计 test 期（与 ML OOS 对齐，更公平）
        </label>
      </div>
      <div style="font-size:12px;color:#a04040;margin-top:4px;">
        ⚠️ 关闭这些开关会让传统信号的回测数字虚高（典型现象：年化 100%+、Sharpe 12+），仅用于诊断对照。
      </div>
    </fieldset>

    <fieldset><legend>6. 回测</legend>
      <div class="row">
        <label><div>topn</div><input name="topn" type="number" min="1"></label>
        <label><div>quantiles</div><input name="quantiles" type="number" min="2"></label>
        <label><div>ic_window</div><input name="ic_window" type="number" min="5"></label>
      </div>
    </fieldset>

    <button id="btn-run" class="btn-primary" type="submit">▶ 运行</button>
  </form>

  <div>
    <div class="panel">
      <h2>运行状态</h2>
      <div id="status" class="status idle">空闲</div>
      <pre id="logs" class="logs">等待运行...</pre>
    </div>
    <div class="panel" style="margin-top:12px;">
      <h2>结果摘要</h2>
      <div id="results">尚无结果。</div>
    </div>
  </div>
</div>

<script>
const form = document.getElementById('cfg-form');
const btn = document.getElementById('btn-run');
const statusEl = document.getElementById('status');
const logsEl = document.getElementById('logs');
const resultsEl = document.getElementById('results');
let _wasRunning = false;

function fillForm(cfg) {{
  for (const [k, v] of Object.entries(cfg)) {{
    if (k === 'factor_libraries' || k === 'ml_model') continue;
    const el = form.elements.namedItem(k);
    if (!el) continue;
    if (el.type === 'checkbox') {{
      el.checked = Boolean(v);
    }} else {{
      el.value = v;
    }}
  }}
  document.querySelectorAll('input[name="factor_libraries"]').forEach(input => {{
    input.checked = (cfg.factor_libraries || []).includes(input.value);
  }});
  const models = Array.isArray(cfg.ml_model) ? cfg.ml_model : [cfg.ml_model || 'lightgbm'];
  document.querySelectorAll('input[name="ml_model"]').forEach(input => {{
    input.checked = models.includes(input.value);
  }});
}}

function parseDateValue(value) {{
  if (!value) return null;
  const date = new Date(value + 'T00:00:00');
  return Number.isNaN(date.getTime()) ? null : date;
}}

function formatDateValue(date) {{
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${{y}}-${{m}}-${{d}}`;
}}

function addDays(date, days) {{
  const next = new Date(date.getTime());
  next.setDate(next.getDate() + days);
  return next;
}}

function autoSetMlDateRanges() {{
  const start = parseDateValue(form.elements.namedItem('start_time')?.value);
  const end = parseDateValue(form.elements.namedItem('end_time')?.value);
  const hint = document.getElementById('ml-date-hint');
  if (!start || !end || end <= start) {{
    if (hint) hint.textContent = '请先设置有效的 start_time / end_time，系统会自动切分训练、验证、测试时间。';
    return;
  }}
  const totalDays = Math.floor((end - start) / 86400000);
  const trainEnd = addDays(start, Math.max(1, Math.floor(totalDays * 0.6)));
  const validEnd = addDays(start, Math.max(2, Math.floor(totalDays * 0.8)));
  let testStart = addDays(validEnd, 1);
  if (testStart > end) testStart = validEnd;
  form.elements.namedItem('train_end_time').value = formatDateValue(trainEnd);
  form.elements.namedItem('valid_end_time').value = formatDateValue(validEnd);
  form.elements.namedItem('test_start_time').value = formatDateValue(testStart);
  if (hint) {{
    hint.textContent = `已自动按总区间约 60% / 20% / 20% 分配：训练 ≤ ${{formatDateValue(trainEnd)}}，验证 ≤ ${{formatDateValue(validEnd)}}，测试 ≥ ${{formatDateValue(testStart)}}。`;
  }}
}}

function readForm() {{
  const data = {{}};
  const seenCheckbox = new Set();
  for (const el of form.elements) {{
    if (!el.name) continue;
    if (el.name === 'factor_libraries' || el.name === 'ml_model') continue;
    if (el.type === 'checkbox') {{
      data[el.name] = el.checked;
      seenCheckbox.add(el.name);
    }} else {{
      data[el.name] = el.value;
    }}
  }}
  data.factor_libraries = Array.from(
    document.querySelectorAll('input[name="factor_libraries"]:checked')
  ).map(x => x.value);
  data.ml_model = Array.from(
    document.querySelectorAll('input[name="ml_model"]:checked')
  ).map(x => x.value);
  return data;
}}

async function refreshCacheStats() {{
  try {{
    const s = await fetch('/api/factor_cache/stats').then(r => r.json());
    const mb = (s.size_bytes / 1024 / 1024).toFixed(2);
    document.getElementById('cache-stats').textContent =
      `${{s.count}} 个文件 / ${{mb}} MB`;
    document.getElementById('cache-stats').title = s.dir || '';
  }} catch (e) {{
    document.getElementById('cache-stats').textContent = '读取失败';
  }}
}}

async function clearFactorCache() {{
  if (!confirm('确认清空因子缓存目录下所有 *.pkl 文件？')) return;
  try {{
    const r = await fetch('/api/factor_cache/clear', {{method:'POST'}}).then(r => r.json());
    alert(`已删除 ${{r.deleted}} 个缓存文件\\n${{r.dir}}`);
    refreshCacheStats();
  }} catch (e) {{
    alert('清空失败: ' + e);
  }}
}}

async function init() {{
  const cfg = await fetch('/api/config').then(r => r.json());
  fillForm(cfg);
  autoSetMlDateRanges();
  form.elements.namedItem('start_time')?.addEventListener('change', autoSetMlDateRanges);
  form.elements.namedItem('end_time')?.addEventListener('change', autoSetMlDateRanges);
  document.getElementById('btn-clear-cache').addEventListener('click', clearFactorCache);
  refreshCacheStats();
  pollStatus();
  setInterval(pollStatus, 1500);
}}

async function pollStatus() {{
  try {{
    const s = await fetch('/api/status').then(r => r.json());
    if (_wasRunning && !s.running) {{
      // 运行刚结束 → 刷新缓存统计
      refreshCacheStats();
    }}
    _wasRunning = !!s.running;
    if (s.running) {{
      statusEl.className = 'status run';
      statusEl.textContent = '运行中... 起始: ' + s.start_time;
      btn.disabled = true;
    }} else if (s.error) {{
      statusEl.className = 'status err';
      statusEl.textContent = '上次运行失败: ' + s.error;
      btn.disabled = false;
    }} else if (s.last_results) {{
      statusEl.className = 'status ok';
      statusEl.textContent = '上次完成于 ' + (s.end_time || '');
      btn.disabled = false;
    }} else {{
      statusEl.className = 'status idle';
      statusEl.textContent = '空闲';
      btn.disabled = false;
    }}
    if (s.logs && s.logs.length) {{
      // 仅当用户当前已在底部附近时才自动跟随，避免向上查看时被弹回
      const nearBottom = (logsEl.scrollHeight - logsEl.scrollTop - logsEl.clientHeight) < 30;
      logsEl.textContent = s.logs.join('\\n');
      if (nearBottom) {{
        logsEl.scrollTop = logsEl.scrollHeight;
      }}
    }}
    if (s.last_results) renderResults(s.last_results);
  }} catch (e) {{}}
}}

function renderResults(r) {{
  const fmt = (v, n=4) => (typeof v === 'number' && Number.isFinite(v)) ? v.toFixed(n) : '—';
  let html = '';
  if (r.performance && r.performance.length) {{
    html += '<h3 style="font-size:14px;margin:6px 0;">📈 策略表现</h3><table><tr><th>signal</th><th>annual_return</th><th>sharpe</th><th>max_drawdown</th><th>excess_return</th></tr>';
    for (const row of r.performance) {{
      html += `<tr><td>${{row.signal}}</td><td>${{(row.annual_return*100).toFixed(2)}}%</td><td>${{row.sharpe.toFixed(2)}}</td><td>${{(row.max_drawdown*100).toFixed(2)}}%</td><td>${{(row.excess_return*100).toFixed(2)}}%</td></tr>`;
    }}
    html += '</table>';
  }}
  html += `<p style="margin:10px 0 4px;">共加载 ${{r.n_factors_total}} 个因子, 过滤后保留 ${{(r.selected_factors||[]).length}} 个。</p>`;
  if (r.factor_profile_summary && Object.keys(r.factor_profile_summary).length) {{
    const labels = r.factor_profile_summary.label_counts || {{}};
    const usages = r.factor_profile_summary.usage_counts || {{}};
    html += '<h3 style="font-size:14px;margin:6px 0;">🧭 因子自动画像</h3>';
    html += `<p style="margin:4px 0;">分类：${{Object.entries(labels).map(([k,v]) => `${{k}}=${{v}}`).join('，') || '—'}}</p>`;
    html += `<p style="margin:4px 0;">用途：${{Object.entries(usages).map(([k,v]) => `${{k}}=${{v}}`).join('，') || '—'}}</p>`;
  }}
  if (r.factor_profile_head && r.factor_profile_head.length) {{
    html += '<table><tr><th>factor</th><th>label</th><th>usage</th><th>ic_future</th><th>ic_past_5d</th><th>ic_risk</th><th>stability</th><th>mono</th></tr>';
    for (const row of r.factor_profile_head) {{
      html += `<tr><td>${{row.factor}}</td><td>${{row.auto_label}}</td><td>${{row.usage}}</td><td>${{fmt(row.ic_future)}}</td><td>${{fmt(row.ic_past_5d)}}</td><td>${{fmt(row.ic_risk)}}</td><td>${{fmt(row.ic_stability, 2)}}</td><td>${{fmt(row.monotonicity, 2)}}</td></tr>`;
    }}
    html += '</table>';
  }}
  if (r.factor_evaluation_head && r.factor_evaluation_head.length) {{
    html += '<h3 style="font-size:14px;margin:6px 0;">🏆 因子评价 Top 20</h3><table><tr><th>factor</th><th>rank_ic_mean</th><th>rank_ic_ir</th><th>ic_win_rate</th></tr>';
    for (const row of r.factor_evaluation_head) {{
      html += `<tr><td>${{row.factor}}</td><td>${{row.rank_ic_mean.toFixed(4)}}</td><td>${{row.rank_ic_ir.toFixed(3)}}</td><td>${{(row.ic_win_rate*100).toFixed(1)}}%</td></tr>`;
    }}
    html += '</table>';
  }}
  resultsEl.innerHTML = html || '尚无结果。';
}}

form.addEventListener('submit', async (ev) => {{
  ev.preventDefault();
  btn.disabled = true;
  const data = readForm();
  const resp = await fetch('/api/run', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(data)}});
  const j = await resp.json();
  if (!j.ok) {{
    alert('启动失败: ' + (j.msg || '未知错误'));
    btn.disabled = false;
  }}
}});
init();
</script>
</body></html>
"""


# ============================================================================
# 入口
# ============================================================================


def main_cli() -> None:
    config = load_saved_config()
    save_config(config)
    wf = WorkflowV2(config)
    wf.run()


def main_web(host: str = "127.0.0.1", port: int = 7778) -> None:
    app = _build_flask_app()
    # 彻底屏蔽 werkzeug 的 HTTP 访问日志（例如 GET /api/status 轮询噪音）
    import logging as _logging
    _wlog = _logging.getLogger("werkzeug")
    _wlog.setLevel(_logging.ERROR)
    _wlog.disabled = True
    _wlog.propagate = False
    try:
        from werkzeug.serving import WSGIRequestHandler  # type: ignore
        WSGIRequestHandler.log_request = lambda *a, **kw: None  # type: ignore[assignment]
        WSGIRequestHandler.log = lambda *a, **kw: None  # type: ignore[assignment]
    except Exception:
        pass
    print(f"🌐 控制台启动: http://{host}:{port}/")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QLib 传统多因子 2.0")
    parser.add_argument("--cli", action="store_true", help="不启动 Web，直接命令行运行")
    parser.add_argument("--port", type=int, default=7778, help="Web 端口（默认 7778）")
    parser.add_argument("--host", default="127.0.0.1", help="Web 主机（默认 127.0.0.1）")
    args = parser.parse_args()
    if args.cli:
        main_cli()
    else:
        main_web(args.host, args.port)
