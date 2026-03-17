"""
Base Trader - XtQuant Trading Interface Wrapper
==============================================

Unified trading interface based on XtQuant API documentation.
"""

from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import pandas as pd
import time
from typing import Optional, Dict, List, Any


class BaseTraderCallback(XtQuantTraderCallback):
    """Base trading callback class for receiving trading status push"""
    
    def __init__(self):
        self.orders = {}
        self.trades = {}
        self.connected = True
        
    def on_disconnected(self):
        """Connection disconnected callback"""
        print("[Callback] Connection lost")
        self.connected = False
        
    def on_stock_order(self, order):
        """Order return push"""
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
        print(f"[Order] {order.stock_code} Status={order.order_status} Traded={order.traded_volume}")
        
    def on_stock_trade(self, trade):
        """Trade change push"""
        trade_info = {
            'trade_id': trade.trade_id,
            'account_id': trade.account_id,
            'stock_code': trade.stock_code,
            'order_id': trade.order_id,
            'traded_price': trade.traded_price,
            'traded_volume': trade.traded_volume
        }
        self.trades[trade.trade_id] = trade_info
        print(f"[Trade] {trade.stock_code} Price={trade.traded_price} Volume={trade.traded_volume}")
        
    def on_order_error(self, order_error):
        """Order failure push"""
        print(f"[Order Error] OrderID:{order_error.order_id} ErrorID:{order_error.error_id} Msg:{order_error.error_msg}")
        
    def on_cancel_error(self, cancel_error):
        """Cancel failure push"""
        print(f"[Cancel Error] OrderID:{cancel_error.order_id} ErrorID:{cancel_error.error_id} Msg:{cancel_error.error_msg}")
        
    def on_order_stock_async_response(self, response):
        """Async order return push"""
        print(f"[Async Order Response] Account:{response.account_id} OrderID:{response.order_id} Seq:{response.seq}")
        
    def on_account_status(self, status):
        """Account status push"""
        print(f"[Account Status] Account:{status.account_id} Type:{status.account_type} Status:{status.status}")


