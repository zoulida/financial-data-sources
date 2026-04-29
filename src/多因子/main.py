from __future__ import annotations

import importlib
import inspect
import json
import sys
import threading
import time
import warnings
from collections.abc import Callable
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API.*",
    category=UserWarning,
)

import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
import pandas as pd

from src.多因子 import config
from src.多因子.backtest_vectorbt import (
    build_rebalance_mask,
    build_target_weights,
    extract_backtest_results,
    run_vectorbt_backtest,
)
from src.多因子.data_loader import (
    build_data_bundle,
    clear_batch_data_cache,
    get_strategy_date_range,
    list_batch_data_cache_files,
)
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
# True 表示“因子值越大越好”；
# False 表示“因子值越小越好”。
# 当前默认均按“越大越好”处理，如个别因子需要反向，可在此单独覆盖。
BASE_FACTOR_HIGHER_BETTER = {
    "momentum_20": True,
    "risk_adjusted_momentum_20": True,
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
            "is_factor_higher_better": True,
            "group": "alpha158",
        }
    return discovered


def _infer_factor_args(module_name: str, function_name: str) -> list[str] | None:
    """从 compute 函数签名推断注册表所需字段名。"""
    try:
        module = importlib.import_module(module_name)
        compute_func = getattr(module, function_name)
        signature = inspect.signature(compute_func)
    except (ImportError, AttributeError, ValueError, TypeError):
        return None

    args: list[str] = []
    for param_name, parameter in signature.parameters.items():
        if parameter.kind not in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            continue
        if not param_name.endswith("_df"):
            return None
        field_name = param_name.removesuffix("_df")
        args.append(field_name)
    return args


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
        module_name = f"src.多因子.factors.alpha101.{factor_name}"
        function_name = f"compute_{factor_name}"
        if spec is None:
            inferred_args = _infer_factor_args(module_name, function_name)
            if inferred_args is None:
                continue
            spec = {"args": inferred_args, "label": f"Alpha101 #{factor_name.removeprefix('alpha')}"}
        factor_key = f"alpha101.{factor_name}"
        discovered[factor_key] = {
            "module": module_name,
            "function": function_name,
            "args": list(spec["args"]),
            "label": str(spec["label"]),
            "is_factor_higher_better": True,
            "group": "alpha101",
        }
    return discovered


def _discover_alpha191_factors() -> dict[str, dict[str, object]]:
    """扫描 alpha191 子目录，构建可注册因子清单。"""
    alpha_dir = Path(__file__).resolve().parent / "factors" / "alpha191"
    if not alpha_dir.exists():
        return {}

    unsupported_factors = {"alpha030", "alpha143"}
    discovered: dict[str, dict[str, object]] = {}
    for file_path in sorted(alpha_dir.glob("alpha*.py")):
        if file_path.stem.startswith("_"):
            continue
        factor_name = file_path.stem
        if factor_name in unsupported_factors:
            continue
        module_name = f"src.多因子.factors.alpha191.{factor_name}"
        function_name = f"compute_{factor_name}"
        inferred_args = _infer_factor_args(module_name, function_name)
        if inferred_args is None:
            continue
        factor_key = f"alpha191.{factor_name}"
        discovered[factor_key] = {
            "module": module_name,
            "function": function_name,
            "args": inferred_args,
            "label": f"国君朝阳191 #{factor_name.removeprefix('alpha')}",
            "is_factor_higher_better": True,
            "group": "alpha191",
        }
    return discovered


FACTOR_REGISTRY: dict[str, dict[str, object]] = {
    "momentum_20": {
        "kind": "builtin",
        "label": BASE_FACTOR_LABELS["momentum_20"],
        "is_factor_higher_better": BASE_FACTOR_HIGHER_BETTER["momentum_20"],
        "group": "base",
    },
    "risk_adjusted_momentum_20": {
        "kind": "builtin",
        "label": BASE_FACTOR_LABELS["risk_adjusted_momentum_20"],
        "is_factor_higher_better": BASE_FACTOR_HIGHER_BETTER["risk_adjusted_momentum_20"],
        "group": "base",
    },
}
FACTOR_REGISTRY.update(_discover_alpha158_factors())
FACTOR_REGISTRY.update(_discover_alpha101_factors())
FACTOR_REGISTRY.update(_discover_alpha191_factors())

FACTOR_HIGHER_BETTER = {name: bool(spec.get("is_factor_higher_better", not bool(spec.get("ascending", False)))) for name, spec in FACTOR_REGISTRY.items()}
FACTOR_DIRECTIONS = {name: not is_factor_higher_better for name, is_factor_higher_better in FACTOR_HIGHER_BETTER.items()}
FACTOR_LABELS = {name: str(spec["label"]) for name, spec in FACTOR_REGISTRY.items()}


FACTOR_CACHE_DIR = Path(__file__).resolve().parent / "factor_cache"
CANDIDATE_EVALUATION_CACHE_DIR = Path(__file__).resolve().parent / "candidate_evaluation_cache"


def _rank_score_by_factor_direction(factor_df: pd.DataFrame, is_factor_higher_better: bool) -> pd.DataFrame:
    """按“因子值高低是否更好”的语义生成分数。"""
    return rank_score(factor_df, ascending=is_factor_higher_better)


def _factor_direction_label(is_factor_higher_better: bool) -> str:
    """生成阶段输出中使用的因子方向说明。"""
    return "因子大→好(is_factor_higher_better=True)" if is_factor_higher_better else "因子小→好(is_factor_higher_better=False)"


def _factor_cache_path(factor_name: str, start_date: str, end_date: str) -> Path:
    """构造因子缓存文件路径。文件名包含日期范围，确保不同区间互不复用。"""
    safe_name = factor_name.replace("/", "_").replace("\\", "_")
    return FACTOR_CACHE_DIR / f"{safe_name}__{start_date}_{end_date}.pkl"


