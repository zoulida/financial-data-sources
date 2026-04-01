"""
交易器模块 - 基于base_trader_zld的交易功能封装
"""
import traceback
from typing import Dict, Any

from xtquant.xttrader import XtQuantTraderCallback
from xtquant import xtconstant

# 导入基础交易器
if __package__ in {None, ""}:
    from md.xtquant交易.base_trader_zld import BaseTrader, BaseTraderCallback
else:
    from md.xtquant交易.base_trader_zld import BaseTrader, BaseTraderCallback


def build_qmt_trader_with_callback(on_filled, path: str, account: str, account_type: str, session_id: int = None) -> BaseTrader:
    """
    构建基于base_trader_zld的交易器
    
    Args:
        on_filled: 成交回调函数
        path: QMT路径
        account: 账户
        account_type: 账户类型
        session_id: 会话ID
    
    Returns:
        BaseTrader实例
    """
    class GridTraderCallback(BaseTraderCallback):
        def __init__(self, filled_callback):
            super().__init__()
            self.filled_callback = filled_callback
        
        def on_stock_order(self, order):
            """委托回报推送"""
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
                    self.filled_callback(evt)
            except Exception:
                traceback.print_exc()

        def on_stock_trade(self, trade):
            """成交推送 - 触发成交回调并传递成交编号"""
            super().on_stock_trade(trade)
            try:
                evt = {
                    "order_id": trade.order_id,
                    "trade_id": trade.trade_id,  # 成交编号
                    "stock_code": trade.stock_code,
                    "traded_price": trade.traded_price,
                    "traded_volume": trade.traded_volume,
                }
                self.filled_callback(evt)
            except Exception:
                traceback.print_exc()
    
    # 创建BaseTrader实例
    trader = BaseTrader(path=path, account=account, session_id=session_id)
    
    # 打印生成的session_id
    print(f"[GridTrader] 使用session_id: {trader.session_id}")
    
    # 注册回调
    callback = GridTraderCallback(on_filled)
    trader.register_callback(callback)
    
    # 连接和订阅
    connect_result = trader.connect()
    if connect_result == 0:
        subscribe_result = trader.subscribe()
        if subscribe_result == 0:
            print(f"[GridTrader] 连接和订阅成功，账户: {account}")
        else:
            print(f"[GridTrader] 订阅失败，错误码: {subscribe_result}")
    else:
        print(f"[GridTrader] 连接失败，错误码: {connect_result}")
    
    return trader
