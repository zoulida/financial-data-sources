"""
Tick 数据订阅工具
================

封装 xtdata 的 tick 行情订阅，参考
`d:/pythonProject/firstBan/source/实盘/xuntou/datadownload/订阅获取Tick数据.py`
"""

import time
import traceback
from typing import Callable, List, Optional, Dict, Any
from queue import Queue

from xtquant import xtdata


def default_tick_callback(datas: Dict[str, Dict[str, Any]]):
    """默认 tick 数据回调，打印基础信息"""
    try:
        for stock_code, tick_data in datas.items():
            last_price = tick_data.get("lastPrice")
            last_close = tick_data.get("lastClose")
            print(
                f"[Tick] {stock_code} 价: {last_price} "
                f"昨收: {last_close} 涨幅: "
                f"{(last_price - last_close) / last_close * 100:.2f}%"
                if last_price is not None and last_close not in (None, 0)
                else f"[Tick] {stock_code} 数据: {tick_data}"
            )
    except Exception as e:
        print(f"[Tick] 回调异常: {e}")
        traceback.print_exc()


class TickSubscriber:
    """Tick 数据订阅封装"""

    def __init__(self):
        self.subscription_id: Optional[int] = None

    def subscribe(
        self,
        stock_codes: List[str],
        callback: Callable[[Dict[str, Dict[str, Any]]], None] = None,
        tick_queue: Optional[Queue] = None,
    ) -> bool:
        """订阅 tick 行情

        Parameters
        ----------
        stock_codes : List[str]
            股票代码列表
        callback : Callable, optional
            自定义回调，默认为打印
        tick_queue : deque, optional
            若提供，将 tick 数据推入队列供 Backtrader 使用
        """
        try:
            if self.subscription_id is not None:
                xtdata.unsubscribe_quote(self.subscription_id)
                print(f"[Tick] 取消上次订阅 ID: {self.subscription_id}")

            def queue_wrapper(datas):
                if tick_queue is not None:
                    for stock_code, tick_data in datas.items():
                        tick_data = dict(tick_data)
                        tick_data["stock_code"] = stock_code
                        tick_queue.put(tick_data)
                cb = callback or default_tick_callback
                if cb:
                    cb(datas)

            cb = queue_wrapper if tick_queue is not None else (callback or default_tick_callback)

            self.subscription_id = xtdata.subscribe_whole_quote(
                code_list=stock_codes, callback=cb
            )
            print(f"[Tick] 订阅成功 ID: {self.subscription_id}，股票数: {len(stock_codes)}")
            return True
        except Exception as e:
            print(f"[Tick] 订阅失败: {e}")
            traceback.print_exc()
            return False

    def unsubscribe(self):
        """取消订阅"""
        try:
            if self.subscription_id is not None:
                xtdata.unsubscribe_quote(self.subscription_id)
                print(f"[Tick] 已取消订阅 ID: {self.subscription_id}")
                self.subscription_id = None
        except Exception as e:
            print(f"[Tick] 取消订阅失败: {e}")
            traceback.print_exc()


