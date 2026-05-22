#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeIssues=false
"""因子库加载器。

设计目标：
- 自动扫描 ``source/factors/`` 下的子目录与顶层散件。
- 通过 ``inspect`` 自动适配每个 ``compute_xxx`` 函数的不同参数签名。
- ImportError / NotImplementedError / 任何运行期异常都被捕获并跳过，不中断流程。
- 输入：``panel = {"open": ..., "high": ..., "low": ..., "close": ..., "volume": ..., "amount": ..., "vwap": ...}``
  其中每个值都是 ``行=date, 列=instrument`` 的宽表 ``pd.DataFrame``。
- 输出：``{factor_name: pd.DataFrame}``，因子名前缀采用 ``{library}__{function_suffix}``。
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
import sys
import traceback
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

# 因子目录在文件系统中的根目录。
FACTORS_ROOT_PATH = Path(__file__).resolve().parent.parent / "factors"
# 顶层散件因子的虚拟库名。
ROOT_LIBRARY_NAME = "_root"

# 参数名 → panel 键名 的映射。所有因子使用统一的命名约定。
_PARAM_TO_PANEL_KEY = {
    "open_df": "open",
    "high_df": "high",
    "low_df": "low",
    "close_df": "close",
    "volume_df": "volume",
    "amount_df": "amount",
    "vwap_df": "vwap",
    "returns_df": "returns",  # 日收益率，由上层 workflow 在构造 panel 时一次性算好
}


def _ensure_factors_on_syspath() -> None:
    """确保 ``source/`` 在 ``sys.path`` 上，使 ``factors`` 可作为顶层包被 import。"""
    source_dir = FACTORS_ROOT_PATH.parent  # source/
    source_str = str(source_dir)
    if source_str not in sys.path:
        sys.path.insert(0, source_str)


def list_libraries() -> List[str]:
    """返回当前可用的因子库列表。

    顶层散件文件（如 ``momentum.py``、``risk_adjusted_momentum.py``）会被打包为
    ``_root`` 虚拟库；子目录（如 ``alpha101/``）按目录名直接列出。
    """
    if not FACTORS_ROOT_PATH.exists():
        return []

    libraries: List[str] = []

    has_root_files = any(
        path.is_file() and path.suffix == ".py" and not path.name.startswith("_")
        for path in FACTORS_ROOT_PATH.iterdir()
    )
    if has_root_files:
        libraries.append(ROOT_LIBRARY_NAME)

    for path in sorted(FACTORS_ROOT_PATH.iterdir()):
        if not path.is_dir():
            continue
        if path.name.startswith("_") or path.name.startswith("."):
            continue
        # 仅当目录是合法 Python 包（含 ``__init__.py``）时才纳入。
        if (path / "__init__.py").exists():
            libraries.append(path.name)

    return libraries


def _iter_factor_modules(library: str) -> Iterable[str]:
    """枚举给定因子库下的因子模块名（完整 dotted path）。"""
    if library == ROOT_LIBRARY_NAME:
        for path in sorted(FACTORS_ROOT_PATH.iterdir()):
            if not path.is_file() or path.suffix != ".py":
                continue
            if path.name.startswith("_"):
                continue
            yield f"factors.{path.stem}"
        return

    package_path = FACTORS_ROOT_PATH / library
    if not package_path.exists():
        return
    package_name = f"factors.{library}"
    try:
        package = importlib.import_module(package_name)
    except Exception:  # pragma: no cover - 包级别 import 失败时直接跳过
        LOGGER.warning("无法导入因子库包 %s，跳过整个目录:\n%s", package_name, traceback.format_exc())
        return

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if module_name.startswith("_"):
            continue
        yield f"{package_name}.{module_name}"


def _find_compute_function(module) -> Optional[Callable]:
    """在模块中查找名字以 ``compute_`` 开头的第一个可调用对象。"""
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if not name.startswith("compute_"):
            continue
        # 只接受定义在该模块内的函数，避免误抓到 import 进来的别名。
        if obj.__module__ != module.__name__:
            continue
        return obj
    return None


def _build_kwargs_for_signature(
    func: Callable, panel: Dict[str, pd.DataFrame]
) -> Optional[Dict[str, pd.DataFrame]]:
    """根据函数签名构造调用参数。

    - 仅为 ``_PARAM_TO_PANEL_KEY`` 中登记的参数注入对应的宽表；
    - 含默认值的参数（如 ``window=20``）若不在登记表中，则保留默认值；
    - 若签名中出现 *无默认值* 且未登记的参数，则返回 ``None`` 表示无法调用。
    """
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return None

    kwargs: Dict[str, pd.DataFrame] = {}
    for param_name, param in signature.parameters.items():
        if param_name in _PARAM_TO_PANEL_KEY:
            panel_key = _PARAM_TO_PANEL_KEY[param_name]
            if panel_key not in panel:
                LOGGER.warning(
                    "因子函数 %s 需要 %s 字段但 panel 中缺失，已跳过",
                    f"{func.__module__}.{func.__name__}",
                    panel_key,
                )
                return None
            kwargs[param_name] = panel[panel_key]
            continue
        # 不在登记表中：含默认值就放过，无默认值则视为不兼容。
        if param.default is inspect.Parameter.empty:
            LOGGER.warning(
                "因子函数 %s 含未识别且无默认值的参数 %s，已跳过",
                f"{func.__module__}.{func.__name__}",
                param_name,
            )
            return None
    return kwargs


def _factor_name(library: str, module_name: str, func_name: str) -> str:
    """构造因子的全局唯一名称。

    形如：``alpha101__alpha001`` 或 ``_root__momentum``。
    """
    suffix = func_name[len("compute_"):] if func_name.startswith("compute_") else func_name
    return f"{library}__{suffix}"


def load_library(
    library: str,
    panel: Dict[str, pd.DataFrame],
    *,
    skip_errors: bool = True,
    verbose: bool = False,
    slow_threshold_sec: float = 5.0,
    cache_dir: Optional[str] = None,
    panel_sig: Optional[str] = None,
    legacy_panel_sig: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """加载单个因子库下的全部因子。

    Args:
        library: 库名（``_root`` 或子目录名）。
        panel: 行情宽表字典。
        skip_errors: 出错因子是否跳过。默认 True，失败因子会打印 warning 并被忽略。
        verbose: 若为 True，打印每个因子的耗时。
        slow_threshold_sec: 即便 ``verbose=False``，单因子耗时超过该阈值时也会打印一行警告。

    Returns:
        ``{factor_name: factor_df}``。
    """
    import time as _time

    _ensure_factors_on_syspath()
    factors: Dict[str, pd.DataFrame] = {}
    skipped: List[str] = []

    cache_enabled = bool(cache_dir and panel_sig)
    cache_hits = 0
    cache_misses = 0
    if cache_enabled:
        try:
            from . import factor_cache  # type: ignore
        except Exception:
            import factor_cache  # type: ignore

    for module_dotted in _iter_factor_modules(library):
        try:
            module = importlib.import_module(module_dotted)
        except Exception as exc:  # ImportError 或其他副作用
            skipped.append(f"{module_dotted}: import 失败 ({exc})")
            if not skip_errors:
                raise
            continue

        func = _find_compute_function(module)
        if func is None:
            continue

        kwargs = _build_kwargs_for_signature(func, panel)
        if kwargs is None:
            skipped.append(f"{module_dotted}: 参数签名不兼容")
            continue

        factor_name = _factor_name(library, module_dotted, func.__name__)

        # ---- 缓存命中检查 ----
        cache_key = None
        if cache_enabled:
            try:
                func_source = inspect.getsource(func)
            except Exception:
                func_source = func.__name__
            cache_key = factor_cache.factor_cache_key(factor_name, panel_sig, func_source)
            cached_df = factor_cache.load(cache_dir, cache_key)
            if cached_df is not None:
                factors[factor_name] = cached_df
                cache_hits += 1
                print(f"  ✅ 缓存命中 {factor_name}", flush=True)
                continue
            if legacy_panel_sig:
                legacy_key = factor_cache.factor_cache_key(factor_name, legacy_panel_sig, func_source)
                cached_df = factor_cache.load(cache_dir, legacy_key)
                if cached_df is not None:
                    factor_cache.save(cache_dir, cache_key, cached_df)
                    factors[factor_name] = cached_df
                    cache_hits += 1
                    print(f"  ✅ 旧缓存命中并迁移 {factor_name}", flush=True)
                    continue

        _t0 = _time.time()
        try:
            result = func(**kwargs)
        except NotImplementedError as exc:
            skipped.append(f"{factor_name}: NotImplementedError ({exc})")
            if not skip_errors:
                raise
            continue
        except Exception as exc:
            skipped.append(f"{factor_name}: 运行异常 {type(exc).__name__}: {exc}")
            if not skip_errors:
                raise
            continue
        elapsed = _time.time() - _t0

        if not isinstance(result, pd.DataFrame) or result.empty:
            skipped.append(f"{factor_name}: 返回空或非 DataFrame")
            continue

        cleaned = result.astype(float).replace([np.inf, -np.inf], np.nan)
        factors[factor_name] = cleaned

        # ---- 写入缓存 ----
        if cache_enabled and cache_key is not None:
            factor_cache.save(cache_dir, cache_key, cleaned)
            cache_misses += 1

        if elapsed > slow_threshold_sec:
            print(
                f"  ⚠️ 重新计算慢因子 {factor_name} 耗时 {elapsed:.2f}s（>{slow_threshold_sec:.0f}s）",
                flush=True,
            )
        else:
            print(f"  🔄 重新计算 {factor_name} 耗时 {elapsed:.2f}s", flush=True)

    if cache_enabled:
        print(
            f"  📦 [{library}] 缓存命中 {cache_hits} 个，新计算并缓存 {cache_misses} 个",
            flush=True,
        )

    if skipped:
        LOGGER.info("因子库 %s 跳过 %d 个因子:\n  - %s", library, len(skipped), "\n  - ".join(skipped))
    LOGGER.info("因子库 %s 加载完成：%d 个因子", library, len(factors))
    return factors


def load_libraries(
    libraries: Iterable[str],
    panel: Dict[str, pd.DataFrame],
    *,
    skip_errors: bool = True,
    verbose: bool = False,
    slow_threshold_sec: float = 5.0,
    cache_dir: Optional[str] = None,
    panel_sig: Optional[str] = None,
    legacy_panel_sig: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """加载多个因子库并合并。"""
    all_factors: Dict[str, pd.DataFrame] = {}
    for lib in libraries:
        lib_factors = load_library(
            lib,
            panel,
            skip_errors=skip_errors,
            verbose=verbose,
            slow_threshold_sec=slow_threshold_sec,
            cache_dir=cache_dir,
            panel_sig=panel_sig,
            legacy_panel_sig=legacy_panel_sig,
        )
        # 因子名已经带库前缀，直接合并即可，不会冲突。
        all_factors.update(lib_factors)
    return all_factors
