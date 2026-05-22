#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeIssues=false
"""自定义因子（DeepSeek 生成 + 对照分析）独立 Web 控制台。

设计目标：
- 与 ``workflow_v2.py`` 完全独立、互不影响：独立类、独立配置文件、独立缓存、独立结果目录、独立 Web 端口。
- 仅覆盖 v2 流程的第 1~6 步：初始化 QLib → 加载行情 → 股票池过滤 → 未来收益 → 加载因子库 → 横截面标准化 → 单因子评价。
- 不做信号合成 / 回测 / ML，先做到因子分析为止。

运行方式：
- ``python workflow_custom_factors.py`` 启动 Flask Web 控制台（端口 8000）。
- ``python workflow_custom_factors.py --cli`` 直接命令行运行。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import os
import pickle
import sys
import threading
import time
import traceback
import uuid
import warnings
import importlib.util
from contextlib import redirect_stdout
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------- sys.path：让 ``factors`` 作为顶层包可被 import ----------
_THIS_DIR = Path(__file__).resolve().parent  # source/qlib传统多因子2.0/
_SOURCE_DIR = _THIS_DIR.parent                # source/
if str(_SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(_SOURCE_DIR))
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

# 同目录复用模块
import factor_cache  # type: ignore  # noqa: E402
import factor_loader  # type: ignore  # noqa: E402
import return_builder  # type: ignore  # noqa: E402
import stock_pool_filter  # type: ignore  # noqa: E402

# DeepSeek 因子生成入口：工具代码放在 source/custom-fa/，正式因子只放在 source/factors/custom/。
_CUSTOM_FA_DIR = _SOURCE_DIR / "custom-fa"
_CUSTOM_FACTOR_LOADER_PATH = _CUSTOM_FA_DIR / "custom_factor_loader.py"
_spec = importlib.util.spec_from_file_location(
    "custom_factor_loader", _CUSTOM_FACTOR_LOADER_PATH
)
if _spec is None or _spec.loader is None:
    raise ImportError(f"无法加载 custom factor loader: {_CUSTOM_FACTOR_LOADER_PATH}")
_custom_factor_loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_custom_factor_loader)

generate_custom_factor = _custom_factor_loader.generate_custom_factor
list_custom_factors = _custom_factor_loader.list_custom_factors
validate_factor_code = _custom_factor_loader.validate_factor_code
describe_llm_config = _custom_factor_loader.describe_llm_config
_CUSTOM_DIR = _custom_factor_loader.CUSTOM_DIR
_LLM_CONFIG_PATH = _custom_factor_loader.LLM_CONFIG_PATH
_LLM_CONFIG_EXAMPLE_PATH = _custom_factor_loader.LLM_CONFIG_EXAMPLE_PATH

# QLib
import qlib  # noqa: E402
from qlib.constant import REG_CN  # noqa: E402
from qlib.data import D  # noqa: E402
from qlib.utils import exists_qlib_data  # noqa: E402

# Flask（缺失时延迟报错）
try:
    from flask import Flask, jsonify, request, send_file  # noqa: E402
except ImportError:  # pragma: no cover
    Flask = None  # type: ignore[assignment]
    jsonify = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]
    send_file = None  # type: ignore[assignment]

# matplotlib：图表用，无图形界面环境也要能跑
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

_CJK_FONT_PROP = None
for _font_path in (
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "msyh.ttc",
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "simhei.ttf",
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "simsun.ttc",
):
    if _font_path.exists():
        font_manager.fontManager.addfont(str(_font_path))
        _CJK_FONT_PROP = font_manager.FontProperties(fname=str(_font_path))
        _cjk_font_name = _CJK_FONT_PROP.get_name()
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = [
            _cjk_font_name,
            "Microsoft YaHei",
            "SimHei",
            "SimSun",
            "Arial Unicode MS",
            "DejaVu Sans",
        ]
        break

matplotlib.rcParams["axes.unicode_minus"] = False
warnings.filterwarnings("ignore", message=r"Glyph .* missing from font\(s\).*", category=UserWarning)

LOGGER = logging.getLogger(__name__)

CONFIG_FILE = _THIS_DIR / "workflow_custom_factors_config.json"

# ============================================================================
# 配置
# ============================================================================


@dataclass
class WorkflowCustomFactorsConfig:
    """自定义因子分析的配置。"""

    # ---- 数据 ----
    provider_uri: str = "d:/pythonProject/sdufe-qlib/source/qlib-data数据下载/cn_data"
    market: str = "csi300"
    benchmark: str = "SH000300"
    start_time: str = "2024-11-01"
    end_time: str = "2025-04-30"
    enable_market_data_cache: bool = True
    market_data_cache_dir: str = ".market_data_cache_custom"
    # ---- 因子库 ----
    factor_libraries: List[str] = field(default_factory=lambda: ["custom"])
    # ---- 未来收益 ----
    future_return_mode: str = "holding_close"  # holding_close | max_high | max_close
    holding_period: int = 1
    # ---- 分层 ----
    quantiles: int = 10
    # ---- 股票池过滤 ----
    enable_price_filter: bool = True
    min_close_price: float = 2.0
    max_close_price: float = 200.0
    price_filter_mode: str = "last"  # last | mean | median
    enable_market_cap_filter: bool = False
    min_market_cap_yi: float = 20.0
    max_market_cap_yi: float = 5000.0
    market_cap_kind: str = "total"  # total | float
    market_cap_cache_max_age_days: int = 30
    force_refresh_market_cap_cache: bool = False
    # ---- 因子缓存 ----
    enable_factor_cache: bool = True
    factor_cache_dir: str = ".factor_cache_custom"
    # ---- 输出 ----
    output_dir: str = "results_custom"


def load_saved_config() -> WorkflowCustomFactorsConfig:
    """读取磁盘配置，文件缺失或字段过期时自动回退到默认值。"""
    if not CONFIG_FILE.exists():
        return WorkflowCustomFactorsConfig()
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        LOGGER.warning("读取 %s 失败，将使用默认配置", CONFIG_FILE)
        return WorkflowCustomFactorsConfig()
    default = WorkflowCustomFactorsConfig()
    merged = asdict(default)
    for k, v in raw.items():
        if k in merged:
            merged[k] = v
    return WorkflowCustomFactorsConfig(**merged)


def save_config(cfg: WorkflowCustomFactorsConfig) -> None:
    CONFIG_FILE.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ============================================================================
# 自定义因子 Workflow
# ============================================================================


class WorkflowCustomFactors:
    """自定义因子分析 pipeline（独立实现，不继承 WorkflowV2）。"""

    def __init__(self, config: WorkflowCustomFactorsConfig):
        self.config = config
        self.output_dir = _THIS_DIR / config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "figs").mkdir(parents=True, exist_ok=True)

        self.panel: Dict[str, pd.DataFrame] = {}
        self.future_return: Optional[pd.DataFrame] = None
        self.holding_return: Optional[pd.DataFrame] = None
        self.factor_dict: Dict[str, pd.DataFrame] = {}
        self.standardized_factors: Dict[str, pd.DataFrame] = {}
        self._stock_pool_initial_count: int = 0
        self._prefilter_report: pd.DataFrame = pd.DataFrame()
        self._market_data_cache_key: str = ""
        self._market_data_cache_path: Optional[Path] = None
        self._market_data_cache_has_amount: bool = True
        self._stock_pool_loaded_from_cache: bool = False
        self._cached_pool_report: pd.DataFrame = pd.DataFrame()

    # ---------------- 主入口 ----------------
    def run(self) -> Dict[str, Any]:
        step_times: List[Tuple[str, float]] = []

        def _timed(name: str, func, *args, **kwargs):
            t0 = time.perf_counter()
            result = func(*args, **kwargs)
            dt = time.perf_counter() - t0
            step_times.append((name, dt))
            print(f"⏱  [{name}] 耗时 {dt:.2f}s")
            return result

        run_t0 = time.perf_counter()
        print("\n" + "=" * 80)
        print(f"自定义因子分析开始 | libraries={self.config.factor_libraries}")
        print("=" * 80)

        _timed("第一步:初始化QLib", self._init_qlib)
        _timed("第二步:加载行情", self._load_market_data)
        pool_report = _timed("第二点五步:股票池过滤", self._filter_stock_pool)
        _timed("第三步:构造未来收益", self._build_returns)
        _timed("第四步:加载因子库", self._load_factors)
        if not self.factor_dict:
            raise RuntimeError("加载到 0 个因子，请检查 factor_libraries 与 custom/ 目录。")
        _timed("第五步:标准化", self._standardize_factors)
        evaluation, rank_ic, quantile_returns, correlation = _timed(
            "第六步:单因子评价", self._evaluate_factors
        )

        results: Dict[str, Any] = {
            "factor_evaluation": evaluation,
            "rank_ic": rank_ic,
            "quantile_returns": quantile_returns,
            "correlation": correlation,
            "pool_report": pool_report,
            "n_factors_total": len(self.factor_dict),
        }
        self._save_results(results)
        self._plot_results(rank_ic, quantile_returns, correlation)

        total = time.perf_counter() - run_t0
        print("\n⏱  步骤耗时汇总：")
        for name, dt in step_times:
            print(f"  - {name}: {dt:.2f}s")
        print("\n" + "=" * 80)
        print(f"分析完成，总耗时 {total:.2f}s")
        print("=" * 80)
        return results

    # ---------------- 第 1 步：QLib ----------------
    def _init_qlib(self) -> None:
        print("\n第一步：初始化 QLib 数据环境")
        provider_uri = os.path.expanduser(self.config.provider_uri)
        if not exists_qlib_data(provider_uri):
            raise FileNotFoundError(f"QLib 数据不存在: {provider_uri}")
        # 与 v2 一致：Windows + 中文目录下强制使用 threading + 单进程，避免 spawn 死锁。
        qlib.init(
            provider_uri=provider_uri,
            region=REG_CN,
            joblib_backend="threading",
            kernels=1,
        )
        print(f"✅ QLib 初始化成功: {provider_uri}")

    # ---------------- 第 2 步：行情 ----------------
    def _load_market_data(self) -> None:
        print("\n第二步：读取股票池行情数据")
        cfg = self.config
        instruments = D.instruments(market=cfg.market)
        instrument_list = D.list_instruments(
            instruments=instruments,
            start_time=cfg.start_time,
            end_time=cfg.end_time,
            freq="day",
            as_list=True,
        )
        self._stock_pool_initial_count = len(instrument_list)
        self._prefilter_report = pd.DataFrame()
        if cfg.enable_market_cap_filter:
            try:
                cap_df = stock_pool_filter.fetch_market_cap_akshare(
                    force_refresh=cfg.force_refresh_market_cap_cache,
                    max_age_days=cfg.market_cap_cache_max_age_days,
                )
                col = f"{cfg.market_cap_kind}_cap_yi"
                if col not in cap_df.columns:
                    raise ValueError(f"未知的 market_cap_kind={cfg.market_cap_kind}（应为 total 或 float）")
                cap_series = cap_df[col].reindex(instrument_list)
                mask = (cap_series >= float(cfg.min_market_cap_yi)) & (cap_series <= float(cfg.max_market_cap_yi))
                kept = [code for code, ok in mask.items() if bool(ok)]
                dropped = [code for code in instrument_list if code not in kept]
                print(
                    f"  💰 市值预过滤: {len(instrument_list)} → {len(kept)} 只 "
                    f"（区间 [{cfg.min_market_cap_yi:.0f}, {cfg.max_market_cap_yi:.0f}] 亿元，{cfg.market_cap_kind}）",
                    flush=True,
                )
                if not kept:
                    aligned = cap_df[col].reindex(instrument_list).dropna()
                    if not aligned.empty:
                        q = aligned.quantile([0.0, 0.25, 0.5, 0.75, 1.0])
                        print("  📊 当前 market 股票池市值分位（亿元）：", flush=True)
                        for p, v in q.items():
                            print(f"     {int(p * 100):>3}%  →  {v:>10.1f}", flush=True)
                    raise RuntimeError("股票池市值预过滤后剩余 0 只股票，请放宽过滤区间")
                self._prefilter_report = pd.DataFrame(
                    [
                        {
                            "step": f"market_cap [{cfg.min_market_cap_yi:.0f},{cfg.max_market_cap_yi:.0f}] 亿",
                            "kept": len(kept),
                            "dropped": len(dropped),
                            "examples": ",".join(dropped[:5]),
                        }
                    ]
                )
                instrument_list = kept
                instruments = instrument_list
            except RuntimeError as exc:
                if "市值预过滤后剩余 0 只股票" in str(exc):
                    raise
                print(f"  ⚠️ 市值预过滤失败（{type(exc).__name__}: {exc}），将加载原始股票池后继续", flush=True)
            except Exception as exc:
                print(f"  ⚠️ 市值预过滤失败（{type(exc).__name__}: {exc}），将加载原始股票池后继续", flush=True)
        base_fields = ["$open", "$high", "$low", "$close", "$volume", "$vwap"]
        cache_fields = ["open", "high", "low", "close", "volume", "vwap", "amount"]
        cache_path: Optional[Path] = None
        cache_key_payload = {
            "version": 1,
            "provider_uri": os.path.abspath(os.path.expanduser(cfg.provider_uri)),
            "market": cfg.market,
            "start_time": cfg.start_time,
            "end_time": cfg.end_time,
            "instruments": sorted(map(str, instrument_list)),
            "fields": cache_fields,
            "enable_price_filter": cfg.enable_price_filter,
            "min_close_price": cfg.min_close_price,
            "max_close_price": cfg.max_close_price,
            "price_filter_mode": cfg.price_filter_mode,
        }
        cache_key = hashlib.md5(json.dumps(cache_key_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        self._market_data_cache_key = cache_key
        if cfg.enable_market_data_cache:
            cache_dir = Path(cfg.market_data_cache_dir)
            if not cache_dir.is_absolute():
                cache_dir = _THIS_DIR / cache_dir
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / f"market_data_{cache_key}.pkl"
            self._market_data_cache_path = cache_path
            if cache_path.exists():
                try:
                    with open(cache_path, "rb") as fp:
                        cached = pickle.load(fp)
                    if cached.get("key") == cache_key:
                        self.panel = cached["panel"]
                        has_amount = bool(cached.get("has_amount", True))
                        self._market_data_cache_has_amount = has_amount
                        self._stock_pool_loaded_from_cache = True
                        report = cached.get("pool_report", pd.DataFrame())
                        self._cached_pool_report = report if isinstance(report, pd.DataFrame) else pd.DataFrame()
                        n_days, n_codes = self.panel["close"].shape
                        print(f"♻️ 命中已过滤行情缓存: {cache_path}")
                        print(
                            f"✅ 行情读取完成: {n_days} 个交易日, {n_codes} 只标的"
                            f"（amount={'真实' if has_amount else '近似'}，来自缓存）"
                        )
                        return
                except Exception as exc:
                    print(f"  ⚠️ 读取行情缓存失败（{type(exc).__name__}: {exc}），将重新读取 QLib", flush=True)
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
            print(f"⚠️ 无 $amount 字段（{exc}），用 close*volume 近似")
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

        index_names = list(data.index.names)
        if "instrument" in index_names:
            inst_level: Any = "instrument"
        elif "code" in index_names:
            inst_level = "code"
        else:
            inst_level = 0

        panel: Dict[str, pd.DataFrame] = {}
        for col in ["open", "high", "low", "close", "volume", "vwap", "amount"]:
            wide = data[col].unstack(inst_level)
            wide.index = pd.to_datetime(wide.index)
            wide = wide.sort_index()
            panel[col] = wide.astype(float)
        panel["returns"] = panel["close"].pct_change(fill_method=None)

        n_days, n_codes = panel["close"].shape
        print(
            f"✅ 行情读取完成: {n_days} 个交易日, {n_codes} 只标的"
            f"（amount={'真实' if has_amount else '近似'}）"
        )
        self.panel = panel
        self._market_data_cache_has_amount = has_amount

    def _save_market_data_cache(self, pool_report: pd.DataFrame) -> None:
        if not self.config.enable_market_data_cache or self._market_data_cache_path is None:
            return
        try:
            with open(self._market_data_cache_path, "wb") as fp:
                pickle.dump(
                    {
                        "key": self._market_data_cache_key,
                        "panel": self.panel,
                        "has_amount": self._market_data_cache_has_amount,
                        "pool_report": pool_report,
                    },
                    fp,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
            print(f"💾 已保存已过滤行情缓存: {self._market_data_cache_path}")
        except Exception as exc:
            print(f"  ⚠️ 保存行情缓存失败（不影响本次运行）: {type(exc).__name__}: {exc}", flush=True)

    # ---------------- 第 2.5 步：股票池 ----------------
    def _filter_stock_pool(self) -> pd.DataFrame:
        cfg = self.config
        if self._stock_pool_loaded_from_cache:
            print("\n第二点五步：股票池过滤（命中已过滤行情缓存，跳过）")
            return self._cached_pool_report
        if not (cfg.enable_market_cap_filter or cfg.enable_price_filter):
            print("\n第二点五步：股票池过滤（已全部禁用，跳过）")
            report = pd.DataFrame(columns=["step", "kept", "dropped", "examples"])
            self._save_market_data_cache(report)
            return report

        print("\n第二点五步：股票池过滤（市值 / 股价）")
        market_cap_done = not self._prefilter_report.empty
        pool_cfg = stock_pool_filter.StockPoolFilterConfig(
            enable_price=cfg.enable_price_filter,
            min_close_price=cfg.min_close_price,
            max_close_price=cfg.max_close_price,
            price_mode=cfg.price_filter_mode,
            enable_market_cap=cfg.enable_market_cap_filter and not market_cap_done,
            min_market_cap_yi=cfg.min_market_cap_yi,
            max_market_cap_yi=cfg.max_market_cap_yi,
            market_cap_kind=cfg.market_cap_kind,
            cache_max_age_days=cfg.market_cap_cache_max_age_days,
            force_refresh_cache=cfg.force_refresh_market_cap_cache,
        )
        before = self.panel["close"].shape[1]
        self.panel, report = stock_pool_filter.apply(self.panel, pool_cfg)
        after = self.panel["close"].shape[1]
        if market_cap_done:
            report = pd.concat(
                [
                    self._prefilter_report,
                    report[report["step"] != "FINAL"],
                    pd.DataFrame(
                        [
                            {
                                "step": "FINAL",
                                "kept": after,
                                "dropped": self._stock_pool_initial_count - after,
                                "examples": "",
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
            print(f"✅ 股票池过滤完成: {self._stock_pool_initial_count} → {after} 只标的")
        else:
            print(f"✅ 股票池过滤完成: {before} → {after} 只标的")
        self._save_market_data_cache(report)
        return report

    # ---------------- 第 3 步：未来收益 ----------------
    def _build_returns(self) -> None:
        cfg = self.config
        print(
            f"\n第三步：构造未来收益 mode={cfg.future_return_mode}, "
            f"holding_period={cfg.holding_period}"
        )
        self.future_return = return_builder.build_future_return(
            self.panel, cfg.future_return_mode, cfg.holding_period
        )
        if cfg.future_return_mode == "holding_close":
            self.holding_return = self.future_return
        else:
            self.holding_return = return_builder.build_holding_period_return(
                self.panel, cfg.holding_period
            )
        print(f"✅ future_return 形状: {self.future_return.shape}")

    # ---------------- 第 4 步：因子库 ----------------
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
                f"现有 {stats.get('count', 0)} 条 / {stats.get('size_mb', 0):.1f}MB)"
            )
        else:
            print("  📦 因子缓存：未启用")

        self.factor_dict = factor_loader.load_libraries(
            cfg.factor_libraries,
            self.panel,
            cache_dir=cache_dir,
            panel_sig=panel_sig,
            legacy_panel_sig=legacy_panel_sig,
        )
        print(f"✅ 共加载 {len(self.factor_dict)} 个因子")

    # ---------------- 第 5 步：标准化 ----------------
    @staticmethod
    def _winsorize_zscore(df: pd.DataFrame, limit: float = 5.0) -> pd.DataFrame:
        # 与 v2 完全一致：MAD 去极值 + 横截面 Z-Score
        median = df.median(axis=1)
        mad = (df.sub(median, axis=0)).abs().median(axis=1)
        # MAD=0（稀疏因子或常值横截面）时，上下界=median 会把全部值裁成同一个数，
        # 导致 std=0、标准化结果全 NaN。这里把 MAD=0 的边界设为 NaN，
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

    # ---------------- 第 6 步：因子评价 ----------------
    def _evaluate_factors(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        print("\n第六步：单因子评价（IC / RankIC / 分层 / 相关性）")
        future = self.future_return
        rows: List[Dict[str, float]] = []
        rank_ic_table = pd.DataFrame(index=future.index)
        quantile_pieces: List[pd.DataFrame] = []
        total = len(self.standardized_factors)

        for idx, (name, factor_df) in enumerate(self.standardized_factors.items(), start=1):
            aligned = factor_df.reindex_like(future)
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
                print(
                    f"  评价进度 {idx}/{total} | rank_ic_ir={rows[-1]['rank_ic_ir']:.3f}",
                    flush=True,
                )

        evaluation = (
            pd.DataFrame(rows)
            .sort_values("rank_ic_ir", key=lambda s: s.abs(), ascending=False, na_position="last")
            .reset_index(drop=True)
        )
        quantile_returns = (
            pd.concat(quantile_pieces, ignore_index=True)
            if quantile_pieces
            else pd.DataFrame(columns=["factor", "date", "quantile", "ret"])
        )

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
        q = max(int(self.config.quantiles), 2)
        ranks = factor_df.rank(axis=1, pct=True)
        bins = np.linspace(0.0, 1.0, q + 1)
        labels = [f"Q{i+1}" for i in range(q)]

        rank_long = ranks.stack(dropna=True).rename("rank")
        ret_long = future.reindex_like(factor_df).stack(dropna=True).rename("ret")
        merged = pd.concat([rank_long, ret_long], axis=1, join="inner")
        if merged.empty:
            return pd.DataFrame(columns=["factor", "date", "quantile", "ret"])

        merged["quantile"] = pd.cut(merged["rank"], bins=bins, labels=labels, include_lowest=True)
        merged = merged.dropna(subset=["quantile"])
        if merged.empty:
            return pd.DataFrame(columns=["factor", "date", "quantile", "ret"])
        date_level = merged.index.get_level_values(0)
        grouped = (
            merged.groupby([date_level, merged["quantile"]], observed=True)["ret"]
            .mean()
            .reset_index()
        )
        grouped.columns = ["date", "quantile", "ret"]
        grouped["factor"] = factor_name
        grouped["quantile"] = grouped["quantile"].astype(str)
        return grouped[["factor", "date", "quantile", "ret"]]

    # ---------------- 第 7 步：保存 ----------------
    def _save_results(self, results: Dict[str, Any]) -> None:
        out = self.output_dir
        results["factor_evaluation"].to_csv(out / "evaluation.csv", index=False, encoding="utf-8-sig")
        results["rank_ic"].to_csv(out / "rank_ic.csv", encoding="utf-8-sig")
        results["quantile_returns"].to_csv(out / "quantile_returns.csv", index=False, encoding="utf-8-sig")
        results["correlation"].to_csv(out / "correlation.csv", encoding="utf-8-sig")
        meta = {
            "n_factors_total": int(results["n_factors_total"]),
            "factor_libraries": list(self.config.factor_libraries),
            "market": self.config.market,
            "start_time": self.config.start_time,
            "end_time": self.config.end_time,
            "future_return_mode": self.config.future_return_mode,
            "holding_period": int(self.config.holding_period),
            "quantiles": int(self.config.quantiles),
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        (out / "run_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"💾 结果已保存到 {out}")

    # ---------------- 第 8 步：图表 ----------------
    def _plot_results(
        self, rank_ic: pd.DataFrame, quantile_returns: pd.DataFrame, correlation: pd.DataFrame
    ) -> None:
        figs_dir = self.output_dir / "figs"
        figs_dir.mkdir(parents=True, exist_ok=True)

        # 1) RankIC 时序：取累计 |rank_ic_ir| 排序后的 Top-K 因子（最多 8 条）
        if not rank_ic.empty:
            try:
                irs = rank_ic.apply(
                    lambda s: float(s.mean() / s.std()) if s.std() and not np.isnan(s.std()) else 0.0
                )
                top_cols = irs.abs().sort_values(ascending=False).head(8).index.tolist()
                fig, ax = plt.subplots(figsize=(11, 5))
                rank_ic[top_cols].rolling(20, min_periods=5).mean().plot(ax=ax)
                ax.set_title("RankIC 滚动均值（窗口=20，Top 8 by |rank_ic_ir|）", **_cjk_text_kwargs())
                ax.set_ylabel("RankIC", **_cjk_text_kwargs())
                ax.grid(alpha=0.3)
                ax.legend(fontsize=8, loc="best")
                fig.tight_layout()
                fig.savefig(figs_dir / "rank_ic_rolling.png", dpi=140)
                plt.close(fig)
            except Exception as exc:
                print(f"⚠️ 绘制 RankIC 图失败: {exc}")

        # 2) 分层收益：选 |rank_ic_ir| 最大的一个因子，画其 10 分位的累计收益
        if not quantile_returns.empty and not rank_ic.empty:
            try:
                irs = rank_ic.apply(
                    lambda s: float(s.mean() / s.std()) if s.std() and not np.isnan(s.std()) else 0.0
                )
                if len(irs) > 0:
                    top_factor = irs.abs().sort_values(ascending=False).index[0]
                    sub = quantile_returns[quantile_returns["factor"] == top_factor]
                    if not sub.empty:
                        pivot = (
                            sub.pivot(index="date", columns="quantile", values="ret")
                            .sort_index()
                            .fillna(0.0)
                        )
                        cum = (1.0 + pivot).cumprod()
                        fig, ax = plt.subplots(figsize=(11, 5))
                        cum.plot(ax=ax)
                        ax.set_title(f"分层累计收益（因子={top_factor}）", **_cjk_text_kwargs())
                        ax.set_ylabel("累计净值", **_cjk_text_kwargs())
                        ax.grid(alpha=0.3)
                        ax.legend(fontsize=8, ncol=5, loc="best")
                        fig.tight_layout()
                        fig.savefig(figs_dir / "quantile_top_factor.png", dpi=140)
                        plt.close(fig)
            except Exception as exc:
                print(f"⚠️ 绘制分层图失败: {exc}")

        # 3) 相关性热力图：取 |rank_ic_ir| Top-30 因子的相关性子矩阵
        if not correlation.empty:
            try:
                if not rank_ic.empty:
                    irs = rank_ic.apply(
                        lambda s: float(s.mean() / s.std()) if s.std() and not np.isnan(s.std()) else 0.0
                    )
                    keep = irs.abs().sort_values(ascending=False).head(30).index.tolist()
                    keep = [c for c in keep if c in correlation.columns]
                    if not keep:
                        keep = correlation.columns.tolist()[:30]
                else:
                    keep = correlation.columns.tolist()[:30]
                sub = correlation.loc[keep, keep]
                fig, ax = plt.subplots(figsize=(8, 7))
                im = ax.imshow(sub.values, cmap="coolwarm", vmin=-1.0, vmax=1.0)
                ax.set_xticks(range(len(keep)))
                ax.set_yticks(range(len(keep)))
                ax.set_xticklabels(keep, rotation=90, fontsize=6)
                ax.set_yticklabels(keep, fontsize=6)
                fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                ax.set_title(f"因子相关性（Top {len(keep)}）", **_cjk_text_kwargs())
                fig.tight_layout()
                fig.savefig(figs_dir / "correlation_heatmap.png", dpi=140)
                plt.close(fig)
            except Exception as exc:
                print(f"⚠️ 绘制相关性热力图失败: {exc}")


# ============================================================================
# 异步运行 / 生成 任务
# ============================================================================

_RUN_LOCK = threading.Lock()
_RUN_STATE: Dict[str, Any] = {
    "running": False,
    "start_time": None,
    "end_time": None,
    "logs": [],
    "last_results": None,
    "error": None,
}

# DeepSeek 因子生成异步任务存储：{job_id: {...}}
_GEN_LOCK = threading.Lock()
_GEN_JOBS: Dict[str, Dict[str, Any]] = {}


def _cjk_text_kwargs() -> Dict[str, Any]:
    return {"fontproperties": _CJK_FONT_PROP} if _CJK_FONT_PROP is not None else {}


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.floating, float)):
        v = float(value)
        return v if np.isfinite(v) else None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    return value


class _LogTee(io.StringIO):
    """把 stdout 同时重定向到 _RUN_STATE['logs'] 缓冲区与原始终端。"""

    def __init__(self, original):
        super().__init__()
        self._original = original

    def write(self, s):
        try:
            self._original.write(s)
        except Exception:
            pass
        if s and s.strip():
            with _RUN_LOCK:
                _RUN_STATE["logs"].append(s.rstrip("\n"))
                # 防止日志爆炸，最多保留最近 800 行
                if len(_RUN_STATE["logs"]) > 800:
                    _RUN_STATE["logs"] = _RUN_STATE["logs"][-800:]
        return len(s)

    def flush(self):
        try:
            self._original.flush()
        except Exception:
            pass


def _run_workflow(cfg: WorkflowCustomFactorsConfig) -> None:
    """后台线程：跑一次完整的 WorkflowCustomFactors，并把结果摘要塞进 _RUN_STATE。"""
    with _RUN_LOCK:
        _RUN_STATE["running"] = True
        _RUN_STATE["start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _RUN_STATE["end_time"] = None
        _RUN_STATE["logs"] = []
        _RUN_STATE["last_results"] = None
        _RUN_STATE["error"] = None

    tee = _LogTee(sys.stdout)
    try:
        with redirect_stdout(tee):
            wf = WorkflowCustomFactors(cfg)
            results = wf.run()
        evaluation: pd.DataFrame = results["factor_evaluation"]
        head_records = (
            evaluation.head(20)
            .round(4)
            .to_dict(orient="records")
            if not evaluation.empty
            else []
        )
        figs_dir = wf.output_dir / "figs"
        figs = []
        for name in ("rank_ic_rolling.png", "quantile_top_factor.png", "correlation_heatmap.png"):
            p = figs_dir / name
            if p.exists():
                figs.append(name)
        with _RUN_LOCK:
            _RUN_STATE["last_results"] = {
                "n_factors_total": int(results["n_factors_total"]),
                "factor_evaluation_head": _json_safe(head_records),
                "figs": figs,
                "output_dir": str(wf.output_dir),
                "end_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception as exc:
        with _RUN_LOCK:
            _RUN_STATE["error"] = f"{type(exc).__name__}: {exc}"
            _RUN_STATE["logs"].append("❌ 运行失败：")
            for line in traceback.format_exc().splitlines():
                _RUN_STATE["logs"].append(line)
    finally:
        with _RUN_LOCK:
            _RUN_STATE["running"] = False
            _RUN_STATE["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")


def _run_generate(job_id: str, payload: Dict[str, Any]) -> None:
    """后台线程：调 DeepSeek 生成一个 custom 因子。"""

    def _set(**kw):
        with _GEN_LOCK:
            _GEN_JOBS[job_id].update(kw)

    _set(running=True, start_time=time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        path = generate_custom_factor(
            description=payload.get("description", ""),
            factor_name=payload.get("factor_name") or None,
            model=payload.get("model") or "deepseek-chat",
            overwrite=bool(payload.get("overwrite", False)),
            dry_run=bool(payload.get("dry_run", False)),
        )
        code_preview = ""
        if path and path.exists():
            try:
                code_preview = path.read_text(encoding="utf-8")
            except Exception:
                pass
        _set(
            running=False,
            ok=True,
            file_path=str(path),
            code_preview=code_preview,
            message=("dry_run 通过校验（未落盘）" if payload.get("dry_run") else f"已落盘到 {path.name}"),
            end_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
    except Exception as exc:
        _set(
            running=False,
            ok=False,
            message=f"{type(exc).__name__}: {exc}",
            traceback=traceback.format_exc(),
            end_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )


# ============================================================================
# Flask Web
# ============================================================================


def _resolve_cache_dir(p: str) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = _THIS_DIR / path
    return path


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
        libs = factor_loader.list_libraries()
        if "custom" not in libs:
            libs = ["custom"] + libs
        return jsonify({"libraries": libs})

    @app.route("/api/llm_config")
    def api_llm_config():
        """返回当前生效的 LLM 配置（key 已脱敏）。"""
        info = describe_llm_config(mask_key=True)
        return jsonify(info)

    @app.route("/api/custom_factors")
    def api_list_custom():
        names = list_custom_factors()
        items = []
        for stem in names:
            f = _CUSTOM_DIR / f"{stem}.py"
            try:
                stat = f.stat()
                mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
                size = stat.st_size
            except Exception:
                mtime, size = "", 0
            items.append({"name": stem, "mtime": mtime, "size": size})
        return jsonify({"items": items})

    @app.route("/api/custom_factors/source")
    def api_custom_source():
        name = (request.args.get("name") or "").strip()
        if not name or name.startswith("_") or "/" in name or "\\" in name:
            return jsonify({"ok": False, "error": "非法 name"}), 400
        path = _CUSTOM_DIR / f"{name}.py"
        if not path.exists():
            return jsonify({"ok": False, "error": f"不存在：{name}.py"}), 404
        try:
            return jsonify({"ok": True, "name": name, "source": path.read_text(encoding="utf-8")})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/custom_factors/delete", methods=["POST"])
    def api_delete_custom():
        body = request.get_json(silent=True) or {}
        name = (body.get("name") or "").strip()
        if not name or name.startswith("_") or "/" in name or "\\" in name:
            return jsonify({"ok": False, "error": "非法 name"}), 400
        path = _CUSTOM_DIR / f"{name}.py"
        if not path.exists():
            return jsonify({"ok": False, "error": "文件不存在"}), 404
        try:
            path.unlink()
            return jsonify({"ok": True})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/custom_factors/generate", methods=["POST"])
    def api_generate_custom():
        body = request.get_json(silent=True) or {}
        if not (body.get("description") or "").strip():
            return jsonify({"ok": False, "error": "description 不能为空"}), 400
        job_id = uuid.uuid4().hex[:12]
        with _GEN_LOCK:
            _GEN_JOBS[job_id] = {
                "running": True,
                "ok": None,
                "message": "",
                "file_path": "",
                "code_preview": "",
                "start_time": "",
                "end_time": "",
            }
        thread = threading.Thread(target=_run_generate, args=(job_id, body), daemon=True)
        thread.start()
        return jsonify({"ok": True, "job_id": job_id})

    @app.route("/api/custom_factors/generate/status")
    def api_generate_status():
        job_id = (request.args.get("job_id") or "").strip()
        with _GEN_LOCK:
            state = _GEN_JOBS.get(job_id)
            if state is None:
                return jsonify({"ok": False, "error": "未知 job_id"}), 404
            return jsonify({"ok": True, "job_id": job_id, **state})

    @app.route("/api/factor_cache/stats")
    def api_factor_cache_stats():
        cfg = load_saved_config()
        cache_dir = _resolve_cache_dir(cfg.factor_cache_dir)
        info = factor_cache.stats(str(cache_dir))
        market_cache_dir = _resolve_cache_dir(cfg.market_data_cache_dir)
        market_info = factor_cache.stats(str(market_cache_dir))
        size_mb = float(info.get("size_bytes", 0)) / 1024 / 1024
        market_size_mb = float(market_info.get("size_bytes", 0)) / 1024 / 1024
        return jsonify(
            {
                "dir": str(cache_dir),
                **info,
                "size_mb": size_mb,
                "market_data_dir": str(market_cache_dir),
                "market_data_count": market_info.get("count", 0),
                "market_data_size_mb": market_size_mb,
            }
        )

    @app.route("/api/factor_cache/clear", methods=["POST"])
    def api_factor_cache_clear():
        cfg = load_saved_config()
        cache_dir = _resolve_cache_dir(cfg.factor_cache_dir)
        deleted = factor_cache.clear(str(cache_dir))
        market_cache_dir = _resolve_cache_dir(cfg.market_data_cache_dir)
        market_deleted = factor_cache.clear(str(market_cache_dir))
        return jsonify(
            {
                "ok": True,
                "deleted": deleted,
                "dir": str(cache_dir),
                "market_data_deleted": market_deleted,
                "market_data_dir": str(market_cache_dir),
            }
        )

    @app.route("/api/config", methods=["GET"])
    def api_get_config():
        cfg = load_saved_config()
        return jsonify(asdict(cfg))

    @app.route("/api/config", methods=["POST"])
    def api_post_config():
        body = request.get_json(silent=True) or {}
        cfg = _merge_config(body)
        save_config(cfg)
        return jsonify({"ok": True, "config": asdict(cfg)})

    @app.route("/api/run", methods=["POST"])
    def api_run():
        with _RUN_LOCK:
            if _RUN_STATE["running"]:
                return jsonify({"ok": False, "error": "已经在运行中"}), 409
        body = request.get_json(silent=True) or {}
        cfg = _merge_config(body)
        save_config(cfg)
        thread = threading.Thread(target=_run_workflow, args=(cfg,), daemon=True)
        thread.start()
        return jsonify({"ok": True, "config": asdict(cfg)})

    @app.route("/api/status")
    def api_status():
        with _RUN_LOCK:
            return jsonify(
                {
                    "running": _RUN_STATE["running"],
                    "start_time": _RUN_STATE["start_time"],
                    "end_time": _RUN_STATE["end_time"],
                    "logs": list(_RUN_STATE["logs"]),
                    "last_results": _RUN_STATE["last_results"],
                    "error": _RUN_STATE["error"],
                }
            )

    @app.route("/api/figs/<path:name>")
    def api_fig(name: str):
        cfg = load_saved_config()
        figs_dir = _THIS_DIR / cfg.output_dir / "figs"
        target = (figs_dir / name).resolve()
        # 防止越权访问
        if not str(target).startswith(str(figs_dir.resolve())):
            return ("forbidden", 403)
        if not target.exists():
            return ("not found", 404)
        return send_file(str(target), mimetype="image/png")

    return app


def _merge_config(body: Dict[str, Any]) -> WorkflowCustomFactorsConfig:
    """把前端 form/json 的字段合进默认 + 已有配置。"""
    default = asdict(WorkflowCustomFactorsConfig())
    merged = asdict(load_saved_config())
    for k, v in (body or {}).items():
        if k not in default:
            continue
        target_type = type(default[k])
        try:
            if target_type is bool:
                merged[k] = bool(v) if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on")
            elif target_type is int:
                merged[k] = int(v)
            elif target_type is float:
                merged[k] = float(v)
            elif target_type is list:
                if isinstance(v, list):
                    merged[k] = [str(x) for x in v]
                elif isinstance(v, str):
                    # 表单可能传逗号分隔
                    merged[k] = [s for s in (x.strip() for x in v.split(",")) if s]
            else:
                merged[k] = str(v)
        except Exception:
            # 类型转换失败时保留原值，避免一处脏数据让整次保存失败
            continue
    return WorkflowCustomFactorsConfig(**merged)


# ============================================================================
# 入口
# ============================================================================


def main_cli() -> None:
    cfg = load_saved_config()
    save_config(cfg)
    wf = WorkflowCustomFactors(cfg)
    wf.run()


def main_web(host: str = "127.0.0.1", port: int = 8000) -> None:
    app = _build_flask_app()
    # 屏蔽 werkzeug 的 HTTP 访问日志（避免 /api/status 轮询噪音刷屏）
    _wlog = logging.getLogger("werkzeug")
    _wlog.setLevel(logging.ERROR)
    _wlog.disabled = True

    print("=" * 80)
    print(f"自定义因子 Web 控制台已启动: http://{host}:{port}")
    print("=" * 80)
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


# HTML 渲染：实现见同文件下方 _render_index_html
from _workflow_custom_factors_html import render_index_html as _render_index_html  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自定义因子 Web 控制台")
    parser.add_argument("--cli", action="store_true", help="不启动 Web，直接命令行运行")
    parser.add_argument("--port", type=int, default=8000, help="Web 端口（默认 8000）")
    parser.add_argument("--host", default="127.0.0.1", help="Web 主机（默认 127.0.0.1）")
    args = parser.parse_args()
    if args.cli:
        main_cli()
    else:
        main_web(args.host, args.port)
