"""主升浪事件标注。

事件定义（向量化实现）：
对每只股票每个交易日 t：
- forward_max_return[t] = max( close[t+1..t+N] ) / close[t] - 1
  (即 t 日收盘后买入，未来 N 日内可能拿到的最大账面浮盈)
- forward_drawdown[t]  = 在到达上述峰值之前的最大回撤（以买入价为基准计算的最低点亏损）
- time_to_peak[t]      = 达到上述峰值用了多少个交易日（1..N）
- is_blastoff[t]       = (forward_max_return[t] >= return_threshold) and (forward_drawdown[t] >= -max_drawdown)

注意：
- 用 t 日收盘价作为买入价（与因子在 t 日收盘后生效的逻辑对齐）；
- 全部使用 numpy 向量化滚动窗口，避免逐股逐日 Python 循环；
- 提供基于参数+日期范围的 pickle 缓存。
"""
from __future__ import annotations

import hashlib
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.主升浪因子挖掘 import config


def _event_cache_path(
    start_date: str,
    end_date: str,
    forward_days: int,
    return_threshold: float,
    max_drawdown: float,
    n_codes: int,
) -> Path:
    key = f"{start_date}|{end_date}|{forward_days}|{return_threshold}|{max_drawdown}|{n_codes}"
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:12]
    return config.EVENT_CACHE_DIR / f"events__{start_date}_{end_date}__{digest}.pkl"


def _compute_max_and_argmax_in_future(arr: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    """对每个位置 t，计算 (t+1 .. t+window) 区间的最大值，以及最大值首次出现的相对天数（1..window）。

    返回 (max_arr, argmax_arr)，越界处填 NaN / -1。
    """
    n_rows, n_cols = arr.shape
    max_arr = np.full((n_rows, n_cols), np.nan, dtype=float)
    arg_arr = np.full((n_rows, n_cols), -1, dtype=np.int32)

    # 直接迭代每个 j 列开销更低（numpy 内循环列）
    for j in range(n_cols):
        col = arr[:, j]
        for t in range(n_rows - 1):
            end = min(t + 1 + window, n_rows)
            window_slice = col[t + 1 : end]
            if window_slice.size == 0:
                continue
            # 跳过全 NaN
            if np.all(np.isnan(window_slice)):
                continue
            local_max = np.nanmax(window_slice)
            local_arg = int(np.nanargmax(window_slice)) + 1  # 1-based
            max_arr[t, j] = local_max
            arg_arr[t, j] = local_arg
    return max_arr, arg_arr


def compute_blastoff_events(
    close_df: pd.DataFrame,
    forward_days: int = config.BLASTOFF_FORWARD_DAYS,
    return_threshold: float = config.BLASTOFF_RETURN_THRESHOLD,
    max_drawdown: float = config.BLASTOFF_MAX_DRAWDOWN,
    use_cache: bool = True,
) -> dict[str, Any]:
    """为每只股票每个交易日计算主升浪事件标注。

    返回 dict 包含：
    - is_blastoff (T×N bool)
    - forward_max_return (T×N float)
    - forward_drawdown (T×N float, 负数；若期间未跌破买入价则为 0)
    - time_to_peak (T×N int, 1..forward_days; -1 表示无效)
    - meta: dict, 记录参数
    """
    if close_df.empty:
        empty = close_df.copy()
        return {
            "is_blastoff": empty.astype(bool),
            "forward_max_return": empty.astype(float),
            "forward_drawdown": empty.astype(float),
            "time_to_peak": empty.astype(int),
            "meta": {
                "forward_days": forward_days,
                "return_threshold": return_threshold,
                "max_drawdown": max_drawdown,
            },
        }

    start_date = str(close_df.index[0])
    end_date = str(close_df.index[-1])
    cache_path = _event_cache_path(
        start_date=start_date,
        end_date=end_date,
        forward_days=forward_days,
        return_threshold=return_threshold,
        max_drawdown=max_drawdown,
        n_codes=close_df.shape[1],
    )
    if use_cache and cache_path.exists():
        try:
            with cache_path.open("rb") as f:
                cached = pickle.load(f)
            if isinstance(cached, dict) and "is_blastoff" in cached:
                print(f"[事件缓存] 命中 {cache_path.name}")
                return cached
        except Exception as exc:  # pragma: no cover
            print(f"[事件缓存] 读取失败 {cache_path.name}: {exc}")

    arr = close_df.to_numpy(dtype=float)
    n_rows, n_cols = arr.shape

    # 1. 未来最大值与到达天数
    forward_max_value, time_to_peak = _compute_max_and_argmax_in_future(arr, forward_days)

    with np.errstate(divide="ignore", invalid="ignore"):
        forward_max_return = forward_max_value / arr - 1.0

    # 2. 在峰值出现之前的最大回撤（以 t 日收盘价为基准）
    forward_drawdown = np.full_like(arr, np.nan, dtype=float)
    for j in range(n_cols):
        col = arr[:, j]
        for t in range(n_rows - 1):
            tp = time_to_peak[t, j]
            if tp <= 0:
                continue
            end = t + 1 + tp  # 包含峰值当日
            window_slice = col[t + 1 : end]
            if window_slice.size == 0 or np.all(np.isnan(window_slice)):
                continue
            local_min = np.nanmin(window_slice)
            base = arr[t, j]
            if not np.isfinite(base) or base <= 0:
                continue
            dd = local_min / base - 1.0
            # drawdown 取期间最低点相对买入价的回撤；若期间从未跌破买入价则为 0（不算回撤）
            forward_drawdown[t, j] = min(dd, 0.0)

    # 3. 事件布尔
    is_blastoff = (
        (forward_max_return >= return_threshold)
        & (forward_drawdown >= -abs(max_drawdown))
        & np.isfinite(forward_max_return)
    )

    result = {
        "is_blastoff": pd.DataFrame(is_blastoff, index=close_df.index, columns=close_df.columns),
        "forward_max_return": pd.DataFrame(forward_max_return, index=close_df.index, columns=close_df.columns),
        "forward_drawdown": pd.DataFrame(forward_drawdown, index=close_df.index, columns=close_df.columns),
        "time_to_peak": pd.DataFrame(time_to_peak, index=close_df.index, columns=close_df.columns),
        "meta": {
            "forward_days": forward_days,
            "return_threshold": return_threshold,
            "max_drawdown": max_drawdown,
            "start_date": start_date,
            "end_date": end_date,
        },
    }

    if use_cache:
        try:
            config.EVENT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with cache_path.open("wb") as f:
                pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"[事件缓存] 已写入 {cache_path.name}")
        except Exception as exc:  # pragma: no cover
            print(f"[事件缓存] 写入失败 {cache_path.name}: {exc}")

    return result


