"""
Tick 数据转换模块

负责将 xtdata 推送的原始行情数据转换为 vnpy 的 TickData 格式，
包括涨跌停价格的提取与估算。
"""
from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from vnpy.trader.object import TickData

from .utils import get_exchange_from_code


def convert_xtdata_to_tick(stock_code: str, tick_data: Dict[str, Any]) -> Optional[TickData]:
    """
    将 xtdata 推送的原始行情字典转换为 vnpy TickData 对象

    Args:
        stock_code: 股票代码，如 "512710.SH"
        tick_data : xtdata 推送的行情数据字典，包含以下常见字段:
                    lastPrice, lastClose, volume, amount,
                    bidPrice1, askPrice1, bidVol1, askVol1,
                    open, high, low, upperLimit, lowerLimit, servertime

    Returns:
        TickData 对象；转换失败返回 None
    """
    try:
        # ── 解析时间 ──
        tick_time = _parse_servertime(tick_data.get("servertime", ""))

        # ── 提取基础字段 ──
        last_price  = tick_data.get("lastPrice", 0.0)
        last_close  = tick_data.get("lastClose", 0.0)
        volume      = tick_data.get("volume", 0)
        amount      = tick_data.get("amount", 0.0)
        bid_price_1 = tick_data.get("bidPrice1", 0.0)
        ask_price_1 = tick_data.get("askPrice1", 0.0)
        bid_vol_1   = tick_data.get("bidVol1", 0)
        ask_vol_1   = tick_data.get("askVol1", 0)
        open_price  = tick_data.get("open", last_close)
        high_price  = tick_data.get("high", last_price)
        low_price   = tick_data.get("low", last_price)

        # ── 涨跌停价格：优先从 xtdata 获取，否则用昨收 ±10% 估算 ──
        limit_up, limit_down = _extract_price_limits(tick_data, last_close)

        # ── 交易所 ──
        exchange = get_exchange_from_code(stock_code)

        # ── 构造 TickData ──
        tick = TickData(
            symbol=stock_code.split(".")[0],
            exchange=exchange,
            datetime=tick_time,
            name=stock_code,
            volume=volume,
            open_interest=0.0,
            last_price=last_price,
            last_volume=0,
            limit_up=limit_up,
            limit_down=limit_down,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            pre_close=last_close,
            bid_price_1=bid_price_1,
            bid_price_2=0.0, bid_price_3=0.0, bid_price_4=0.0, bid_price_5=0.0,
            ask_price_1=ask_price_1,
            ask_price_2=0.0, ask_price_3=0.0, ask_price_4=0.0, ask_price_5=0.0,
            bid_volume_1=bid_vol_1,
            bid_volume_2=0, bid_volume_3=0, bid_volume_4=0, bid_volume_5=0,
            ask_volume_1=ask_vol_1,
            ask_volume_2=0, ask_volume_3=0, ask_volume_4=0, ask_volume_5=0,
            gateway_name="xtdata",
        )
        return tick

    except Exception as e:
        print(f"[TickConverter] 转换失败 {stock_code}: {e}")
        traceback.print_exc()
        return None


# ================================================================
#  内部辅助函数
# ================================================================

def _parse_servertime(servertime: Any) -> datetime:
    """
    解析 xtdata 的 servertime 字段为 datetime

    支持格式：
        - "2026-04-01 14:30:00"
        - "20260401 143000"
        - 其他格式回退到 datetime.now()
    """
    if not servertime or not isinstance(servertime, str):
        return datetime.now()

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y%m%d %H:%M:%S"):
        try:
            return datetime.strptime(servertime, fmt)
        except ValueError:
            continue
    return datetime.now()


def _extract_price_limits(tick_data: Dict[str, Any], last_close: float) -> tuple[float, float]:
    """
    提取涨跌停价格

    优先级：
        1. tick_data 中的 upperLimit / limitUp 和 lowerLimit / limitDown
        2. 用昨收 ±10% 估算

    Returns:
        (limit_up, limit_down) 元组
    """
    limit_up = tick_data.get("upperLimit", 0.0) or tick_data.get("limitUp", 0.0)
    limit_down = tick_data.get("lowerLimit", 0.0) or tick_data.get("limitDown", 0.0)

    if (not limit_up or limit_up <= 0) and last_close > 0:
        limit_up = round(last_close * 1.1, 3)
    if (not limit_down or limit_down <= 0) and last_close > 0:
        limit_down = round(last_close * 0.9, 3)

    return float(limit_up or 0), float(limit_down or 0)
