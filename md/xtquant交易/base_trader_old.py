"""
基础交易类 - XtQuant 交易接口封装
====================================

基于迅投XtQuant API文档创建的统一交易接口，包含买入、卖出、撤单、查询等常用功能。
"""

from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import pandas as pd
import time
from typing import Optional, Dict, List, Any


class BaseTraderCallback(XtQuantTraderCallback):
    """基础交易回调类，用于接收交易状态推送"""
    
    def __init__(self):
        self.orders = {}  # 存储委托信息
        self.trades = {}  # 存储成交信息
        self.connected = True
        
    def on_disconnected(self):
        """连接断开回调"""
        print("[回调] 连接断开")
        self.connected = False
        
    def on_stock_order(self, order):
        """委托回报推送"""
        order_info = {
            'order_id': order.order_id,
            'stock_code': order.stock_code,
            'order_status': order.order_status,
            'order_sysid': order.order_sysid,
            'order_type': order.order_type,
            'order_volume': order.order_volume,
            'traded_volume': order.traded_volume,
            'price': order.price
        }
        self.orders[order.order_id] = order_info
        print(f"[委托] {order.stock_code} 状态={order.order_status} 已成交={order.traded_volume}")
        
    def on_stock_trade(self, trade):
        """成交变动推送"""
        trade_info = {
            'trade_id': trade.trade_id,
            'account_id': trade.account_id,
            'stock_code': trade.stock_code,
            'order_id': trade.order_id,
            'traded_price': trade.traded_price,
            'traded_volume': trade.traded_volume
        }
        self.trades[trade.trade_id] = trade_info
        print(f"[成交] {trade.stock_code} 价格={trade.traded_price} 数量={trade.traded_volume}")
        
    def on_order_error(self, order_error):
        """委托失败推送"""
        print(f"[委托失败] 订单ID:{order_error.order_id} 错误码:{order_error.error_id} 错误信息:{order_error.error_msg}")
        
    def on_cancel_error(self, cancel_error):
        """撤单失败推送"""
        print(f"[撤单失败] 订单ID:{cancel_error.order_id} 错误码:{cancel_error.error_id} 错误信息:{cancel_error.error_msg}")
        
    def on_order_stock_async_response(self, response):
        """异步下单回报推送"""
        print(f"[异步下单回报] 账号:{response.account_id} 订单ID:{response.order_id} 序号:{response.seq}")
        
    def on_account_status(self, status):
        """账号状态推送"""
        print(f"[账号状态] 账号:{status.account_id} 类型:{status.account_type} 状态:{status.status}")


