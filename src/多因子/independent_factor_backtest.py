from __future__ import annotations

import re
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import ttk

from src.多因子 import config
from src.多因子.backtest_vectorbt import extract_backtest_results, run_vectorbt_backtest
from src.多因子.data_loader import build_data_bundle, get_strategy_date_range
from src.多因子.factor_evaluation import (
    build_forward_returns,
    calc_ic_series,
    calc_rank_ic_series,
    calc_rr_series,
    summarize_factor_metrics,
)

from src.多因子.main import (
    FACTOR_HIGHER_BETTER,
    FACTOR_LABELS,
    _compute_registered_factor,
    _factor_direction_label,
    _factor_style_label,
    _load_factor_from_cache,
    _load_last_run_config,
    _load_last_run_dates,
    _rank_score_by_factor_direction,
    _save_factor_to_cache,
    _save_last_run_config,
)
from src.多因子.scoring import mask_factor, select_top_n
from src.多因子.universe import build_tradable_mask


@dataclass(frozen=True)
class RunParams:
    start_date: str | None
    end_date: str | None
    factor_names: list[str]
    hold_num: int
    period_days: int
    use_batch_data_cache: bool
    use_factor_cache: bool


def _parse_factor_names(text: str) -> list[str]:
    raw = (
        text.replace("\n", ",")
        .replace("\r", ",")
        .replace(";", ",")
        .replace("，", ",")
    )
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for name in parts:
        if name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def _build_rebalance_mask_by_n_days(index: pd.Index, period_days: int) -> pd.Series:
    if period_days <= 0:
        raise ValueError("period_days 必须为正整数")
    mask = pd.Series(False, index=index)
    if len(index) == 0:
        return mask
    for i in range(0, len(index), period_days):
        mask.iloc[i] = True
    return mask


def _run_single_factor_backtest_custom(
    *,
    factor_df: pd.DataFrame,
    tradable_mask: pd.DataFrame,
    close_df: pd.DataFrame,
    rebalance_mask: pd.Series,
    benchmark_close: pd.Series | None,
    hold_num: int,
    is_factor_higher_better: bool,
) -> dict[str, Any]:
    masked_factor_df = mask_factor(factor_df, tradable_mask)
    factor_score_df = _rank_score_by_factor_direction(masked_factor_df, is_factor_higher_better)
    selection_df = select_top_n(factor_score_df, n=hold_num)

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
    results["score_df"] = factor_score_df
    results["masked_factor_df"] = masked_factor_df
    return results


