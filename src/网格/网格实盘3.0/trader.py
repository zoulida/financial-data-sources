"""
QMT 交易器构建模块

封装 BaseTrader 的创建过程和回调注册，
提供 build_qmt_trader_with_callback 工厂函数。

与 BaseTrader 的交互流程：
    1. 创建 BaseTrader(path, account, session_id)
    2. 创建回调类（继承 BaseTraderCallback）
    3. trader.register_callback(callback)
    4. trader.connect()
    5. trader.subscribe()
"""
from __future__ import annotations

import traceback
from typing import Any, Callable, Dict, Optional

from md.xtquant交易.base_trader_zld import BaseTrader, BaseTraderCallback


class GridTraderCallback(BaseTraderCallback):
    """
    QMT 交易回调处理器

    继承 BaseTraderCallback，接收券商的委托回报和成交回报，
    并转发给上层注册的回调函数。

    成交判定方式（二选一即触发）：
        1. order_status == 56（已成）
        2. traded_volume >= order_volume（全部成交）
    """

    def __init__(self, on_filled: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        super().__init__()
        self._on_filled = on_filled

    def on_stock_order(self, order) -> None:
        """
        委托回报推送

        当券商确认委托状态变化时触发。
        判断是否已成交，若是则构造事件字典转发给回调。
        """
        super().on_stock_order(order)
        try:
            # 56: 已成，或成交数量达到委托数量
            if (getattr(order, "order_status", None) == 56 or
                    getattr(order, "traded_volume", 0) >= getattr(order, "order_volume", 0)):
                evt = {
                    "order_id": order.order_id,
                    "stock_code": order.stock_code,
                    "order_type": getattr(order, "order_type", None),
                    "order_volume": getattr(order, "order_volume", 0),
                    "traded_volume": getattr(order, "traded_volume", 0),
                    "traded_price": getattr(order, "traded_price", 0.0),
                    "order_status": getattr(order, "order_status", 0),
                }
                if self._on_filled:
                    self._on_filled(evt)
        except Exception:
            traceback.print_exc()

    def on_stock_trade(self, trade) -> None:
        """
        成交推送

        当订单（部分或全部）成交时触发，传递成交编号等详细信息。
        """
        super().on_stock_trade(trade)
        try:
            evt = {
                "order_id": trade.order_id,
                "trade_id": trade.trade_id,
                "stock_code": trade.stock_code,
                "traded_price": trade.traded_price,
                "traded_volume": trade.traded_volume,
            }
            if self._on_filled:
                self._on_filled(evt)
        except Exception:
            traceback.print_exc()


def build_qmt_trader_with_callback(
    on_filled: Optional[Callable[[Dict[str, Any]], None]] = None,
    path: str = r"D:\国金证券QMT交易端\userdata_mini",
    account: str = "8886063599",
    account_type: str = "STOCK",
    session_id: Optional[int] = None,
) -> Optional[BaseTrader]:
    """
    工厂函数：创建并连接 QMT 交易器

    流程：
        1. 创建 BaseTrader 实例（path, account, session_id）
        2. 注册回调（GridTraderCallback）
        3. 连接交易服务器
        4. 订阅账户信息

    Args:
        on_filled    : 成交回调函数
        path         : QMT userdata 路径
        account      : 交易账户
        account_type : 账户类型（预留参数，BaseTrader 当前不使用）
        session_id   : 会话ID（None 则自动生成）

    Returns:
        已连接的 BaseTrader 实例，连接失败返回 None
    """
    try:
        # 1. 创建 BaseTrader（注意：不传 account_type）
        trader = BaseTrader(path=path, account=account, session_id=session_id)
        print(f"[GridTrader] 使用session_id: {trader.session_id}")

        # 2. 注册回调
        callback = GridTraderCallback(on_filled=on_filled)
        trader.register_callback(callback)

        # 3. 连接
        connect_result = trader.connect()
        if connect_result == 0:
            # 4. 订阅
            subscribe_result = trader.subscribe()
            if subscribe_result == 0:
                print(f"[GridTrader] 连接和订阅成功，账户: {account}")
            else:
                print(f"[GridTrader] 订阅失败，错误码: {subscribe_result}")
        else:
            print(f"[GridTrader] 连接失败，错误码: {connect_result}")

        return trader

    except Exception as e:
        print(f"[build_qmt_trader] 创建交易器失败: {e}")
        traceback.print_exc()
        return None
