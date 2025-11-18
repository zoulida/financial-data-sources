"""
XtQuant 交易基础类
==================

基于 XtQuant.Xttrade 模块实现的交易基础类，提供完整的交易功能。

功能包括：
- 下单委托（同步/异步，返回成功/失败状态）
- 委托撤单
- 委托状态查询（全部/单个）
- 委托成交回报（回调）
- 成交查询
- 持仓查询（全部/单个）
- 资产查询（可用现金、总资产）

参考文档：http://dict.thinktrader.net/nativeApi/xttrader.html?id=nOY9mc
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import (
    StockAccount, XtAsset, XtOrder, XtTrade, XtPosition,
    XtOrderResponse, XtCancelOrderResponse, XtOrderError, XtCancelError
)

# 账号类型常量（根据XtQuant API文档）
# StockAccount 需要字符串类型
ACCOUNT_TYPE_STOCK = "STOCK"
ACCOUNT_TYPE_CREDIT = "CREDIT"
ACCOUNT_TYPE_FUTURES = "FUTURES"


class OrderStatus(Enum):
    """委托状态枚举"""
    UNKNOWN = "未知"
    SUBMITTED = "已报"
    PARTIAL_FILLED = "部成"
    FILLED = "已成"
    CANCELLED = "已撤"
    REJECTED = "已拒"
    PARTIAL_CANCELLED = "部撤"


@dataclass
class OrderResult:
    """下单结果"""
    success: bool
    order_id: Optional[str] = None
    order_sysid: Optional[str] = None
    error_id: Optional[int] = None
    error_msg: Optional[str] = None
    seq: Optional[int] = None


@dataclass
class CancelResult:
    """撤单结果"""
    success: bool
    error_id: Optional[int] = None
    error_msg: Optional[str] = None


class XtTraderCallbackImpl(XtQuantTraderCallback):
    """XtQuant 交易回调实现类"""
    
    def __init__(self, trader_base):
        """
        初始化回调类
        
        Parameters:
        -----------
        trader_base : XtTraderBase
            交易基础类实例，用于存储回调数据
        """
        super().__init__()
        self.trader_base = trader_base
    
    def on_disconnected(self):
        """连接状态回调"""
        print("[回调] 连接断开")
        self.trader_base._on_disconnected()
    
    def on_account_status(self, status):
        """账号状态信息推送"""
        print(f"[回调] 账号状态更新: {status.account_id}, 状态: {status.status}")
        self.trader_base._on_account_status(status)
    
    def on_stock_order(self, order):
        """委托信息推送"""
        print(f"[回调] 委托更新: {order.stock_code}, 状态: {order.order_status}, 系统ID: {order.order_sysid}")
        self.trader_base._on_stock_order(order)
    
    def on_stock_trade(self, trade):
        """成交信息推送"""
        print(f"[回调] 成交回报: {trade.stock_code}, 数量: {trade.traded_volume}, 价格: {trade.traded_price}")
        self.trader_base._on_stock_trade(trade)
    
    def on_order_error(self, order_error):
        """下单失败信息推送"""
        print(f"[回调] 下单失败: {order_error.order_id}, 错误ID: {order_error.error_id}, 错误信息: {order_error.error_msg}")
        self.trader_base._on_order_error(order_error)
    
    def on_cancel_error(self, cancel_error):
        """撤单失败信息推送"""
        print(f"[回调] 撤单失败: {cancel_error.order_id}, 错误ID: {cancel_error.error_id}, 错误信息: {cancel_error.error_msg}")
        self.trader_base._on_cancel_error(cancel_error)
    
    def on_order_stock_async_response(self, response):
        """异步下单回报推送"""
        print(f"[回调] 异步下单回报: 账号={response.account_id}, 委托ID={response.order_id}, 序列号={response.seq}")
        self.trader_base._on_order_stock_async_response(response)
    
    def on_smt_appointment_async_response(self, response):
        """约券相关异步接口的回报推送"""
        print(f"[回调] 约券回报: {response.account_id}, 系统ID={response.order_sysid}")
        self.trader_base._on_smt_appointment_async_response(response)


class XtTraderBase:
    """
    XtQuant 交易基础类
    
    提供完整的交易功能，包括下单、撤单、查询等。
    """
    
    def __init__(self, account_id: str, account_type: str = ACCOUNT_TYPE_STOCK, 
                 path: str = "", session: int = 0):
        """
        初始化交易基础类
        
        Parameters:
        -----------
        account_id : str
            资金账号，例如 '8886063599'
        account_type : str
            账号类型，默认为 ACCOUNT_TYPE_STOCK ("STOCK")
            可选值：
            - ACCOUNT_TYPE_STOCK ("STOCK"): 股票账号
            - ACCOUNT_TYPE_CREDIT ("CREDIT"): 信用账号
            - ACCOUNT_TYPE_FUTURES ("FUTURES"): 期货账号
        path : str
            策略路径，默认为空字符串
        session : int
            会话ID，默认为0
        """
        self.account_id = account_id
        self.account_type = account_type
        
        # 创建 StockAccount 对象
        self.account = StockAccount(account_id, account_type)
        
        # 创建交易API实例
        # XtQuantTrader 需要 path 和 session 参数
        self.trader = XtQuantTrader(path=path, session=session)
        
        # 创建回调类实例
        self.callback = XtTraderCallbackImpl(self)
        
        # 注册回调类
        self.trader.register_callback(self.callback)
        
        # 准备API环境
        self.trader.start()
        
        # 创建连接
        connect_result = self.trader.connect()
        if connect_result != 0:
            raise Exception(f"连接失败，错误码：{connect_result}，请检查 MiniQMT 是否已启动并登录")
        
        # 订阅账号信息（使用 subscribe 方法）
        self.trader.subscribe(self.account)
        
        # 存储回调数据
        self._orders: Dict[str, XtOrder] = {}  # 委托字典，key为order_id
        self._trades: List[XtTrade] = []  # 成交列表
        self._order_responses: Dict[str, XtOrderResponse] = {}  # 异步下单回报
        self._order_errors: Dict[str, XtOrderError] = {}  # 下单失败信息
        self._cancel_errors: Dict[str, XtCancelError] = {}  # 撤单失败信息
        self._account_status = None  # 账号状态
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 等待事件（用于同步等待委托回报）
        self._order_events: Dict[str, threading.Event] = {}
        self._order_results: Dict[str, OrderResult] = {}
        
        print(f"[交易类] 初始化完成，账号: {account_id}, 类型: {account_type}")
    
    def _on_disconnected(self):
        """连接断开回调"""
        with self._lock:
            print("[交易类] 连接已断开")
    
    def _on_account_status(self, status):
        """账号状态更新回调"""
        with self._lock:
            self._account_status = status
    
    def _on_stock_order(self, order):
        """委托信息推送回调"""
        with self._lock:
            self._orders[order.order_id] = order
            # 如果有等待该委托的事件，通知
            if order.order_id in self._order_events:
                self._order_events[order.order_id].set()
    
    def _on_stock_trade(self, trade):
        """成交信息推送回调"""
        with self._lock:
            self._trades.append(trade)
    
    def _on_order_error(self, order_error):
        """下单失败回调"""
        with self._lock:
            self._order_errors[order_error.order_id] = order_error
            # 如果有等待该委托的事件，通知
            if order_error.order_id in self._order_events:
                self._order_results[order_error.order_id] = OrderResult(
                    success=False,
                    order_id=order_error.order_id,
                    error_id=order_error.error_id,
                    error_msg=order_error.error_msg
                )
                self._order_events[order_error.order_id].set()
    
    def _on_cancel_error(self, cancel_error):
        """撤单失败回调"""
        with self._lock:
            self._cancel_errors[cancel_error.order_id] = cancel_error
    
    def _on_order_stock_async_response(self, response):
        """异步下单回报回调"""
        with self._lock:
            self._order_responses[response.order_id] = response
            # 如果有等待该委托的事件，通知
            if response.order_id in self._order_events:
                if response.error_id == 0:
                    self._order_results[response.order_id] = OrderResult(
                        success=True,
                        order_id=response.order_id,
                        order_sysid=response.order_sysid,
                        seq=response.seq
                    )
                else:
                    self._order_results[response.order_id] = OrderResult(
                        success=False,
                        order_id=response.order_id,
                        error_id=response.error_id,
                        error_msg=response.error_msg,
                        seq=response.seq
                    )
                self._order_events[response.order_id].set()
    
    def _on_smt_appointment_async_response(self, response):
        """约券回报回调"""
        with self._lock:
            print(f"[交易类] 约券回报: {response.account_id}")
    
    # ==================== 下单接口 ====================
    
    def order_stock_sync(self, stock_code: str, order_type: int, price_type: int, 
                        price: float, volume: int, strategy_name: str = "", 
                        order_remark: str = "") -> OrderResult:
        """
        股票同步报单
        
        Parameters:
        -----------
        stock_code : str
            证券代码，例如 '000001.SZ'
        order_type : int
            委托类型，例如 23 (买入) 或 24 (卖出)
        price_type : int
            报价类型，例如 4 (限价) 或 11 (市价)
        price : float
            委托价格（限价单必填，市价单可填0）
        volume : int
            委托数量（股数，100的整数倍）
        strategy_name : str
            策略名称
        order_remark : str
            委托备注
        
        Returns:
        --------
        OrderResult
            下单结果，包含成功/失败状态和相关信息
        """
        try:
            result = self.trader.order_stock(
                self.account,
                stock_code,
                order_type,
                price_type,
                price,
                volume,
                strategy_name,
                order_remark
            )
            
            if result is None:
                return OrderResult(success=False, error_msg="下单返回None，可能连接异常")
            
            # 解析返回结果
            if hasattr(result, 'order_id') and result.order_id:
                return OrderResult(
                    success=True,
                    order_id=result.order_id,
                    order_sysid=getattr(result, 'order_sysid', None)
                )
            else:
                return OrderResult(
                    success=False,
                    error_id=getattr(result, 'error_id', -1),
                    error_msg=getattr(result, 'error_msg', '未知错误')
                )
        except Exception as e:
            return OrderResult(success=False, error_msg=f"下单异常: {str(e)}")
    
    def order_stock_async(self, stock_code: str, order_type: int, price_type: int,
                         price: float, volume: int, strategy_name: str = "",
                         order_remark: str = "", timeout: float = 10.0) -> OrderResult:
        """
        股票异步报单（等待回报）
        
        Parameters:
        -----------
        stock_code : str
            证券代码
        order_type : int
            委托类型
        price_type : int
            报价类型
        price : float
            委托价格
        volume : int
            委托数量
        strategy_name : str
            策略名称
        order_remark : str
            委托备注
        timeout : float
            等待回报的超时时间（秒），默认10秒
        
        Returns:
        --------
        OrderResult
            下单结果
        """
        # 生成临时order_id用于等待
        import uuid
        temp_order_id = str(uuid.uuid4())
        
        # 创建等待事件
        event = threading.Event()
        with self._lock:
            self._order_events[temp_order_id] = event
            self._order_results[temp_order_id] = None
        
        try:
            # 异步下单
            result = self.trader.order_stock_async(
                self.account,
                stock_code,
                order_type,
                price_type,
                price,
                volume,
                strategy_name,
                order_remark
            )
            
            if result is None:
                with self._lock:
                    self._order_events.pop(temp_order_id, None)
                return OrderResult(success=False, error_msg="异步下单返回None")
            
            # 获取实际的order_id
            actual_order_id = result.order_id if hasattr(result, 'order_id') else None
            
            if actual_order_id:
                # 更新事件字典的key
                with self._lock:
                    if temp_order_id in self._order_events:
                        event = self._order_events.pop(temp_order_id)
                        self._order_events[actual_order_id] = event
                        self._order_results[actual_order_id] = None
                
                # 等待回报
                if event.wait(timeout):
                    with self._lock:
                        order_result = self._order_results.pop(actual_order_id, None)
                        self._order_events.pop(actual_order_id, None)
                        if order_result:
                            return order_result
                        else:
                            return OrderResult(
                                success=False,
                                order_id=actual_order_id,
                                error_msg="等待回报超时或未收到回报"
                            )
                else:
                    with self._lock:
                        self._order_events.pop(actual_order_id, None)
                        self._order_results.pop(actual_order_id, None)
                    return OrderResult(
                        success=False,
                        order_id=actual_order_id,
                        error_msg=f"等待回报超时（{timeout}秒）"
                    )
            else:
                with self._lock:
                    self._order_events.pop(temp_order_id, None)
                return OrderResult(
                    success=False,
                    error_id=getattr(result, 'error_id', -1),
                    error_msg=getattr(result, 'error_msg', '异步下单失败')
                )
        except Exception as e:
            with self._lock:
                self._order_events.pop(temp_order_id, None)
            return OrderResult(success=False, error_msg=f"异步下单异常: {str(e)}")
    
    # ==================== 撤单接口 ====================
    
    def cancel_order_stock_sync(self, order_id: str) -> CancelResult:
        """
        股票同步撤单
        
        Parameters:
        -----------
        order_id : str
            委托编号
        
        Returns:
        --------
        CancelResult
            撤单结果
        """
        try:
            result = self.trader.cancel_order_stock(self.account, order_id)
            
            if result is None:
                return CancelResult(success=False, error_msg="撤单返回None")
            
            if hasattr(result, 'error_id') and result.error_id == 0:
                return CancelResult(success=True)
            else:
                return CancelResult(
                    success=False,
                    error_id=getattr(result, 'error_id', -1),
                    error_msg=getattr(result, 'error_msg', '撤单失败')
                )
        except Exception as e:
            return CancelResult(success=False, error_msg=f"撤单异常: {str(e)}")
    
    def cancel_order_stock_async(self, order_id: str, timeout: float = 5.0) -> CancelResult:
        """
        股票异步撤单（等待回报）
        
        Parameters:
        -----------
        order_id : str
            委托编号
        timeout : float
            等待回报的超时时间（秒）
        
        Returns:
        --------
        CancelResult
            撤单结果
        """
        try:
            result = self.trader.cancel_order_stock_async(self.account, order_id)
            
            if result is None:
                return CancelResult(success=False, error_msg="异步撤单返回None")
            
            # 异步撤单通常立即返回，但需要等待回调确认
            # 这里简化处理，直接返回
            if hasattr(result, 'error_id') and result.error_id == 0:
                return CancelResult(success=True)
            else:
                return CancelResult(
                    success=False,
                    error_id=getattr(result, 'error_id', -1),
                    error_msg=getattr(result, 'error_msg', '异步撤单失败')
                )
        except Exception as e:
            return CancelResult(success=False, error_msg=f"异步撤单异常: {str(e)}")
    
    # ==================== 查询接口 ====================
    
    def query_stock_orders(self) -> List[XtOrder]:
        """
        查询所有委托状态
        
        Returns:
        --------
        List[XtOrder]
            委托列表
        """
        try:
            orders = self.trader.query_stock_orders(self.account)
            if orders is None:
                return []
            return list(orders) if isinstance(orders, (list, tuple)) else [orders]
        except Exception as e:
            print(f"查询委托异常: {e}")
            return []
    
    def query_stock_order(self, order_id: str) -> Optional[XtOrder]:
        """
        查询单个委托状态
        
        Parameters:
        -----------
        order_id : str
            委托编号
        
        Returns:
        --------
        Optional[XtOrder]
            委托信息，如果不存在返回None
        """
        orders = self.query_stock_orders()
        for order in orders:
            if order.order_id == order_id:
                return order
        return None
    
    def query_stock_trades(self) -> List[XtTrade]:
        """
        查询所有成交
        
        Returns:
        --------
        List[XtTrade]
            成交列表
        """
        try:
            trades = self.trader.query_stock_trades(self.account)
            if trades is None:
                return []
            return list(trades) if isinstance(trades, (list, tuple)) else [trades]
        except Exception as e:
            print(f"查询成交异常: {e}")
            return []
    
    def query_stock_asset(self) -> Optional[XtAsset]:
        """
        查询资产信息（包含可用现金和总资产）
        
        Returns:
        --------
        Optional[XtAsset]
            资产信息
        """
        try:
            asset = self.trader.query_stock_asset(self.account)
            return asset
        except Exception as e:
            print(f"查询资产异常: {e}")
            return None
    
    def get_available_cash(self) -> float:
        """
        查询当前可用现金
        
        Returns:
        --------
        float
            可用现金
        """
        asset = self.query_stock_asset()
        if asset:
            # XtAsset 使用 m_dCash 属性
            return getattr(asset, 'm_dCash', getattr(asset, 'cash', 0.0))
        return 0.0
    
    def get_total_asset(self) -> float:
        """
        查询当前总资产
        
        Returns:
        --------
        float
            总资产
        """
        asset = self.query_stock_asset()
        if asset:
            # XtAsset 使用 m_dTotalAsset 属性
            return getattr(asset, 'm_dTotalAsset', getattr(asset, 'total_asset', 0.0))
        return 0.0
    
    def query_stock_positions(self) -> List[XtPosition]:
        """
        查询当前所有持仓
        
        Returns:
        --------
        List[XtPosition]
            持仓列表
        """
        try:
            positions = self.trader.query_stock_positions(self.account)
            if positions is None:
                return []
            return list(positions) if isinstance(positions, (list, tuple)) else [positions]
        except Exception as e:
            print(f"查询持仓异常: {e}")
            return []
    
    def query_stock_position(self, stock_code: str) -> Optional[XtPosition]:
        """
        查询单个证券持仓
        
        Parameters:
        -----------
        stock_code : str
            证券代码
        
        Returns:
        --------
        Optional[XtPosition]
            持仓信息，如果不存在返回None
        """
        positions = self.query_stock_positions()
        for pos in positions:
            if pos.stock_code == stock_code:
                return pos
        return None
    
    # ==================== 工具方法 ====================
    
    def wait_for_order_response(self, order_id: str, timeout: float = 10.0) -> Optional[OrderResult]:
        """
        等待指定委托的回报
        
        Parameters:
        -----------
        order_id : str
            委托编号
        timeout : float
            超时时间（秒）
        
        Returns:
        --------
        Optional[OrderResult]
            委托结果，如果超时返回None
        """
        event = threading.Event()
        with self._lock:
            self._order_events[order_id] = event
        
        if event.wait(timeout):
            with self._lock:
                result = self._order_results.pop(order_id, None)
                self._order_events.pop(order_id, None)
                return result
        else:
            with self._lock:
                self._order_events.pop(order_id, None)
            return None
    
    def stop(self):
        """停止交易API"""
        try:
            if hasattr(self, 'trader') and self.trader is not None:
                self.trader.stop()
                print("[交易类] 交易API已停止")
        except Exception as e:
            print(f"[交易类] 停止API异常: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.stop()
        except:
            pass  # 忽略析构时的异常

