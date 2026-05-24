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
    kline_count: int = 320
    initial_account: float = 1_000_000.0
    open_cost: float = 0.0
    close_cost: float = 0.0
    slippage: float = 0.0
    output_dir: str = "outputs"
    enable_data_cache: bool = True
    cache_dir: str = "cache"
    force_refresh_cache: bool = False
    debug_max_codes: int = 30
    enable_capital_flow_factor: bool = True
    enable_board_heat_factor: bool = False
    enable_unusual_factor: bool = True
    factor_weights: dict[str, float] = field(default_factory=lambda: {
        "momentum_20": 0.25,
        "momentum_60": 0.15,
        "volatility_20": -0.15,
        "amount_mean_20": 0.15,
        "turnover_mean_20": 0.10,
        "price_strength_20": 0.15,
        "capital_flow_strength": 0.10,
        "unusual_count": 0.05,
    })


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
        self.standardized_factors: dict[str, pd.DataFrame] = {}
        self.factor_scores = pd.DataFrame()
        self.selection = pd.DataFrame()
        self.target_weights = pd.DataFrame()
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
        _timed("第四步:构造未来收益", self._build_future_return)
        _timed("第五步:计算基础因子", self._build_factors)
        _timed("第六步:横截面标准化", self._standardize_factors)
        evaluation, rank_ic, quantile_returns = _timed("第七步:单因子评价", self._evaluate_factors)
        _timed("第八步:构造综合信号", self._build_signals)
        performance = _timed("第九步:组合回测", self._run_backtest)
        # _run_backtest 已经把 equity_curve / returns / drawdown 写入 self.results，
        # 用 update 而不是覆盖赋值，避免回测阶段的中间产物丢失。
        self.results.update({
            "stock_pool_report": pool_report,
            "factor_evaluation": evaluation,
            "rank_ic": rank_ic,
            "quantile_returns": quantile_returns,
            "performance": performance,
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
        self.panel = self.loader.load_kline_panel(codes, count=int(self.config.kline_count))
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

    def _build_future_return(self) -> None:
        close = self.panel["close"]
        hp = max(int(self.config.holding_period), 1)
        self.future_return = close.shift(-hp) / close - 1.0
        print(f"✅ future_return 形状: {self.future_return.shape}, holding_period={hp}")

    def _build_factors(self) -> None:
        close = self.panel["close"]
        amount = self.panel.get("amount", pd.DataFrame()).reindex_like(close)
        turnover = self.panel.get("turnover", pd.DataFrame()).reindex_like(close)
        returns = close.pct_change()
        factors: dict[str, pd.DataFrame] = {
            "momentum_20": close / close.shift(20) - 1.0,
            "momentum_60": close / close.shift(60) - 1.0,
            "volatility_20": returns.rolling(20).std(),
            "amount_mean_20": amount.rolling(20).mean(),
            "price_strength_20": close / close.rolling(20).mean() - 1.0,
        }
        if not turnover.empty and turnover.notna().sum().sum() > 0:
            factors["turnover_mean_20"] = turnover.rolling(20).mean()
        if self.config.enable_capital_flow_factor:
            factors["capital_flow_strength"] = self._build_capital_flow_factor(close)
        if self.config.enable_unusual_factor:
            factors["unusual_count"] = self._build_unusual_factor(close)
        self.factor_dict = {k: v.reindex_like(close) for k, v in factors.items() if not v.empty}
        print(f"✅ 已构造 {len(self.factor_dict)} 个基础因子: {list(self.factor_dict)}")

    def _build_capital_flow_factor(self, close: pd.DataFrame) -> pd.DataFrame:
        try:
            codes = self.universe["ts_code"].astype(str).tolist()
            df = self.loader.load_capital_flow(codes)
            if df.empty:
                return pd.DataFrame(index=close.index, columns=close.columns, dtype=float)
            numeric = df.set_index("ts_code").apply(pd.to_numeric, errors="coerce")
            candidates = [c for c in numeric.columns if any(x in c for x in ["主力", "主买", "净", "流入"])]
            series = numeric[candidates].sum(axis=1) if candidates else numeric.sum(axis=1)
            return pd.DataFrame([series.reindex(close.columns)] * len(close.index), index=close.index, columns=close.columns)
        except Exception as exc:
            print(f"⚠️ 资金流因子构造失败，跳过: {exc}")
            return pd.DataFrame(index=close.index, columns=close.columns, dtype=float)

    def _build_unusual_factor(self, close: pd.DataFrame) -> pd.DataFrame:
        try:
            events = self.loader.load_monitor_events(self.config.markets, count=5000)
            if events.empty or "ts_code" not in events.columns:
                return pd.DataFrame(index=close.index, columns=close.columns, dtype=float)
            counts = events.groupby("ts_code").size().astype(float)
            return pd.DataFrame([counts.reindex(close.columns).fillna(0.0)] * len(close.index), index=close.index, columns=close.columns)
        except Exception as exc:
            print(f"⚠️ 异动因子构造失败，跳过: {exc}")
            return pd.DataFrame(index=close.index, columns=close.columns, dtype=float)

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

    def _build_signals(self) -> None:
        close = self.panel["close"]
        weights = {k: float(v) for k, v in self.config.factor_weights.items() if k in self.standardized_factors}
        if not weights:
            raise RuntimeError("没有可用因子权重")
        scale = sum(abs(v) for v in weights.values()) or 1.0
        score = pd.DataFrame(0.0, index=close.index, columns=close.columns)
        for name, weight in weights.items():
            score = score.add(self.standardized_factors[name].reindex_like(close).fillna(0.0) * (weight / scale), fill_value=0.0)
        self.factor_scores = score
        rebalance = self._build_rebalance_mask(close.index)
        selection = pd.DataFrame(False, index=close.index, columns=close.columns)
        for dt in close.index[rebalance.values]:
            row = score.loc[dt].replace([np.inf, -np.inf], np.nan).dropna().sort_values(ascending=False)
            selected = row.head(max(int(self.config.topn), 1)).index.tolist()
            if selected:
                selection.loc[dt, selected] = True
        self.selection = selection
        target = pd.DataFrame(0.0, index=close.index, columns=close.columns)
        last = pd.Series(0.0, index=close.columns)
        for dt in close.index:
            if bool(rebalance.get(dt, False)):
                picked = selection.loc[dt]
                count = int(picked.sum())
                last = picked.astype(float) / count if count > 0 else pd.Series(0.0, index=close.columns)
            target.loc[dt] = last.values
        self.target_weights = target.shift(1).fillna(0.0)
        print(f"✅ 信号完成: 调仓次数={int(selection.any(axis=1).sum())}, TopN={self.config.topn}")

    def _run_backtest(self) -> pd.DataFrame:
        close = self.panel["close"]
        weights = self.target_weights.reindex_like(close).fillna(0.0)
        ret = close.pct_change().fillna(0.0)
        gross = (weights.shift(1).fillna(0.0) * ret).sum(axis=1)
        turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
        cost = turnover * (float(self.config.open_cost) + float(self.config.close_cost) + float(self.config.slippage))
        strategy_ret = gross - cost
        equity = (1.0 + strategy_ret).cumprod() * float(self.config.initial_account)
        drawdown = equity / equity.cummax() - 1.0
        self.results["equity_curve"] = equity
        self.results["returns"] = strategy_ret
        self.results["drawdown"] = drawdown
        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) > 1 else 0.0
        days = max((equity.index[-1] - equity.index[0]).days, 1) if len(equity) > 1 else 1
        annual_return = (1.0 + total_return) ** (365.0 / days) - 1.0
        sharpe = float(strategy_ret.mean() / strategy_ret.std() * np.sqrt(252)) if float(strategy_ret.std()) > 0 else 0.0
        performance = pd.DataFrame([{
            "signal": "opentdx_basic_multifactor",
            "start": str(equity.index[0].date()) if len(equity) else "",
            "end": str(equity.index[-1].date()) if len(equity) else "",
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": float(drawdown.min()) if len(drawdown) else 0.0,
            "sharpe": sharpe,
            "final_equity": float(equity.iloc[-1]) if len(equity) else float(self.config.initial_account),
        }])
        print("✅ 回测完成")
        print(performance.to_string(index=False))
        return performance

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
        for name in ["stock_pool_report", "factor_evaluation", "rank_ic", "quantile_returns", "performance"]:
            value = self.results.get(name)
            if isinstance(value, pd.DataFrame):
                value.to_csv(self.output_dir / f"{name}.csv", index=name != "rank_ic", encoding="utf-8-sig")
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
            for key, fname in (("equity_curve", "equity_curve.png"), ("drawdown", "drawdown.png")):
                if (Path(output_dir) / fname).exists():
                    image_urls[key] = f"/api/output/{run_id}/{fname}"
        with _RUN_LOCK:
            _RUN_STATE["last_results"] = {
                "performance": performance.to_dict(orient="records") if isinstance(performance, pd.DataFrame) else [],
                "factor_evaluation_head": evaluation.head(20).to_dict(orient="records") if isinstance(evaluation, pd.DataFrame) else [],
                "output_dir": output_dir,
                "run_id": run_id,
                "image_urls": image_urls,
                "step_times": results.get("step_times", []),
                "total_time": results.get("total_time", 0.0),
            }
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
    index_html = _render_index_html()

    @app.route("/")
    def index():
        return index_html

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
body{font-family:-apple-system,"Segoe UI","Microsoft Yahei",sans-serif;margin:0;padding:20px;background:#f5f6fa;color:#222}.layout{display:grid;grid-template-columns:440px 1fr;gap:16px}.panel{background:#fff;border-radius:8px;padding:16px;box-shadow:0 2px 6px rgba(0,0,0,.06)}h1{font-size:22px}.row{display:flex;gap:8px;margin:8px 0}.row label{flex:1;font-size:12px;color:#555}.row div{font-size:11px;color:#888;margin-bottom:2px}input,select{width:100%;box-sizing:border-box;padding:6px;border:1px solid #d0d7de;border-radius:4px}button{padding:8px 14px;border:0;border-radius:5px;background:#4a90e2;color:#fff;font-weight:600;cursor:pointer}button:disabled{background:#a4bfdf}.danger{background:#c0504d}.status{padding:8px;border-radius:5px;background:#e9ecef}.run{background:#fff3cd}.ok{background:#d4edda}.err{background:#f8d7da}pre{height:360px;overflow:auto;background:#1e1e2e;color:#d6e2f0;padding:10px;border-radius:6px;font-size:12px}table{border-collapse:collapse;width:100%;font-size:12px}th,td{border:1px solid #e1e4e8;padding:5px;text-align:right}th:first-child,td:first-child{text-align:left}
</style></head><body><h1>📊 OpenTDX 多因子控制台</h1><div class="layout"><form id="form" class="panel"><h2>运行参数</h2>
<div class="row"><label><div>OpenTDX路径</div><input name="opentdx_path"></label></div>
<div class="row"><label><div>开始日期</div><input name="start_time"></label><label><div>结束日期</div><input name="end_time"></label></div>
<div class="row"><label><div>市场(SZ,SH,BJ)</div><input name="markets"></label><label><div>Debug最大股票数</div><input name="debug_max_codes" type="number"></label></div>
<div class="row"><label><div>股价上限</div><input name="max_price" type="number" step="0.1"></label><label><div>总市值上限(亿)</div><input name="max_market_cap_yi" type="number" step="1"></label></div>
<div class="row"><label><div>TopN</div><input name="topn" type="number"></label><label><div>调仓频率</div><input name="rebalance_freq"></label><label><div>持有期</div><input name="holding_period" type="number"></label></div>
<div class="row"><label><div>K线数量</div><input name="kline_count" type="number"></label><label><div>初始资金</div><input name="initial_account" type="number"></label></div>
<div class="row"><label><input name="enable_data_cache" type="checkbox"> 使用缓存</label><label><input name="force_refresh_cache" type="checkbox"> 强制刷新</label></div>
<div class="row"><label><input name="enable_capital_flow_factor" type="checkbox"> 资金流因子</label><label><input name="enable_unusual_factor" type="checkbox"> 异动因子</label></div>
<div class="row"><button id="run" type="submit">▶ 运行</button><button id="clear" type="button" class="danger">清空缓存</button></div>
<div id="cache" style="font-size:12px;color:#666">缓存状态读取中...</div></form><div><div class="panel"><h2>运行状态</h2><div id="status" class="status">空闲</div><pre id="logs">等待运行...</pre></div><div class="panel" style="margin-top:12px"><h2>步骤耗时</h2><div id="timing">运行后显示每步耗时与总耗时</div></div><div class="panel" style="margin-top:12px"><h2>结果摘要</h2><div id="results">暂无结果</div></div><div class="panel" style="margin-top:12px"><h2>图表</h2><div id="charts">运行后在这里查看净值与回撤图</div></div></div></div>
<script>
const form=document.getElementById('form'),btn=document.getElementById('run'),statusEl=document.getElementById('status'),logsEl=document.getElementById('logs'),resultsEl=document.getElementById('results');
function fill(cfg){for(const[k,v]of Object.entries(cfg)){const el=form.elements.namedItem(k);if(!el)continue;if(el.type==='checkbox')el.checked=!!v;else if(Array.isArray(v))el.value=v.join(',');else if(typeof v!=='object')el.value=v;}}
function read(){const d={};for(const el of form.elements){if(!el.name)continue;if(el.type==='checkbox')d[el.name]=el.checked;else if(el.name==='markets')d[el.name]=el.value.split(',').map(x=>x.trim()).filter(Boolean);else d[el.name]=el.value;}return d;}
async function init(){const cfg=await fetch('/api/config').then(r=>r.json());fill(cfg);stats();poll();setInterval(poll,1500)}
async function stats(){try{const s=await fetch('/api/cache/stats').then(r=>r.json());document.getElementById('cache').textContent=`缓存：${s.count} 个文件 / ${(s.size_bytes/1024/1024).toFixed(2)} MB`;}catch(e){document.getElementById('cache').textContent='缓存状态读取失败';}}
let lastResultsKey='',lastLogsLen=0;
async function poll(){try{const s=await fetch('/api/status').then(r=>r.json());btn.disabled=!!s.running;statusEl.className='status '+(s.running?'run':s.error?'err':s.last_results?'ok':'');statusEl.textContent=s.running?'运行中 '+s.start_time:(s.error?'失败 '+s.error:(s.last_results?'完成 '+(s.end_time||''):'空闲'));if(s.logs&&s.logs.length&&s.logs.length!==lastLogsLen){lastLogsLen=s.logs.length;logsEl.textContent=s.logs.join('\n');logsEl.scrollTop=logsEl.scrollHeight;}if(s.last_results){const key=(s.last_results.run_id||'')+'|'+(s.end_time||'');if(key!==lastResultsKey){lastResultsKey=key;render(s.last_results);}}}catch(e){}}
function render(r){const tEl=document.getElementById('timing');if(r.step_times&&r.step_times.length){const tot=r.total_time||0;let th=`<p><b>总耗时：</b>${tot.toFixed(2)} s</p><table><tr><th>步骤</th><th>耗时(s)</th><th>占比</th></tr>`;for(const x of r.step_times){const pct=tot>0?(x.seconds/tot*100).toFixed(1):'0.0';th+=`<tr><td>${x.step}</td><td>${x.seconds.toFixed(2)}</td><td>${pct}%</td></tr>`;}th+='</table>';tEl.innerHTML=th;}else{tEl.textContent='本次运行未记录耗时';}let html=`<p>输出目录：${r.output_dir||''}</p>`;if(r.performance&&r.performance.length){html+='<table><tr><th>signal</th><th>total</th><th>annual</th><th>drawdown</th><th>sharpe</th></tr>';for(const x of r.performance){html+=`<tr><td>${x.signal}</td><td>${(x.total_return*100).toFixed(2)}%</td><td>${(x.annual_return*100).toFixed(2)}%</td><td>${(x.max_drawdown*100).toFixed(2)}%</td><td>${x.sharpe.toFixed(2)}</td></tr>`;}html+='</table>';}if(r.factor_evaluation_head&&r.factor_evaluation_head.length){html+='<h3>因子评价Top</h3><table><tr><th>factor</th><th>rank_ic</th><th>ir</th><th>win</th></tr>';for(const x of r.factor_evaluation_head){html+=`<tr><td>${x.factor}</td><td>${x.rank_ic_mean.toFixed(4)}</td><td>${x.rank_ic_ir.toFixed(3)}</td><td>${(x.ic_win_rate*100).toFixed(1)}%</td></tr>`;}html+='</table>';}resultsEl.innerHTML=html;const cEl=document.getElementById('charts');if(r.image_urls){const tag=r.run_id||'v';let ch='';if(r.image_urls.equity_curve)ch+=`<h3>净值曲线</h3><img style="max-width:100%;border:1px solid #e1e4e8;border-radius:4px" src="${r.image_urls.equity_curve}?v=${tag}">`;if(r.image_urls.drawdown)ch+=`<h3>回撤</h3><img style="max-width:100%;border:1px solid #e1e4e8;border-radius:4px" src="${r.image_urls.drawdown}?v=${tag}">`;cEl.innerHTML=ch||'本次运行未生成图表';}}
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
