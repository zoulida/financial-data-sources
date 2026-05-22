#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from workflow_v2 import WorkflowConfigV2, WorkflowV2, _step7_cache_path, load_saved_config  # noqa: E402


@dataclass
class MainWavePullbackConfig:
    topn: int = 20
    max_holding_days: int = 7
    stale_exit_days: int = 3
    stale_exit_min_return: float = 0.01
    stop_loss: float = -0.06
    trailing_stop: float = -0.08
    risk_buy_max: float = 0.80
    risk_sell_min: float = 0.90
    buy_score_min: float = 0.55
    sell_score_min: float = 0.45
    trend_buy_min: float = 0.55
    trend_sell_min: float = 0.45
    pullback_buy_min: float = 0.60
    amount_min: float = 30000000.0
    ret20_min: float = 0.03
    ret60_min: float = 0.00
    max_distance_from_high20: float = 0.12
    max_close_to_ma5: float = 1.03
    max_ret3_for_pullback: float = 0.02
    max_ret5_for_pullback: float = 0.06
    min_rebound_from_low10: float = 0.03
    overheat_ret5: float = 0.15
    overheat_ma5_distance: float = 1.08
    trend_weight: float = 0.45
    pullback_weight: float = 0.45
    risk_weight: float = 0.30
    max_trend_factors: int = 30
    max_pullback_factors: int = 30
    max_risk_factors: int = 20
    min_pullback_factors: int = 5
    output_dir: str = "results_main_wave"
    force_refresh: bool = False


