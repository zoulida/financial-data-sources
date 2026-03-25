"""
Base Trader - XtQuant Trading Interface Wrapper
"""

from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import time
from typing import Optional, Dict, List


class BaseTraderCallback(XtQuantTraderCallback):
    """Base trading callback class"""
    
    def __init__(self):
        self.orders = {}
        self.trades = {}
        self.connected = True
        
    def _get_order_status_desc(self, status_code: int) -> str:
        """Get order status description"""
        status_map = {
            48: "未报",
            49: "待报",
            50: "已报",
            51: "已报待撤", 
            52: "部成待撤",
            53: "部撤",
            54: "已撤",
            55: "部成",
            56: "已成",
            57: "废单",
            255: "未知"
        }
        return status_map.get(status_code, f"未知状态({status_code})")
        
    def on_disconnected(self):
        print("[Callback] Connection lost")
        self.connected = False
        
    def on_stock_order(self, order):
        from datetime import datetime
        order_info = {
            'order_id': order.order_id,
            'stock_code': order.stock_code,
            'order_status': order.order_status,
            'traded_volume': order.traded_volume,
            'price': order.price
        }
        self.orders[order.order_id] = order_info
        status_desc = self._get_order_status_desc(order.order_status)
        current_time = datetime.now().strftime("%H:%M:%S")
        print(f"[Order] ID:{order.order_id} {order.stock_code} 状态={status_desc}({order.order_status}) 成交量={order.traded_volume} 价格={order.price:.6f} 时间={current_time} 方向={'BUY' if getattr(order, 'order_type', None) == 23 else 'SELL' if getattr(order, 'order_type', None) == 24 else 'UNKNOWN'}")
        
    def on_stock_trade(self, trade):
        trade_info = {
            'trade_id': trade.trade_id,
            'stock_code': trade.stock_code,
            'order_id': trade.order_id,
            'traded_price': trade.traded_price,
            'traded_volume': trade.traded_volume
        }
        self.trades[trade.trade_id] = trade_info
        print(f"[Trade] {trade.stock_code} Price={trade.traded_price} Volume={trade.traded_volume}")
        
    def on_order_error(self, order_error):
        print(f"[Order Error] OrderID:{order_error.order_id} ErrorID:{order_error.error_id}")


import random

