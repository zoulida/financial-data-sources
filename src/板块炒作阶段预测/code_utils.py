# -*- coding: utf-8 -*-
"""股票代码格式转换工具。

XtQuant 使用 ``600000.SH`` / ``000001.SZ`` / ``430017.BJ`` 形式；
Qlib 使用 ``SH600000`` / ``SZ000001`` / ``BJ430017`` 形式。

本模块提供两种格式之间的互转，并支持简单的 A 股代码过滤
（剔除指数、债券、基金、退市整理板等非常规标的）。
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

# A 股有效前缀：上海主板/科创板、深圳主板/创业板、北交所
_A_SHARE_PREFIXES: Tuple[str, ...] = (
    "60",   # 沪市主板
    "68",   # 科创板（剔除可在调用层做）
    "00",   # 深市主板
    "30",   # 创业板
    "8",    # 北交所 8 开头
    "43",   # 北交所 43 开头
    "92",   # 北交所新增
)


def xt_to_qlib(code: str) -> str:
    """``600000.SH`` -> ``SH600000``。"""
    code = str(code).strip()
    if "." not in code:
        return code.upper()
    head, tail = code.split(".", 1)
    return f"{tail.upper()}{head}"


def qlib_to_xt(code: str) -> str:
    """``SH600000`` -> ``600000.SH``。"""
    code = str(code).strip()
    if not code:
        return code
    prefix = code[:2].upper()
    body = code[2:]
    if prefix in {"SH", "SZ", "BJ"}:
        return f"{body}.{prefix}"
    return code


def is_a_share_xt(code: str) -> bool:
    """判断 XtQuant 风格的代码是否属于普通 A 股股票。

    剔除指数、债券、基金、可转债、ST 退市整理等非常规标的。
    """
    code = str(code).strip()
    if "." not in code:
        return False
    body, market = code.split(".", 1)
    market = market.upper()
    if market not in {"SH", "SZ", "BJ"}:
        return False
    if not body.isdigit():
        return False
    # 上交所股票必须 6 开头；科创板 688/689 也是股票
    if market == "SH":
        return body.startswith(("60", "68"))
    if market == "SZ":
        return body.startswith(("00", "30"))
    # 北交所
    return body.startswith(("8", "43", "92"))


def filter_a_share_xt(codes: Iterable[str]) -> List[str]:
    """过滤出 XtQuant 代码列表中的普通 A 股股票。"""
    return [c for c in codes if is_a_share_xt(c)]


def convert_xt_list_to_qlib(codes: Iterable[str]) -> List[str]:
    """批量把 XtQuant 代码转换为 Qlib 代码。"""
    return [xt_to_qlib(c) for c in codes]
