#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore
"""因子过滤模块。

支持三种策略：

- ``none``：返回全部因子，不做任何过滤。
- ``threshold``：先按 ``|rank_ic_mean| > rank_ic_min`` 且 ``|rank_ic_ir| > rank_ic_ir_min``
  过滤；再在剩余因子中两两计算相关性，对 ``|相关性| > corr_max`` 的因子对去除质量较差者
  （以 ``|rank_ic_ir|`` 衡量）。
- ``topk``：按 ``|rank_ic_ir|`` 降序选 K 个。

输入：

- ``factor_evaluation``：单因子评价表，至少包含列 ``factor`` / ``rank_ic_mean`` / ``rank_ic_ir``。
- ``correlation``：因子两两相关性矩阵 ``DataFrame``，``index`` / ``columns`` 都是因子名。

输出：

- ``selected``：过滤后保留的因子名列表（保留原顺序）。
- ``report``：``DataFrame``，含每个因子的 ``selected`` 标记与判定原因。
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

VALID_METHODS = ("none", "threshold", "topk")


def _filter_none(evaluation: pd.DataFrame) -> Tuple[List[str], pd.DataFrame]:
    selected = evaluation["factor"].tolist()
    report = evaluation.assign(selected=True, drop_reason="").copy()
    return selected, report


def _threshold_filter(
    evaluation: pd.DataFrame,
    correlation: pd.DataFrame,
    rank_ic_min: float,
    rank_ic_ir_min: float,
    corr_max: float,
) -> Tuple[List[str], pd.DataFrame]:
    report = evaluation.copy()
    report["abs_rank_ic_mean"] = report["rank_ic_mean"].abs()
    report["abs_rank_ic_ir"] = report["rank_ic_ir"].abs()
    report["selected"] = (
        (report["abs_rank_ic_mean"] > rank_ic_min)
        & (report["abs_rank_ic_ir"] > rank_ic_ir_min)
    )
    report["drop_reason"] = ""
    report.loc[report["abs_rank_ic_mean"] <= rank_ic_min, "drop_reason"] = (
        f"|rank_ic_mean|<={rank_ic_min}"
    )
    mask_ir = report["abs_rank_ic_ir"] <= rank_ic_ir_min
    report.loc[mask_ir & (report["drop_reason"] == ""), "drop_reason"] = (
        f"|rank_ic_ir|<={rank_ic_ir_min}"
    )

    # 第一阶段：阈值通过的因子。
    primary = report[report["selected"]].copy()
    if primary.empty or correlation is None or correlation.empty:
        return primary["factor"].tolist(), report

    # 第二阶段：相关性去重，每次找最大相关系数对，去除其中 |IR| 较小者。
    primary_factors = primary["factor"].tolist()
    abs_ir_map: Dict[str, float] = dict(zip(primary["factor"], primary["abs_rank_ic_ir"]))
    available = list(primary_factors)
    available_set = set(available)

    while True:
        sub_corr = correlation.loc[available, available].abs().copy()
        np.fill_diagonal(sub_corr.values, np.nan)
        if sub_corr.dropna(how="all").empty:
            break
        max_value = sub_corr.max().max()
        if pd.isna(max_value) or max_value <= corr_max:
            break

        stacked = sub_corr.stack()
        stacked = stacked[stacked > corr_max]
        if stacked.empty:
            break
        # 取相关性最大的那一对。
        f_a, f_b = stacked.idxmax()
        ir_a = abs_ir_map.get(f_a, 0.0)
        ir_b = abs_ir_map.get(f_b, 0.0)
        # 保留 IR 大的那一个；相同则按字母序保留靠前者，剔除靠后者。
        if ir_a < ir_b or (ir_a == ir_b and f_a > f_b):
            drop_factor = f_a
        else:
            drop_factor = f_b

        available.remove(drop_factor)
        available_set.discard(drop_factor)
        report.loc[report["factor"] == drop_factor, "selected"] = False
        report.loc[report["factor"] == drop_factor, "drop_reason"] = (
            f"|corr|>{corr_max} 的高相关因子（保留 IR 更高者）"
        )

    selected = [f for f in primary_factors if f in available_set]
    return selected, report


def _topk_filter(evaluation: pd.DataFrame, topk: int) -> Tuple[List[str], pd.DataFrame]:
    report = evaluation.copy()
    report["abs_rank_ic_ir"] = report["rank_ic_ir"].abs()
    sorted_report = report.sort_values("abs_rank_ic_ir", ascending=False, na_position="last")
    keep_factors = sorted_report.head(topk)["factor"].tolist()
    keep_set = set(keep_factors)
    report["selected"] = report["factor"].isin(keep_set)
    report["drop_reason"] = ""
    report.loc[~report["selected"], "drop_reason"] = (
        f"按 |rank_ic_ir| 降序未进入前 {topk} 名"
    )
    return keep_factors, report


def apply(
    method: str,
    factor_evaluation: pd.DataFrame,
    correlation: pd.DataFrame | None = None,
    *,
    rank_ic_min: float = 0.02,
    rank_ic_ir_min: float = 0.3,
    corr_max: float = 0.7,
    topk: int = 20,
) -> Tuple[List[str], pd.DataFrame]:
    """执行因子过滤。

    Args:
        method: ``"none"`` / ``"threshold"`` / ``"topk"``。
        factor_evaluation: 单因子评价表，需要包含 ``factor`` / ``rank_ic_mean`` / ``rank_ic_ir``。
        correlation: 因子两两相关性矩阵；``threshold`` 模式需要传入。
        rank_ic_min / rank_ic_ir_min / corr_max / topk: 各方法的阈值参数。

    Returns:
        ``(selected_factors, report_df)``。
    """
    if method not in VALID_METHODS:
        raise ValueError(f"method 必须是 {VALID_METHODS}，当前为 {method}")

    if "factor" not in factor_evaluation.columns:
        raise ValueError("factor_evaluation 必须包含 factor 列")
    for required in ("rank_ic_mean", "rank_ic_ir"):
        if required not in factor_evaluation.columns:
            raise ValueError(f"factor_evaluation 缺少 {required} 列")

    if method == "none":
        return _filter_none(factor_evaluation)
    if method == "threshold":
        return _threshold_filter(
            factor_evaluation,
            correlation if correlation is not None else pd.DataFrame(),
            rank_ic_min,
            rank_ic_ir_min,
            corr_max,
        )
    if method == "topk":
        return _topk_filter(factor_evaluation, max(int(topk), 1))
    raise AssertionError("unreachable")  # pragma: no cover
