"""
网格策略工具函数模块
"""
from datetime import datetime, time as dtime
from vnpy.trader.constant import Exchange


def get_exchange_from_code(stock_code: str) -> Exchange:
    """
    根据股票代码判断交易所
    
    Args:
        stock_code: 股票代码，如 "000001.SZ" 或 "600000.SH"
        
    Returns:
        Exchange 枚举值
    """
    code_upper = stock_code.upper()
    if code_upper.endswith('.SZ'):
        return Exchange.SZSE
    elif code_upper.endswith('.SH'):
        return Exchange.SSE
    elif code_upper.startswith(('0', '3')):
        # 深圳股票：0开头或3开头
        return Exchange.SZSE
    elif code_upper.startswith('6'):
        # 上海股票：6开头
        return Exchange.SSE
    else:
        # 默认返回深圳交易所
        return Exchange.SZSE


def within_trading_window(now: datetime) -> bool:
    """判断是否在交易时段内"""
    t = now.time()
    morning_start = dtime(9, 30)
    morning_end = dtime(11, 30)
    afternoon_start = dtime(13, 0)
    afternoon_end = dtime(15, 1)
    return (morning_start <= t <= morning_end) or (afternoon_start <= t <= afternoon_end)