class BaseTrader:
    """
    Base Trader Class
    
    Usage:
        trader = BaseTrader(
            path=r'D:\国金证券QMT交易端\userdata_mini',
            account='8886063599', 
            session_id=123456
        )
        trader.connect()
        
        # Buy stock
        order_id = trader.buy('512710.SH', 100, 0.661)
        
        # Query positions
        positions = trader.get_positions()
    """
    
    def __init__(self, path: str, account: str, session_id: int = 123456):
        """
        Initialize trading interface
        
        Parameters:
        -----------
        path : str
            QMT user data path, e.g. r'D:\国金证券QMT交易端\userdata_mini'
        account : str
            Account number, e.g. '8886063599'
        session_id : int
            Session ID, different strategies use different session IDs, default 123456
        """
        self.path = path
        self.account = account
        self.session_id = session_id
        
        # Create stock account object
        self.stock_account = StockAccount(account, "STOCK")
        
        # Create XtQuantTrader instance
        self.xt_trader = XtQuantTrader(path, session_id)
        
        # Connection status
        self._connected = False
        
        # Callback object
        self.callback = None
        
    def connect(self) -> int:
        """
        Connect to trading system
        
        Returns:
        --------
        int
            Connection result, 0 means success
        """
        # Start trading thread
        self.xt_trader.start()
        
        # Establish trading connection
        connect_result = self.xt_trader.connect()
        
        if connect_result == 0:
            self._connected = True
            print(f"[BaseTrader] Connected successfully, account: {self.account}")
        else:
            print(f"[BaseTrader] Connection failed, error code: {connect_result}")
            
        return connect_result
    
    def subscribe(self) -> int:
        """
        Subscribe account information, receive trading push
        
        Returns:
        --------
        int
            Subscribe result, 0 means success
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
            return -1
            
        subscribe_result = self.xt_trader.subscribe(self.stock_account)
        
        if subscribe_result == 0:
            print(f"[BaseTrader] Subscribe successfully, account: {self.account}")
        else:
            print(f"[BaseTrader] Subscribe failed, error code: {subscribe_result}")
            
        return subscribe_result
    
    def register_callback(self, callback: XtQuantTraderCallback):
        """
        Register callback function
        
        Parameters:
        -----------
        callback : XtQuantTraderCallback
            Callback object
        """
        self.callback = callback
        self.xt_trader.register_callback(callback)
        print("[BaseTrader] Callback registered successfully")
    
    def buy(self, stock_code: str, volume: int, price: float,
            price_type: int = xtconstant.FIX_PRICE,
            strategy_name: str = "base_trader",
            order_remark: str = "") -> Optional[int]:
        """
        Buy stock
        
        Parameters:
        -----------
        stock_code : str
            Stock code, e.g. '600000.SH'
        volume : int
            Order volume (shares)
        price : float
            Order price
        price_type : int
            Price type, default limit price xtconstant.FIX_PRICE
        strategy_name : str
            Strategy name
        order_remark : str
            Order remark
            
        Returns:
        --------
        int
            Order ID, success returns positive integer, failure returns -1
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
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
            print(f"[BaseTrader] Buy order success: {stock_code} Volume={volume} Price={price} OrderID={order_id}")
        else:
            print(f"[BaseTrader] Buy order failed: {stock_code} Error code={order_id}")
            
        return order_id
    
    def sell(self, stock_code: str, volume: int, price: float,
             price_type: int = xtconstant.FIX_PRICE,
             strategy_name: str = "base_trader",
             order_remark: str = "") -> Optional[int]:
        """
        Sell stock
        
        Parameters:
        -----------
        stock_code : str
            Stock code, e.g. '600000.SH'
        volume : int
            Order volume (shares)
        price : float
            Order price
        price_type : int
            Price type, default limit price xtconstant.FIX_PRICE
        strategy_name : str
            Strategy name
        order_remark : str
            Order remark
            
        Returns:
        --------
        int
            Order ID, success returns positive integer, failure returns -1
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
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
            print(f"[BaseTrader] Sell order success: {stock_code} Volume={volume} Price={price} OrderID={order_id}")
        else:
            print(f"[BaseTrader] Sell order failed: {stock_code} Error code={order_id}")
            
        return order_id
    
    def buy_async(self, stock_code: str, volume: int, price: float,
                  price_type: int = xtconstant.FIX_PRICE,
                  strategy_name: str = "base_trader",
                  order_remark: str = "") -> Optional[int]:
        """
        Async buy stock
        
        Returns:
        --------
        int
            Order request sequence number, can correspond with async callback
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
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
        
        print(f"[BaseTrader] Async buy request: {stock_code} Volume={volume} Price={price} Seq={seq}")
        return seq
    
    def cancel_order(self, order_id: int) -> int:
        """
        Cancel order
        
        Parameters:
        -----------
        order_id : int
            Order ID
            
        Returns:
        --------
        int
            Cancel result, 0 means success
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
            return -1
            
        result = self.xt_trader.cancel_order_stock(self.stock_account, order_id)
        
        if result == 0:
            print(f"[BaseTrader] Cancel order success: OrderID={order_id}")
        else:
            print(f"[BaseTrader] Cancel order failed: OrderID={order_id} Error code={result}")
            
        return result
    
    def get_asset(self) -> Optional[Dict]:
        """
        Query stock asset
        
        Returns:
        --------
        Dict
            Asset information, contains cash and other fields
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
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
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        """
        Query order by order ID
        
        Parameters:
        -----------
        order_id : int
            Order ID
            
        Returns:
        --------
        Dict
            Order information
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
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
            print(f"[BaseTrader] Query order failed: OrderID={order_id}")
            return None
    
    def get_orders(self) -> List[Dict]:
        """
        Query all orders of the day
        
        Returns:
        --------
        List[Dict]
            Order list
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
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
                
        print(f"[BaseTrader] Found {len(orders_list)} order records")
        return orders_list
    
    def get_trades(self) -> List[Dict]:
        """
        Query all trades of the day
        
        Returns:
        --------
        List[Dict]
            Trade list
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
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
                
        print(f"[BaseTrader] Found {len(trades_list)} trade records")
        return trades_list
    
    def get_positions(self) -> List[Dict]:
        """
        Query all positions of the day
        
        Returns:
        --------
        List[Dict]
            Position list
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
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
                
        print(f"[BaseTrader] Found {len(positions_list)} position records")
        return positions_list
    
    def get_position(self, stock_code: str) -> Optional[Dict]:
        """
        Query position by stock code
        
        Parameters:
        -----------
        stock_code : str
            Stock code
            
        Returns:
        --------
        Dict
            Position information
        """
        if not self._connected:
            print("[BaseTrader] Please connect to trading system first")
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
            print(f"[BaseTrader] Query position failed: {stock_code}")
            return None
    
    def run_forever(self):
        """
        Block thread, receive trading push
        """
        print("[BaseTrader] Start receiving trading push...")
        self.xt_trader.run_forever()
    
    def stop(self):
        """
        Stop trading thread
        """
        self.xt_trader.stop()
        self._connected = False
        print("[BaseTrader] Trading thread stopped")
