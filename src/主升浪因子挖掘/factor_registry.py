"""自动发现 factors/ 子目录下的因子并注册。

约定：
- 每个因子文件 factors/<name>.py 必须导出 compute_<name>(...) 函数；
- 函数参数命名形如 close_df / volume_df / amount_df / open_df / high_df / low_df，
  通过参数名后缀 "_df" 自动推断需要的字段；
- 因子方向统一为"值越大越接近起爆前夜"。
"""
from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any, Callable

import pandas as pd

FACTOR_LABEL_OVERRIDES: dict[str, str] = {
    "vol_shrink_20": "20日缩量盘整",
    "range_squeeze_20": "20日布林带收窄",
    "higher_lows_20": "20日低点抬升",
    "amount_anomaly_5": "5日成交额异动",
    "ma_alignment": "5/10/20/60均线粘合",
}


def _infer_factor_args(module_name: str, function_name: str) -> list[str] | None:
    """从 compute 函数签名推断输入字段名（参数名去掉 "_df" 后缀）。"""
    try:
        module = importlib.import_module(module_name)
        compute_func = getattr(module, function_name)
        signature = inspect.signature(compute_func)
    except (ImportError, AttributeError, ValueError, TypeError):
        return None

    args: list[str] = []
    for param_name, parameter in signature.parameters.items():
        if parameter.kind not in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            continue
        # 只取以 _df 结尾的位置参数，其余视为 window 等可调参数（用默认值）
        if not param_name.endswith("_df"):
            break
        args.append(param_name.removesuffix("_df"))
    return args


def discover_blastoff_factors() -> dict[str, dict[str, Any]]:
    """扫描 factors/ 子目录构建注册表。"""
    factor_dir = Path(__file__).resolve().parent / "factors"
    if not factor_dir.exists():
        return {}

    discovered: dict[str, dict[str, Any]] = {}
    for file_path in sorted(factor_dir.glob("*.py")):
        if file_path.stem.startswith("_"):
            continue
        factor_name = file_path.stem
        module_name = f"src.主升浪因子挖掘.factors.{factor_name}"
        function_name = f"compute_{factor_name}"
        args = _infer_factor_args(module_name, function_name)
        if not args:
            continue
        discovered[f"blastoff.{factor_name}"] = {
            "module": module_name,
            "function": function_name,
            "args": args,
            "label": FACTOR_LABEL_OVERRIDES.get(factor_name, factor_name),
            "is_factor_higher_better": True,
            "group": "blastoff",
        }
    return discovered


FACTOR_REGISTRY: dict[str, dict[str, Any]] = discover_blastoff_factors()


def compute_factor(factor_name: str, data_bundle: dict[str, Any]) -> pd.DataFrame:
    """按注册表定义计算单个因子。"""
    spec = FACTOR_REGISTRY.get(factor_name)
    if spec is None:
        raise ValueError(f"未注册的因子: {factor_name}")

    module_name = str(spec["module"])
    function_name = str(spec["function"])
    module = importlib.import_module(module_name)
    compute_func: Callable[..., pd.DataFrame] = getattr(module, function_name)

    args: list[pd.DataFrame] = []
    for field in spec.get("args", []):
        field_df = data_bundle.get(str(field))
        if not isinstance(field_df, pd.DataFrame):
            raise ValueError(f"计算因子 {factor_name} 时缺少字段: {field}")
        args.append(field_df)
    return compute_func(*args)


def list_factor_names() -> list[str]:
    """返回所有注册因子名称（带 blastoff. 前缀）。"""
    return list(FACTOR_REGISTRY.keys())