def run_independent_factor_backtest(
    params: RunParams,
    progress_callback: Callable[[str, str, int | None, int | None], None] | None = None,
) -> dict[str, Any]:
    if not params.factor_names:
        raise ValueError("未输入任何因子")
    if params.hold_num <= 0:
        raise ValueError("每期选股数量必须为正整数")
    if params.period_days <= 0:
        raise ValueError("周期天数必须为正整数")

    def report(stage: str, detail: str, current: int | None = None, total: int | None = None) -> None:
        if total and total > 0 and current is not None:
            pct = max(0.0, min(100.0, current * 100.0 / total))
            console_msg = f"[{stage}] ({current}/{total} {pct:5.1f}%) {detail}"
        else:
            console_msg = f"[{stage}] {detail}"
        print(console_msg, flush=True)
        if progress_callback is not None:
            try:
                progress_callback(stage, detail, current, total)
            except Exception:
                pass

    t0 = time.perf_counter()

    report("阶段0：加载数据", "正在加载股票池、行情和基准数据...", 0, 1)
    data_bundle = build_data_bundle(
        max_price=config.MAX_PRICE,
        max_mcap=config.MAX_MCAP,
        need_download=config.NEED_DOWNLOAD,
        dividend_type=config.DIVIDEND_TYPE,
        start_date=params.start_date,
        end_date=params.end_date,
        use_batch_data_cache=params.use_batch_data_cache,
    )

    close_df = data_bundle.get("close")
    universe_df = data_bundle.get("universe")
    benchmark_close = data_bundle.get("benchmark_close")
    if close_df is None or universe_df is None:
        raise ValueError("数据加载失败，缺少必要字段 close/universe")
    if close_df.empty:
        raise ValueError("未获取到有效行情数据")

    report("阶段0：加载数据", f"close.shape={close_df.shape}，构建可交易掩码...", 1, 1)
    tradable_mask = build_tradable_mask(universe_df=universe_df, close_df=close_df)

    report("阶段0：加载数据", f"按 {params.period_days} 个交易日构建调仓掩码并计算未来收益...", 1, 1)
    rebalance_mask = _build_rebalance_mask_by_n_days(close_df.index, params.period_days)
    forward_returns_df = build_forward_returns(close_df, rebalance_mask)

    cache_start = str(data_bundle.get("start_date", params.start_date or ""))
    cache_end = str(data_bundle.get("end_date", params.end_date or ""))

    factor_results: dict[str, dict[str, Any]] = {}
    metrics_list: list[pd.DataFrame] = []

    total_factors = len(params.factor_names)
    for factor_index, factor_name in enumerate(params.factor_names, start=1):
        if factor_name not in FACTOR_LABELS:
            raise ValueError(f"因子未注册：{factor_name}")

        report("阶段1：计算因子", f"[{factor_index}/{total_factors}] {factor_name} - 计算/读取因子值...", factor_index - 1, total_factors)
        factor_df: pd.DataFrame | None = None
        if params.use_factor_cache:
            factor_df = _load_factor_from_cache(factor_name, cache_start, cache_end)

        if factor_df is None:
            factor_df = _compute_registered_factor(factor_name, data_bundle)
            if params.use_factor_cache:
                _save_factor_to_cache(factor_name, cache_start, cache_end, factor_df)

        report("阶段2：单因子回测", f"[{factor_index}/{total_factors}] {factor_name} - 运行 vectorbt 回测...", factor_index - 1, total_factors)
        is_higher_better = bool(FACTOR_HIGHER_BETTER.get(factor_name, True))
        single = _run_single_factor_backtest_custom(
            factor_df=factor_df,
            tradable_mask=tradable_mask,
            close_df=close_df,
            rebalance_mask=rebalance_mask,
            benchmark_close=benchmark_close,
            hold_num=params.hold_num,
            is_factor_higher_better=is_higher_better,
        )

        report("阶段3：因子评估", f"[{factor_index}/{total_factors}] {factor_name} - 计算 IC / RankIC / RR ...", factor_index - 1, total_factors)
        masked_factor_df = single["masked_factor_df"]
        ic_series = calc_ic_series(masked_factor_df, forward_returns_df)
        rank_ic_series = calc_rank_ic_series(masked_factor_df, forward_returns_df)
        rr_series = calc_rr_series(masked_factor_df, forward_returns_df, hold_num=params.hold_num)
        summary_df = summarize_factor_metrics(
            factor_name=factor_name,
            ic_series=ic_series,
            rank_ic_series=rank_ic_series,
            rr_series=rr_series,
            periods_per_year=config.IC_PERIODS_PER_YEAR,
        )
        summary_df["方向"] = _factor_direction_label(is_higher_better)
        summary_df["风格"] = _factor_style_label(factor_name)
        summary_df["选股数"] = params.hold_num
        summary_df["周期天数"] = params.period_days

        stats_obj = single.get("stats")
        try:
            total_ret = float(stats_obj.loc["Total Return [%]"]) if stats_obj is not None and "Total Return [%]" in stats_obj.index else float("nan")
            bench_ret = float(stats_obj.loc["Benchmark Return [%]"]) if stats_obj is not None and "Benchmark Return [%]" in stats_obj.index else float("nan")
        except Exception:
            total_ret, bench_ret = float("nan"), float("nan")
        summary_df["组合收益[%]"] = total_ret
        summary_df["基准收益[%]"] = bench_ret
        summary_df["超额收益[%]"] = total_ret - bench_ret if not (np.isnan(total_ret) or np.isnan(bench_ret)) else float("nan")

        factor_results[factor_name] = {
            "factor_df": factor_df,
            "summary_df": summary_df,
            "single_factor_results": single,
            "ic_series": ic_series,
            "rank_ic_series": rank_ic_series,
            "rr_series": rr_series,
            "is_factor_higher_better": is_higher_better,
        }
        metrics_list.append(summary_df)
        report("阶段3：因子评估", f"[{factor_index}/{total_factors}] {factor_name} 完成", factor_index, total_factors)

    metrics_df = pd.concat(metrics_list, ignore_index=True) if metrics_list else pd.DataFrame()

    report("阶段4：保存结果", "正在写入 CSV ...", 0, 1)
    output_dir = _save_results_to_csv(
        metrics_df=metrics_df,
        factor_results=factor_results,
        params=params,
        cache_start=cache_start,
        cache_end=cache_end,
    )
    report("阶段4：保存结果", f"已保存到 {output_dir}", 1, 1)
    report("完成", f"共 {total_factors} 个因子评估完成，结果目录：{output_dir}", total_factors, total_factors)

    elapsed = time.perf_counter() - t0
    return {
        "start_date": data_bundle.get("start_date"),
        "end_date": data_bundle.get("end_date"),
        "date_reason": data_bundle.get("date_reason"),
        "bar_count": len(data_bundle.get("bars", {})),
        "metrics_df": metrics_df,
        "factor_results": factor_results,
        "output_dir": str(output_dir),
        "elapsed": elapsed,
    }


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-.]+", "_", name)