class BaseTrader:
    """Base Trader Class"""
    
    def __init__(self, path: str, account: str, session_id: int = None):
        self.path = path
        self.account = account
        # 随机生成8位数的session_id
        self.session_id = session_id if session_id is not None else random.randint(10000000, 99999999)
        self.stock_account = StockAccount(account, "STOCK")
        self.xt_trader = XtQuantTrader(path, self.session_id)
        self._connected = False
        self.callback = None
        
    def connect(self) -> int:
        self.xt_trader.start()
        connect_result = self.xt_trader.connect()
        
        if connect_result == 0:
            self._connected = True
            print(f"[BaseTrader] Connected successfully, account: {self.account}")
        else:
            print(f"[BaseTrader] Connection failed, error code: {connect_result}")
            
        return connect_result
    
    def subscribe(self) -> int:
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return -1
            
        subscribe_result = self.xt_trader.subscribe(self.stock_account)
        
        if subscribe_result == 0:
            print(f"[BaseTrader] Subscribe successful")
        else:
            print(f"[BaseTrader] Subscribe failed, error code: {subscribe_result}")
            
        return subscribe_result
    
    def register_callback(self, callback: XtQuantTraderCallback):
        self.callback = callback
        self.xt_trader.register_callback(callback)
        print("[BaseTrader] Callback registered")
    
    def buy(self, stock_code: str, volume: int, price: float,
            price_type: int = xtconstant.FIX_PRICE,
            strategy_name: str = "base_trader",
            order_remark: str = "") -> Optional[int]:
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return -1
            
        order_id = self.xt_trader.order_stock(
            self.stock_account, stock_code, xtconstant.STOCK_BUY,
            volume, price_type, price, strategy_name, order_remark or stock_code
        )
        
        if order_id > 0:
            print(f"[BaseTrader] Buy order success: {stock_code} Volume={volume} Price={price} ID={order_id}")
        else:
            print(f"[BaseTrader] Buy order failed: {stock_code} Error={order_id}")
            
        return order_id
    
    def sell(self, stock_code: str, volume: int, price: float,
             price_type: int = xtconstant.FIX_PRICE,
             strategy_name: str = "base_trader",
             order_remark: str = "") -> Optional[int]:
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return -1
            
        order_id = self.xt_trader.order_stock(
            self.stock_account, stock_code, xtconstant.STOCK_SELL,
            volume, price_type, price, strategy_name, order_remark or stock_code
        )
        
        if order_id > 0:
            print(f"[BaseTrader] Sell order success: {stock_code} Volume={volume} Price={price} ID={order_id}")
        else:
            print(f"[BaseTrader] Sell order failed: {stock_code} Error={order_id}")
            
        return order_id
    
    def cancel_order(self, order_id: int) -> int:
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return -1
            
        result = self.xt_trader.cancel_order_stock(self.stock_account, order_id)
        
        if result == 0:
            print(f"[BaseTrader] Cancel success: ID={order_id}")
        else:
            print(f"[BaseTrader] Cancel failed: ID={order_id} Error={result}")
            
        return result
    
    def get_asset(self) -> Optional[Dict]:
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return None
            
        asset = self.xt_trader.query_stock_asset(self.stock_account)
        
        if asset:
            asset_info = {
                'cash': asset.cash,
                'frozen_cash': getattr(asset, 'frozen_cash', 0),
                'market_value': getattr(asset, 'market_value', 0),
                'total_asset': getattr(asset, 'total_asset', 0)
            }
            print(f"[BaseTrader] Available cash: {asset_info['cash']:.2f}")
            return asset_info
        else:
            print("[BaseTrader] Query asset failed")
            return None
    
    def get_orders(self) -> List[Dict]:
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return []
            
        orders = self.xt_trader.query_stock_orders(self.stock_account)
        orders_list = []
        
        if orders:
            for order in orders:
                order_info = {
                    'order_id': order.order_id,
                    'stock_code': order.stock_code,
                    'order_volume': order.order_volume,
                    'traded_volume': order.traded_volume,
                    'price': order.price,
                    'order_status': order.order_status,
                    'order_type': getattr(order, 'order_type', None),  # 添加订单类型字段
                    'order_remark': getattr(order, 'order_remark', '')  # 添加订单备注字段
                }
                orders_list.append(order_info)
                
        print(f"[BaseTrader] Found {len(orders_list)} orders")
        return orders_list
    
    def get_trades(self) -> List[Dict]:
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return []
            
        trades = self.xt_trader.query_stock_trades(self.stock_account)
        trades_list = []
        
        if trades:
            for trade in trades:
                trade_info = {
                    'trade_id': getattr(trade, 'traded_id', ''),
                    'stock_code': trade.stock_code,
                    'order_id': trade.order_id,
                    'traded_price': trade.traded_price,
                    'traded_volume': trade.traded_volume
                }
                trades_list.append(trade_info)
                
        print(f"[BaseTrader] Found {len(trades_list)} trades")
        return trades_list
    
    def get_positions(self) -> List[Dict]:
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return []
            
        positions = self.xt_trader.query_stock_positions(self.stock_account)
        positions_list = []
        
        if positions:
            for position in positions:
                position_info = {
                    'stock_code': position.stock_code,
                    'volume': position.volume,
                    'can_use_volume': getattr(position, 'can_use_volume', 0),
                    'frozen_volume': getattr(position, 'frozen_volume', 0),
                    'open_price': getattr(position, 'open_price', 0),
                    'avg_price': getattr(position, 'avg_price', 0),
                    'market_value': getattr(position, 'market_value', 0)
                }
                positions_list.append(position_info)
                
        # print(f"[BaseTrader] Found {len(positions_list)} positions")
        return positions_list
    
    def get_position(self, stock_code: str) -> Optional[Dict]:
        """Query position by stock code"""
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return None
            
        position = self.xt_trader.query_stock_position(self.stock_account, stock_code)
        
        if position:
            position_info = {
                'stock_code': position.stock_code,
                'volume': position.volume,
                'can_use_volume': getattr(position, 'can_use_volume', 0),
                'frozen_volume': getattr(position, 'frozen_volume', 0),
                'open_price': getattr(position, 'open_price', 0),
                'avg_price': getattr(position, 'avg_price', 0),
                'market_value': getattr(position, 'market_value', 0)
            }
            return position_info
        else:
            return None
    
    def query_stock_orders_raw(self) -> List:
        """Query raw stock orders from broker (single API call)"""
        if not self._connected:
            print("[BaseTrader] Please connect first")
            return []
            
        return self.xt_trader.query_stock_orders(self.stock_account)
    
    def get_unfilled_orders(self, verbose: bool = True) -> List[Dict]:
        """Query unfilled orders (orders that haven't been fully executed)"""
        #print('开始调用self.query_stock_orders_raw()')
        orders = self.query_stock_orders_raw()
        #print("结束      了")
        unfilled_orders = []
        
        # Order status mapping based on 委托状态说明
        # 54: 已撤单 - 排除
        # 56: 已成交 - 排除  
        # 57: 废单 - 排除
        # 其他状态(50,51,52,53,58,59等)都算未成交订单
        
        if orders:
            for order in orders:
                # 排除已撤单(54)、已成交(56)、废单(57)，其他状态都算未成交订单
                if order.order_status not in [54, 56, 57]:
                    order_info = {
                        'order_id': order.order_id,
                        'stock_code': order.stock_code,
                        'order_volume': order.order_volume,
                        'traded_volume': order.traded_volume,
                        'price': order.price,
                        'order_status': order.order_status,
                        'order_type': getattr(order, 'order_type', None),  # 添加订单类型字段
                        'order_remark': getattr(order, 'order_remark', ''),  # 添加订单备注字段
                        'status_desc': self._get_order_status_desc(order.order_status)
                    }
                    unfilled_orders.append(order_info)
                    
        if verbose:
            print(f"[BaseTrader] Found {len(unfilled_orders)} unfilled orders")
        return unfilled_orders
    
    def _get_order_status_desc(self, status_code: int) -> str:
        """Get order status description"""
        status_map = {
            48: "未报",
            49: "待报",
            50: "已报",
            51: "已报待撤", 
            52: "部成待撤",
            53: "部撤",
            54: "已撤",
            55: "部成",
            56: "已成",
            57: "废单",
            255: "未知"
        }
        return status_map.get(status_code, f"未知状态({status_code})")
    
    def stop(self):
        self.xt_trader.stop()
        self._connected = False
        print("[BaseTrader] Stopped")