class MainWavePullbackStrategy:
    def __init__(self, wf_config: WorkflowConfigV2, config: MainWavePullbackConfig):
        self.wf_config = wf_config
        self.config = config
        self.output_dir = _THIS_DIR / config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workflow = WorkflowV2(wf_config)
        self.factor_profile = pd.DataFrame()
        self.factor_groups = pd.DataFrame()
        self.trend_rank = pd.DataFrame()
        self.pullback_rank = pd.DataFrame()
        self.risk_rank = pd.DataFrame()
        self.main_wave_score = pd.DataFrame()
        self.strong_trend_mask = pd.DataFrame()
        self.pullback_shape_count = pd.DataFrame()
        self.buy_signal = pd.DataFrame()
        self.condition_diagnostics: Dict[str, Any] = {}

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print("🚀 主升浪回踩再启动策略启动")
        self._prepare_context()
        groups = self._select_factor_groups()
        self.factor_groups = groups
        self._build_scores(groups)
        benchmark = self.workflow._load_benchmark_returns()
        trades, positions, daily_ret = self._run_portfolio()
        daily_signals = self._build_daily_signals(trades)
        backtest, performance = self._build_backtest(daily_ret, benchmark, trades)
        paths = self._save_outputs(groups, daily_signals, trades, positions, backtest, performance, t0)
        print("🎉 主升浪回踩再启动策略完成")
        print(f"📁 结果目录: {self.output_dir}")
        return {
            "factor_groups": groups,
            "daily_signals": daily_signals,
            "trades": trades,
            "positions": positions,
            "backtest": backtest,
            "performance": performance,
            "paths": paths,
        }

    def _prepare_context(self) -> None:
        cfg = self.wf_config
        cfg.enable_factor_profile = True
        cfg.filter_use_train_only = True
        self.workflow._init_qlib()
        if not self.config.force_refresh and self._restore_from_step_cache():
            return
        self.workflow._load_market_data()
        self.workflow._filter_stock_pool()
        self.workflow._build_returns()
        self.workflow._load_factors()
        if not self.workflow.factor_dict:
            raise RuntimeError("加载到 0 个因子，请检查 factor_libraries。")
        self.workflow._standardize_factors()
        eval_upper_bound = cfg.train_end_time if (cfg.filter_use_train_only and cfg.train_end_time) else None
        evaluation, rank_ic, quantile_returns = self._evaluate_factors_for_profile(eval_upper_bound)
        self.factor_profile = self.workflow._profile_factors(
            evaluation, rank_ic, quantile_returns, eval_upper_bound
        )
        if self.factor_profile.empty:
            raise RuntimeError("factor_profile 为空，无法按趋势/回踩/风险分组。")

    def _restore_from_step_cache(self) -> bool:
        cache_path = _step7_cache_path(self.wf_config)
        payload = self._read_step_cache_payload(cache_path)
        used_cache_path = cache_path
        if payload is None:
            latest = self._find_latest_profile_cache()
            if latest is None:
                print(f"  ♻️ 未找到可用第七步画像缓存，将重新生成画像")
                return False
            payload = latest[1]
            used_cache_path = latest[0]
        factor_profile = payload.get("factor_profile", pd.DataFrame())
        standardized_factors = payload.get("standardized_factors", {})
        future_return = payload.get("future_return")
        holding_return = payload.get("holding_return")
        if (
            not isinstance(standardized_factors, dict)
            or not standardized_factors
            or future_return is None
        ):
            print("  ⚠️ 第七步缓存缺少标准化因子或 future_return，将重新生成画像")
            return False
        self.workflow._load_market_data()
        self.workflow._filter_stock_pool()
        self.workflow.future_return = future_return
        self.workflow.holding_return = holding_return if holding_return is not None else future_return
        selected = [str(x) for x in payload.get("selected", [])]
        if selected:
            kept = [name for name in selected if name in standardized_factors]
            if kept:
                standardized_factors = {name: standardized_factors[name] for name in kept}
                print(f"  ♻️ 仅对 selected 因子补画像: {len(kept)} 个")
        self.workflow.standardized_factors = standardized_factors
        if not isinstance(factor_profile, pd.DataFrame) or factor_profile.empty:
            evaluation = payload.get("evaluation", pd.DataFrame())
            rank_ic = payload.get("rank_ic", pd.DataFrame())
            quantile_returns = payload.get("quantile_returns", pd.DataFrame())
            if (
                not isinstance(evaluation, pd.DataFrame)
                or evaluation.empty
                or not isinstance(rank_ic, pd.DataFrame)
                or rank_ic.empty
                or not isinstance(quantile_returns, pd.DataFrame)
            ):
                print("  ⚠️ 第七步缓存缺少画像所需 evaluation/rank_ic/quantile_returns，将重新生成画像")
                return False
            if selected:
                selected_set = set(standardized_factors.keys())
                evaluation = evaluation[evaluation["factor"].astype(str).isin(selected_set)].copy()
                rank_ic = rank_ic[[c for c in rank_ic.columns if str(c) in selected_set]].copy()
                quantile_returns = quantile_returns[
                    quantile_returns["factor"].astype(str).isin(selected_set)
                ].copy()
            eval_upper_bound = (
                self.wf_config.train_end_time
                if (self.wf_config.filter_use_train_only and self.wf_config.train_end_time)
                else None
            )
            print("  ♻️ 缓存无 factor_profile，使用缓存 evaluation/rank_ic 补生成画像")
            factor_profile = self.workflow._profile_factors(evaluation, rank_ic, quantile_returns, eval_upper_bound)
            if factor_profile.empty:
                print("  ⚠️ 补生成 factor_profile 为空，将重新生成画像")
                return False
            payload["factor_profile"] = factor_profile
            try:
                with open(used_cache_path, "wb") as fp:
                    pickle.dump(payload, fp, protocol=pickle.HIGHEST_PROTOCOL)
                print(f"  💾 已将补生成 factor_profile 写回缓存: {used_cache_path.name}")
            except Exception as exc:
                print(f"  ⚠️ factor_profile 写回缓存失败（不影响运行）: {exc}")
        self.factor_profile = factor_profile
        print(f"  ♻️ 已从第七步缓存恢复因子画像与标准化因子: {used_cache_path.name}")
        return True

    @staticmethod
    def _read_step_cache_payload(cache_path: Path) -> Optional[Dict[str, Any]]:
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, "rb") as fp:
                payload = pickle.load(fp)
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def _find_latest_profile_cache(self) -> Optional[Tuple[Path, Dict[str, Any]]]:
        cache_dir = _THIS_DIR / ".step_cache"
        candidates = sorted(cache_dir.glob("step7_*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in candidates:
            payload = self._read_step_cache_payload(path)
            if payload is None:
                continue
            factor_profile = payload.get("factor_profile", pd.DataFrame())
            standardized_factors = payload.get("standardized_factors", {})
            if (
                isinstance(standardized_factors, dict)
                and standardized_factors
                and payload.get("future_return") is not None
                and (
                    (isinstance(factor_profile, pd.DataFrame) and not factor_profile.empty)
                    or (
                        isinstance(payload.get("evaluation"), pd.DataFrame)
                        and not payload.get("evaluation").empty
                        and isinstance(payload.get("rank_ic"), pd.DataFrame)
                        and not payload.get("rank_ic").empty
                    )
                )
            ):
                print(f"  ♻️ 当前 key 未命中，改用最新可用第七步缓存: {path.name}")
                return path, payload
        return None

    def _evaluate_factors_for_profile(
        self, upper_bound_date: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        future = self.workflow.future_return
        if future is None:
            raise RuntimeError("future_return 尚未构造。")
        if upper_bound_date is not None:
            cutoff = pd.Timestamp(upper_bound_date)
            future = future.loc[future.index <= cutoff]
            if future.empty:
                raise ValueError(f"训练期截断 upper_bound_date={upper_bound_date} 后 future_return 为空。")
            print(f"  🛡️  轻量画像评价：仅使用 <= {upper_bound_date} 的数据")
        rows: List[Dict[str, float]] = []
        rank_ic_table = pd.DataFrame(index=future.index)
        quantile_pieces: List[pd.DataFrame] = []
        total = len(self.workflow.standardized_factors)
        print("\n第六步：轻量单因子评价（跳过相关性矩阵）")
        for idx, (name, factor_df) in enumerate(self.workflow.standardized_factors.items(), start=1):
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
            quantile_pieces.append(self.workflow._quantile_returns_vectorized(name, aligned, future))
            if idx == 1 or idx == total or idx % max(total // 10, 1) == 0:
                print(f"  评价进度 {idx}/{total} | rank_ic_ir={rows[-1]['rank_ic_ir']:.3f}", flush=True)
        evaluation = pd.DataFrame(rows).sort_values(
            "rank_ic_ir", key=lambda s: s.abs(), ascending=False, na_position="last"
        ).reset_index(drop=True)
        quantile_returns = (
            pd.concat(quantile_pieces, ignore_index=True)
            if quantile_pieces
            else pd.DataFrame(columns=["factor", "date", "quantile", "ret"])
        )
        print(f"✅ 轻量评价完成: {len(evaluation)} 个因子")
        return evaluation, rank_ic_table, quantile_returns

    def _select_factor_groups(self) -> pd.DataFrame:
        profile = self.factor_profile.copy()
        for col in ["ic_future", "ic_stability", "monotonicity", "ic_past_5d", "ic_risk"]:
            if col not in profile.columns:
                profile[col] = np.nan
        trend = profile[
            (profile["auto_label"] == "trend")
            & (profile["usage"].isin(["alpha_core", "conditional_alpha"]))
            & (profile["ic_future"] > 0.005)
            & (profile["ic_stability"] >= 0.50)
            & (profile["monotonicity"] >= 0.50)
        ].copy()
        trend = self._sort_profile(trend).head(self.config.max_trend_factors)
        trend["group"] = "trend"

        pullback = profile[
            (profile["auto_label"] == "reversal")
            & (profile["usage"] == "conditional_alpha")
            & (profile["ic_future"] > 0.005)
            & (profile["ic_past_5d"] < 0)
            & (profile["ic_stability"] >= 0.45)
        ].copy()
        pullback = self._sort_profile(pullback).head(self.config.max_pullback_factors)
        if len(pullback) < self.config.min_pullback_factors:
            existing = set(pullback["factor"].astype(str)) if not pullback.empty else set()
            fallback = profile[
                (~profile["factor"].astype(str).isin(existing))
                & (profile["usage"] == "conditional_alpha")
                & (profile["ic_future"] > 0.005)
                & (profile["ic_stability"] >= 0.45)
            ].copy()
            need = max(self.config.min_pullback_factors - len(pullback), 0)
            fallback = self._sort_profile(fallback).head(need)
            pullback = pd.concat([pullback, fallback], ignore_index=True)
        pullback = pullback.head(self.config.max_pullback_factors)
        pullback["group"] = "pullback"

        risk = profile[
            (profile["usage"] == "risk_filter")
            & (profile["auto_label"].isin(["risk", "overheat_risk", "negative_trend"]))
            & ((profile["ic_risk"] > 0.02) | (profile["ic_future"] < -0.005))
        ].copy()
        risk = risk.sort_values(
            ["ic_risk", "ic_stability", "ic_future"], ascending=[False, False, True], na_position="last"
        ).head(self.config.max_risk_factors)
        risk["group"] = "risk"

        groups = pd.concat([trend, pullback, risk], ignore_index=True)
        if groups.empty:
            raise RuntimeError("没有可用因子分组，请先检查 factor_profile 分类结果。")
        print(
            "✅ 因子分组完成: "
            f"trend={int((groups['group'] == 'trend').sum())}, "
            f"pullback={int((groups['group'] == 'pullback').sum())}, "
            f"risk={int((groups['group'] == 'risk').sum())}"
        )
        return groups

    @staticmethod
    def _sort_profile(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        temp = df.copy()
        temp["abs_ic_future"] = temp["ic_future"].abs()
        temp = temp.sort_values(
            ["ic_stability", "abs_ic_future", "monotonicity"],
            ascending=[False, False, False],
            na_position="last",
        )
        return temp.drop(columns=["abs_ic_future"], errors="ignore")

    def _build_scores(self, groups: pd.DataFrame) -> None:
        trend_names = groups.loc[groups["group"] == "trend", "factor"].astype(str).tolist()
        pullback_names = groups.loc[groups["group"] == "pullback", "factor"].astype(str).tolist()
        risk_names = groups.loc[groups["group"] == "risk", "factor"].astype(str).tolist()
        profile_map = groups.set_index("factor")

        trend_score = self._combine_factors(trend_names, profile_map, direction_col="ic_future")
        pullback_score = self._combine_factors(pullback_names, profile_map, direction_col="ic_future")
        risk_score = self._combine_factors(risk_names, profile_map, direction_col="ic_risk", fallback_col="ic_future", fallback_sign=-1.0)

        self.trend_rank = trend_score.rank(axis=1, pct=True)
        self.pullback_rank = pullback_score.rank(axis=1, pct=True)
        if risk_score.empty:
            close = self.workflow.panel["close"]
            self.risk_rank = pd.DataFrame(0.5, index=close.index, columns=close.columns)
        else:
            self.risk_rank = risk_score.rank(axis=1, pct=True)

        self.main_wave_score = (
            self.config.trend_weight * self.trend_rank
            + self.config.pullback_weight * self.pullback_rank
            - self.config.risk_weight * self.risk_rank
        )
        self._build_price_masks()
        self.buy_signal = (
            self.strong_trend_mask
            & (self.pullback_rank >= self.config.pullback_buy_min)
            & (self.trend_rank >= self.config.trend_buy_min)
            & (self.risk_rank <= self.config.risk_buy_max)
            & (self.main_wave_score >= self.config.buy_score_min)
            & (self.pullback_shape_count >= 2)
        )
        print("✅ 信号矩阵构造完成")

    def _combine_factors(
        self,
        names: List[str],
        profile_map: pd.DataFrame,
        direction_col: str,
        fallback_col: Optional[str] = None,
        fallback_sign: float = 1.0,
    ) -> pd.DataFrame:
        pieces: List[pd.DataFrame] = []
        for name in names:
            if name not in self.workflow.standardized_factors:
                continue
            direction_value = profile_map.loc[name, direction_col] if direction_col in profile_map.columns else np.nan
            if not np.isfinite(direction_value) or float(direction_value) == 0.0:
                if fallback_col and fallback_col in profile_map.columns:
                    direction_value = fallback_sign * profile_map.loc[name, fallback_col]
            multiplier = float(np.sign(direction_value)) if np.isfinite(direction_value) and float(direction_value) != 0.0 else 1.0
            pieces.append(self.workflow.standardized_factors[name] * multiplier)
        if not pieces:
            return pd.DataFrame()
        panel = pd.concat(pieces, keys=range(len(pieces)), names=["factor", "date"])
        return panel.groupby(level="date").mean()

    def _build_price_masks(self) -> None:
        panel = self.workflow.panel
        close = panel["close"]
        amount = panel.get("amount", close * panel.get("volume", 0.0))
        ma5 = close.rolling(5, min_periods=5).mean()
        ma10 = close.rolling(10, min_periods=10).mean()
        ma20 = close.rolling(20, min_periods=20).mean()
        hh20 = close.rolling(20, min_periods=20).max()
        ll10 = close.rolling(10, min_periods=10).min()
        ret3 = close / close.shift(3) - 1.0
        ret5 = close / close.shift(5) - 1.0
        ret20 = close / close.shift(20) - 1.0
        ret60 = close / close.shift(60) - 1.0
        amount_mean_5 = amount.rolling(5, min_periods=5).mean()
        self.ma5 = ma5
        self.ma10 = ma10
        self.ma20 = ma20
        self.ret5 = ret5

        cond_close_ma20 = close > ma20
        cond_ma5_ma10 = ma5 > ma10
        cond_ma10_ma20 = ma10 >= ma20 * 0.995
        cond_ret20 = ret20 >= self.config.ret20_min
        cond_ret60 = ret60 >= self.config.ret60_min
        cond_hh20 = close >= hh20 * (1.0 - self.config.max_distance_from_high20)
        cond_amount_abs = amount_mean_5 >= self.config.amount_min
        cond_amount_rank = amount_mean_5.rank(axis=1, pct=True) >= 0.20
        cond_amount = cond_amount_abs | cond_amount_rank

        self.strong_trend_mask = (
            cond_close_ma20
            & cond_ma5_ma10
            & cond_ma10_ma20
            & cond_ret20
            & cond_ret60
            & cond_hh20
            & cond_amount
        )
        shape_items = [
            close <= ma5 * self.config.max_close_to_ma5,
            close >= ma20,
            ret3 <= self.config.max_ret3_for_pullback,
            ret5 <= self.config.max_ret5_for_pullback,
            close >= ll10 * (1.0 + self.config.min_rebound_from_low10),
        ]
        self.pullback_shape_count = sum(item.astype(float).fillna(0.0) for item in shape_items)
        self.condition_diagnostics = {
            "cond_close_ma20_true": int(cond_close_ma20.fillna(False).sum().sum()),
            "cond_ma5_ma10_true": int(cond_ma5_ma10.fillna(False).sum().sum()),
            "cond_ma10_ma20_true": int(cond_ma10_ma20.fillna(False).sum().sum()),
            "cond_ret20_true": int(cond_ret20.fillna(False).sum().sum()),
            "cond_ret60_true": int(cond_ret60.fillna(False).sum().sum()),
            "cond_hh20_true": int(cond_hh20.fillna(False).sum().sum()),
            "cond_amount_abs_true": int(cond_amount_abs.fillna(False).sum().sum()),
            "cond_amount_rank_true": int(cond_amount_rank.fillna(False).sum().sum()),
            "strong_trend_true": int(self.strong_trend_mask.fillna(False).sum().sum()),
            "amount_filter_note": "amount_mean_5 >= 30000000 或当日成交额横截面排名 >= 20%",
        }

    def _run_portfolio(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
        close = self.workflow.panel["close"]
        dates = close.index.intersection(self.main_wave_score.index).sort_values()
        instruments = close.columns
        next_ret = close.shift(-1) / close - 1.0
        positions: Dict[str, Dict[str, Any]] = {}
        trade_rows: List[Dict[str, Any]] = []
        position_rows: List[Dict[str, Any]] = []
        daily_returns: Dict[pd.Timestamp, float] = {}
        sell_signal_map: Dict[Tuple[pd.Timestamp, str], str] = {}

        for date_pos, date in enumerate(dates):
            if date not in close.index:
                continue
            close_row = close.loc[date]
            sell_list: List[Tuple[str, str]] = []
            for code, pos in list(positions.items()):
                price = close_row.get(code, np.nan)
                if not np.isfinite(price):
                    sell_list.append((code, "price_nan"))
                    continue
                pos["highest_close_since_entry"] = max(float(pos["highest_close_since_entry"]), float(price))
                holding_days = int(date_pos - pos["entry_pos"])
                reason = self._sell_reason(date, code, pos, price, holding_days)
                if reason:
                    sell_list.append((code, reason))

            for code, reason in sell_list:
                pos = positions.get(code)
                price = close_row.get(code, np.nan)
                if pos is None or not np.isfinite(price):
                    continue
                holding_days = int(date_pos - pos["entry_pos"])
                realized_return = float(price) / float(pos["entry_price"]) - 1.0
                trade_rows.append(
                    {
                        "trade_date": date,
                        "signal_date": date,
                        "instrument": code,
                        "action": "SELL",
                        "price": float(price),
                        "weight": float(pos.get("weight", 0.0)),
                        "reason": reason,
                        "holding_days": holding_days,
                        "realized_return": realized_return,
                    }
                )
                sell_signal_map[(date, code)] = reason
                positions.pop(code, None)

            slots = max(self.config.topn - len(positions), 0)
            if slots > 0:
                candidates = self._buy_candidates(date, instruments, positions)
                for code in candidates[:slots]:
                    price = close_row.get(code, np.nan)
                    if not np.isfinite(price) or price <= 0:
                        continue
                    positions[code] = {
                        "entry_date": date,
                        "entry_pos": date_pos,
                        "entry_price": float(price),
                        "highest_close_since_entry": float(price),
                        "weight": 0.0,
                    }
                    trade_rows.append(
                        {
                            "trade_date": date,
                            "signal_date": date,
                            "instrument": code,
                            "action": "BUY",
                            "price": float(price),
                            "weight": np.nan,
                            "reason": "buy_main_wave_pullback",
                            "holding_days": 0,
                            "realized_return": np.nan,
                        }
                    )

            weight = 1.0 / len(positions) if positions else 0.0
            for pos in positions.values():
                pos["weight"] = weight
            for row in reversed(trade_rows):
                if row["trade_date"] != date:
                    break
                if row["action"] == "BUY":
                    row["weight"] = weight

            held_codes = list(positions.keys())
            if held_codes and date in next_ret.index:
                ret_value = float(next_ret.loc[date].reindex(held_codes).mean())
                daily_returns[date] = 0.0 if not np.isfinite(ret_value) else ret_value
            else:
                daily_returns[date] = 0.0

            for code, pos in positions.items():
                price = close_row.get(code, np.nan)
                if not np.isfinite(price):
                    continue
                holding_days = int(date_pos - pos["entry_pos"])
                position_rows.append(
                    {
                        "date": date,
                        "instrument": code,
                        "weight": weight,
                        "entry_date": pos["entry_date"],
                        "entry_price": float(pos["entry_price"]),
                        "holding_days": holding_days,
                        "highest_close_since_entry": float(pos["highest_close_since_entry"]),
                        "unrealized_return": float(price) / float(pos["entry_price"]) - 1.0,
                    }
                )

        trades = pd.DataFrame(trade_rows)
        positions_df = pd.DataFrame(position_rows)
        daily_ret = pd.Series(daily_returns, name="main_wave_pullback").sort_index()
        self._sell_signal_map = sell_signal_map
        return trades, positions_df, daily_ret

    def _sell_reason(
        self, date: pd.Timestamp, code: str, pos: Dict[str, Any], price: float, holding_days: int
    ) -> str:
        ma10_value = self._safe_at(self.ma10, date, code)
        ma20_value = self._safe_at(self.ma20, date, code)
        ma5_value = self._safe_at(self.ma5, date, code)
        ret5_value = self._safe_at(self.ret5, date, code)
        if np.isfinite(ma10_value) and price < ma10_value:
            return "trend_break_ma10"
        if np.isfinite(ma20_value) and price < ma20_value * 0.98:
            return "trend_break_ma20_2pct"
        trend_value = self._safe_at(self.trend_rank, date, code)
        score_value = self._safe_at(self.main_wave_score, date, code)
        risk_value = self._safe_at(self.risk_rank, date, code)
        if np.isfinite(trend_value) and trend_value < self.config.trend_sell_min:
            return "trend_rank_below_045"
        if np.isfinite(score_value) and score_value < self.config.sell_score_min:
            return "score_below_045"
        if np.isfinite(risk_value) and risk_value >= self.config.risk_sell_min:
            return "risk_rank_above_090"
        if np.isfinite(ret5_value) and np.isfinite(ma5_value):
            if ret5_value >= self.config.overheat_ret5 and price > ma5_value * self.config.overheat_ma5_distance:
                return "overheat_ret5_ma5_distance"
        entry_price = float(pos["entry_price"])
        if price / entry_price - 1.0 <= self.config.stop_loss:
            return "stop_loss_6pct"
        highest = float(pos["highest_close_since_entry"])
        if highest > 0 and price / highest - 1.0 <= self.config.trailing_stop:
            return "trailing_stop_8pct"
        if holding_days >= self.config.max_holding_days:
            return "max_holding_days_7"
        if holding_days >= self.config.stale_exit_days and price / entry_price - 1.0 < self.config.stale_exit_min_return:
            return "stale_exit_3d_lt_1pct"
        return ""

    def _buy_candidates(
        self, date: pd.Timestamp, instruments: pd.Index, positions: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        if date not in self.buy_signal.index:
            return []
        row = self.buy_signal.loc[date].reindex(instruments).fillna(False)
        codes = [str(code) for code, ok in row.items() if bool(ok) and str(code) not in positions]
        if not codes:
            return []
        rank_df = pd.DataFrame(
            {
                "main_wave_score": self.main_wave_score.loc[date].reindex(codes),
                "trend_rank": self.trend_rank.loc[date].reindex(codes),
                "pullback_rank": self.pullback_rank.loc[date].reindex(codes),
                "risk_rank": self.risk_rank.loc[date].reindex(codes),
            }
        ).dropna(subset=["main_wave_score"])
        rank_df = rank_df.sort_values(
            ["main_wave_score", "trend_rank", "pullback_rank", "risk_rank"],
            ascending=[False, False, False, True],
        )
        return [str(x) for x in rank_df.index.tolist()]

    @staticmethod
    def _safe_at(df: pd.DataFrame, date: pd.Timestamp, code: str) -> float:
        try:
            value = df.at[date, code]
            return float(value) if np.isfinite(value) else np.nan
        except Exception:
            return np.nan

    def _build_daily_signals(self, trades: pd.DataFrame) -> pd.DataFrame:
        records: List[pd.DataFrame] = []
        fields = {
            "trend_rank": self.trend_rank,
            "pullback_rank": self.pullback_rank,
            "risk_rank": self.risk_rank,
            "main_wave_score": self.main_wave_score,
            "strong_trend_mask": self.strong_trend_mask,
            "pullback_shape_count": self.pullback_shape_count,
            "buy_signal": self.buy_signal,
        }
        stacked = []
        for name, df in fields.items():
            s = df.stack(dropna=False).rename(name)
            stacked.append(s)
        result = pd.concat(stacked, axis=1).reset_index()
        result.columns = ["signal_date", "instrument"] + list(fields.keys())
        result["trade_date"] = result["signal_date"]
        result["sell_signal"] = False
        result["sell_reason"] = ""
        if not trades.empty:
            sells = trades[trades["action"] == "SELL"]
            sell_keys = {(row.trade_date, row.instrument): row.reason for row in sells.itertuples(index=False)}
            if sell_keys:
                key_series = list(zip(result["signal_date"], result["instrument"].astype(str)))
                result["sell_reason"] = [sell_keys.get(key, "") for key in key_series]
                result["sell_signal"] = result["sell_reason"] != ""
        active = result["buy_signal"].fillna(False).astype(bool) | result["sell_signal"].fillna(False).astype(bool)
        high_score = result["main_wave_score"] >= self.config.buy_score_min
        return result[active | high_score].reset_index(drop=True)

    def _build_backtest(
        self, daily_ret: pd.Series, benchmark: pd.Series, trades: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        test_start = pd.Timestamp(self.wf_config.test_start_time) if self.wf_config.test_start_time else None
        perf_trades = trades
        if test_start is not None:
            daily_ret = daily_ret.loc[daily_ret.index >= test_start]
            benchmark = benchmark.loc[benchmark.index >= test_start]
            if not trades.empty and "trade_date" in trades.columns:
                trade_dates = pd.to_datetime(trades["trade_date"])
                perf_trades = trades.loc[trade_dates >= test_start].copy()
        common = daily_ret.index.union(benchmark.index).sort_values()
        backtest = pd.DataFrame(index=common)
        backtest["main_wave_pullback"] = daily_ret.reindex(common).fillna(0.0)
        backtest["benchmark"] = benchmark.reindex(common).fillna(0.0)
        backtest["main_wave_nav"] = (1.0 + backtest["main_wave_pullback"]).cumprod()
        backtest["benchmark_nav"] = (1.0 + backtest["benchmark"]).cumprod()
        perf = self._performance(backtest["main_wave_pullback"], backtest["benchmark"], perf_trades)
        return backtest, pd.DataFrame([perf])

    def _performance(self, daily_ret: pd.Series, benchmark: pd.Series, trades: pd.DataFrame) -> Dict[str, Any]:
        if daily_ret.empty:
            return {
                "signal": "main_wave_pullback",
                "annual_return": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "excess_return": 0.0,
                "win_rate": 0.0,
                "avg_holding_days": 0.0,
                "turnover": 0.0,
                "trade_count": 0,
            }
        cumulative = (1.0 + daily_ret.fillna(0.0)).cumprod()
        ann_ret = cumulative.iloc[-1] ** (252.0 / max(len(daily_ret), 1)) - 1.0
        std = daily_ret.std()
        sharpe = daily_ret.mean() / std * np.sqrt(252.0) if std > 0 else 0.0
        max_dd = float(((cumulative - cumulative.cummax()) / cumulative.cummax()).min())
        common = daily_ret.index.intersection(benchmark.index)
        excess = float((daily_ret.loc[common] - benchmark.loc[common]).mean() * 252.0) if len(common) else 0.0
        sells = trades[trades["action"] == "SELL"] if not trades.empty else pd.DataFrame()
        win_rate = float((sells["realized_return"] > 0).mean()) if not sells.empty else 0.0
        avg_holding = float(sells["holding_days"].mean()) if not sells.empty else 0.0
        buys = trades[trades["action"] == "BUY"] if not trades.empty else pd.DataFrame()
        turnover = float(len(buys) / max(len(daily_ret), 1))
        return {
            "signal": "main_wave_pullback",
            "annual_return": float(ann_ret),
            "sharpe": float(sharpe),
            "max_drawdown": max_dd,
            "excess_return": excess,
            "win_rate": win_rate,
            "avg_holding_days": avg_holding,
            "turnover": turnover,
            "trade_count": int(len(trades)),
            "ic_periods": int(len(daily_ret)),
        }

    def _save_outputs(
        self,
        groups: pd.DataFrame,
        daily_signals: pd.DataFrame,
        trades: pd.DataFrame,
        positions: pd.DataFrame,
        backtest: pd.DataFrame,
        performance: pd.DataFrame,
        start_time: float,
    ) -> Dict[str, str]:
        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        paths = {
            "factor_groups": self.output_dir / f"main_wave_factor_groups_{ts}.csv",
            "daily_signals": self.output_dir / f"main_wave_daily_signals_{ts}.csv",
            "trades": self.output_dir / f"main_wave_trades_{ts}.csv",
            "positions": self.output_dir / f"main_wave_positions_{ts}.csv",
            "backtest": self.output_dir / f"main_wave_backtest_{ts}.csv",
            "performance": self.output_dir / f"main_wave_performance_{ts}.csv",
            "summary": self.output_dir / f"main_wave_summary_{ts}.json",
        }
        groups.to_csv(paths["factor_groups"], index=False, encoding="utf-8-sig")
        daily_signals.to_csv(paths["daily_signals"], index=False, encoding="utf-8-sig")
        trades.to_csv(paths["trades"], index=False, encoding="utf-8-sig")
        positions.to_csv(paths["positions"], index=False, encoding="utf-8-sig")
        backtest.to_csv(paths["backtest"], encoding="utf-8-sig")
        performance.to_csv(paths["performance"], index=False, encoding="utf-8-sig")
        summary = {
            "execution_mode": "same_day_close_mode",
            "lookahead_note": "信号使用 T 日完整日线并假设 T 日收盘成交，属于尾盘/收盘集合竞价可执行假设；不使用 T+1 及以后未来数据。",
            "workflow_config": asdict(self.wf_config),
            "strategy_config": asdict(self.config),
            "factor_group_counts": groups["group"].value_counts().to_dict() if not groups.empty else {},
            "condition_diagnostics": self.condition_diagnostics,
            "trade_count": int(len(trades)),
            "position_rows": int(len(positions)),
            "elapsed_seconds": round(time.perf_counter() - start_time, 2),
            "paths": {k: str(v) for k, v in paths.items()},
        }
        with open(paths["summary"], "w", encoding="utf-8") as fp:
            json.dump(summary, fp, ensure_ascii=False, indent=2, default=str)
        print("💾 已保存主升浪策略结果")
        return {k: str(v) for k, v in paths.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="主升浪回踩再启动策略")
    parser.add_argument("--topn", type=int, default=20)
    parser.add_argument("--max-holding-days", type=int, default=7)
    parser.add_argument("--stop-loss", type=float, default=-0.06)
    parser.add_argument("--trailing-stop", type=float, default=-0.08)
    parser.add_argument("--buy-score-min", type=float, default=0.55)
    parser.add_argument("--risk-buy-max", type=float, default=0.80)
    parser.add_argument("--force-refresh", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wf_config = load_saved_config()
    strategy_config = MainWavePullbackConfig(
        topn=args.topn,
        max_holding_days=args.max_holding_days,
        stop_loss=args.stop_loss,
        trailing_stop=args.trailing_stop,
        buy_score_min=args.buy_score_min,
        risk_buy_max=args.risk_buy_max,
        force_refresh=bool(args.force_refresh),
    )
    strategy = MainWavePullbackStrategy(wf_config, strategy_config)
    strategy.run()


if __name__ == "__main__":
    main()
