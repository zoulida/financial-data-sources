#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Windows 下优先使用常见中文字体，避免图表中的中文变成方框
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

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

from opentdx_loader import OpenTdxDataLoader, ensure_dir, resolve_opentdx_path

try:
    from flask import Flask, abort, jsonify, request, send_from_directory
except ImportError:
    Flask = None
    jsonify = None
    request = None
    abort = None
    send_from_directory = None

CONFIG_FILE = _THIS_DIR / "workflow_opentdx_config.json"
BENCHMARK_NAMES = {
    "000300.SH": "沪深300",
    "000852.SH": "中证1000",
    "999999.SH": "上证综指",
    "932000.SH": "中证2000",
}


@dataclass
class OpenTdxWorkflowConfig:
    opentdx_path: str = field(default_factory=lambda: str(resolve_opentdx_path()))
    start_time: str = "2024-11-01"
    end_time: str = "2026-04-30"
    markets: list[str] = field(default_factory=lambda: ["SZ", "SH", "BJ"])
    max_price: float = 15.0
    max_market_cap_yi: float = 120.0
    market_cap_kind: str = "total"
    topn: int = 30
    rebalance_freq: str = "W-FRI"
    holding_period: int = 5
    kline_count: int = 360
    initial_account: float = 1_000_000.0
    open_cost: float = 0.0
    close_cost: float = 0.0
    slippage: float = 0.0
    output_dir: str = "outputs"
    enable_data_cache: bool = True
    cache_dir: str = "cache"
    force_refresh_cache: bool = False
    debug_max_codes: int = 30
    # v2 新增：因子库配置
    enabled_factor_groups: list[str] = field(default_factory=lambda: [
        "momentum", "reversal", "volatility", "turnover",
        "corr", "position", "indicator", "relative_pattern", "share_change",
    ])
    # v2 新增：IC 筛选阈值
    min_rank_ic_ir: float = 0.30
    min_ic_win_rate: float = 0.55
    # v2 新增：基准（默认沪深300，用于超额收益）
    benchmark_codes: list[str] = field(default_factory=lambda: ["000300.SH", "000852.SH", "999999.SH", "932000.SH"])
    # 兼容旧配置：保留但不再起作用
    enable_capital_flow_factor: bool = True
    enable_board_heat_factor: bool = False
    enable_unusual_factor: bool = True
    enable_ml_strategy: bool = False
    factor_weights: dict[str, float] = field(default_factory=dict)


def load_saved_config() -> OpenTdxWorkflowConfig:
    default = OpenTdxWorkflowConfig()
    if not CONFIG_FILE.exists():
        return default
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        valid = set(asdict(default).keys())
        merged = {**asdict(default), **{k: v for k, v in data.items() if k in valid}}
        if not isinstance(merged.get("markets"), list):
            merged["markets"] = [x.strip() for x in str(merged.get("markets", "SZ,SH,BJ")).split(",") if x.strip()]
        if not isinstance(merged.get("factor_weights"), dict):
            merged["factor_weights"] = default.factor_weights
        if not isinstance(merged.get("enabled_factor_groups"), list):
            merged["enabled_factor_groups"] = [x.strip() for x in str(merged.get("enabled_factor_groups", "")).split(",") if x.strip()] or default.enabled_factor_groups
        if not isinstance(merged.get("benchmark_codes"), list):
            merged["benchmark_codes"] = [x.strip() for x in str(merged.get("benchmark_codes", "")).split(",") if x.strip()] or default.benchmark_codes
        return OpenTdxWorkflowConfig(**merged)
    except Exception as exc:
        print(f"⚠️ 读取配置失败，使用默认配置: {exc}")
        return default


def save_config(config: OpenTdxWorkflowConfig) -> None:
    CONFIG_FILE.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 已保存配置: {CONFIG_FILE}")