class BaseTrader:
    """
    基础交易类
    
    使用示例:
        trader = BaseTrader(
            path=r'D:\国金证券QMT交易端\userdata_mini',
            account='8886063599', 
            session_id=123456
        )
        trader.connect()
        
        # 买入股票
        order_id = trader.buy('512710.SH', 100, 0.661)
        
        # 查询持仓
        positions = trader.get_positions()
    """
    
    def __init__(self, path: str, account: str, session_id: int = 123456):
        """
        初始化交易接口
        
        Parameters:
        -----------
        path : str
            QMT用户数据路径，如 r'D:\国金证券QMT交易端\userdata_mini'
        account : str
            资金账号，如 '8886063599'
        session_id : int
            会话编号，不同策略使用不同会话编号，默认为 123456
        """
        self.path = path
        self.account = account
        self.session_id = session_id
        
        # 创建资金账号对象
        self.stock_account = StockAccount(account, "STOCK")
        
        # 创建XtQuantTrader实例
        self.xt_trader = XtQuantTrader(path, session_id)
        
        # 连接状态
        self._connected = False
        
        # 回调对象
        self.callback = None
        
    def connect(self) -> int:
        """
        连接交易系统
        
        Returns:
        --------
        int
            连接结果，0表示连接成功
        """
        # 启动交易线程
        self.xt_trader.start()
        
        # 建立交易连接
        connect_result = self.xt_trader.connect()
        
        if connect_result == 0:
            self._connected = True
            print(f"[BaseTrader] 连接成功，账号: {self.account}")
        else:
            print(f"[BaseTrader] 连接失败，错误码: {connect_result}")
            
        return connect_result
    
    def subscribe(self) -> int:
        """
        订阅账号信息，接收交易主推
        
        Returns:
        --------
        int
            订阅结果，0表示订阅成功
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return -1
            
        subscribe_result = self.xt_trader.subscribe(self.stock_account)
        
        if subscribe_result == 0:
            print(f"[BaseTrader] 订阅成功，账号: {self.account}")
        else:
            print(f"[BaseTrader] 订阅失败，错误码: {subscribe_result}")
            
        return subscribe_result
    
    def register_callback(self, callback: XtQuantTraderCallback):
        """
        注册回调函数
        
        Parameters:
        -----------
        callback : XtQuantTraderCallback
            回调对象
        """
        self.callback = callback
        self.xt_trader.register_callback(callback)
        print("[BaseTrader] 回调注册成功")
    
    def buy(self, stock_code: str, volume: int, price: float,
            price_type: int = xtconstant.FIX_PRICE,
            strategy_name: str = "base_trader",
            order_remark: str = "") -> Optional[int]:
        """
        买入股票
        
        Parameters:
        -----------
        stock_code : str
            证券代码，如 '600000.SH'
        volume : int
            委托数量（股）
        price : float
            委托价格
        price_type : int
            报价类型，默认为限价 xtconstant.FIX_PRICE
        strategy_name : str
            策略名称
        order_remark : str
            委托备注
            
        Returns:
        --------
        int
            订单编号，成功返回大于0的正整数，失败返回-1
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return -1
            
        order_id = self.xt_trader.order_stock(
            self.stock_account,
            stock_code,
            xtconstant.STOCK_BUY,
            volume,
            price_type,
            price,
            strategy_name,
            order_remark or stock_code
        )
        
        if order_id > 0:
            print(f"[BaseTrader] 买入委托成功: {stock_code} 数量={volume} 价格={price} 订单ID={order_id}")
        else:
            print(f"[BaseTrader] 买入委托失败: {stock_code} 错误码={order_id}")
            
        return order_id
    
    def sell(self, stock_code: str, volume: int, price: float,
             price_type: int = xtconstant.FIX_PRICE,
             strategy_name: str = "base_trader",
             order_remark: str = "") -> Optional[int]:
        """
        卖出股票
        
        Parameters:
        -----------
        stock_code : str
            证券代码，如 '600000.SH'
        volume : int
            委托数量（股）
        price : float
            委托价格
        price_type : int
            报价类型，默认为限价 xtconstant.FIX_PRICE
        strategy_name : str
            策略名称
        order_remark : str
            委托备注
            
        Returns:
        --------
        int
            订单编号，成功返回大于0的正整数，失败返回-1
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return -1
            
        order_id = self.xt_trader.order_stock(
            self.stock_account,
            stock_code,
            xtconstant.STOCK_SELL,
            volume,
            price_type,
            price,
            strategy_name,
            order_remark or stock_code
        )
        
        if order_id > 0:
            print(f"[BaseTrader] 卖出委托成功: {stock_code} 数量={volume} 价格={price} 订单ID={order_id}")
        else:
            print(f"[BaseTrader] 卖出委托失败: {stock_code} 错误码={order_id}")
            
        return order_id
    
    def buy_async(self, stock_code: str, volume: int, price: float,
                  price_type: int = xtconstant.FIX_PRICE,
                  strategy_name: str = "base_trader",
                  order_remark: str = "") -> Optional[int]:
        """
        异步买入股票
        
        Returns:
        --------
        int
            下单请求序号seq，可用于与异步回调对应
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return -1
            
        seq = self.xt_trader.order_stock_async(
            self.stock_account,
            stock_code,
            xtconstant.STOCK_BUY,
            volume,
            price_type,
            price,
            strategy_name,
            order_remark or stock_code
        )
        
        print(f"[BaseTrader] 异步买入请求: {stock_code} 数量={volume} 价格={price} 序号={seq}")
        return seq
    
    def cancel_order(self, order_id: int) -> int:
        """
        撤销委托
        
        Parameters:
        -----------
        order_id : int
            订单编号
            
        Returns:
        --------
        int
            撤单结果，0表示成功
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return -1
            
        result = self.xt_trader.cancel_order_stock(self.stock_account, order_id)
        
        if result == 0:
            print(f"[BaseTrader] 撤单成功: 订单ID={order_id}")
        else:
            print(f"[BaseTrader] 撤单失败: 订单ID={order_id} 错误码={result}")
            
        return result
    
    def get_asset(self) -> Optional[Dict]:
        """
        查询证券资产
        
        Returns:
        --------
        Dict
            资产信息，包含cash等字段
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return None
            
        asset = self.xt_trader.query_stock_asset(self.stock_account)
        
        if asset:
            asset_info = {
                'cash': asset.cash,
                'frozen_cash': getattr(asset, 'frozen_cash', 0),
                'market_value': getattr(asset, 'market_value', 0),
                'total_asset': getattr(asset, 'total_asset', 0)
            }
            print(f"[BaseTrader] 可用资金: {asset_info['cash']:.2f}")
            return asset_info
        else:
            print("[BaseTrader] 查询资产失败")
            return None
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        """
        根据订单编号查询委托
        
        Parameters:
        -----------
        order_id : int
            订单编号
            
        Returns:
        --------
        Dict
            委托信息
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return None
            
        order = self.xt_trader.query_stock_order(self.stock_account, order_id)
        
        if order:
            order_info = {
                'order_id': order.order_id,
                'stock_code': order.stock_code,
                'order_type': order.order_type,
                'order_volume': order.order_volume,
                'traded_volume': order.traded_volume,
                'price': order.price,
                'order_status': order.order_status,
                'strategy_name': getattr(order, 'strategy_name', ''),
                'order_remark': getattr(order, 'order_remark', '')
            }
            return order_info
        else:
            print(f"[BaseTrader] 查询委托失败: 订单ID={order_id}")
            return None
    
    def get_orders(self) -> List[Dict]:
        """
        查询当日所有委托
        
        Returns:
        --------
        List[Dict]
            委托列表
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return []
            
        orders = self.xt_trader.query_stock_orders(self.stock_account)
        orders_list = []
        
        if orders:
            for order in orders:
                order_info = {
                    'order_id': order.order_id,
                    'stock_code': order.stock_code,
                    'order_type': order.order_type,
                    'order_volume': order.order_volume,
                    'traded_volume': order.traded_volume,
                    'price': order.price,
                    'order_status': order.order_status,
                    'strategy_name': getattr(order, 'strategy_name', ''),
                    'order_remark': getattr(order, 'order_remark', '')
                }
                orders_list.append(order_info)
                
        print(f"[BaseTrader] 查询到 {len(orders_list)} 条委托记录")
        return orders_list
    
    def get_trades(self) -> List[Dict]:
        """
        查询当日所有成交
        
        Returns:
        --------
        List[Dict]
            成交列表
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return []
            
        trades = self.xt_trader.query_stock_trades(self.stock_account)
        trades_list = []
        
        if trades:
            for trade in trades:
                trade_info = {
                    'trade_id': trade.trade_id,
                    'stock_code': trade.stock_code,
                    'order_id': trade.order_id,
                    'traded_price': trade.traded_price,
                    'traded_volume': trade.traded_volume,
                    'trade_time': getattr(trade, 'trade_time', '')
                }
                trades_list.append(trade_info)
                
        print(f"[BaseTrader] 查询到 {len(trades_list)} 条成交记录")
        return trades_list
    
    def get_positions(self) -> List[Dict]:
        """
        查询当日所有持仓
        
        Returns:
        --------
        List[Dict]
            持仓列表
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return []
            
        positions = self.xt_trader.query_stock_positions(self.stock_account)
        positions_list = []
        
        if positions:
            for position in positions:
                position_info = {
                    'account_id': position.account_id,
                    'stock_code': position.stock_code,
                    'volume': position.volume,
                    'can_use_volume': getattr(position, 'can_use_volume', 0),
                    'open_price': getattr(position, 'open_price', 0),
                    'market_value': getattr(position, 'market_value', 0)
                }
                positions_list.append(position_info)
                
        print(f"[BaseTrader] 查询到 {len(positions_list)} 条持仓记录")
        return positions_list
    
    def get_position(self, stock_code: str) -> Optional[Dict]:
        """
        根据股票代码查询对应持仓
        
        Parameters:
        -----------
        stock_code : str
            证券代码
            
        Returns:
        --------
        Dict
            持仓信息
        """
        if not self._connected:
            print("[BaseTrader] 请先连接交易系统")
            return None
            
        position = self.xt_trader.query_stock_position(self.stock_account, stock_code)
        
        if position:
            position_info = {
                'account_id': position.account_id,
                'stock_code': position.stock_code,
                'volume': position.volume,
                'can_use_volume': getattr(position, 'can_use_volume', 0),
                'open_price': getattr(position, 'open_price', 0),
                'market_value': getattr(position, 'market_value', 0)
            }
            return position_info
        else:
            print(f"[BaseTrader] 查询持仓失败: {stock_code}")
            return None
    
    def run_forever(self):
        """
        阻塞线程，接收交易推送
        """
        print("[BaseTrader] 开始接收交易推送...")
        self.xt_trader.run_forever()
    
    def stop(self):
        """
        停止交易线程
        """
        self.xt_trader.stop()
        self._connected = False
        print("[BaseTrader] 交易线程已停止")