def _save_results_to_csv(
    *,
    metrics_df: pd.DataFrame,
    factor_results: dict[str, dict[str, Any]],
    params: RunParams,
    cache_start: str,
    cache_end: str,
) -> Path:
    base_dir = Path(__file__).resolve().parent / config.OUTPUT_DIR / "independent_factor_backtest"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base_dir / f"{cache_start}_{cache_end}__hold{params.hold_num}_period{params.period_days}__{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    if metrics_df is not None and not metrics_df.empty:
        summary_with_label = metrics_df.copy()
        summary_with_label.insert(1, "label", summary_with_label["factor"].map(FACTOR_LABELS))
        summary_with_label.to_csv(run_dir / "summary.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        {
            "key": [
                "start_date",
                "end_date",
                "hold_num",
                "period_days",
                "use_batch_data_cache",
                "use_factor_cache",
                "factors",
            ],
            "value": [
                cache_start,
                cache_end,
                params.hold_num,
                params.period_days,
                params.use_batch_data_cache,
                params.use_factor_cache,
                ",".join(params.factor_names),
            ],
        }
    ).to_csv(run_dir / "run_params.csv", index=False, encoding="utf-8-sig")

    for factor_name, info in factor_results.items():
        factor_dir = run_dir / "per_factor" / _safe_filename(factor_name)
        factor_dir.mkdir(parents=True, exist_ok=True)

        single = info.get("single_factor_results") or {}
        stats = single.get("stats")
        if stats is not None and hasattr(stats, "to_frame"):
            try:
                total_ret = float(stats.loc["Total Return [%]"]) if "Total Return [%]" in stats.index else float("nan")
                bench_ret = float(stats.loc["Benchmark Return [%]"]) if "Benchmark Return [%]" in stats.index else float("nan")
                stats_to_save = stats.copy()
                if not (np.isnan(total_ret) or np.isnan(bench_ret)):
                    stats_to_save.loc["Excess Return [%]"] = total_ret - bench_ret
            except Exception:
                stats_to_save = stats
            stats_to_save.to_frame(name="value").to_csv(factor_dir / "stats.csv", encoding="utf-8-sig")

        equity_curve = single.get("equity_curve")
        if isinstance(equity_curve, pd.Series):
            equity_curve.to_frame(name="equity").to_csv(factor_dir / "equity_curve.csv", encoding="utf-8-sig")

        returns = single.get("returns")
        if isinstance(returns, pd.Series):
            returns.to_frame(name="returns").to_csv(factor_dir / "returns.csv", encoding="utf-8-sig")

        benchmark_returns = single.get("benchmark_returns")
        if isinstance(benchmark_returns, pd.Series):
            benchmark_returns.to_frame(name="benchmark_returns").to_csv(factor_dir / "benchmark_returns.csv", encoding="utf-8-sig")

        ic_series = info.get("ic_series")
        rank_ic_series = info.get("rank_ic_series")
        rr_series = info.get("rr_series")
        ts_frames = []
        if isinstance(ic_series, pd.Series):
            ts_frames.append(ic_series.rename("IC"))
        if isinstance(rank_ic_series, pd.Series):
            ts_frames.append(rank_ic_series.rename("RankIC"))
        if isinstance(rr_series, pd.Series):
            ts_frames.append(rr_series.rename("RR"))
        if ts_frames:
            pd.concat(ts_frames, axis=1).to_csv(factor_dir / "ic_rank_ic_rr.csv", encoding="utf-8-sig")

        selection_df = single.get("selection_df")
        if isinstance(selection_df, pd.DataFrame) and not selection_df.empty:
            selected_long = (
                selection_df.stack().rename("selected").reset_index()
                if hasattr(selection_df, "stack")
                else None
            )
            if selected_long is not None:
                selected_long.columns = ["date", "code", "selected"]
                selected_long = selected_long[selected_long["selected"].astype(bool)].drop(columns="selected")
                selected_long.to_csv(factor_dir / "selected_stocks.csv", index=False, encoding="utf-8-sig")

    return run_dir


class IndependentFactorApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("独立因子回测")
        self.root.resizable(True, True)
        self.root.minsize(900, 720)

        latest_start, latest_end, _ = get_strategy_date_range()
        self._latest_start = latest_start
        self._latest_end = latest_end
        last_start, last_end = _load_last_run_dates()
        default_start = last_start or latest_start
        default_end = last_end or latest_end

        last_cfg = _load_last_run_config()
        ind_cfg = last_cfg.get("independent_factor_backtest") if isinstance(last_cfg, dict) else None
        if not isinstance(ind_cfg, dict):
            ind_cfg = {}
        default_factors_text = str(ind_cfg.get("factors_text", ""))
        default_hold_num = int(ind_cfg.get("hold_num", config.HOLD_NUM)) if str(ind_cfg.get("hold_num", "")).strip() != "" else config.HOLD_NUM
        default_period_days = int(ind_cfg.get("period_days", 5)) if str(ind_cfg.get("period_days", "")).strip() != "" else 5
        default_use_batch_data_cache = bool(ind_cfg.get("use_batch_data_cache", True))
        default_use_factor_cache = bool(ind_cfg.get("use_factor_cache", True))

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        container = ttk.Frame(self.root, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="开始日期（YYYYMMDD）").grid(row=0, column=0, sticky="w", pady=(0, 8))
        start_frame = ttk.Frame(container)
        start_frame.grid(row=0, column=1, sticky="w", pady=(0, 8))
        self.start_entry = ttk.Entry(start_frame, width=22)
        self.start_entry.pack(side="left")
        self.start_entry.insert(0, default_start)
        ttk.Button(start_frame, text="设为最新", command=self._reset_dates_to_latest).pack(side="left", padx=(8, 0))

        ttk.Label(container, text="结束日期（YYYYMMDD）").grid(row=1, column=0, sticky="w", pady=(0, 8))
        end_frame = ttk.Frame(container)
        end_frame.grid(row=1, column=1, sticky="w", pady=(0, 8))
        self.end_entry = ttk.Entry(end_frame, width=22)
        self.end_entry.pack(side="left")
        self.end_entry.insert(0, default_end)
        self.date_hint_var = tk.StringVar(
            value=f"最新可用范围：{self._latest_start} ~ {self._latest_end}"
        )
        ttk.Label(end_frame, textvariable=self.date_hint_var, foreground="#666666").pack(side="left", padx=(8, 0))

        ttk.Label(container, text="每期选股数量").grid(row=2, column=0, sticky="w", pady=(0, 8))
        self.hold_num_entry = ttk.Entry(container, width=24)
        self.hold_num_entry.grid(row=2, column=1, sticky="w", pady=(0, 8))
        self.hold_num_entry.insert(0, str(default_hold_num))

        ttk.Label(container, text="周期天数（交易日）").grid(row=3, column=0, sticky="w", pady=(0, 8))
        self.period_days_entry = ttk.Entry(container, width=24)
        self.period_days_entry.grid(row=3, column=1, sticky="w", pady=(0, 8))
        self.period_days_entry.insert(0, str(default_period_days))

        ttk.Label(container, text="批量数据缓存").grid(row=4, column=0, sticky="w", pady=(0, 8))
        self.use_batch_data_cache_var = tk.BooleanVar(value=default_use_batch_data_cache)
        ttk.Checkbutton(container, text="使用缓存数据回测", variable=self.use_batch_data_cache_var).grid(
            row=4, column=1, sticky="w", pady=(0, 8)
        )

        ttk.Label(container, text="因子缓存").grid(row=5, column=0, sticky="w", pady=(0, 8))
        self.use_factor_cache_var = tk.BooleanVar(value=default_use_factor_cache)
        ttk.Checkbutton(container, text="使用因子缓存（按区间）", variable=self.use_factor_cache_var).grid(
            row=5, column=1, sticky="w", pady=(0, 8)
        )

        ttk.Label(container, text="独立因子列表（逗号/换行分隔）").grid(row=6, column=0, sticky="nw", pady=(0, 8))
        factors_frame = ttk.Frame(container)
        factors_frame.grid(row=6, column=1, sticky="we", pady=(0, 8))
        factors_frame.columnconfigure(0, weight=1)
        self.factors_text = tk.Text(factors_frame, width=78, height=8, wrap="word")
        self.factors_text.grid(row=0, column=0, sticky="we")
        factors_yscroll = ttk.Scrollbar(factors_frame, orient="vertical", command=self.factors_text.yview)
        factors_yscroll.grid(row=0, column=1, sticky="ns")
        self.factors_text.configure(yscrollcommand=factors_yscroll.set)
        if default_factors_text:
            self.factors_text.insert("1.0", default_factors_text)

        action_frame = ttk.Frame(container)
        action_frame.grid(row=7, column=0, columnspan=2, sticky="e", pady=(4, 10))
        self.run_button = ttk.Button(action_frame, text="开始回测", command=self._on_run)
        self.run_button.pack(side="right")

        progress_frame = ttk.LabelFrame(container, text="运行进度", padding=8)
        progress_frame.grid(row=8, column=0, columnspan=2, sticky="we", pady=(8, 4))
        self.stage_var = tk.StringVar(value="（待运行）")
        ttk.Label(
            progress_frame,
            textvariable=self.stage_var,
            foreground="#1f4d8c",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(anchor="w")
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=720,
            mode="determinate",
            maximum=100,
        )
        self.progress_bar.pack(anchor="w", pady=(4, 4))
        self.status_var = tk.StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.status_var, foreground="#666666").pack(anchor="w")

        output_frame = ttk.Frame(container)
        output_frame.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        container.rowconfigure(9, weight=1)

        self.output_text = tk.Text(output_frame, width=92, height=18, wrap="none", state="disabled")
        self.output_text.grid(row=0, column=0, sticky="nsew")
        output_yscroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        output_yscroll.grid(row=0, column=1, sticky="ns")
        output_xscroll = ttk.Scrollbar(output_frame, orient="horizontal", command=self.output_text.xview)
        output_xscroll.grid(row=1, column=0, sticky="we")
        self.output_text.configure(yscrollcommand=output_yscroll.set, xscrollcommand=output_xscroll.set)

        self._worker: threading.Thread | None = None

    def _append_output(self, text: str) -> None:
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def _reset_dates_to_latest(self) -> None:
        latest_start, latest_end, _ = get_strategy_date_range()
        self._latest_start = latest_start
        self._latest_end = latest_end
        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, latest_start)
        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(0, latest_end)
        self.date_hint_var.set(f"最新可用范围：{self._latest_start} ~ {self._latest_end}")

    def _persist_config(self, params: RunParams) -> None:
        try:
            cfg = _load_last_run_config()
            if not isinstance(cfg, dict):
                cfg = {}
            cfg["independent_factor_backtest"] = {
                "factors_text": self.factors_text.get("1.0", "end").rstrip(),
                "hold_num": int(params.hold_num),
                "period_days": int(params.period_days),
                "use_batch_data_cache": bool(params.use_batch_data_cache),
                "use_factor_cache": bool(params.use_factor_cache),
                "start_date": params.start_date or "",
                "end_date": params.end_date or "",
            }
            if params.start_date:
                cfg["start_date"] = params.start_date
            if params.end_date:
                cfg["end_date"] = params.end_date
            _save_last_run_config(cfg)
        except Exception as exc:
            print(f"[配置] 保存独立因子回测配置失败：{exc}")

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.root.update_idletasks()

    def _update_progress(self, stage: str, detail: str, current: int | None, total: int | None) -> None:
        self.stage_var.set(stage)
        self.status_var.set(detail)
        if total and total > 0 and current is not None:
            pct = max(0.0, min(100.0, current * 100.0 / total))
            self.progress_bar.configure(mode="determinate", maximum=100)
            self.progress_bar["value"] = pct
            self.progress_bar.stop()
        else:
            if str(self.progress_bar.cget("mode")) != "indeterminate":
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start(80)
        self.root.update_idletasks()

    def _on_run(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return

        start_date = self.start_entry.get().strip() or None
        end_date = self.end_entry.get().strip() or None
        factor_names = _parse_factor_names(self.factors_text.get("1.0", "end").strip())

        try:
            hold_num = int(self.hold_num_entry.get().strip())
            period_days = int(self.period_days_entry.get().strip())
        except ValueError:
            self._append_output("[参数错误] 每期选股数量 / 周期天数 必须是整数\n")
            return

        params = RunParams(
            start_date=start_date,
            end_date=end_date,
            factor_names=factor_names,
            hold_num=hold_num,
            period_days=period_days,
            use_batch_data_cache=bool(self.use_batch_data_cache_var.get()),
            use_factor_cache=bool(self.use_factor_cache_var.get()),
        )

        self._persist_config(params)

        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

        self.run_button.configure(state="disabled")
        self.progress_bar["value"] = 0
        self.stage_var.set("准备中...")
        self._set_status("运行中...")

        def _progress_cb(stage: str, detail: str, current: int | None, total: int | None) -> None:
            self.root.after(0, lambda: self._update_progress(stage, detail, current, total))

        def _emit(text: str) -> None:
            print(text, end="" if text.endswith("\n") else "\n", flush=True)
            self.root.after(0, lambda: self._append_output(text))

        def _task() -> None:
            try:
                result = run_independent_factor_backtest(params, progress_callback=_progress_cb)
                metrics_df: pd.DataFrame = result["metrics_df"]
                _emit(f"时间范围: {result['start_date']} -> {result['end_date']} ({result['date_reason']})\n")
                _emit(f"行情数量: {result['bar_count']}\n")
                _emit(f"耗时: {result['elapsed']:.2f} 秒\n")
                if result.get("output_dir"):
                    _emit(f"结果目录: {result['output_dir']}\n\n")
                else:
                    _emit("\n")

                if metrics_df is not None and not metrics_df.empty:
                    show_df = metrics_df.copy()
                    show_df["label"] = show_df["factor"].map(FACTOR_LABELS)
                    cols = [
                        "factor",
                        "label",
                        "方向",
                        "风格",
                        "选股数",
                        "周期天数",
                        "组合收益[%]",
                        "基准收益[%]",
                        "超额收益[%]",
                        "IC均值",
                        "ICIR",
                        "RankIC均值",
                        "RankICIR",
                        "RR均值",
                        "RR胜率",
                    ]
                    cols = [c for c in cols if c in show_df.columns]
                    table_text = show_df[cols].to_string(index=False)
                    _emit("=" * 90 + "\n")
                    _emit("【独立因子评估汇总】\n")
                    _emit(table_text + "\n\n")

                for factor_name, info in result["factor_results"].items():
                    single = info["single_factor_results"]
                    stats = single.get("stats")
                    _emit("=" * 90 + "\n")
                    _emit(f"因子: {factor_name} ({FACTOR_LABELS.get(factor_name, '')})\n")
                    _emit(f"方向: {_factor_direction_label(bool(info.get('is_factor_higher_better', True)))}  风格: {_factor_style_label(factor_name)}\n")
                    if stats is not None and hasattr(stats, "to_string"):
                        stats_with_excess = stats
                        try:
                            total_ret = float(stats.loc["Total Return [%]"]) if "Total Return [%]" in stats.index else float("nan")
                            bench_ret = float(stats.loc["Benchmark Return [%]"]) if "Benchmark Return [%]" in stats.index else float("nan")
                            if not (np.isnan(total_ret) or np.isnan(bench_ret)):
                                excess = total_ret - bench_ret
                                stats_with_excess = stats.copy()
                                stats_with_excess.loc["Excess Return [%]"] = excess
                        except Exception:
                            pass
                        _emit(stats_with_excess.to_string() + "\n")

                output_dir = result.get("output_dir")
                if output_dir:
                    _emit("\n" + "=" * 90 + "\n")
                    _emit(f"[结果已保存] {output_dir}\n")
                    _emit(f"  - summary.csv          因子汇总指标（含组合/基准/超额收益）\n")
                    _emit(f"  - run_params.csv       本次运行参数\n")
                    _emit(f"  - per_factor/<因子名>/  每个因子的 stats / equity_curve / returns / IC-RankIC-RR / selected_stocks\n")
                    self.root.after(0, lambda: self._update_progress("完成", f"结果已保存到 {output_dir}", 1, 1))
                    self.root.after(0, lambda: self._set_status(f"完成，结果目录：{output_dir}"))
                else:
                    self.root.after(0, lambda: self._update_progress("完成", "全部因子评估完成", 1, 1))
                    self.root.after(0, lambda: self._set_status("完成"))
            except Exception as exc:
                err = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                print("[异常]\n" + err, flush=True)
                self.root.after(0, lambda: self._append_output("[异常]\n" + err + "\n"))
                self.root.after(0, lambda: self.stage_var.set("异常"))
                self.root.after(0, lambda: self._set_status("异常，详情见输出区"))
            finally:
                self.root.after(0, lambda: self.progress_bar.stop())
                self.root.after(0, lambda: self.run_button.configure(state="normal"))

        self._worker = threading.Thread(target=_task, daemon=True)
        self._worker.start()


if __name__ == "__main__":
    app = IndependentFactorApp()
    app.root.mainloop()