class OpenTdxWorkflow:
    def __init__(self, config: OpenTdxWorkflowConfig) -> None:
        self.config = config
        self.cache_dir = _THIS_DIR / config.cache_dir
        self.base_output_dir = _THIS_DIR / config.output_dir
        self.run_id = time.strftime("%Y%m%d_%H%M%S")
        self.output_dir = ensure_dir(self.base_output_dir / self.run_id)
        self.loader = OpenTdxDataLoader(
            opentdx_path=config.opentdx_path,
            cache_dir=self.cache_dir,
            enable_cache=config.enable_data_cache,
            force_refresh=config.force_refresh_cache,
        )
        self.stock_list = pd.DataFrame()
        self.quotes = pd.DataFrame()
        self.universe = pd.DataFrame()
        self.panel: dict[str, pd.DataFrame] = {}
        self.future_return = pd.DataFrame()
        self.factor_dict: dict[str, pd.DataFrame] = {}
        self.factor_groups: dict[str, str] = {}  # factor_name -> group_name
        self.standardized_factors: dict[str, pd.DataFrame] = {}
        self.factor_scores = pd.DataFrame()
        self.strategy_scores: dict[str, pd.DataFrame] = {}
        self.strategy_weights: dict[str, pd.DataFrame] = {}
        self.selection = pd.DataFrame()
        self.target_weights = pd.DataFrame()
        self.selected_factors: list[str] = []  # IC 筛选后保留的因子
        self.factor_directions: dict[str, int] = {}  # +1 或 -1（按 rank_ic 方向自动确定）
        self.factor_auto_weights: dict[str, float] = {}
        self.benchmark_close: dict[str, pd.Series] = {}  # ts_code -> close series
        self.results: dict[str, Any] = {}

    def run(self) -> dict[str, Any]:
        print("🚀 OpenTDX 多因子 workflow 启动")
        print("=" * 80)
        step_times: list[tuple[str, float]] = []

        def _timed(name: str, func, *args, **kwargs):
            t0 = time.perf_counter()
            result = func(*args, **kwargs)
            dt = time.perf_counter() - t0
            step_times.append((name, dt))
            print(f"⏱  [{name}] 耗时 {dt:.2f}s")
            return result

        t0 = time.perf_counter()
        _timed("第一步:初始化OpenTDX", self._init_opentdx)
        _timed("第二步:加载股票列表与报价", self._load_stock_list_and_quotes)
        pool_report = _timed("第二点五步:股票池过滤", self._filter_stock_pool)
        _timed("第三步:加载历史K线", self._load_market_data)
        _timed("第三点五步:加载基准指数", self._load_benchmarks)
        _timed("第四步:构造未来收益", self._build_future_return)
        _timed("第五步:计算基础因子", self._build_factors)
        _timed("第六步:横截面标准化", self._standardize_factors)
        evaluation, rank_ic, quantile_returns = _timed("第七步:单因子评价", self._evaluate_factors)
        filter_report, correlation = _timed("第七点五步:因子筛选与相关性", lambda: self._filter_factors(evaluation))
        _timed("第八步:构造综合信号", self._build_signals)
        performance, quantile_curves, benchmark_curves, excess_metrics = _timed(
            "第九步:组合回测+分位+基准", self._run_backtest_full,
        )
        self.results.update({
            "stock_pool_report": pool_report,
            "factor_evaluation": evaluation,
            "rank_ic": rank_ic,
            "quantile_returns": quantile_returns,
            "factor_filter_report": filter_report,
            "factor_correlation": correlation,
            "factor_auto_weights": pd.DataFrame(
                [{"factor": k, "direction": self.factor_directions.get(k, 1), "weight": v}
                 for k, v in self.factor_auto_weights.items()]
            ),
            "performance": performance,
            "quantile_curves": quantile_curves,
            "benchmark_curves": benchmark_curves,
            "excess_metrics": excess_metrics,
            "output_dir": str(self.output_dir),
        })
        _timed("第十步:保存结果", self._save_results)
        _timed("第十一步:生成图表", self._plot_results)
        total = time.perf_counter() - t0
        # 将步骤耗时写入 self.results，供 CLI 和 Web 一起读取
        self.results["step_times"] = [{"step": name, "seconds": float(dt)} for name, dt in step_times]
        self.results["total_time"] = float(total)
        print("\n⏲ 各步骤耗时：")
        for name, dt in step_times:
            print(f"  - {name:<18s} {dt:7.2f}s ({dt / total * 100 if total else 0:5.1f}%)")
        print(f"🕛 总耗时: {total:.2f}s")
        print(f"📁 结果目录: {self.output_dir}")
        print("🎉 workflow 完成")
        return self.results

    def _init_opentdx(self) -> None:
        path = resolve_opentdx_path(self.config.opentdx_path)
        if not (path / "opentdx" / "tdxClient.py").exists():
            raise FileNotFoundError(f"OpenTDX 路径不可用: {path}")
        print(f"✅ OpenTDX 路径: {path}")
        print(f"✅ 缓存目录: {self.cache_dir}")

    def _load_stock_list_and_quotes(self) -> None:
        cfg = self.config
        self.stock_list = self.loader.load_stock_list(cfg.markets)
        if self.stock_list.empty:
            raise RuntimeError("OpenTDX 股票列表为空")
        stock = self.stock_list.copy()
        code_raw = stock["code"].astype(str).str.zfill(6)
        common_a_mask = (
            code_raw.str.startswith(("000", "001", "002", "003", "300", "301", "600", "601", "603", "605", "688", "689", "430", "830", "831", "832", "833", "834", "835", "836", "837", "838", "839", "870", "871", "872", "873", "920"))
            & ~stock.get("name", pd.Series("", index=stock.index)).astype(str).str.contains("指数|基金|债|ETF|LOF|退", case=False, na=False)
        )
        candidate_stock = stock.loc[common_a_mask].copy()
        if candidate_stock.empty:
            candidate_stock = stock
        codes = candidate_stock["ts_code"].dropna().astype(str).tolist()
        if cfg.debug_max_codes and cfg.debug_max_codes > 0:
            codes = codes[: int(cfg.debug_max_codes)]
            print(f"🧪 Debug 模式限制股票数量: {len(codes)}")
        self.quotes = self.loader.load_quotes(codes)
        print(f"✅ 股票列表 {len(self.stock_list)} 条，报价 {len(self.quotes)} 条")

    def _filter_stock_pool(self) -> pd.DataFrame:
        cfg = self.config
        if self.quotes.empty:
            raise RuntimeError("报价数据为空，无法过滤股票池")
        quote = self.quotes.copy()
        names = self.stock_list[["ts_code", "name"]].drop_duplicates("ts_code") if "name" in self.stock_list.columns else pd.DataFrame(columns=["ts_code", "name"])
        quote = quote.merge(names, on="ts_code", how="left", suffixes=("", "_list"))
        if "name_list" in quote.columns:
            quote["name"] = quote.get("name").fillna(quote["name_list"])
        quote["close"] = pd.to_numeric(quote.get("close"), errors="coerce")
        quote["amount"] = pd.to_numeric(quote.get("amount"), errors="coerce")
        quote["market_cap_yi"] = pd.to_numeric(quote.get("market_cap_yi"), errors="coerce")
        quote["drop_reason"] = ""
        conditions = [
            (quote["close"].isna() | (quote["close"] <= 0), "无有效价格"),
            (quote["close"] >= cfg.max_price, f"价格>= {cfg.max_price}"),
            (quote["market_cap_yi"].notna() & (quote["market_cap_yi"] >= cfg.max_market_cap_yi), f"市值>= {cfg.max_market_cap_yi}亿"),
            (quote.get("name", pd.Series("", index=quote.index)).astype(str).str.contains("ST", case=False, na=False), "ST"),
        ]
        keep = pd.Series(True, index=quote.index)
        for mask, reason in conditions:
            mask = mask.fillna(False)
            quote.loc[mask & (quote["drop_reason"] == ""), "drop_reason"] = reason
            keep &= ~mask
        self.universe = quote.loc[keep].copy().reset_index(drop=True)
        # 详细报告：原始 -> 各原因丢弃 -> 最终股票池
        report_rows: list[dict[str, Any]] = [
            {"step": "原始报价", "kept": int(len(quote)), "dropped": 0, "examples": ""},
        ]
        reason_counts = quote.loc[quote["drop_reason"] != "", "drop_reason"].value_counts()
        for reason, cnt in reason_counts.items():
            examples = quote.loc[quote["drop_reason"] == reason, "ts_code"].head(5).astype(str).tolist()
            report_rows.append({"step": f"丢弃:{reason}", "kept": 0, "dropped": int(cnt), "examples": ",".join(examples)})
        report_rows.append({
            "step": "过滤后股票池",
            "kept": int(len(self.universe)),
            "dropped": int(len(quote) - len(self.universe)),
            "examples": ",".join(self.universe.get("ts_code", pd.Series(dtype=str)).head(5).astype(str).tolist()),
        })
        report = pd.DataFrame(report_rows)
        # 保存被丢弃记录供查验
        self._dropped_quotes = quote.loc[quote["drop_reason"] != ""].copy()
        if self.universe.empty:
            raise RuntimeError("股票池过滤后为空，请放宽价格/市值条件或关闭 debug 限制")
        print(f"✅ 股票池过滤完成: {len(quote)} → {len(self.universe)}")
        return report

    def _load_market_data(self) -> None:
        codes = self.universe["ts_code"].astype(str).tolist()
        count = self._effective_kline_count()
        self.panel = self.loader.load_kline_panel(
            codes,
            count=count,
            start_time=self.config.start_time,
            end_time=self.config.end_time,
        )
        close = self.panel.get("close", pd.DataFrame())
        if close.empty:
            raise RuntimeError("历史 K 线 close 面板为空")
        start = pd.Timestamp(self.config.start_time)
        end = pd.Timestamp(self.config.end_time)
        for key, df in list(self.panel.items()):
            if not df.empty:
                self.panel[key] = df.loc[(df.index >= start) & (df.index <= end)].sort_index()
        if self.panel.get("close", pd.DataFrame()).empty:
            raise RuntimeError("按日期截断后 close 面板为空")
        print(f"✅ close 面板形状: {self.panel['close'].shape}")

    def _effective_kline_count(self) -> int:
        base = max(int(self.config.kline_count), 1)
        try:
            start = pd.to_datetime(self.config.start_time)
            end = pd.to_datetime(self.config.end_time)
            span_days = max(int((end - start).days), 1)
            auto_count = span_days + 260
        except Exception:
            span_days = 0
            auto_count = base
        count = max(base, auto_count)
        print(f"  自动K线请求数量: 配置下限={base}, 日期跨度={span_days}天, 实际请求={count}根")
        return count

    def _build_future_return(self) -> None:
        close = self.panel["close"]
        hp = max(int(self.config.holding_period), 1)
        self.future_return = close.shift(-hp) / close - 1.0
        print(f"✅ future_return 形状: {self.future_return.shape}, holding_period={hp}")

    def _load_benchmarks(self) -> None:
        """加载基准指数 K 线，落到 self.benchmark_close（dict[ts_code -> Series]）。"""
        self.benchmark_close = {}
        if not self.config.benchmark_codes:
            return
        for ts_code in self.config.benchmark_codes:
            ts_code = str(ts_code).strip().upper()
            if not (ts_code.endswith(".SH") or ts_code.endswith(".SZ")):
                print(f"⚠️ 基准 {ts_code} 未带交易所后缀，跳过；请用 000300.SH 这种格式，避免和股票代码混淆")
                continue
            try:
                suffix = "上海" if ts_code.endswith(".SH") else "深圳"
                name = BENCHMARK_NAMES.get(ts_code, "指数")
                print(f"  准备加载基准指数: {name} {ts_code}（{suffix}市场指数代码，走 index_kline 缓存）")
                df = self.loader.load_index_kline(
                    ts_code,
                    count=self._effective_kline_count(),
                    start_time=self.config.start_time,
                    end_time=self.config.end_time,
                )
                if isinstance(df, pd.DataFrame) and not df.empty and "close" in df.columns:
                    self.benchmark_close[ts_code] = pd.to_numeric(df["close"], errors="coerce").dropna()
                    print(f"  基准 {name} {ts_code} K线 {len(df)} 行")
            except Exception as exc:
                print(f"⚠️ 基准 {ts_code} 加载失败: {exc}")
        print(f"✅ 加载基准 {len(self.benchmark_close)} / {len(self.config.benchmark_codes)}")

    def _build_factors(self) -> None:
        """从 factors/ 子模块自动收集所有因子（按 enabled_factor_groups 启用）。"""
        import importlib

        close = self.panel["close"]
        # 准备 ctx：用第一只基准（默认上证综指）作为相对强度类的对标
        index_close = pd.Series(dtype=float)
        if self.benchmark_close:
            index_close = next(iter(self.benchmark_close.values()))
        ctx: dict[str, Any] = {"index_close": index_close, "config": self.config}

        groups = self.config.enabled_factor_groups or []
        all_factors: dict[str, pd.DataFrame] = {}
        all_groups: dict[str, str] = {}
        for group in groups:
            try:
                mod = importlib.import_module(f"factors.{group}")
                got = mod.get_factors(self.panel, ctx)
            except Exception as exc:
                print(f"⚠️ factors.{group} 加载失败，跳过: {exc}")
                continue
            cnt = 0
            for name, df in got.items():
                if not isinstance(df, pd.DataFrame) or df.empty:
                    continue
                aligned = df.reindex_like(close).astype(float)
                # 过滤全 NaN 的因子
                if aligned.notna().sum().sum() == 0:
                    continue
                all_factors[name] = aligned
                all_groups[name] = group
                cnt += 1
            print(f"  factors.{group} -> {cnt} 个")
        if not all_factors:
            raise RuntimeError("所有因子组都返回空，请检查 enabled_factor_groups 与 K 线数据")
        self.factor_dict = all_factors
        self.factor_groups = all_groups
        print(f"✅ 已构造 {len(self.factor_dict)} 个因子，覆盖 {len(set(all_groups.values()))} 组")

    @staticmethod
    def _winsorize_zscore(df: pd.DataFrame, limit: float = 5.0) -> pd.DataFrame:
        median = df.median(axis=1)
        mad = df.sub(median, axis=0).abs().median(axis=1).replace(0.0, np.nan)
        upper = median + limit * 1.4826 * mad
        lower = median - limit * 1.4826 * mad
        clipped = df.clip(lower=lower, upper=upper, axis=0)
        mean = clipped.mean(axis=1)
        std = clipped.std(axis=1).replace(0.0, np.nan)
        return clipped.sub(mean, axis=0).div(std, axis=0)

    def _standardize_factors(self) -> None:
        self.standardized_factors = {name: self._winsorize_zscore(df) for name, df in self.factor_dict.items()}
        print(f"✅ 标准化完成: {len(self.standardized_factors)} 个因子")

    def _evaluate_factors(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        future = self.future_return
        rows: list[dict[str, Any]] = []
        rank_ic = pd.DataFrame(index=future.index)
        quantile_rows: list[dict[str, Any]] = []
        for name, df in self.standardized_factors.items():
            aligned = df.reindex_like(future)
            ic = aligned.corrwith(future, axis=1, method="pearson")
            ric = aligned.corrwith(future, axis=1, method="spearman")
            rows.append({
                "factor": name,
                "ic_mean": float(ic.mean()),
                "ic_ir": float(ic.mean() / ic.std()) if float(ic.std()) > 0 else 0.0,
                "rank_ic_mean": float(ric.mean()),
                "rank_ic_ir": float(ric.mean() / ric.std()) if float(ric.std()) > 0 else 0.0,
                "ic_win_rate": float((ic > 0).mean()),
            })
            rank_ic[name] = ric
            ranks = aligned.rank(axis=1, pct=True)
            for q in range(1, 6):
                low, high = (q - 1) / 5, q / 5
                mask = (ranks > low) & (ranks <= high) if q > 1 else (ranks >= low) & (ranks <= high)
                qret = future.where(mask).mean(axis=1)
                for dt, value in qret.dropna().items():
                    quantile_rows.append({"factor": name, "date": dt, "quantile": f"Q{q}", "ret": float(value)})
        evaluation = pd.DataFrame(rows).sort_values("rank_ic_ir", key=lambda s: s.abs(), ascending=False).reset_index(drop=True) if rows else pd.DataFrame()
        quantile_returns = pd.DataFrame(quantile_rows)
        print(f"✅ 因子评价完成: {len(evaluation)} 个因子")
        return evaluation, rank_ic, quantile_returns

    def _build_rebalance_mask(self, index: pd.Index) -> pd.Series:
        dt_index = pd.to_datetime(index)
        periods = dt_index.to_period(self.config.rebalance_freq)
        first_dates = pd.Series(dt_index, index=index).groupby(periods).head(1).index
        mask = pd.Series(False, index=index)
        mask.loc[first_dates] = True
        return mask

    def _filter_factors(self, evaluation: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """按 IC_IR 与胜率筛选因子，并算因子相关性。"""
        if evaluation.empty:
            self.selected_factors = []
            self.factor_directions = {}
            return pd.DataFrame(), pd.DataFrame()
        thresh_ir = float(self.config.min_rank_ic_ir)
        thresh_win = float(self.config.min_ic_win_rate)
        rows = []
        for _, r in evaluation.iterrows():
            name = r["factor"]
            ric_ir = float(r.get("rank_ic_ir", 0.0))
            win = float(r.get("ic_win_rate", 0.0))
            # 接受双向：|IR| >= 阈值 且 max(win, 1-win) >= 阈值
            keep = (abs(ric_ir) >= thresh_ir) and (max(win, 1.0 - win) >= thresh_win)
            direction = 1 if ric_ir >= 0 else -1
            reason = ""
            if not keep:
                if abs(ric_ir) < thresh_ir:
                    reason = f"|rank_ic_ir|<{thresh_ir}"
                else:
                    reason = f"胜率偏离 0.5 不足 {thresh_win}"
            rows.append({
                "factor": name,
                "group": self.factor_groups.get(name, ""),
                "rank_ic_ir": ric_ir,
                "rank_ic_mean": float(r.get("rank_ic_mean", 0.0)),
                "ic_win_rate": win,
                "direction": direction,
                "kept": bool(keep),
                "reason": reason,
            })
        report = pd.DataFrame(rows)
        kept = report.loc[report["kept"]].copy()
        self.selected_factors = kept["factor"].tolist()
        self.factor_directions = {row["factor"]: int(row["direction"]) for _, row in kept.iterrows()}
        # 全量 IR 映射（含未通过筛选的，回退路径会用）
        self.factor_ir_map = evaluation.set_index("factor")["rank_ic_ir"].to_dict()
        # 因子相关性（仅在保留的因子之间），用每日横截面排名相关均值作为代理
        if self.selected_factors:
            future = self.future_return
            sample_dates = future.index[::max(len(future.index) // 30, 1)]
            corr_sum = pd.DataFrame(0.0, index=self.selected_factors, columns=self.selected_factors)
            n_dates = 0
            for dt in sample_dates:
                vecs = {}
                for name in self.selected_factors:
                    df = self.standardized_factors.get(name)
                    if df is None or dt not in df.index:
                        continue
                    s = df.loc[dt].rank()
                    if s.notna().sum() < 5:
                        continue
                    vecs[name] = s
                if len(vecs) < 2:
                    continue
                cdf = pd.DataFrame(vecs).corr().reindex(index=self.selected_factors, columns=self.selected_factors)
                corr_sum = corr_sum.add(cdf.fillna(0.0), fill_value=0.0)
                n_dates += 1
            correlation = corr_sum / max(n_dates, 1)
        else:
            correlation = pd.DataFrame()
        kept_n, dropped_n = int(report["kept"].sum()), int((~report["kept"]).sum())
        print(f"✅ 因子筛选: 保留 {kept_n} / 剔除 {dropped_n}（阈值 |IR|≥{thresh_ir}, 胜率偏离≥{thresh_win}）")
        return report, correlation

    def _build_signals(self) -> None:
        close = self.panel["close"]
        ir_map = getattr(self, "factor_ir_map", {}) or {}
        # 选用 IC 筛选后的因子；若一个都没保留则回退到 IR 绝对值 Top5
        selected = list(self.selected_factors)
        if not selected and ir_map:
            top = sorted(ir_map.items(), key=lambda kv: abs(kv[1]), reverse=True)[:5]
            selected = [name for name, _ in top]
            self.factor_directions = {name: (1 if ir >= 0 else -1) for name, ir in top}
            print(f"⚠️ 没有因子通过筛选，回退到 IR 绝对值 Top5: {selected}")
        if not selected:
            raise RuntimeError("没有可用因子用于合成信号")

        # IC_IR 加权
        raw_weights = {name: abs(float(ir_map.get(name, 0.0))) for name in selected}
        scale = sum(raw_weights.values()) or 1.0
        self.factor_auto_weights = {k: v / scale for k, v in raw_weights.items()}

        # 合成分数：方向 × 标准化因子 × 权重
        score = pd.DataFrame(0.0, index=close.index, columns=close.columns)
        for name in selected:
            df = self.standardized_factors.get(name)
            if df is None:
                continue
            d = float(self.factor_directions.get(name, 1))
            w = float(self.factor_auto_weights.get(name, 0.0))
            score = score.add(df.reindex_like(close).fillna(0.0) * (d * w), fill_value=0.0)
        self.factor_scores = score

        # 多策略信号：IC加权、多因子等权、动量、低波动、机器学习线性预测
        equal_score = pd.DataFrame(0.0, index=close.index, columns=close.columns)
        for name in selected:
            df = self.standardized_factors.get(name)
            if df is not None:
                equal_score = equal_score.add(df.reindex_like(close).fillna(0.0) * float(self.factor_directions.get(name, 1)), fill_value=0.0)
        equal_score = equal_score / max(len(selected), 1)

        momentum_score = self.standardized_factors.get("mom_20", score).reindex_like(close).fillna(0.0)
        lowvol_base = self.standardized_factors.get("vol_20", score).reindex_like(close).fillna(0.0)
        lowvol_score = -lowvol_base
        self.strategy_scores = {
            "ic_weighted": score,
            "equal_weighted": equal_score,
            "momentum_20": momentum_score,
            "low_volatility": lowvol_score,
        }
        if bool(self.config.enable_ml_strategy):
            ml_score = self._build_ml_linear_score(selected)
            self.strategy_scores["ml_linear"] = ml_score
        else:
            print("ℹ️ 机器学习策略未启用，跳过 ml_linear")
        self.strategy_weights = {}
        for name, score_df in self.strategy_scores.items():
            self.strategy_weights[name] = self._score_to_target_weights(score_df)
        self.selection = self.strategy_weights["ic_weighted"].gt(0)
        self.target_weights = self.strategy_weights["ic_weighted"]
        print(f"✅ 信号完成: 策略 {len(self.strategy_weights)} 个，因子 {len(selected)} 个，TopN={self.config.topn}")

    def _score_to_target_weights(self, score: pd.DataFrame) -> pd.DataFrame:
        close = self.panel["close"]
        score = score.reindex_like(close)
        rebalance = self._build_rebalance_mask(close.index)
        target = pd.DataFrame(0.0, index=close.index, columns=close.columns)
        last = pd.Series(0.0, index=close.columns)
        for dt in close.index:
            if bool(rebalance.get(dt, False)):
                row = score.loc[dt].replace([np.inf, -np.inf], np.nan).dropna().sort_values(ascending=False)
                picked = row.head(max(int(self.config.topn), 1)).index.tolist()
                last = pd.Series(0.0, index=close.columns)
                if picked:
                    last.loc[picked] = 1.0 / len(picked)
            target.loc[dt] = last.values
        return target.shift(1).fillna(0.0)

    def _build_ml_linear_score(self, selected: list[str]) -> pd.DataFrame:
        close = self.panel["close"]
        if not selected:
            return self.factor_scores.copy()
        ir_map = getattr(self, "factor_ir_map", {}) or {}
        selected = sorted(selected, key=lambda x: abs(float(ir_map.get(x, 0.0))), reverse=True)[:20]
        print(f"  ML策略开始: 使用 Top{len(selected)} 因子，样本股票 {close.shape[1]} 只，日期 {close.shape[0]} 天")
        future = self.future_return.reindex_like(close)
        score = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
        rebalance = self._build_rebalance_mask(close.index)
        rebalance_dates = [dt for i, dt in enumerate(close.index) if bool(rebalance.get(dt, False)) and i >= max(40, int(self.config.holding_period) * 8)]
        total_jobs = max(len(rebalance_dates), 1)
        done_jobs = 0
        min_train_days = max(40, int(self.config.holding_period) * 8)
        ridge = 1e-3
        dates = list(close.index)
        for i, dt in enumerate(dates):
            if not bool(rebalance.get(dt, False)) or i < min_train_days:
                continue
            done_jobs += 1
            if done_jobs == 1 or done_jobs == total_jobs or done_jobs % 10 == 0:
                print(f"  ML训练进度 {done_jobs}/{total_jobs} ({done_jobs / total_jobs * 100:.1f}%) 当前调仓日 {pd.Timestamp(dt).date()}", flush=True)
            train_dates = dates[max(0, i - 252):i]
            xs, ys = [], []
            for td in train_dates:
                y = future.loc[td] if td in future.index else None
                if y is None:
                    continue
                mats = []
                for fname in selected:
                    f = self.standardized_factors.get(fname)
                    if f is not None and td in f.index:
                        mats.append(f.loc[td].reindex(close.columns))
                if len(mats) != len(selected):
                    continue
                xdf = pd.concat(mats, axis=1)
                xdf.columns = selected
                tmp = xdf.assign(_y=y).replace([np.inf, -np.inf], np.nan).dropna()
                if len(tmp) >= max(10, len(selected) + 2):
                    xs.append(tmp[selected].to_numpy(dtype=float))
                    ys.append(tmp["_y"].to_numpy(dtype=float))
            if not xs:
                continue
            x = np.vstack(xs)
            y = np.concatenate(ys)
            if len(y) < max(50, len(selected) * 3):
                continue
            x_mean = x.mean(axis=0)
            x_std = x.std(axis=0)
            x_std[x_std == 0] = 1.0
            xz = (x - x_mean) / x_std
            y_center = y - y.mean()
            xtx = xz.T @ xz + ridge * np.eye(len(selected))
            try:
                beta = np.linalg.solve(xtx, xz.T @ y_center)
            except np.linalg.LinAlgError:
                beta = np.linalg.pinv(xtx) @ xz.T @ y_center
            today_cols = []
            for fname in selected:
                f = self.standardized_factors.get(fname)
                today_cols.append(f.loc[dt].reindex(close.columns) if f is not None and dt in f.index else pd.Series(np.nan, index=close.columns))
            today_x = pd.concat(today_cols, axis=1)
            today_x.columns = selected
            pred = ((today_x - x_mean) / x_std).to_numpy(dtype=float) @ beta
            score.loc[dt] = pred
        score = score.ffill().reindex_like(close)
        if score.notna().sum().sum() == 0:
            print("⚠️ 机器学习策略训练样本不足，回退到 IC 加权分数")
            return self.factor_scores.copy()
        print("✅ 机器学习线性策略完成: 滚动 Ridge 横截面预测")
        return score.fillna(self.factor_scores)

    def _run_backtest_full(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """组合回测 + 5 分位组净值 + 基准对齐与超额指标。"""
        close = self.panel["close"]
        ret = close.pct_change(fill_method=None).fillna(0.0)
        rows = []
        strategy_returns: dict[str, pd.Series] = {}
        strategy_equity: dict[str, pd.Series] = {}
        strategy_drawdown: dict[str, pd.Series] = {}
        weights_map = self.strategy_weights or {"ic_weighted": self.target_weights}
        for name, weight_df in weights_map.items():
            weights = weight_df.reindex_like(close).fillna(0.0)
            gross = (weights.shift(1).fillna(0.0) * ret).sum(axis=1)
            turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
            cost = turnover * (float(self.config.open_cost) + float(self.config.close_cost) + float(self.config.slippage))
            strategy_ret = gross - cost
            equity = (1.0 + strategy_ret).cumprod() * float(self.config.initial_account)
            drawdown = equity / equity.cummax() - 1.0
            strategy_returns[name] = strategy_ret
            strategy_equity[name] = equity
            strategy_drawdown[name] = drawdown
            total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) > 1 else 0.0
            days = max((equity.index[-1] - equity.index[0]).days, 1) if len(equity) > 1 else 1
            annual_return = (1.0 + total_return) ** (365.0 / days) - 1.0
            sharpe = float(strategy_ret.mean() / strategy_ret.std() * np.sqrt(252)) if float(strategy_ret.std()) > 0 else 0.0
            rows.append({
                "signal": f"opentdx_v2_{name}",
                "start": str(equity.index[0].date()) if len(equity) else "",
                "end": str(equity.index[-1].date()) if len(equity) else "",
                "total_return": total_return,
                "annual_return": annual_return,
                "max_drawdown": float(drawdown.min()) if len(drawdown) else 0.0,
                "sharpe": sharpe,
                "final_equity": float(equity.iloc[-1]) if len(equity) else float(self.config.initial_account),
            })
        performance = pd.DataFrame(rows)
        primary = "ic_weighted" if "ic_weighted" in strategy_equity else next(iter(strategy_equity))
        self.results["equity_curve"] = strategy_equity[primary]
        self.results["returns"] = strategy_returns[primary]
        self.results["drawdown"] = strategy_drawdown[primary]
        self.results["strategy_equity_curves"] = pd.DataFrame({k: v / float(self.config.initial_account) for k, v in strategy_equity.items()})
        print("✅ 多策略回测完成")
        print(performance.to_string(index=False))

        # ---- 5 分位组累计净值 ----
        quantile_curves = self._compute_quantile_curves(ret)

        # ---- 基准对齐与超额指标 ----
        benchmark_curves, excess_metrics = self._compute_benchmark_curves(strategy_returns)

        return performance, quantile_curves, benchmark_curves, excess_metrics

    def _compute_quantile_curves(self, daily_ret: pd.DataFrame) -> pd.DataFrame:
        """按综合分数把每个调仓日 universe 分 5 组等权，逐日推进，返回 (date × Q1..Q5+LS) 净值。"""
        score = self.factor_scores
        if score.empty:
            return pd.DataFrame()
        close = self.panel["close"]
        rebalance = self._build_rebalance_mask(close.index)
        rebalance_dates = list(close.index[rebalance.values])
        if not rebalance_dates:
            return pd.DataFrame()

        n_q = 5
        weights_by_q: dict[int, pd.DataFrame] = {q: pd.DataFrame(0.0, index=close.index, columns=close.columns) for q in range(1, n_q + 1)}
        last_w: dict[int, pd.Series] = {q: pd.Series(0.0, index=close.columns) for q in range(1, n_q + 1)}
        for dt in close.index:
            if bool(rebalance.get(dt, False)):
                row = score.loc[dt].replace([np.inf, -np.inf], np.nan).dropna()
                if len(row) >= n_q:
                    ranks = row.rank(pct=True)
                    for q in range(1, n_q + 1):
                        low, high = (q - 1) / n_q, q / n_q
                        if q == 1:
                            mask = (ranks >= low) & (ranks <= high)
                        else:
                            mask = (ranks > low) & (ranks <= high)
                        codes = ranks.index[mask].tolist()
                        cnt = len(codes)
                        w = pd.Series(0.0, index=close.columns)
                        if cnt > 0:
                            w.loc[codes] = 1.0 / cnt
                        last_w[q] = w
            for q in range(1, n_q + 1):
                weights_by_q[q].loc[dt] = last_w[q].values

        curves = pd.DataFrame(index=close.index)
        for q in range(1, n_q + 1):
            w_shift = weights_by_q[q].shift(1).fillna(0.0)
            ret_q = (w_shift * daily_ret).sum(axis=1)
            curves[f"Q{q}"] = (1.0 + ret_q).cumprod()
        # 多空：Q5 - Q1
        ls_ret = ((weights_by_q[n_q].shift(1).fillna(0.0) - weights_by_q[1].shift(1).fillna(0.0)) * daily_ret).sum(axis=1)
        curves["LongShort"] = (1.0 + ls_ret).cumprod()
        return curves

    def _compute_benchmark_curves(self, strategy_returns: dict[str, pd.Series]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """把策略净值与基准对齐，返回 (curves, metrics) 两张表。"""
        if not self.benchmark_close:
            return pd.DataFrame(), pd.DataFrame()
        if not strategy_returns:
            return pd.DataFrame(), pd.DataFrame()
        primary_name = "ic_weighted" if "ic_weighted" in strategy_returns else next(iter(strategy_returns))
        idx = strategy_returns[primary_name].index
        curves = pd.DataFrame(index=idx)
        for name, ret_s in strategy_returns.items():
            curves[f"strategy_{name}"] = (1.0 + ret_s.reindex(idx).fillna(0.0)).cumprod()
        rows = []
        n_days = max((idx[-1] - idx[0]).days, 1) if len(idx) > 1 else 1
        for ts_code, close_series in self.benchmark_close.items():
            bench = close_series.reindex(idx).ffill()
            if bench.dropna().empty:
                continue
            first_label = bench.first_valid_index()
            base_val = float(bench.loc[first_label]) if first_label is not None else float("nan")
            bench_norm = bench / base_val if base_val and not np.isnan(base_val) else bench
            curves[ts_code] = bench_norm
            bench_ret = bench.pct_change(fill_method=None).fillna(0.0)
            bench_total = float(bench.iloc[-1] / base_val - 1.0) if base_val else 0.0
            bench_annual = (1.0 + bench_total) ** (365.0 / n_days) - 1.0
            for name, strategy_ret in strategy_returns.items():
                sr = strategy_ret.reindex(idx).fillna(0.0)
                excess = sr - bench_ret
                ann_excess = float((1.0 + excess.mean()) ** 252 - 1.0) if not excess.empty else 0.0
                ir = float(excess.mean() / excess.std() * np.sqrt(252)) if float(excess.std()) > 0 else 0.0
                win = float((excess > 0).mean())
                corr = float(sr.corr(bench_ret)) if sr.std() > 0 and bench_ret.std() > 0 else 0.0
                rows.append({
                    "signal": f"opentdx_v2_{name}",
                    "benchmark": ts_code,
                    "annual_excess": ann_excess,
                    "information_ratio": ir,
                    "daily_win_rate": win,
                    "correlation": corr,
                    "benchmark_total_return": bench_total,
                    "benchmark_annual_return": bench_annual,
                })
        return curves, pd.DataFrame(rows)

    def _save_results(self) -> None:
        (self.output_dir / "factor_values").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "config.json").write_text(json.dumps(asdict(self.config), ensure_ascii=False, indent=2), encoding="utf-8")
        # 只保存与报价相关的股票列表部分，避免上万条 5MB 的原始列表占用过多空间
        if not self.quotes.empty and "ts_code" in self.stock_list.columns:
            relevant = self.stock_list.loc[self.stock_list["ts_code"].isin(self.quotes["ts_code"])]
        else:
            relevant = self.stock_list
        relevant.to_csv(self.output_dir / "stock_list.csv", index=False, encoding="utf-8-sig")
        if isinstance(getattr(self, "_dropped_quotes", None), pd.DataFrame) and not self._dropped_quotes.empty:
            self._dropped_quotes.to_csv(self.output_dir / "dropped_quotes.csv", index=False, encoding="utf-8-sig")
        self.quotes.to_csv(self.output_dir / "quotes.csv", index=False, encoding="utf-8-sig")
        self.universe.to_csv(self.output_dir / "universe.csv", index=False, encoding="utf-8-sig")
        for key, df in self.panel.items():
            if not df.empty:
                df.to_csv(self.output_dir / f"price_panel_{key}.csv", encoding="utf-8-sig")
        for name, df in self.factor_dict.items():
            df.to_csv(self.output_dir / "factor_values" / f"{name}.csv", encoding="utf-8-sig")
        self.factor_scores.to_csv(self.output_dir / "factor_scores.csv", encoding="utf-8-sig")
        self.selection.to_csv(self.output_dir / "selection.csv", encoding="utf-8-sig")
        self.target_weights.to_csv(self.output_dir / "target_weights.csv", encoding="utf-8-sig")
        for name, df in self.strategy_weights.items():
            df.to_csv(self.output_dir / f"target_weights_{name}.csv", encoding="utf-8-sig")
        df_outputs = [
            "stock_pool_report", "factor_evaluation", "rank_ic", "quantile_returns",
            "factor_filter_report", "factor_correlation", "factor_auto_weights",
            "performance", "quantile_curves", "benchmark_curves", "excess_metrics", "strategy_equity_curves",
        ]
        index_keep = {"rank_ic", "factor_correlation", "quantile_curves", "benchmark_curves", "strategy_equity_curves"}
        for name in df_outputs:
            value = self.results.get(name)
            if isinstance(value, pd.DataFrame) and not value.empty:
                value.to_csv(self.output_dir / f"{name}.csv", index=(name in index_keep), encoding="utf-8-sig")
        for name in ["equity_curve", "returns", "drawdown"]:
            value = self.results.get(name)
            if isinstance(value, pd.Series):
                value.to_csv(self.output_dir / f"{name}.csv", encoding="utf-8-sig")
        holdings = []
        for dt, row in self.selection.iterrows():
            codes = row.index[row.fillna(False)].tolist()
            for code in codes:
                holdings.append({"date": dt, "ts_code": code, "weight": float(self.target_weights.loc[dt, code]) if code in self.target_weights.columns else 0.0})
        pd.DataFrame(holdings).to_csv(self.output_dir / "holdings_by_rebalance.csv", index=False, encoding="utf-8-sig")
        print(f"✅ 结果已保存: {self.output_dir}")

    def _plot_results(self) -> None:
        equity = self.results.get("equity_curve")
        drawdown = self.results.get("drawdown")
        if isinstance(equity, pd.Series) and not equity.empty:
            plt.figure(figsize=(12, 5))
            equity.plot(linewidth=2)
            plt.title("OpenTDX 多因子策略净值曲线")
            plt.xlabel("日期")
            plt.ylabel("权益")
            plt.tight_layout()
            plt.savefig(self.output_dir / "equity_curve.png", dpi=150)
            plt.close()
        if isinstance(drawdown, pd.Series) and not drawdown.empty:
            plt.figure(figsize=(12, 4))
            drawdown.plot(color="#c0504d", linewidth=1.5)
            plt.title("OpenTDX 多因子策略回撤")
            plt.xlabel("日期")
            plt.ylabel("回撤")
            plt.tight_layout()
            plt.savefig(self.output_dir / "drawdown.png", dpi=150)
            plt.close()

        # 5 分位组净值
        qc = self.results.get("quantile_curves")
        if isinstance(qc, pd.DataFrame) and not qc.empty:
            plt.figure(figsize=(12, 5))
            for col in qc.columns:
                if col == "LongShort":
                    qc[col].plot(linewidth=2.0, color="#000", linestyle="--", label="Q5-Q1")
                else:
                    qc[col].plot(linewidth=1.4, label=col)
            plt.title("综合分数 5 分位组累计净值（看单调性）")
            plt.xlabel("日期")
            plt.ylabel("累计净值（起点 1.0）")
            plt.legend()
            plt.tight_layout()
            plt.savefig(self.output_dir / "quantile_curves.png", dpi=150)
            plt.close()

        # 策略 vs 基准
        bc = self.results.get("benchmark_curves")
        if isinstance(bc, pd.DataFrame) and not bc.empty:
            plt.figure(figsize=(12, 5))
            for col in bc.columns:
                lw = 2.1 if str(col).startswith("strategy_ic_weighted") else 1.3
                bc[col].plot(linewidth=lw, label=col)
            plt.title("多策略 vs 沪深300等基准（归一净值）")
            plt.xlabel("日期")
            plt.ylabel("归一净值")
            plt.legend()
            plt.tight_layout()
            plt.savefig(self.output_dir / "equity_vs_benchmark.png", dpi=150)
            plt.close()

        # 因子 IC_IR 柱图（按绝对值排序，颜色区分保留/剔除）
        report = self.results.get("factor_filter_report")
        if isinstance(report, pd.DataFrame) and not report.empty:
            df = report.copy().assign(absir=lambda d: d["rank_ic_ir"].abs())
            df = df.sort_values("absir", ascending=False).head(40)
            colors = ["#2e8b57" if k else "#bbbbbb" for k in df["kept"]]
            plt.figure(figsize=(12, max(4, 0.25 * len(df))))
            plt.barh(df["factor"][::-1], df["rank_ic_ir"][::-1], color=colors[::-1])
            plt.axvline(0, color="#444", linewidth=0.8)
            plt.title("因子 RankIC_IR（绿色=保留，灰色=剔除）")
            plt.xlabel("RankIC_IR")
            plt.tight_layout()
            plt.savefig(self.output_dir / "factor_ic_bar.png", dpi=150)
            plt.close()

        print("✅ 图表生成完成")


_RUN_LOCK = threading.Lock()
_RUN_STATE: dict[str, Any] = {"running": False, "logs": [], "last_results": None, "error": None, "start_time": None, "end_time": None}


class _StreamToLog:
    def __init__(self, original) -> None:
        self.original = original

    def write(self, data: str) -> int:
        if data:
            self.original.write(data)
            self.original.flush()
            for line in data.splitlines():
                if line.strip():
                    with _RUN_LOCK:
                        _RUN_STATE["logs"].append(line)
                        _RUN_STATE["logs"] = _RUN_STATE["logs"][-1000:]
        return len(data)

    def flush(self) -> None:
        try:
            self.original.flush()
        except Exception:
            pass


def _coerce_config(payload: dict[str, Any]) -> OpenTdxWorkflowConfig:
    default = asdict(OpenTdxWorkflowConfig())
    merged = {**default}
    for key, value in payload.items():
        if key not in default:
            continue
        try:
            if isinstance(default[key], bool):
                merged[key] = bool(value)
            elif isinstance(default[key], int):
                merged[key] = int(value)
            elif isinstance(default[key], float):
                merged[key] = float(value)
            elif isinstance(default[key], list):
                merged[key] = value if isinstance(value, list) else [x.strip() for x in str(value).split(",") if x.strip()]
            elif isinstance(default[key], dict):
                merged[key] = value if isinstance(value, dict) else default[key]
            else:
                merged[key] = str(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"参数 {key} 转换失败: {exc}") from exc
    return OpenTdxWorkflowConfig(**merged)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.floating, float)):
        v = float(value)
        return v if np.isfinite(v) else None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if value is pd.NA or value is pd.NaT:
        return None
    return value


def _run_workflow_background(config: OpenTdxWorkflowConfig) -> None:
    with _RUN_LOCK:
        _RUN_STATE.update({"running": True, "logs": [], "last_results": None, "error": None, "start_time": time.strftime("%Y-%m-%d %H:%M:%S"), "end_time": None})
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _StreamToLog(original_stdout), _StreamToLog(original_stderr)
    try:
        save_config(config)
        workflow = OpenTdxWorkflow(config)
        results = workflow.run()
        performance = results.get("performance", pd.DataFrame())
        evaluation = results.get("factor_evaluation", pd.DataFrame())
        output_dir = results.get("output_dir", "")
        run_id = Path(output_dir).name if output_dir else ""
        image_urls: dict[str, str] = {}
        if run_id:
            chart_files = (
                ("equity_curve", "equity_curve.png"),
                ("drawdown", "drawdown.png"),
                ("quantile_curves", "quantile_curves.png"),
                ("equity_vs_benchmark", "equity_vs_benchmark.png"),
                ("factor_ic_bar", "factor_ic_bar.png"),
            )
            for key, fname in chart_files:
                if (Path(output_dir) / fname).exists():
                    image_urls[key] = f"/api/output/{run_id}/{fname}"
        filter_report = results.get("factor_filter_report", pd.DataFrame())
        auto_weights = results.get("factor_auto_weights", pd.DataFrame())
        excess_metrics = results.get("excess_metrics", pd.DataFrame())
        with _RUN_LOCK:
            _RUN_STATE["last_results"] = _json_safe({
                "performance": performance.to_dict(orient="records") if isinstance(performance, pd.DataFrame) else [],
                "factor_evaluation_head": evaluation.head(30).to_dict(orient="records") if isinstance(evaluation, pd.DataFrame) else [],
                "factor_filter_summary": ({
                    "kept": int(filter_report["kept"].sum()),
                    "dropped": int((~filter_report["kept"]).sum()),
                    "top_kept": filter_report.loc[filter_report["kept"]].head(10).to_dict(orient="records"),
                } if isinstance(filter_report, pd.DataFrame) and not filter_report.empty else {}),
                "auto_weights": auto_weights.to_dict(orient="records") if isinstance(auto_weights, pd.DataFrame) else [],
                "excess_metrics": excess_metrics.to_dict(orient="records") if isinstance(excess_metrics, pd.DataFrame) else [],
                "output_dir": output_dir,
                "run_id": run_id,
                "image_urls": image_urls,
                "step_times": results.get("step_times", []),
                "total_time": results.get("total_time", 0.0),
            })
    except Exception as exc:
        traceback.print_exc()
        with _RUN_LOCK:
            _RUN_STATE["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        with _RUN_LOCK:
            _RUN_STATE["running"] = False
            _RUN_STATE["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")


def _build_flask_app() -> Any:
    if Flask is None:
        raise ImportError("缺少 flask，请先 pip install flask")
    app = Flask(__name__, static_folder=None)

    @app.after_request
    def _no_cache(resp):
        # 禁掉浏览器缓存，避免老牌页面老 JS 卡住
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    @app.route("/")
    def index():
        # 每次重新生成，保证代码热更新后能被看到
        return _render_index_html()

    @app.route("/api/config")
    def api_config():
        return jsonify(asdict(load_saved_config()))

    @app.route("/api/run", methods=["POST"])
    def api_run():
        with _RUN_LOCK:
            if _RUN_STATE["running"]:
                return jsonify({"ok": False, "msg": "已有运行中的任务"}), 400
        payload = request.get_json(force=True, silent=True) or {}
        try:
            cfg = _coerce_config(payload)
        except ValueError as exc:
            return jsonify({"ok": False, "msg": str(exc)}), 400
        threading.Thread(target=_run_workflow_background, args=(cfg,), daemon=True).start()
        return jsonify({"ok": True})

    @app.route("/api/status")
    def api_status():
        with _RUN_LOCK:
            return jsonify({
                "running": _RUN_STATE["running"],
                "logs": list(_RUN_STATE["logs"][-300:]),
                "last_results": _RUN_STATE["last_results"],
                "error": _RUN_STATE["error"],
                "start_time": _RUN_STATE["start_time"],
                "end_time": _RUN_STATE["end_time"],
            })

    @app.route("/api/cache/stats")
    def api_cache_stats():
        cfg = load_saved_config()
        loader = OpenTdxDataLoader(cfg.opentdx_path, _THIS_DIR / cfg.cache_dir, cfg.enable_data_cache, False)
        return jsonify(loader.cache_stats())

    @app.route("/api/cache/clear", methods=["POST"])
    def api_cache_clear():
        cfg = load_saved_config()
        loader = OpenTdxDataLoader(cfg.opentdx_path, _THIS_DIR / cfg.cache_dir, cfg.enable_data_cache, False)
        return jsonify({"ok": True, "deleted": loader.clear_cache()})

    @app.route("/api/output/<run_id>/<path:filename>")
    def api_output_file(run_id: str, filename: str):
        # 只允许读取本项目 outputs/<run_id>/ 下的文件，避免路径穿越
        cfg = load_saved_config()
        base = (_THIS_DIR / cfg.output_dir / run_id).resolve()
        outputs_root = (_THIS_DIR / cfg.output_dir).resolve()
        if not base.exists() or not str(base).startswith(str(outputs_root)):
            return abort(404)
        return send_from_directory(str(base), filename)

    return app


def _render_index_html() -> str:
    # 用原始字符串，避免 JS 里的 \n 被 Python 当作真实换行符破坏脚本语法
    return r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>OpenTDX 多因子控制台</title>
<style>
body{font-family:-apple-system,"Segoe UI","Microsoft Yahei",sans-serif;margin:0;padding:8px;background:#f5f6fa;color:#222;font-size:12px}.layout{display:grid;grid-template-columns:360px 1fr;gap:8px;align-items:start}.main{display:grid;grid-template-columns:minmax(520px,1.25fr) minmax(360px,.75fr);gap:8px}.panel{background:#fff;border-radius:6px;padding:8px;box-shadow:0 1px 4px rgba(0,0,0,.05);overflow:auto}h1{font-size:16px;margin:0 0 6px}h2{font-size:14px;margin:0 0 6px}h3{font-size:13px;margin:8px 0 4px}.row{display:flex;gap:6px;margin:5px 0}.row label{flex:1;font-size:11px;color:#555}.row div{font-size:10px;color:#888;margin-bottom:1px}input,select{width:100%;box-sizing:border-box;padding:4px 5px;border:1px solid #d0d7de;border-radius:4px;height:26px;font-size:12px}button{padding:6px 10px;border:0;border-radius:5px;background:#4a90e2;color:#fff;font-weight:600;cursor:pointer;font-size:12px}button:disabled{background:#a4bfdf}.danger{background:#c0504d}.status{padding:5px;border-radius:5px;background:#e9ecef;margin-bottom:6px}.run{background:#fff3cd}.ok{background:#d4edda}.err{background:#f8d7da}pre{height:280px;overflow:auto;background:#1e1e2e;color:#d6e2f0;padding:8px;border-radius:5px;font-size:11px;line-height:1.25;margin:0}table{border-collapse:collapse;width:100%;font-size:11px;line-height:1.15}th,td{border:1px solid #e1e4e8;padding:3px 4px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}.table-scroll{max-height:290px;overflow:auto}.wide{grid-column:1 / -1}#timing table{font-size:10px}#timing td,#timing th{padding:2px 3px}#results p{margin:4px 0}#charts img{max-height:420px;object-fit:contain}.switch-row{display:flex;gap:8px;align-items:stretch;margin:6px 0}.switch-card{flex:1;border:1px solid #d0d7de;border-radius:6px;padding:7px 8px;background:#fafbfc;cursor:pointer;display:flex;gap:7px;align-items:center}.switch-card input{width:14px;height:14px;margin:0}.switch-card b{display:block;font-size:12px;color:#222}.switch-card span{display:block;font-size:10px;color:#777;margin-top:2px}.switch-card:has(input:checked){border-color:#4a90e2;background:#eef6ff}
</style></head><body><h1>📊 OpenTDX 多因子控制台</h1><div class="layout"><form id="form" class="panel"><h2>运行参数</h2>
<div class="row"><label><div>OpenTDX路径</div><input name="opentdx_path"></label></div>
<div class="row"><label><div>开始日期</div><input name="start_time"></label><label><div>结束日期</div><input name="end_time"></label></div>
<div class="row"><label><div>市场(SZ,SH,BJ)</div><input name="markets"></label><label><div>Debug最大股票数（0=全市场）</div><input name="debug_max_codes" type="number"></label></div>
<div class="row"><label><div>股价上限</div><input name="max_price" type="number" step="0.1"></label><label><div>总市值上限(亿)</div><input name="max_market_cap_yi" type="number" step="1"></label></div>
<div class="row"><label><div>TopN</div><input name="topn" type="number"></label><label><div>调仓频率</div><input name="rebalance_freq"></label><label><div>持有期</div><input name="holding_period" type="number"></label></div>
<input name="kline_count" type="hidden"><div class="row"><label><div>初始资金</div><input name="initial_account" type="number"></label></div>
<div class="row"><label><div>启用因子组(逗号分隔)</div><input name="enabled_factor_groups"></label></div>
<div class="row"><label><div>RankIC_IR最低绝对值</div><input name="min_rank_ic_ir" type="number" step="0.01"></label><label><div>IC方向胜率最低值</div><input name="min_ic_win_rate" type="number" step="0.01"></label></div>
<div class="row"><label><div>基准指数(逗号分隔)</div><input name="benchmark_codes"></label></div>
<div class="switch-row"><label class="switch-card"><input name="enable_ml_strategy" type="checkbox"><span><b>机器学习策略</b><span>勾选后额外运行 ML，较慢</span></span></label></div>
<input name="enable_data_cache" type="hidden"><input name="force_refresh_cache" type="hidden">
<div class="switch-row"><label class="switch-card"><input name="data_mode" type="radio" value="cache"><span><b>优先使用缓存</b><span>命中直接读，缺失自动下载</span></span></label><label class="switch-card"><input name="data_mode" type="radio" value="refresh"><span><b>强制重新下载</b><span>忽略旧缓存并覆盖</span></span></label></div>
<div class="row"><button id="run" type="submit">▶ 运行</button><button id="clear" type="button" class="danger">清空缓存</button></div>
<div id="cache" style="font-size:11px;color:#666">缓存状态读取中...</div></form><div class="main"><div class="panel"><h2>运行状态</h2><div id="status" class="status">空闲</div><pre id="logs">等待运行...</pre></div><div class="panel"><h2>步骤耗时</h2><div id="timing">运行后显示每步耗时与总耗时</div></div><div class="panel"><h2>结果摘要</h2><div id="results">暂无结果</div></div><div class="panel"><h2>图表</h2><div id="charts">运行后在这里查看净值与回撤图</div></div></div></div>
<script>
const form=document.getElementById('form'),btn=document.getElementById('run'),statusEl=document.getElementById('status'),logsEl=document.getElementById('logs'),resultsEl=document.getElementById('results');
function fill(cfg){for(const[k,v]of Object.entries(cfg)){const el=form.elements.namedItem(k);if(!el)continue;if(el.type==='checkbox')el.checked=!!v;else if(Array.isArray(v))el.value=v.join(',');else if(typeof v!=='object')el.value=v;}const mode=cfg.force_refresh_cache?'refresh':'cache';const m=form.querySelector(`input[name="data_mode"][value="${mode}"]`);if(m)m.checked=true;}
function read(){const d={};const listFields=new Set(['markets','enabled_factor_groups','benchmark_codes']);for(const el of form.elements){if(!el.name||el.name==='data_mode')continue;if(el.type==='checkbox')d[el.name]=el.checked;else if(listFields.has(el.name))d[el.name]=el.value.split(',').map(x=>x.trim()).filter(Boolean);else d[el.name]=el.value;}const mode=(form.querySelector('input[name="data_mode"]:checked')||{}).value||'cache';d.enable_data_cache=true;d.force_refresh_cache=mode==='refresh';return d;}
async function init(){const cfg=await fetch('/api/config').then(r=>r.json());fill(cfg);stats();poll();setInterval(poll,800)}
function fnum(v,d){return (v===null||v===undefined||(typeof v==='number'&&!Number.isFinite(v)))?'-':Number(v).toFixed(d);}
function fpct(v,d){return (v===null||v===undefined||(typeof v==='number'&&!Number.isFinite(v)))?'-':(Number(v)*100).toFixed(d)+'%';}
async function stats(){try{const s=await fetch('/api/cache/stats').then(r=>r.json());document.getElementById('cache').textContent=`缓存：${s.count} 个文件 / ${(s.size_bytes/1024/1024).toFixed(2)} MB`;}catch(e){document.getElementById('cache').textContent='缓存状态读取失败';}}
let lastResultsKey='',lastLogsLen=0;
async function poll(){let s;try{s=await fetch('/api/status',{cache:'no-store'}).then(r=>r.json());}catch(e){return;}try{btn.disabled=!!s.running;statusEl.className='status '+(s.running?'run':s.error?'err':s.last_results?'ok':'');statusEl.textContent=s.running?('运行中 '+s.start_time+' （日志 '+(s.logs?s.logs.length:0)+' 行）'):(s.error?'失败 '+s.error:(s.last_results?'✅ 完成 '+(s.end_time||''):'空闲'));const newLogs=(s.logs&&s.logs.length)?s.logs.join('\n'):'';if(newLogs!==logsEl.textContent){const wasAtBottom=Math.abs(logsEl.scrollHeight-logsEl.clientHeight-logsEl.scrollTop)<40;logsEl.textContent=newLogs||'等待运行...';if(wasAtBottom||s.running)logsEl.scrollTop=logsEl.scrollHeight;}}catch(e){console.warn('status update failed',e);}if(s.last_results){const key=(s.last_results.run_id||'')+'|'+(s.end_time||'');if(key!==lastResultsKey){lastResultsKey=key;try{render(s.last_results);}catch(e){console.error('render failed',e);resultsEl.innerHTML='<p style="color:#c0504d">渲染异常: '+e.message+'，请查看 F12 控制台。原始 JSON 见 /api/status。</p>';}}}}
function render(r){const tEl=document.getElementById('timing');if(r.step_times&&r.step_times.length){const tot=r.total_time||0;let th=`<p><b>总耗时：</b>${fnum(tot,2)} s</p><table><tr><th>步骤</th><th>耗时(s)</th><th>占比</th></tr>`;for(const x of r.step_times){const pct=tot>0?(x.seconds/tot*100).toFixed(1):'0.0';th+=`<tr><td>${x.step}</td><td>${fnum(x.seconds,2)}</td><td>${pct}%</td></tr>`;}th+='</table>';tEl.innerHTML=th;}else{tEl.textContent='本次运行未记录耗时';}
let html=`<p>输出目录：${r.output_dir||''}</p>`;
if(r.performance&&r.performance.length){html+='<h3>多策略</h3><table><tr><th>signal</th><th>total</th><th>annual</th><th>drawdown</th><th>sharpe</th></tr>';for(const x of r.performance){html+=`<tr><td>${x.signal}</td><td>${fpct(x.total_return,2)}</td><td>${fpct(x.annual_return,2)}</td><td>${fpct(x.max_drawdown,2)}</td><td>${fnum(x.sharpe,2)}</td></tr>`;}html+='</table>';}
if(r.factor_filter_summary&&typeof r.factor_filter_summary.kept!=='undefined'){const fs=r.factor_filter_summary;html+=`<h3>因子筛选：保留 ${fs.kept} / 剔除 ${fs.dropped}</h3>`;if(fs.top_kept&&fs.top_kept.length){html+='<table><tr><th>factor</th><th>group</th><th>rank_ic_ir</th><th>direction</th></tr>';for(const x of fs.top_kept){html+=`<tr><td>${x.factor}</td><td>${x.group||''}</td><td>${fnum(x.rank_ic_ir,3)}</td><td>${x.direction}</td></tr>`;}html+='</table>';}}
if(r.auto_weights&&r.auto_weights.length){html+='<h3>自动权重 Top10</h3><table><tr><th>factor</th><th>direction</th><th>weight</th></tr>';for(const x of r.auto_weights.slice(0,10)){html+=`<tr><td>${x.factor}</td><td>${x.direction}</td><td>${fpct(x.weight,2)}</td></tr>`;}html+='</table>';}
if(r.excess_metrics&&r.excess_metrics.length){html+='<h3>对沪深300超额</h3><table><tr><th>signal</th><th>benchmark</th><th>年化超额</th><th>IR</th><th>日胜率</th><th>相关性</th></tr>';for(const x of r.excess_metrics){html+=`<tr><td>${x.signal||''}</td><td>${x.benchmark}</td><td>${fpct(x.annual_excess,2)}</td><td>${fnum(x.information_ratio,2)}</td><td>${fpct(x.daily_win_rate,1)}</td><td>${fnum(x.correlation,2)}</td></tr>`;}html+='</table>';}
if(r.factor_evaluation_head&&r.factor_evaluation_head.length){html+='<h3>因子评价Top</h3><table><tr><th>factor</th><th>rank_ic</th><th>ir</th><th>win</th></tr>';for(const x of r.factor_evaluation_head){html+=`<tr><td>${x.factor}</td><td>${fnum(x.rank_ic_mean,4)}</td><td>${fnum(x.rank_ic_ir,3)}</td><td>${fpct(x.ic_win_rate,1)}</td></tr>`;}html+='</table>';}
resultsEl.innerHTML=html;
const cEl=document.getElementById('charts');if(r.image_urls){const tag=r.run_id||'v';const order=[['equity_curve','净值曲线'],['equity_vs_benchmark','策略 vs 基准'],['drawdown','回撤'],['quantile_curves','5 分位组累计净值'],['factor_ic_bar','因子 RankIC_IR']];let ch='';for(const[k,t]of order){if(r.image_urls[k])ch+=`<h3>${t}</h3><img style="max-width:100%;border:1px solid #e1e4e8;border-radius:4px" src="${r.image_urls[k]}?v=${tag}">`;}cEl.innerHTML=ch||'本次运行未生成图表';}}
form.addEventListener('submit',async e=>{e.preventDefault();btn.disabled=true;const resp=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(read())});const j=await resp.json();if(!j.ok){alert(j.msg||'启动失败');btn.disabled=false;}});
document.getElementById('clear').addEventListener('click',async()=>{if(!confirm('确认清空缓存？'))return;const r=await fetch('/api/cache/clear',{method:'POST'}).then(r=>r.json());alert('已删除 '+r.deleted+' 个缓存');stats();});init();
</script></body></html>"""


def main_cli(overrides: dict[str, Any] | None = None) -> None:
    cfg = load_saved_config()
    data = asdict(cfg)
    for key, value in (overrides or {}).items():
        if value is not None and key in data:
            data[key] = value
    cfg = _coerce_config(data)
    save_config(cfg)
    OpenTdxWorkflow(cfg).run()


def main_web(host: str = "127.0.0.1", port: int = 7788) -> None:
    app = _build_flask_app()
    import logging as _logging
    _logging.getLogger("werkzeug").setLevel(_logging.ERROR)
    print(f"🌐 OpenTDX 多因子控制台启动: http://{host}:{port}/")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenTDX 多因子 Workflow")
    parser.add_argument("--cli", action="store_true", help="不启动 Web，直接命令行运行")
    parser.add_argument("--host", default="127.0.0.1", help="Web 主机")
    parser.add_argument("--port", type=int, default=7788, help="Web 端口")
    parser.add_argument("--start-time", dest="start_time", default=None, help="开始日期")
    parser.add_argument("--end-time", dest="end_time", default=None, help="结束日期")
    parser.add_argument("--topn", type=int, default=None, help="持仓数量")
    parser.add_argument("--debug-max-codes", dest="debug_max_codes", type=int, default=None, help="调试股票数量")
    parser.add_argument("--force-refresh-cache", dest="force_refresh_cache", action="store_true", help="强制刷新缓存")
    args = parser.parse_args()
    if args.cli:
        main_cli({"start_time": args.start_time, "end_time": args.end_time, "topn": args.topn, "debug_max_codes": args.debug_max_codes, "force_refresh_cache": args.force_refresh_cache})
    else:
        main_web(args.host, args.port)
