"""
Easy QMT Trader - 简化的 XtQuant 交易接口封装
===============================================

提供更简单的接口来使用 XtQuant 进行交易。
"""

from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import pandas as pd


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
        # 同步缓存
        self.latest_positions = pd.DataFrame()
        self.latest_orders = pd.DataFrame()
        self.latest_assets = pd.DataFrame()
        self.latest_available_cash = None

    def _ensure_connected(self):
        if not self._connected:
            print("[EasyQMT] 错误: 未连接，请先调用 connect()")
            return False
        return True
    
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

    def sync_positions(self):
        """
        同步仓位信息，返回 DataFrame 形式的最新持仓快照。
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        positions = self.xt_trader.query_stock_positions(self.stock_account)
        records = []
        if positions:
            for item in positions:
                records.append(
                    {
                        "账号类型": item.account_type,
                        "资金账号": item.account_id,
                        "证券代码": item.stock_code,
                        "股票余额": item.volume,
                        "可用余额": item.can_use_volume,
                        "成本价": item.open_price,
                        "市值": item.market_value,
                    }
                )
        self.latest_positions = pd.DataFrame(records)
        if self.latest_positions.empty:
            print("[EasyQMT] 当前无持仓数据")
        return self.latest_positions

    def sync_orders(self):
        """
        同步当日委托信息，返回 DataFrame。
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        orders = self.xt_trader.query_stock_orders(self.stock_account)
        records = []
        if orders:
            for order in orders:
                records.append(
                    {
                        "账号类型": order.account_type,
                        "资金账号": order.account_id,
                        "证券代码": order.stock_code,
                        "订单编号": order.order_id,
                        "委托类型": order.order_type,
                        "委托数量": order.order_volume,
                        "成交数量": order.traded_volume,
                        "委托价格": order.price,
                        "委托状态": order.order_status,
                        "策略名称": order.strategy_name,
                        "备注": order.order_remark,
                    }
                )
        self.latest_orders = pd.DataFrame(records)
        if self.latest_orders.empty:
            print("[EasyQMT] 当前无委托数据")
        return self.latest_orders

    def sync_fund(self):
        """
        同步账户资金信息（含可用/冻结/总资产等），返回 DataFrame。
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        asset = self.xt_trader.query_stock_asset(account=self.stock_account)
        if asset:
            data = {
                "账号类型": [asset.account_type],
                "资金账户": [asset.account_id],
                "可用金额": [asset.cash],
                "冻结金额": [asset.frozen_cash],
                "持仓市值": [asset.market_value],
                "总资产": [asset.total_asset],
            }
            self.latest_assets = pd.DataFrame(data)
        else:
            self.latest_assets = pd.DataFrame()
            print("[EasyQMT] 获取资金信息失败")
        return self.latest_assets

    def sync_available_cash(self):
        """
        同步可用资金数值，返回 float。
        """
        assets = self.sync_fund()
        if assets.empty:
            self.latest_available_cash = None
        else:
            self.latest_available_cash = float(assets.loc[0, "可用金额"])
        return self.latest_available_cash
    
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

