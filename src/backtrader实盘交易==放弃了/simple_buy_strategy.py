"""
简单买入策略
============

策略逻辑：买入 159100.SZ，1手=100股，持有。
"""

import backtrader as bt
from datetime import datetime


class SimpleBuyStrategy(bt.Strategy):
    """
    简单买入策略
    
    在策略开始时买入 159100.SZ，1手=100股，然后持有。
    """
    
    params = (
        ('stock_code', '159100.SZ'),
        ('buy_volume', 100),  # 1手=100股
        ('buy_price', 0.90),  # 买入价格（限价单）
    )
    
    def __init__(self):
        """初始化策略"""
        self.order = None
        self.bought = False
        self.buy_price = 0.0
        self.buy_time = None
        
        print(f"[策略] 初始化完成，目标股票: {self.p.stock_code}, 买入数量: {self.p.buy_volume}, 买入价格: {self.p.buy_price:.2f}元")
    
    def next(self):
        """
        策略主逻辑
        
        在每个 bar 执行一次
        """
        # 检查是否有成交事件
        broker = self.broker
        if hasattr(broker, 'get_trade_events'):
            trade_events = broker.get_trade_events()
            for event in trade_events:
                self._on_trade(event)
        
        # 如果还没有买入，且没有未完成的订单
        if not self.bought and self.order is None:
            # 检查是否有足够的资金
            cash = self.broker.getcash()
            buy_price = self.p.buy_price  # 使用指定的买入价格
            required_cash = buy_price * self.p.buy_volume * (1 + self.broker.p.commission)
            
            if cash >= required_cash:
                # 买入（限价单，价格为 0.90 元）
                self.order = self.buy(
                    exectype=bt.Order.Limit,
                    price=buy_price,
                    size=self.p.buy_volume
                )
                current_price = self.data.close[0] if len(self.data) > 0 else 0.0
                print(f"[策略] 提交买入订单: {self.p.stock_code}, 数量: {self.p.buy_volume}, "
                      f"限价: {buy_price:.2f}元, 当前价格: {current_price:.2f}, 需要资金: {required_cash:.2f}")
            else:
                print(f"[策略] 资金不足，无法买入。可用资金: {cash:.2f}, 需要资金: {required_cash:.2f}")
    
    def _on_trade(self, trade_event):
        """
        处理成交事件
        
        Parameters:
        -----------
        trade_event : dict
            成交事件，包含以下字段：
            - order: backtrader 订单对象
            - trade: XtTrade 对象
            - stock_code: 股票代码
            - price: 成交价格
            - volume: 成交数量
            - time: 成交时间
        """
        order = trade_event['order']
        stock_code = trade_event['stock_code']
        price = trade_event['price']
        volume = trade_event['volume']
        trade_time = trade_event.get('time', '')
        
        # 检查是否是我们的订单
        if order == self.order:
            if order.isbuy():
                # 买入成交
                self.bought = True
                self.buy_price = price
                self.buy_time = trade_time
                
                print(f"\n{'='*60}")
                print(f"[策略] ✅ 买入成交！")
                print(f"  股票代码: {stock_code}")
                print(f"  成交价格: {price:.2f}")
                print(f"  成交数量: {volume} 股")
                print(f"  成交时间: {trade_time}")
                print(f"  订单ID: {order.ref}")
                print(f"{'='*60}\n")
                
                # 订单状态已由 Broker 更新，这里只需要标记
                if hasattr(order, 'executed') and hasattr(order.executed, 'size'):
                    if order.executed.size >= order.created.size:
                        # 全部成交，清空订单引用
                        self.order = None
            elif order.issell():
                # 卖出成交
                print(f"\n{'='*60}")
                print(f"[策略] ✅ 卖出成交！")
                print(f"  股票代码: {stock_code}")
                print(f"  成交价格: {price:.2f}")
                print(f"  成交数量: {volume} 股")
                print(f"  成交时间: {trade_time}")
                print(f"{'='*60}\n")
    
    def notify_order(self, order):
        """
        订单状态通知
        
        Parameters:
        -----------
        order : bt.order.Order
            订单对象
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或已接受
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"[策略] 买入订单完成: {order.data._name}, 数量: {order.executed.size}, "
                      f"价格: {order.executed.price:.2f}")
            elif order.issell():
                print(f"[策略] 卖出订单完成: {order.data._name}, 数量: {order.executed.size}, "
                      f"价格: {order.executed.price:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"[策略] 订单状态: {order.getstatusname()}, 原因: {order.info}")
    
    def notify_trade(self, trade):
        """
        成交通知（backtrader 内部调用）
        
        Parameters:
        -----------
        trade : bt.trade.Trade
            成交对象
        """
        if trade.isclosed:
            print(f"[策略] 交易关闭: {trade.data._name}, 盈亏: {trade.pnl:.2f}, "
                  f"净利润: {trade.pnlcomm:.2f}")
    
    def stop(self):
        """策略结束"""
        print(f"\n[策略] 策略结束")
        if self.bought:
            print(f"  已买入: {self.p.stock_code}")
            print(f"  买入价格: {self.buy_price:.2f}")
            print(f"  买入时间: {self.buy_time}")
        else:
            print(f"  未买入: {self.p.stock_code}")