def _load_factor_from_cache(factor_name: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    """命中缓存时加载因子矩阵；未命中或读取失败返回 None。"""
    cache_path = _factor_cache_path(factor_name, start_date, end_date)
    if not cache_path.exists():
        return None
    try:
        cached = pd.read_pickle(cache_path)
    except Exception as exc:  # pragma: no cover - 缓存损坏时回退重新计算
        print(f"[缓存] 读取 {cache_path.name} 失败，将重新计算：{exc}")
        return None
    if not isinstance(cached, pd.DataFrame):
        return None
    return cached


def _save_factor_to_cache(factor_name: str, start_date: str, end_date: str, factor_df: pd.DataFrame) -> None:
    """把因子矩阵写入缓存文件，确保目录存在。"""
    FACTOR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _factor_cache_path(factor_name, start_date, end_date)
    try:
        factor_df.to_pickle(cache_path)
    except Exception as exc:  # pragma: no cover - 写缓存失败不影响主流程
        print(f"[缓存] 写入 {cache_path.name} 失败：{exc}")


def _list_factor_cache_files() -> list[Path]:
    """列出当前缓存目录下的全部因子缓存文件。"""
    if not FACTOR_CACHE_DIR.exists():
        return []
    return sorted(FACTOR_CACHE_DIR.glob("*.pkl"))


def _candidate_evaluation_cache_path(factor_name: str, start_date: str, end_date: str) -> Path:
    """构造候选因子评估缓存文件路径。"""
    safe_name = factor_name.replace("/", "_").replace("\\", "_")
    return CANDIDATE_EVALUATION_CACHE_DIR / f"{safe_name}__{start_date}_{end_date}.pkl"


def _load_candidate_evaluation_from_cache(factor_name: str, start_date: str, end_date: str) -> dict[str, object] | None:
    """命中缓存时加载候选因子评估结果；未命中或读取失败返回 None。"""
    cache_path = _candidate_evaluation_cache_path(factor_name, start_date, end_date)
    if not cache_path.exists():
        return None
    try:
        cached = pd.read_pickle(cache_path)
    except Exception as exc:  # pragma: no cover - 缓存损坏时回退重新计算
        print(f"[评估缓存] 读取 {cache_path.name} 失败，将重新计算：{exc}")
        return None
    if not isinstance(cached, dict):
        return None
    required_keys = {
        "masked_factor_df",
        "factor_score_df",
        "ic_series",
        "rank_ic_series",
        "rr_series",
        "summary_df",
        "single_factor_results",
    }
    if not required_keys.issubset(cached.keys()):
        return None
    return cached


def _save_candidate_evaluation_to_cache(
    factor_name: str,
    start_date: str,
    end_date: str,
    evaluation_result: dict[str, object],
) -> None:
    """把候选因子评估结果写入缓存文件。"""
    CANDIDATE_EVALUATION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _candidate_evaluation_cache_path(factor_name, start_date, end_date)
    try:
        pd.to_pickle(evaluation_result, cache_path)
    except Exception as exc:  # pragma: no cover - 写缓存失败不影响主流程
        print(f"[评估缓存] 写入 {cache_path.name} 失败：{exc}")


LAST_RUN_PATH = Path(__file__).resolve().parent / ".last_run.json"


def _load_last_run_config() -> dict[str, object]:
    if not LAST_RUN_PATH.exists():
        return {}
    try:
        data = json.loads(LAST_RUN_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - 配置损坏时回退默认
        print(f"[配置] 读取 {LAST_RUN_PATH.name} 失败，将使用默认配置：{exc}")
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _load_last_run_dates() -> tuple[str | None, str | None]:
    """读取上次运行时使用的日期范围；无文件或解析失败返回 (None, None)。"""
    data = _load_last_run_config()
    start = data.get("start_date") if isinstance(data, dict) else None
    end = data.get("end_date") if isinstance(data, dict) else None
    if isinstance(start, str) and isinstance(end, str):
        return start, end
    return None, None


def _save_last_run_config(run_config: dict[str, object]) -> None:
    try:
        LAST_RUN_PATH.write_text(
            json.dumps(run_config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:  # pragma: no cover - 持久化失败不影响主流程
        print(f"[配置] 写入 {LAST_RUN_PATH.name} 失败：{exc}")


def _save_last_run_dates(start_date: str, end_date: str) -> None:
    """保存本次运行使用的日期，下次启动作为默认值。"""
    _save_last_run_config({"start_date": start_date, "end_date": end_date})


def _load_last_selected_factors(group: str, default: list[str] | None = None) -> list[str]:
    config_data = _load_last_run_config()
    selected_factors = config_data.get("selected_factors")
    if not isinstance(selected_factors, list):
        return list(default or [])
    valid_factors = set(_iter_factor_names(group))
    return [factor for factor in selected_factors if isinstance(factor, str) and factor in valid_factors]


def _clear_factor_cache() -> tuple[int, list[str]]:
    """删除全部因子缓存文件。返回 (删除数量, 失败文件列表)。"""
    deleted = 0
    failures: list[str] = []
    for cache_file in _list_factor_cache_files():
        try:
            cache_file.unlink()
            deleted += 1
        except Exception as exc:  # pragma: no cover - 极少触发
            failures.append(f"{cache_file.name}: {exc}")
    return deleted, failures


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


class Alpha191SelectionDialog(FactorGroupSelectionDialog):
    """国君朝阳191 因子单独选择窗口。"""

    def __init__(self, selected_factors: list[str] | None = None) -> None:
        super().__init__(group="alpha191", title="国君朝阳191", selected_factors=selected_factors)


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
        latest_start, latest_end, _ = get_strategy_date_range()
        self._latest_start = latest_start
        self._latest_end = latest_end
        last_start, last_end = _load_last_run_dates()
        default_start = last_start or latest_start
        default_end = last_end or latest_end
        last_run_config = _load_last_run_config()
        default_base_factors = _load_last_selected_factors("base", _iter_factor_names("base"))
        self.selected_alpha158_factors: list[str] = _load_last_selected_factors("alpha158")
        self.selected_alpha101_factors: list[str] = _load_last_selected_factors("alpha101")
        self.selected_alpha191_factors: list[str] = _load_last_selected_factors("alpha191")
        last_max_stage = last_run_config.get("max_stage")
        default_max_stage = last_max_stage if isinstance(last_max_stage, int) and 1 <= last_max_stage <= 4 else 4
        default_use_cache = bool(last_run_config.get("use_cache", False))
        default_use_batch_data_cache = bool(last_run_config.get("use_batch_data_cache", False))
        default_use_candidate_evaluation_cache = bool(last_run_config.get("use_candidate_evaluation_cache", False))
        default_save_single_factor = bool(last_run_config.get("save_single_factor_results", True))
        last_weight_method = last_run_config.get("weight_method")
        default_weight_method = (
            last_weight_method
            if isinstance(last_weight_method, str) and last_weight_method in {"equal", "icir", "max_ir"}
            else "equal"
        )

        self.root = tk.Tk()
        self.root.title("多因子运行参数")
        self.root.resizable(False, False)
        self._center_window(820, 800)

        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        title = ttk.Label(container, text="请选择本次运行参数", font=("Microsoft YaHei", 14, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        ttk.Label(container, text="开始日期（YYYYMMDD）").grid(row=1, column=0, sticky="w", pady=(0, 8))
        start_frame = ttk.Frame(container)
        start_frame.grid(row=1, column=1, sticky="w", pady=(0, 8))
        self.start_entry = ttk.Entry(start_frame, width=22)
        self.start_entry.pack(side="left")
        self.start_entry.insert(0, default_start)
        ttk.Button(start_frame, text="设为最新", command=self._reset_dates_to_latest).pack(side="left", padx=(8, 0))

        ttk.Label(container, text="结束日期（YYYYMMDD）").grid(row=2, column=0, sticky="w", pady=(0, 12))
        end_frame = ttk.Frame(container)
        end_frame.grid(row=2, column=1, sticky="w", pady=(0, 12))
        self.end_entry = ttk.Entry(end_frame, width=22)
        self.end_entry.pack(side="left")
        self.end_entry.insert(0, default_end)
        self.date_hint_var = tk.StringVar(
            value=f"最新可用范围：{self._latest_start} ~ {self._latest_end}"
        )
        ttk.Label(end_frame, textvariable=self.date_hint_var, foreground="#666666").pack(side="left", padx=(8, 0))

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
            var = tk.BooleanVar(value=factor_name in default_base_factors)
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
        self._sync_alpha158_main_state()

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
        self._sync_alpha101_main_state()

        ttk.Label(container, text="国君朝阳191 因子").grid(row=6, column=0, sticky="nw", pady=(0, 12))
        alpha191_frame = ttk.Frame(container)
        alpha191_frame.grid(row=6, column=1, sticky="w", pady=(0, 12))
        self.alpha191_var = tk.IntVar(value=0)
        self.alpha191_check = tk.Checkbutton(
            alpha191_frame,
            text="启用 国君朝阳191",
            variable=self.alpha191_var,
            onvalue=1,
            offvalue=0,
            tristatevalue=-1,
            indicatoron=True,
            selectcolor="#bfbfbf",
            command=self._toggle_alpha191_from_main,
        )
        self.alpha191_check.pack(side="left")
        ttk.Button(alpha191_frame, text="选择 国君朝阳191 因子...", command=self._open_alpha191_dialog).pack(side="left", padx=(10, 0))
        self.alpha191_summary_var = tk.StringVar(value=self._build_alpha191_summary())
        ttk.Label(alpha191_frame, textvariable=self.alpha191_summary_var, foreground="#666666").pack(side="left", padx=(10, 0))
        self._sync_alpha191_main_state()

        ttk.Label(container, text="因子缓存").grid(row=7, column=0, sticky="nw", pady=(0, 12))
        cache_frame = ttk.Frame(container)
        cache_frame.grid(row=7, column=1, sticky="w", pady=(0, 12))
        self.use_cache_var = tk.BooleanVar(value=default_use_cache)
        ttk.Checkbutton(
            cache_frame,
            text="启用因子缓存（按日期范围复用，命中时跳过计算）",
            variable=self.use_cache_var,
        ).pack(side="left")
        ttk.Button(cache_frame, text="清除缓存", command=self._clear_cache).pack(side="left", padx=(10, 0))
        self.cache_status_var = tk.StringVar(value=self._build_cache_status_text())
        ttk.Label(cache_frame, textvariable=self.cache_status_var, foreground="#666666").pack(side="left", padx=(10, 0))

        ttk.Label(container, text="批量数据缓存").grid(row=8, column=0, sticky="nw", pady=(0, 12))
        batch_cache_frame = ttk.Frame(container)
        batch_cache_frame.grid(row=8, column=1, sticky="w", pady=(0, 12))
        self.use_batch_data_cache_var = tk.BooleanVar(value=default_use_batch_data_cache)
        ttk.Checkbutton(
            batch_cache_frame,
            text="使用缓存数据回测（命中则不下载；未命中则下载后缓存）",
            variable=self.use_batch_data_cache_var,
        ).pack(side="left")
        ttk.Button(batch_cache_frame, text="清除批量数据缓存", command=self._clear_batch_data_cache).pack(side="left", padx=(10, 0))
        self.batch_data_cache_status_var = tk.StringVar(value=self._build_batch_data_cache_status_text())
        ttk.Label(batch_cache_frame, textvariable=self.batch_data_cache_status_var, foreground="#666666").pack(side="left", padx=(10, 0))

        ttk.Label(container, text="候选因子评估缓存").grid(row=9, column=0, sticky="nw", pady=(0, 12))
        candidate_eval_cache_frame = ttk.Frame(container)
        candidate_eval_cache_frame.grid(row=9, column=1, sticky="w", pady=(0, 12))
        self.use_candidate_evaluation_cache_var = tk.BooleanVar(value=default_use_candidate_evaluation_cache)
        ttk.Checkbutton(
            candidate_eval_cache_frame,
            text="使用评估候选因子缓存（按因子名+日期范围复用，命中时跳过阶段1评估）",
            variable=self.use_candidate_evaluation_cache_var,
        ).pack(side="left")

        ttk.Label(container, text="单因子分析结果").grid(row=10, column=0, sticky="nw", pady=(0, 12))
        save_sf_frame = ttk.Frame(container)
        save_sf_frame.grid(row=10, column=1, sticky="w", pady=(0, 12))
        self.save_single_factor_var = tk.BooleanVar(value=default_save_single_factor)
        ttk.Checkbutton(
            save_sf_frame,
            text="保存单因子分析结果（summary/IC时序/单因子统计 CSV，未勾选则跳过以节省时间）",
            variable=self.save_single_factor_var,
        ).pack(side="left")

        ttk.Label(container, text="运行到第几阶段").grid(row=11, column=0, sticky="nw")
        stage_frame = ttk.Frame(container)
        stage_frame.grid(row=11, column=1, sticky="w")
        self.max_stage_var = tk.IntVar(value=default_max_stage)
        for stage, label in [
            (1, "阶段1：单因子评估"),
            (2, "阶段2：指标初筛"),
            (3, "阶段3：相关性去冗余"),
            (4, "阶段4：组合构建与回测"),
        ]:
            ttk.Radiobutton(stage_frame, text=label, variable=self.max_stage_var, value=stage).pack(anchor="w", pady=1)

        ttk.Label(container, text="阶段4 权重方法").grid(row=12, column=0, sticky="nw", pady=(8, 0))
        weight_frame = ttk.Frame(container)
        weight_frame.grid(row=12, column=1, sticky="w", pady=(8, 0))
        self.weight_method_var = tk.StringVar(value=default_weight_method)
        for value, label in [
            ("equal", "等权重"),
            ("icir", "ICIR 加权（按 RankIC 均值/标准差，截断负值后归一化）"),
            ("max_ir", "Max IR（协方差压缩降噪后求 Σ⁻¹·μ，最大化复合 IR）"),
        ]:
            ttk.Radiobutton(weight_frame, text=label, variable=self.weight_method_var, value=value).pack(anchor="w", pady=1)

        ttk.Label(container, text="默认日期沿用当前策略原始范围，可直接修改。", foreground="#666666").grid(
            row=13, column=0, columnspan=2, sticky="w", pady=(12, 4)
        )

        self.message_var = tk.StringVar(value="")
        ttk.Label(container, textvariable=self.message_var, foreground="#cc3333").grid(row=14, column=0, columnspan=2, sticky="w", pady=(14, 8))

        button_frame = ttk.Frame(container)
        button_frame.grid(row=15, column=0, columnspan=2, sticky="e")
        ttk.Button(button_frame, text="取消", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(button_frame, text="开始运行", command=self._confirm).pack(side="right")

        container.columnconfigure(1, weight=1)
        self._sync_alpha158_main_state()
        self._sync_alpha101_main_state()
        self._sync_alpha191_main_state()
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

    def _set_alpha191_state(self, state: str) -> None:
        """设置国君朝阳191主复选框状态。"""
        if state == "all":
            self.alpha191_var.set(1)
        elif state == "partial":
            self.alpha191_var.set(-1)
        else:
            self.alpha191_var.set(0)
        self.alpha191_check.update_idletasks()

    def _sync_alpha191_main_state(self) -> None:
        """根据已选数量同步主界面国君朝阳191复选框状态。"""
        total_count = len(_iter_factor_names("alpha191"))
        selected_count = len(self.selected_alpha191_factors)
        if selected_count <= 0:
            self._set_alpha191_state("none")
        elif selected_count >= total_count:
            self._set_alpha191_state("all")
        else:
            self._set_alpha191_state("partial")
        self.alpha191_summary_var.set(self._build_alpha191_summary())

    def _toggle_alpha191_from_main(self) -> None:
        """主界面切换国君朝阳191全选/全不选。"""
        if self.alpha191_var.get() == 1:
            self.selected_alpha191_factors = _iter_factor_names("alpha191")
        else:
            self.selected_alpha191_factors = []
        self._sync_alpha191_main_state()

    def _build_alpha191_summary(self) -> str:
        total_count = len(_iter_factor_names("alpha191"))
        selected_count = len(self.selected_alpha191_factors)
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

    def _open_alpha191_dialog(self) -> None:
        dialog = Alpha191SelectionDialog(self.selected_alpha191_factors)
        selected = dialog.show()
        if selected is None:
            return
        self.selected_alpha191_factors = selected
        self._sync_alpha191_main_state()

    def _reset_dates_to_latest(self) -> None:
        """把日期输入框重置为统一日期函数返回的最新范围。"""
        latest_start, latest_end, _ = get_strategy_date_range()
        self._latest_start = latest_start
        self._latest_end = latest_end
        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, latest_start)
        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(0, latest_end)
        self.date_hint_var.set(f"最新可用范围：{latest_start} ~ {latest_end}")

    def _build_cache_status_text(self) -> str:
        """统计当前缓存目录下的因子文件数量与体积。"""
        files = _list_factor_cache_files()
        if not files:
            return "当前缓存：0 个文件"
        total_bytes = sum(f.stat().st_size for f in files if f.exists())
        size_mb = total_bytes / (1024 * 1024)
        return f"当前缓存：{len(files)} 个文件，约 {size_mb:.1f} MB"

    def _refresh_cache_status(self) -> None:
        """刷新缓存状态文本。"""
        self.cache_status_var.set(self._build_cache_status_text())

    def _clear_cache(self) -> None:
        """点击「清除缓存」按钮：弹确认框并删除全部缓存文件。"""
        files = _list_factor_cache_files()
        if not files:
            messagebox.showinfo("清除因子缓存", "当前没有缓存文件。", parent=self.root)
            self._refresh_cache_status()
            return
        confirmed = messagebox.askyesno(
            "清除因子缓存",
            f"将删除 {len(files)} 个缓存文件，操作不可恢复，是否继续？",
            parent=self.root,
        )
        if not confirmed:
            return
        deleted, failures = _clear_factor_cache()
        self._refresh_cache_status()
        if failures:
            messagebox.showwarning(
                "清除因子缓存",
                f"已删除 {deleted} 个文件，{len(failures)} 个失败：\n" + "\n".join(failures),
                parent=self.root,
            )
        else:
            messagebox.showinfo("清除因子缓存", f"已删除 {deleted} 个缓存文件。", parent=self.root)

    def _build_batch_data_cache_status_text(self) -> str:
        files = list_batch_data_cache_files()
        if not files:
            return "当前缓存：0 个文件"
        total_bytes = sum(f.stat().st_size for f in files if f.exists())
        size_mb = total_bytes / (1024 * 1024)
        return f"当前缓存：{len(files)} 个文件，约 {size_mb:.1f} MB"

    def _refresh_batch_data_cache_status(self) -> None:
        self.batch_data_cache_status_var.set(self._build_batch_data_cache_status_text())

    def _clear_batch_data_cache(self) -> None:
        files = list_batch_data_cache_files()
        if not files:
            messagebox.showinfo("清除批量数据缓存", "当前没有批量数据缓存文件。", parent=self.root)
            self._refresh_batch_data_cache_status()
            return
        confirmed = messagebox.askyesno(
            "清除批量数据缓存",
            f"将删除 {len(files)} 个批量数据缓存文件，操作不可恢复，是否继续？",
            parent=self.root,
        )
        if not confirmed:
            return
        deleted, failures = clear_batch_data_cache()
        self._refresh_batch_data_cache_status()
        if failures:
            messagebox.showwarning(
                "清除批量数据缓存",
                f"已删除 {deleted} 个文件，{len(failures)} 个失败：\n" + "\n".join(failures),
                parent=self.root,
            )
        else:
            messagebox.showinfo("清除批量数据缓存", f"已删除 {deleted} 个缓存文件。", parent=self.root)

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
        selected_factors = (
            selected_base_factors
            + self.selected_alpha158_factors
            + self.selected_alpha101_factors
            + self.selected_alpha191_factors
        )
        if not selected_factors:
            self.message_var.set("请至少选择一个因子")
            return

        self.result = {
            "start_date": start_date,
            "end_date": end_date,
            "max_stage": int(self.max_stage_var.get()),
            "selected_factors": selected_factors,
            "use_cache": bool(self.use_cache_var.get()),
            "use_batch_data_cache": bool(self.use_batch_data_cache_var.get()),
            "use_candidate_evaluation_cache": bool(self.use_candidate_evaluation_cache_var.get()),
            "save_single_factor_results": bool(self.save_single_factor_var.get()),
            "weight_method": str(self.weight_method_var.get()),
        }
        _save_last_run_config(self.result)
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


def _infer_is_factor_higher_better(row: pd.Series) -> bool:
    """根据候选因子指标推断是否“因子值越大越好”。

    选方向的优先级（从强到弱）：
    1. 分组端组平均未来收益（G1=因子最大组，G5=因子最小组）：
       - 哪一端的平均收益更高，就把方向对齐到那一端；
       - 这是与"分组单调性最优方向"完全一致的判定，避免出现
         "RankIC符号 与 端组实际更赚的那头" 不一致的情况。
    2. RankIC 均值的符号（兜底）。
    3. IC 均值的符号（再兜底）。
    4. 默认 True。

    返回值：
    - True 表示"因子值越大越好"；
    - False 表示"因子值越小越好"。
    """
    g1_mean = row.get("G1平均收益")
    g5_mean = row.get("G5平均收益")
    if pd.notna(g1_mean) and pd.notna(g5_mean) and float(g1_mean) != float(g5_mean):
        return float(g1_mean) > float(g5_mean)

    rank_ic_mean = row.get("RankIC均值")
    if pd.notna(rank_ic_mean) and float(rank_ic_mean) != 0.0:
        return float(rank_ic_mean) > 0

    ic_mean = row.get("IC均值")
    if pd.notna(ic_mean) and float(ic_mean) != 0.0:
        return float(ic_mean) > 0

    return True


def _apply_factor_direction(score_df: pd.DataFrame, direction: int) -> pd.DataFrame:
    """按推断方向统一因子分数，保证分数越高越偏多。"""
    if direction >= 0:
        return score_df
    return score_df * -1


def _compute_group_returns(
    masked_factor_df: pd.DataFrame,
    forward_returns_df: pd.DataFrame,
    group_count: int = 5,
) -> pd.DataFrame:
    result_rows: list[pd.Series] = []
    valid_dates = masked_factor_df.index.intersection(forward_returns_df.index)
    labels = [f"G{i}" for i in range(1, group_count + 1)]

    for dt in valid_dates:
        merged = pd.concat(
            [masked_factor_df.loc[dt], forward_returns_df.loc[dt]],
            axis=1,
            keys=["factor", "future_return"],
        ).dropna()
        if len(merged) < group_count:
            continue

        merged = merged.sort_values("factor", ascending=False).reset_index(drop=True)
        merged["group"] = pd.qcut(merged.index + 1, q=group_count, labels=labels)
        group_return = merged.groupby("group", observed=False)["future_return"].mean()
        group_return.name = dt
        result_rows.append(group_return)

    if not result_rows:
        return pd.DataFrame(columns=labels)
    return pd.DataFrame(result_rows).reindex(columns=labels)


def _calc_monotonicity_metric(masked_factor_df: pd.DataFrame, forward_returns_df: pd.DataFrame) -> float:
    group_return_df = _compute_group_returns(masked_factor_df, forward_returns_df, group_count=5)
    if group_return_df.empty:
        return np.nan

    avg_returns = group_return_df.mean().reindex(["G1", "G2", "G3", "G4", "G5"])
    values = avg_returns.to_numpy(dtype=float)
    diffs = np.diff(values)
    valid_diffs = diffs[~np.isnan(diffs)]
    if len(valid_diffs) == 0:
        return np.nan

    decreasing_score = float((valid_diffs < 0).sum() / len(valid_diffs))
    increasing_score = float((valid_diffs > 0).sum() / len(valid_diffs))
    return max(decreasing_score, increasing_score)


def _build_candidate_status(candidate_metrics_df: pd.DataFrame) -> pd.DataFrame:
    """根据候选因子指标总表，生成“阶段一：初筛状态表”。"""
    rows: list[dict[str, object]] = []
    for _, row in candidate_metrics_df.iterrows():
        is_factor_higher_better = _infer_is_factor_higher_better(row)
        direction_sign = 1 if is_factor_higher_better else -1
        directional_rr_mean = row["RR均值"] * direction_sign if pd.notna(row["RR均值"]) else row["RR均值"]
        metric_checks = {
            "IC均值通过": _passes_threshold(row["IC均值"], config.MIN_IC_MEAN, use_abs=True),
            "ICIR通过": _passes_threshold(row["ICIR"], config.MIN_ICIR, use_abs=True),
            "RankIC均值通过": _passes_threshold(row["RankIC均值"], config.MIN_RANK_IC_MEAN, use_abs=True),
            "RankICIR通过": _passes_threshold(row["RankICIR"], config.MIN_RANK_ICIR, use_abs=True),
            "RR均值通过": _passes_threshold(directional_rr_mean, config.MIN_RR_MEAN),
            "RR胜率通过": _passes_threshold(row["RR胜率"], config.MIN_RR_WIN_RATE),
            "单调性通过": _passes_threshold(row.get("单调性指标"), getattr(config, "MIN_MONOTONICITY", None)),
        }
        rows.append(
            {
                "factor": row["factor"],
                "is_factor_higher_better": is_factor_higher_better,
                "推断方向": _factor_direction_label(is_factor_higher_better),
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
    valid_columns = [
        column
        for column in score_panel.columns
        if score_panel[column].dropna().nunique(dropna=True) > 1
    ]
    score_panel = score_panel[valid_columns]
    if score_panel.empty:
        factor_names = list(flattened.keys())
        return pd.DataFrame(index=factor_names, columns=factor_names, dtype=float), pd.DataFrame(
            columns=["factor_a", "factor_b", "corr"]
        )
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
        if "is_factor_higher_better" in screened_metrics_df.columns:
            factor_row = screened_metrics_df.loc[screened_metrics_df["factor"] == factor_name]
            is_factor_higher_better = bool(factor_row["is_factor_higher_better"].iloc[0]) if not factor_row.empty else True
        else:
            is_factor_higher_better = True
        final_rows.append(
            {
                "factor": factor_name,
                "是否入选最终组合": factor_name in selected,
                "组合权重": 1.0 / len(selected) if factor_name in selected and selected else 0.0,
                "阶段4方向": _factor_direction_label(is_factor_higher_better),
                "is_factor_higher_better": is_factor_higher_better,
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


def _print_backtest_metrics(
    title: str,
    stats: object,
    period_days: float | None = None,
    returns: pd.Series | None = None,
    benchmark_returns: pd.Series | None = None,
    periods_per_year: int = 252,
) -> None:
    """按 single_factor_stats.csv 的统计量打印组合/因子的核心评价指标。

    输出：总收益率、基准收益率、超额收益、年化收益、超额年化、波动率、夏普比率、最大回撤。
    其中 超额年化 / 波动率 需要传入 returns 序列（以及可选的基准收益率序列）。
    """
    if stats is None or not hasattr(stats, "loc"):
        print(f"[{title}] 无可用统计数据")
        return

    def _get(key: str) -> float:
        try:
            value = stats.loc[key]
        except Exception:
            return float("nan")
        try:
            return float(value)
        except (TypeError, ValueError):
            return float("nan")

    total_return = _get("Total Return [%]")
    benchmark_return = _get("Benchmark Return [%]")
    sharpe = _get("Sharpe Ratio")
    max_dd = _get("Max Drawdown [%]")

    # 年化收益：优先按 returns / benchmark_returns 索引的首尾日期计算日历天数，
    # 否则退回 stats["Period"]（注意 vectorbt 的 Period 是 bar 数*1天，按交易日计，
    # 会比真实日历区间小，导致年化收益被高估）。
    annualized = float("nan")
    days: float | None = period_days

    def _calendar_days_from_index(series: pd.Series | None) -> float | None:
        if not isinstance(series, pd.Series) or series.empty:
            return None
        try:
            idx = pd.to_datetime(series.index)
        except Exception:
            return None
        if len(idx) < 2:
            return None
        delta = idx[-1] - idx[0]
        d = float(delta.days) + delta.seconds / 86400.0
        return d if d > 0 else None

    if days is None:
        days = _calendar_days_from_index(returns)
    if days is None:
        days = _calendar_days_from_index(benchmark_returns)
    if days is None:
        try:
            period_value = stats.loc["Period"] if "Period" in stats.index else None
        except Exception:
            period_value = None
        if isinstance(period_value, pd.Timedelta):
            days = float(period_value.days) + period_value.seconds / 86400.0
    if days is not None and days > 0 and not np.isnan(total_return):
        years = days / 365.25
        if years > 0:
            annualized = ((1.0 + total_return / 100.0) ** (1.0 / years) - 1.0) * 100.0

    excess = float("nan")
    if not np.isnan(total_return) and not np.isnan(benchmark_return):
        excess = total_return - benchmark_return

    # 基准年化（用于超额年化）
    benchmark_annualized = float("nan")
    if days is not None and days > 0 and not np.isnan(benchmark_return):
        years = days / 365.25
        if years > 0:
            benchmark_annualized = ((1.0 + benchmark_return / 100.0) ** (1.0 / years) - 1.0) * 100.0

    excess_annualized = float("nan")
    if not np.isnan(annualized) and not np.isnan(benchmark_annualized):
        excess_annualized = annualized - benchmark_annualized

    # 年化波动率：基于日收益率序列。
    volatility = float("nan")
    if isinstance(returns, pd.Series) and not returns.empty:
        ret_clean = returns.dropna()
        if len(ret_clean) > 1:
            volatility = float(ret_clean.std(ddof=1) * np.sqrt(periods_per_year) * 100.0)

    def _fmt(x: float, suffix: str = "%") -> str:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "N/A"
        return f"{x:.6f}{suffix}"

    _print_separator("-", 90)
    print(f"[{title}]")
    _print_separator("-", 90)
    print(f"  总收益率   ：{_fmt(total_return)}")
    print(f"  基准收益率 ：{_fmt(benchmark_return)}")
    print(f"  超额收益   ：{_fmt(excess)}")
    print(f"  年化收益   ：{_fmt(annualized)}")
    print(f"  超额年化   ：{_fmt(excess_annualized)}")
    print(f"  波动率     ：{_fmt(volatility)}")
    print(f"  夏普比率   ：{_fmt(sharpe, suffix='')}")
    print(f"  最大回撤   ：{_fmt(max_dd)}")
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


def _equal_weights(factor_names: list[str]) -> dict[str, float]:
    """生成等权重字典。"""
    if not factor_names:
        return {}
    weight_value = 1.0 / len(factor_names)
    return {name: weight_value for name in factor_names}


def _collect_aligned_rank_ic(
    factor_names: list[str],
    factor_analysis: dict[str, dict[str, object]],
    is_higher_better: dict[str, bool],
) -> pd.DataFrame:
    """汇总各因子的 RankIC 序列并按方向对齐（lower_better 取反），返回宽表。"""
    series_dict: dict[str, pd.Series] = {}
    for name in factor_names:
        info = factor_analysis.get(name) or {}
        series = info.get("rank_ic_series")
        if not isinstance(series, pd.Series) or series.empty:
            continue
        sign = 1.0 if bool(is_higher_better.get(name, True)) else -1.0
        series_dict[name] = series.astype(float) * sign
    if not series_dict:
        return pd.DataFrame()
    return pd.concat(series_dict, axis=1).dropna(how="all")


def _normalize_positive_weights(
    factor_names: list[str],
    raw_weights: dict[str, float],
) -> dict[str, float]:
    """把负值截断为 0 后归一化；若全为 0 则回退到等权。"""
    clipped = {name: max(float(raw_weights.get(name, 0.0)), 0.0) for name in factor_names}
    total = sum(clipped.values())
    if total <= 0 or not np.isfinite(total):
        return _equal_weights(factor_names)
    return {name: value / total for name, value in clipped.items()}


def _compute_factor_weights(
    factor_names: list[str],
    factor_analysis: dict[str, dict[str, object]],
    method: str,
    is_higher_better: dict[str, bool],
) -> dict[str, float]:
    """根据用户选择的方法计算阶段4各因子的合成权重。

    - equal：等权重；
    - icir：按方向对齐后的 RankIC 均值/标准差，截断负值后归一化；
    - max_ir：协方差压缩降噪（对角线收缩）后求 Σ⁻¹·μ，最大化复合 IR，截断负值后归一化。
    任意方法在数值不稳定（NaN/全 0/Σ 不可逆）时自动回退到等权重。
    """
    if not factor_names:
        return {}
    if method == "equal":
        return _equal_weights(factor_names)

    ic_df = _collect_aligned_rank_ic(factor_names, factor_analysis, is_higher_better)
    if ic_df.empty:
        print("[阶段4][权重] RankIC 序列为空，回退等权重")
        return _equal_weights(factor_names)
    # 仅对存在 IC 序列的因子求权重，缺失因子兜底为 0（之后归一化）。
    available_names = [name for name in factor_names if name in ic_df.columns]
    missing_names = [name for name in factor_names if name not in ic_df.columns]
    if missing_names:
        print(f"[阶段4][权重] 以下因子无有效 RankIC 序列，权重置 0：{missing_names}")

    mean_ic = ic_df[available_names].mean(axis=0)
    std_ic = ic_df[available_names].std(axis=0, ddof=1)

    if method == "icir":
        with np.errstate(divide="ignore", invalid="ignore"):
            icir = mean_ic / std_ic.replace(0.0, np.nan)
        raw_weights = {name: float(icir.get(name, np.nan)) for name in factor_names}
        raw_weights = {
            name: (value if np.isfinite(value) else 0.0)
            for name, value in raw_weights.items()
        }
        return _normalize_positive_weights(factor_names, raw_weights)

    if method == "max_ir":
        if len(available_names) < 2:
            # 单因子无需协方差，直接退化为 ICIR / 等权。
            print("[阶段4][权重] Max IR 需要 ≥2 个因子，回退等权重")
            return _equal_weights(factor_names)
        mu = mean_ic.values.astype(float)
        cov = ic_df[available_names].cov().values.astype(float)
        # Ledoit-Wolf 风格的对角线收缩：Σ_shrunk = (1-α)Σ + α * diag(Σ)，α=0.1。
        shrinkage = 0.1
        diag_only = np.diag(np.diag(cov))
        cov_shrunk = (1.0 - shrinkage) * cov + shrinkage * diag_only
        # 数值正则化，避免奇异矩阵。
        ridge = 1e-8 * np.trace(cov_shrunk) / max(cov_shrunk.shape[0], 1)
        cov_shrunk = cov_shrunk + np.eye(cov_shrunk.shape[0]) * max(ridge, 1e-12)
        try:
            raw_w = np.linalg.solve(cov_shrunk, mu)
        except np.linalg.LinAlgError as exc:
            print(f"[阶段4][权重] Max IR 求解失败({exc})，回退等权重")
            return _equal_weights(factor_names)
        if not np.all(np.isfinite(raw_w)):
            print("[阶段4][权重] Max IR 求解出现非有限值，回退等权重")
            return _equal_weights(factor_names)
        raw_weights = {name: 0.0 for name in factor_names}
        for name, value in zip(available_names, raw_w):
            raw_weights[name] = float(value)
        return _normalize_positive_weights(factor_names, raw_weights)

    # 防御性兜底（理论上前面已校验）。
    return _equal_weights(factor_names)


def run_strategy(
    start_date: str | None = None,
    end_date: str | None = None,
    max_stage: int = 4,
    selected_factors: list[str] | None = None,
    progress_callback: Callable[[str, str, int | None, int | None], None] | None = None,
    use_cache: bool = False,
    use_batch_data_cache: bool = False,
    use_candidate_evaluation_cache: bool = False,
    save_single_factor_results: bool = True,
    weight_method: str = "equal",
) -> dict[str, object]:
    """运行多因子研究与回测主流程。"""
    if max_stage < 1 or max_stage > 4:
        raise ValueError("max_stage 必须在 1 到 4 之间")
    if weight_method not in {"equal", "icir", "max_ir"}:
        raise ValueError(f"weight_method 不合法：{weight_method}")

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
        use_batch_data_cache=use_batch_data_cache,
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
    cache_start = str(data_bundle.get("start_date", start_date or ""))
    cache_end = str(data_bundle.get("end_date", end_date or ""))
    if use_cache:
        print(f"[缓存] 已启用因子缓存，目录：{FACTOR_CACHE_DIR}，区间：{cache_start} ~ {cache_end}")
    for factor_index, factor_name in enumerate(selected_factors, start=1):
        cached_df: pd.DataFrame | None = None
        if use_cache:
            cached_df = _load_factor_from_cache(factor_name, cache_start, cache_end)
        if cached_df is not None:
            report_progress(
                "阶段0：计算候选因子",
                f"命中缓存 {factor_name}，跳过计算",
                factor_index,
                total_factors,
            )
            all_factor_dict[factor_name] = cached_df
            continue
        report_progress(
            "阶段0：计算候选因子",
            f"正在计算 {factor_name} ...",
            factor_index,
            total_factors,
        )
        factor_df = _compute_registered_factor(factor_name, data_bundle)
        all_factor_dict[factor_name] = factor_df
        if use_cache:
            _save_factor_to_cache(factor_name, cache_start, cache_end, factor_df)
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
    if use_candidate_evaluation_cache:
        print(f"[评估缓存] 已启用候选因子评估缓存，目录：{CANDIDATE_EVALUATION_CACHE_DIR}，区间：{cache_start} ~ {cache_end}")
    factor_analysis: dict[str, dict[str, object]] = {}
    candidate_metrics_list: list[pd.DataFrame] = []
    candidate_factor_scores: dict[str, pd.DataFrame] = {}

    for factor_index, (factor_name, raw_factor_df) in enumerate(raw_factor_dict.items(), start=1):
        cached_evaluation: dict[str, object] | None = None
        if use_candidate_evaluation_cache:
            cached_evaluation = _load_candidate_evaluation_from_cache(factor_name, cache_start, cache_end)
        if cached_evaluation is not None:
            report_progress(
                "阶段1：评估候选因子",
                f"命中评估缓存 {factor_name}，跳过评估",
                factor_index,
                len(raw_factor_dict),
            )
            factor_analysis[factor_name] = {
                "raw_factor_df": raw_factor_df,
                **cached_evaluation,
            }
            summary_df = cached_evaluation["summary_df"]
            factor_score_df = cached_evaluation["factor_score_df"]
            if not isinstance(summary_df, pd.DataFrame) or not isinstance(factor_score_df, pd.DataFrame):
                raise TypeError(f"{factor_name} 的评估缓存格式不正确")
            candidate_metrics_list.append(summary_df)
            candidate_factor_scores[factor_name] = factor_score_df
            _print_factor_evaluation(factor_name, summary_df)
            continue

        report_progress(
            "阶段1：评估候选因子",
            f"正在评估 {factor_name} ...",
            factor_index,
            len(raw_factor_dict),
        )
        masked_factor_df = mask_factor(raw_factor_df, tradable_mask)
        is_factor_higher_better = bool(FACTOR_HIGHER_BETTER.get(factor_name, True))
        factor_score_df = _rank_score_by_factor_direction(masked_factor_df, is_factor_higher_better)

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
        summary_df["单调性指标"] = _calc_monotonicity_metric(masked_factor_df, forward_returns_df)
        # 额外计算分组端组（G1=因子最大组，G5=因子最小组）的平均未来收益，
        # 供 _infer_is_factor_higher_better 选择"分组单调收益更高的那一端"作为最终方向。
        group_return_df_for_dir = _compute_group_returns(masked_factor_df, forward_returns_df, group_count=5)
        if not group_return_df_for_dir.empty:
            summary_df["G1平均收益"] = float(group_return_df_for_dir["G1"].mean())
            summary_df["G5平均收益"] = float(group_return_df_for_dir["G5"].mean())
        else:
            summary_df["G1平均收益"] = np.nan
            summary_df["G5平均收益"] = np.nan

        single_factor_results = run_single_factor_backtest(
            factor_df=raw_factor_df,
            tradable_mask=tradable_mask,
            close_df=close_df,
            rebalance_mask=rebalance_mask,
            benchmark_close=benchmark_close,
            hold_num=config.HOLD_NUM,
            factor_ascending=is_factor_higher_better,
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
        if use_candidate_evaluation_cache:
            _save_candidate_evaluation_to_cache(
                factor_name,
                cache_start,
                cache_end,
                {
                    "masked_factor_df": masked_factor_df,
                    "factor_score_df": factor_score_df,
                    "ic_series": ic_series,
                    "rank_ic_series": rank_ic_series,
                    "rr_series": rr_series,
                    "summary_df": summary_df,
                    "single_factor_results": single_factor_results,
                },
            )
        candidate_metrics_list.append(summary_df)
        candidate_factor_scores[factor_name] = factor_score_df
        _print_factor_evaluation(factor_name, summary_df)

        # 阶段1即时落盘单因子分析结果（可通过对话框开关跳过以节省时间）。
        if save_single_factor_results:
            stage1_output_dir = Path(__file__).resolve().parent / config.OUTPUT_DIR
            save_factor_evaluation_results(
                output_dir=str(stage1_output_dir),
                factor_name=factor_name,
                ic_series=ic_series,
                rank_ic_series=rank_ic_series,
                rr_series=rr_series,
                summary_df=summary_df,
                backtest_results=single_factor_results,
            )
            factor_output_dir = stage1_output_dir / "factor_analysis" / factor_name / "latest"
            print(f"[阶段1] 已保存单因子分析目录：{factor_output_dir}")

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

    inferred_factor_higher_better = {
        row["factor"]: bool(row["is_factor_higher_better"])
        for _, row in candidate_status_df.iterrows()
    }
    # 阶段4直接按阶段2推断出的 is_factor_higher_better 重新生成分数。
    adjusted_factor_scores = {
        factor_name: _rank_score_by_factor_direction(
            factor_analysis[factor_name]["masked_factor_df"],
            bool(inferred_factor_higher_better.get(factor_name, True)),
        )
        for factor_name in screened_factors
    }
    screened_metrics_df = candidate_metrics_df[candidate_metrics_df["factor"].isin(screened_factors)].reset_index(drop=True)
    screened_metrics_df["is_factor_higher_better"] = screened_metrics_df["factor"].map(inferred_factor_higher_better).fillna(True).astype(bool)
    screened_metrics_df["阶段4方向"] = screened_metrics_df["is_factor_higher_better"].map(_factor_direction_label)

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
    final_weights = _compute_factor_weights(
        final_factor_names,
        factor_analysis,
        method=weight_method,
        is_higher_better=inferred_factor_higher_better,
    )
    print(f"[阶段4] 权重方法：{weight_method}")
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
    # 阶段1 已即时落盘单因子分析结果（若勾选），阶段4 不再重复写盘或打印单因子评价。

    print(f"[阶段4] 组合构建完成：最终因子={', '.join(final_factor_names)}")
    print(f"[阶段4] 对应权重：{final_weights}")
    _print_backtest_metrics(
        "阶段4 组合回测评价",
        results.get("stats"),
        returns=results.get("returns"),
        benchmark_returns=results.get("benchmark_returns"),
    )

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
        # 从用户点击「开始运行」后立即计时，覆盖整个运行流程
        _run_start_time = time.perf_counter()
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
                    use_cache=bool(run_params.get("use_cache", False)),
                    use_batch_data_cache=bool(run_params.get("use_batch_data_cache", False)),
                    use_candidate_evaluation_cache=bool(run_params.get("use_candidate_evaluation_cache", False)),
                    save_single_factor_results=bool(run_params.get("save_single_factor_results", True)),
                    weight_method=str(run_params.get("weight_method", "equal")),
                )
            except Exception as exc:  # pragma: no cover - 运行期异常展示
                run_error_holder.append(exc)

        worker = threading.Thread(target=_run_task, daemon=True)
        worker.start()
        worker.join()

        def _format_elapsed(seconds: float) -> str:
            total_seconds = int(seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            return f"{hours} 小时 {minutes} 分钟 {secs} 秒（共 {seconds:.2f} 秒）"

        if run_error_holder:
            _elapsed = time.perf_counter() - _run_start_time
            print(f"[运行耗时] 任务异常中止，总耗时: {_format_elapsed(_elapsed)}")
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
            # 打印每个入选因子的方向（基于阶段2推断的 is_factor_higher_better）
            direction_map: dict[str, bool] = {}
            final_selection_df = summary.get("stage_results", {}).get("final_selection")
            if final_selection_df is not None and not final_selection_df.empty and "is_factor_higher_better" in final_selection_df.columns:
                for _, _row in final_selection_df.iterrows():
                    direction_map[str(_row["factor"])] = bool(_row["is_factor_higher_better"])
            print("入选因子方向:")
            for _factor_name in summary["selected_factors"]:
                _is_higher_better = direction_map.get(_factor_name, FACTOR_HIGHER_BETTER.get(_factor_name, True))
                print(f"  - {_factor_name}: {_factor_direction_label(_is_higher_better)}")
        if summary["output_dir"]:
            print(f"输出目录: {summary['output_dir']}")

        _elapsed = time.perf_counter() - _run_start_time
        _print_separator("=", 90)
        print(f"[运行耗时] 总耗时: {_format_elapsed(_elapsed)}")
        _print_separator("=", 90)