def summarize_events(events: dict[str, Any]) -> pd.DataFrame:
    """对事件标注矩阵做一个总览统计，便于直观看正样本规模。"""
    is_blastoff = events.get("is_blastoff")
    forward_max_return = events.get("forward_max_return")
    time_to_peak = events.get("time_to_peak")
    if not isinstance(is_blastoff, pd.DataFrame) or is_blastoff.empty:
        return pd.DataFrame()

    total_obs = int(is_blastoff.notna().to_numpy().sum())
    total_events = int(is_blastoff.fillna(False).to_numpy().sum())
    event_rate = (total_events / total_obs) if total_obs > 0 else float("nan")

    summary = {
        "样本观测数": total_obs,
        "主升浪事件数": total_events,
        "事件占比": event_rate,
    }
    if isinstance(forward_max_return, pd.DataFrame):
        masked = forward_max_return.where(is_blastoff.fillna(False))
        summary["事件平均最大涨幅"] = float(masked.stack().mean()) if masked.notna().any().any() else float("nan")
    if isinstance(time_to_peak, pd.DataFrame):
        masked_ttp = time_to_peak.where(is_blastoff.fillna(False)).replace(-1, pd.NA)
        try:
            summary["事件平均起爆速度(日)"] = float(pd.to_numeric(masked_ttp.stack(), errors="coerce").mean())
        except Exception:
            summary["事件平均起爆速度(日)"] = float("nan")

    return pd.DataFrame([summary])
