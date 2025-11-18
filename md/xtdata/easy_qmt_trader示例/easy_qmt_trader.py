"""
Easy QMT Trader - 简化的 XtQuant 交易接口封装
===============================================

提供更简单的接口来使用 XtQuant 进行交易。
"""

from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount
from xtquant import xtconstant


class easy_qmt_trader:
    """
    简化的 QMT 交易接口
    
    使用示例:
        trader = easy_qmt_trader(
            path=r'D:\\国金QMT\\userdata_mini',
            account='55009640',
            session_id=123456
        )
        trader.connect()
    """
    
    def __init__(self, path: str, account: str, session_id: int = 0):
        """
        初始化交易接口
        
        Parameters:
        -----------
        path : str
            QMT 用户数据路径，例如 r'D:\\国金QMT\\userdata_mini'
        account : str
            资金账号，例如 '55009640'
        session_id : int
            会话ID，默认为 0
        """
        self.path = path
        self.account = account
        self.session_id = session_id
        
        # 创建 StockAccount 对象
        self.stock_account = StockAccount(account, "STOCK")
        
        # 创建 XtQuantTrader 实例
        self.xt_trader = XtQuantTrader(path=path, session=session_id)
        
        # 连接状态
        self._connected = False
    
    def connect(self):
        """
        连接到 QMT 交易系统
        
        Returns:
        --------
        int
            连接结果，0 表示成功
        """
        # 启动交易接口
        self.xt_trader.start()
        
        # 连接
        result = self.xt_trader.connect()
        
        if result == 0:
            self._connected = True
            # 订阅账号
            self.xt_trader.subscribe(self.stock_account)
            print(f"[EasyQMT] 连接成功，账号: {self.account}")
        else:
            print(f"[EasyQMT] 连接失败，错误码: {result}")
        
        return result
    
    def buy(
        self,
        stock_code: str,
        volume: int,
        price: float,
        price_type: int = xtconstant.FIX_PRICE,
        strategy_name: str = "easy_qmt",
        order_remark: str = "",
    ):
        """
        买入股票
        
        Parameters:
        -----------
        stock_code : str
            股票代码，例如 '600031.SH'
        volume : int
            买入数量（股数）
        price : float
            买入价格
        
        Returns:
        --------
        str
            委托ID，如果失败返回 None
        """
        if not self._connected:
            print("[EasyQMT] 错误: 未连接，请先调用 connect()")
            return None
        
        order_id = self.xt_trader.order_stock(
            self.stock_account,
            stock_code,
            xtconstant.STOCK_BUY,  # 买入
            volume,
            price_type,
            price,
            strategy_name,
            order_remark or stock_code,
        )
        
        if order_id:
            print(f"[EasyQMT] 买入委托已提交: {stock_code}, 数量={volume}, 价格={price}, 委托ID={order_id}")
        else:
            print(f"[EasyQMT] 买入委托失败: {stock_code}")
        
        return order_id
    
    def sell(
        self,
        stock_code: str,
        volume: int,
        price: float,
        price_type: int = xtconstant.FIX_PRICE,
        strategy_name: str = "easy_qmt",
        order_remark: str = "",
    ):
        """
        卖出股票
        
        Parameters:
        -----------
        stock_code : str
            股票代码，例如 '600031.SH'
        volume : int
            卖出数量（股数）
        price : float
            卖出价格
        
        Returns:
        --------
        str
            委托ID，如果失败返回 None
        """
        if not self._connected:
            print("[EasyQMT] 错误: 未连接，请先调用 connect()")
            return None
        
        order_id = self.xt_trader.order_stock(
            self.stock_account,
            stock_code,
            xtconstant.STOCK_SELL,  # 卖出
            volume,
            price_type,
            price,
            strategy_name,
            order_remark or stock_code,
        )
        
        if order_id:
            print(f"[EasyQMT] 卖出委托已提交: {stock_code}, 数量={volume}, 价格={price}, 委托ID={order_id}")
        else:
            print(f"[EasyQMT] 卖出委托失败: {stock_code}")
        
        return order_id

