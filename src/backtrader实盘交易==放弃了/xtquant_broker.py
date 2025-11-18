"""
XtQuant Broker for Backtrader
==============================

基于 XtQuant 实现的 Backtrader Broker，支持实盘交易。
"""

import time
import threading
from typing import Dict, Optional
from collections import deque

import backtrader as bt
from xtquant import xtdata
from xtquant import xtconstant
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount, XtTrade, XtOrder

from xttrader_base import XtTraderBase


class XtQuantBroker(bt.broker.BrokerBase):
    """
    XtQuant Broker for Backtrader
    
    将 XtQuant 交易接口封装为 Backtrader 的 Broker。
    """
    
    params = (
        ('account_id', ''),
        ('account_type', 'STOCK'),
        ('path', ''),
        ('session', 0),
        ('commission', 0.0003),  # 默认佣金 0.03%
        ('slippage', 0.0),  # 滑点
    )
    
    def __init__(self):
        super().__init__()
        
        # 初始化 XtTraderBase
        self.xt_trader = XtTraderBase(
            account_id=self.p.account_id,
            account_type=self.p.account_type,
            path=self.p.path,
            session=self.p.session if self.p.session > 0 else int(time.time())
        )
        
        # 订单映射：backtrader order -> xtquant order_id
        self._order_map: Dict[bt.order.Order, str] = {}
        self._order_id_map: Dict[str, bt.order.Order] = {}
        
        # 成交队列：用于通知策略
        self._trade_queue = deque()
        self._trade_lock = threading.Lock()
        
        # 注册成交回调
        self._original_on_trade = self.xt_trader._on_stock_trade
        self.xt_trader._on_stock_trade = self._on_trade_callback
        
        # 获取初始资金
        self._cash = self.xt_trader.get_available_cash()
        self._value = self.xt_trader.get_total_asset()
        
        print(f"[Broker] 初始化完成，可用资金: {self._cash:.2f}, 总资产: {self._value:.2f}")
    
    def _on_trade_callback(self, trade: XtTrade):
        """
        成交回调处理
        将 XtQuant 的成交信息转换为 backtrader 的订单状态更新
        """
        # 调用原始回调
        self._original_on_trade(trade)
        
        # 查找对应的 backtrader 订单
        order_id = trade.order_id
        if order_id in self._order_id_map:
            order = self._order_id_map[order_id]
            
            # 更新订单状态
            if not hasattr(order, 'executed'):
                order.executed = bt.order.OrderExecutionData()
            
            # 累计成交数量
            if not hasattr(order.executed, 'size'):
                order.executed.size = 0
            order.executed.size += trade.traded_volume
            
            # 更新成交价格（使用加权平均）
            if order.executed.size > 0:
                if hasattr(order.executed, 'price') and order.executed.price > 0:
                    # 加权平均价格
                    total_value = order.executed.price * (order.executed.size - trade.traded_volume) + trade.traded_price * trade.traded_volume
                    order.executed.price = total_value / order.executed.size
                else:
                    order.executed.price = trade.traded_price
            
            # 更新成交金额和佣金
            order.executed.value = order.executed.price * order.executed.size
            order.executed.comm = self.p.commission * order.executed.value
            
            # 更新剩余数量
            order.executed.remsize = max(0, order.created.size - order.executed.size)
            
            # 检查是否全部成交
            if order.executed.remsize <= 0:
                order.completed()
            
            # 将成交信息放入队列，等待策略处理
            with self._trade_lock:
                self._trade_queue.append({
                    'order': order,
                    'trade': trade,
                    'stock_code': trade.stock_code,
                    'price': trade.traded_price,
                    'volume': trade.traded_volume,
                    'time': getattr(trade, 'traded_time', '')
                })
    
    def get_trade_events(self):
        """
        获取成交事件列表（供策略调用）
        
        Returns:
        --------
        list: 成交事件列表
        """
        with self._trade_lock:
            events = list(self._trade_queue)
            self._trade_queue.clear()
            return events
    
    def getcash(self):
        """获取可用现金"""
        # 实时查询
        self._cash = self.xt_trader.get_available_cash()
        return self._cash
    
    def getvalue(self, datas=None):
        """获取总资产"""
        # 实时查询
        self._value = self.xt_trader.get_total_asset()
        return self._value
    
    def getposition(self, data, clone=True):
        """获取持仓"""
        stock_code = self._get_stock_code(data)
        position = self.xt_trader.query_stock_position(stock_code)
        
        if position:
            size = position.m_nVolume if hasattr(position, 'm_nVolume') else position.volume
            price = position.m_dAvgPrice if hasattr(position, 'm_dAvgPrice') else getattr(position, 'avg_price', 0.0)
        else:
            size = 0
            price = 0.0
        
        return bt.position.Position(size=size, price=price)
    
    def _get_stock_code(self, data):
        """从 data 对象获取股票代码"""
        # 尝试从 data 的 _name 或 params 获取
        if hasattr(data, '_name'):
            return data._name
        elif hasattr(data, 'p') and hasattr(data.p, 'dataname'):
            return data.p.dataname
        else:
            # 默认处理
            return str(data)
    
    def submit(self, order):
        """提交订单"""
        # 获取股票代码
        stock_code = self._get_stock_code(order.data)
        
        # 确定委托类型
        if order.isbuy():
            order_type = xtconstant.STOCK_BUY
        elif order.issell():
            order_type = xtconstant.STOCK_SELL
        else:
            order.reject()
            return
        
        # 获取价格
        if order.exectype == bt.Order.Market:
            price_type = xtconstant.LATEST_PRICE
            price = 0.0
        elif order.exectype == bt.Order.Limit:
            price_type = xtconstant.FIX_PRICE
            price = order.created.price
        else:
            # 默认使用限价单
            price_type = xtconstant.FIX_PRICE
            price = order.data.close[0] if len(order.data) > 0 else 0.0
        
        # 获取数量（确保是100的整数倍）
        volume = int(order.created.size)
        if volume % 100 != 0:
            volume = (volume // 100) * 100
            if volume == 0:
                order.reject()
                return
        
        # 提交订单
        try:
            result = self.xt_trader.order_stock_async(
                stock_code=stock_code,
                order_type=order_type,
                price_type=price_type,
                price=price,
                volume=volume,
                strategy_name='backtrader_strategy',
                order_remark=f'backtrader_order_{order.ref}',
                timeout=10.0
            )
            
            if result.success:
                # 保存订单映射
                self._order_map[order] = result.order_id
                self._order_id_map[result.order_id] = order
                
                # 更新订单状态
                order.submit()
                order.accept()
                
                print(f"[Broker] 订单提交成功: {stock_code}, 数量: {volume}, 价格: {price:.2f}, 订单ID: {result.order_id}")
            else:
                order.reject()
                print(f"[Broker] 订单提交失败: {result.error_msg}")
        except Exception as e:
            order.reject()
            print(f"[Broker] 订单提交异常: {e}")
    
    def cancel(self, order):
        """取消订单"""
        if order not in self._order_map:
            return
        
        order_id = self._order_map[order]
        result = self.xt_trader.cancel_order_stock_sync(order_id)
        
        if result.success:
            order.cancel()
            print(f"[Broker] 订单取消成功: {order_id}")
        else:
            print(f"[Broker] 订单取消失败: {result.error_msg}")
    
    def stop(self):
        """停止 Broker"""
        if hasattr(self, 'xt_trader'):
            self.xt_trader.stop()
        print("[Broker] Broker 已停止")
    
    def _get_stock_code_from_data(self, data):
        """从 data 对象获取股票代码（辅助方法）"""
        return self._get_stock_code(data)

