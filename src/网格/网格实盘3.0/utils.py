"""
通用工具函数模块

提供交易所判断、交易时段判断等基础工具。
"""
from __future__ import annotations

from datetime import datetime, time as dtime

from vnpy.trader.constant import Exchange


def get_exchange_from_code(stock_code: str) -> Exchange:
    """
    根据股票代码后缀判断交易所

    Args:
        stock_code: 股票代码，如 "512710.SH" 或 "162411.SZ"

    Returns:
        Exchange 枚举值
    """
    code_upper = stock_code.upper()
    if code_upper.endswith(".SH"):
        return Exchange.SSE
    elif code_upper.endswith(".SZ"):
        return Exchange.SZSE
    else:
        # 默认返回上交所
        return Exchange.SSE


def within_trading_window(now: datetime | None = None) -> bool:
    """
    判断当前时间是否在 A 股交易时段内

    交易时段：
        - 上午: 09:15 ~ 11:30
        - 下午: 13:00 ~ 15:00

    Args:
        now: 要检查的时间，默认使用当前时间

    Returns:
        True 表示在交易时段内
    """
    if now is None:
        now = datetime.now()
    t = now.time()
    morning = dtime(9, 15) <= t <= dtime(11, 30)
    afternoon = dtime(13, 0) <= t <= dtime(15, 0)
    return morning or afternoon


def clean_stock_code(stock_code: str) -> str:
    """
    清理股票代码中的交易所后缀

    例如: "512710.SH" → "512710"
    """
    return stock_code.replace(".SH", "").replace(".SZ", "").replace(".", "")


def match_stock_code(code_a: str, code_b: str) -> bool:
    """
    比较两个股票代码是否指向同一只股票（忽略后缀差异）

    Args:
        code_a: 股票代码 A
        code_b: 股票代码 B

    Returns:
        True 表示是同一只股票
    """
    return clean_stock_code(code_a) == clean_stock_code(code_b)
