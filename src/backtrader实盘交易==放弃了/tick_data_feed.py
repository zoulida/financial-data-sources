"""
Tick 实时数据 Feed
=================

将 tick 行情队列转换为 Backtrader 数据源。
"""

from datetime import datetime
from queue import Queue, Empty
from typing import Dict, Any, Optional

import backtrader as bt


def parse_tick_datetime(tick_data: Dict[str, Any]) -> datetime:
    """解析 xtdata tick 的时间信息"""
    date_str = tick_data.get("date") or tick_data.get("Date")
    time_str = tick_data.get("time") or tick_data.get("Time")
    if date_str and time_str:
        candidates = [
            "%Y%m%d %H:%M:%S.%f",
            "%Y%m%d %H:%M:%S",
        ]
        dt_str = f"{date_str} {time_str}"
        for fmt in candidates:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
    elif time_str:
        for fmt in ["%H:%M:%S.%f", "%H:%M:%S"]:
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                return datetime.strptime(f"{today} {time_str}", "%Y-%m-%d " + fmt)
            except ValueError:
                continue
    return datetime.now()


class TickDataFeed(bt.feeds.DataBase):
    """
    基于实时 tick 队列的数据源
    """

    params = dict(
        tick_queue=None,
        stock_code="",
        timeout=1.0,
    )

    lines = ("open", "high", "low", "close", "volume", "openinterest")
    datafields = lines

    def __init__(self, tick_queue: Optional[Queue], stock_code: str, timeout: float = 1.0):
        super().__init__()
        self.tick_queue: Queue = tick_queue or Queue()
        self.stock_code = stock_code
        self.p.timeout = timeout

    def islive(self):
        return True

    def _load(self):
        try:
            tick = self.tick_queue.get(timeout=self.p.timeout)
        except Empty:
            return None

        price = tick.get("price") or tick.get("lastPrice") or 0.0
        volume = (
            tick.get("volume")
            or tick.get("lastVolume")
            or tick.get("volumeDelta")
            or 0.0
        )
        dt = tick.get("datetime") or parse_tick_datetime(tick)

        self.lines.datetime[0] = bt.date2num(dt)
        self.lines.open[0] = price
        self.lines.high[0] = price
        self.lines.low[0] = price
        self.lines.close[0] = price
        self.lines.volume[0] = volume
        self.lines.openinterest[0] = 0

        return True

