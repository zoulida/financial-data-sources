"""
数据获取模块
============

集成Wind API和模拟数据，为妖股因子计算提供数据支持。
优先使用Wind API获取真实数据，获取不到则使用模拟数据。

数据获取优先级：
1. 优先使用 XtQuant (xtdata) - 行情数据
2. 财务数据使用 Wind API
3. 获取不到数据则使用模拟数据
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
import warnings
warnings.filterwarnings('ignore')

# 尝试导入Wind API
try:
    import WindPy as w
    WIND_AVAILABLE = True
except ImportError:
    WIND_AVAILABLE = False
    print("警告：Wind API未安装，将使用模拟数据")

# 尝试导入XtQuant
try:
    from xtquant import xtdata
    XTQUANT_AVAILABLE = True
except ImportError:
    XTQUANT_AVAILABLE = False
    print("警告：XtQuant未安装，将使用模拟数据")


class MonsterStockDataFetcher:
    """妖股数据获取器"""
    
    def __init__(self, 
                 wind_token: Optional[str] = None,
                 xtquant_token: Optional[str] = None,
                 use_mock_data: bool = False):
        """
        初始化数据获取器
        
        Parameters:
        -----------
        wind_token : str, optional
            Wind API token
        xtquant_token : str, optional
            XtQuant API token
        use_mock_data : bool
            是否强制使用模拟数据
        """
        self.wind_token = wind_token
        self.xtquant_token = xtquant_token
        self.use_mock_data = use_mock_data
        
        # 初始化API
        self.wind_initialized = False
        self.xtquant_initialized = False
        
        if not use_mock_data:
            self._initialize_apis()
    
    def _initialize_apis(self):
        """初始化API"""
        # 初始化Wind API
        if WIND_AVAILABLE and self.wind_token:
            try:
                w.start()
                self.wind_initialized = True
                print("Wind API初始化成功")
            except Exception as e:
                print(f"Wind API初始化失败: {e}")
        
        # 初始化XtQuant API
        if XTQUANT_AVAILABLE and self.xtquant_token:
            try:
                xtdata.set_token(self.xtquant_token)
                self.xtquant_initialized = True
                print("XtQuant API初始化成功")
            except Exception as e:
                print(f"XtQuant API初始化失败: {e}")
    
    def fetch_stock_data(self, 
                        stock_code: str,
                        start_date: str,
                        end_date: str,
                        fields: List[str] = None) -> pd.DataFrame:
        """
        获取股票数据
        
        Parameters:
        -----------
        stock_code : str
            股票代码，如'000001.SZ'
        start_date : str
            开始日期，格式'YYYYMMDD'
        end_date : str
            结束日期，格式'YYYYMMDD'
        fields : list, optional
            需要获取的字段列表
            
        Returns:
        --------
        pd.DataFrame : 股票数据
        """
        if self.use_mock_data or not (self.wind_initialized or self.xtquant_initialized):
            return self._generate_mock_stock_data(stock_code, start_date, end_date, fields)
        
        # 优先使用XtQuant获取行情数据
        if self.xtquant_initialized and fields and self._is_market_data_fields(fields):
            try:
                return self._fetch_xtquant_data(stock_code, start_date, end_date, fields)
            except Exception as e:
                print(f"XtQuant数据获取失败: {e}")
        
        # 使用Wind API
        if self.wind_initialized and fields:
            try:
                return self._fetch_wind_data(stock_code, start_date, end_date, fields)
            except Exception as e:
                print(f"Wind数据获取失败: {e}")
        
        # 都失败了，使用模拟数据
        print("所有API都失败，使用模拟数据")
        return self._generate_mock_stock_data(stock_code, start_date, end_date, fields)
    
    def _is_market_data_fields(self, fields: List[str]) -> bool:
        """判断是否为行情数据字段"""
        if fields is None:
            return False
        market_fields = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover']
        return any(field in market_fields for field in fields)
    
    def _fetch_xtquant_data(self, stock_code: str, start_date: str, end_date: str, fields: List[str]) -> pd.DataFrame:
        """使用XtQuant获取数据"""
        # 转换字段名
        xtquant_fields = self._convert_to_xtquant_fields(fields)
        
        # 获取数据
        data = xtdata.get_market_data_ex(
            field_list=xtquant_fields,
            stock_list=[stock_code],
            period='1d',
            start_time=start_date,
            end_time=end_date
        )
        
        if data.ErrorCode != 0:
            raise Exception(f"XtQuant数据获取失败: {data.ErrorCode}")
        
        # 转换为DataFrame
        df = pd.DataFrame()
        for field in xtquant_fields:
            if field in data and len(data[field]) > 0:
                df[field] = data[field][stock_code]
        
        df.index = pd.to_datetime(df.index)
        df.index.name = 'Date'
        
        return df
    
    def _fetch_wind_data(self, stock_code: str, start_date: str, end_date: str, fields: List[str]) -> pd.DataFrame:
        """使用Wind API获取数据"""
        # 转换字段名
        wind_fields = self._convert_to_wind_fields(fields)
        
        # 获取数据
        data = w.wsd(
            codes=stock_code,
            fields=','.join(wind_fields),
            beginTime=start_date,
            endTime=end_date,
            options="Days=Trading"
        )
        
        if data.ErrorCode != 0:
            raise Exception(f"Wind数据获取失败: {data.ErrorCode}")
        
        # 转换为DataFrame
        df = pd.DataFrame(data.Data, columns=data.Fields, index=data.Times)
        df.index.name = 'Date'
        
        return df
    
    def _convert_to_xtquant_fields(self, fields: List[str]) -> List[str]:
        """转换字段名为XtQuant格式"""
        if fields is None:
            return []
        field_mapping = {
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'amount',
            'turnover': 'turnover',
            'pct_chg': 'pct_chg'
        }
        
        return [field_mapping.get(field, field) for field in fields if field in field_mapping]
    
    def _convert_to_wind_fields(self, fields: List[str]) -> List[str]:
        """转换字段名为Wind格式"""
        if fields is None:
            return []
        field_mapping = {
            'open': 'open',
            'high': 'high',
            'low': 'low', 
            'close': 'close',
            'volume': 'volume',
            'amount': 'amt',
            'turnover': 'turn',
            'pct_chg': 'pct_chg'
        }
        
        return [field_mapping.get(field, field) for field in fields if field in field_mapping]
    
    def _generate_mock_stock_data(self, stock_code: str, start_date: str, end_date: str, fields: List[str]) -> pd.DataFrame:
        """生成模拟股票数据"""
        # 生成日期序列
        dates = pd.date_range(start_date, end_date, freq='D')
        # 过滤掉周末
        dates = dates[dates.weekday < 5]
        
        np.random.seed(hash(stock_code) % 2**32)
        
        # 基础价格
        base_price = 10.0 + (hash(stock_code) % 100) / 10.0
        
        # 生成价格数据
        returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
        prices = base_price * np.exp(np.cumsum(returns))
        
        # 生成OHLCV数据
        data = {}
        
        if 'close' in fields:
            data['close'] = prices
        
        if 'open' in fields:
            # 开盘价基于前一日收盘价
            data['open'] = np.roll(prices, 1) * (1 + np.random.normal(0, 0.005, len(dates)))
            data['open'][0] = prices[0]
        
        if 'high' in fields:
            # 最高价
            data['high'] = np.maximum(data.get('open', prices), prices) * (1 + np.abs(np.random.normal(0, 0.01, len(dates))))
        
        if 'low' in fields:
            # 最低价
            data['low'] = np.minimum(data.get('open', prices), prices) * (1 - np.abs(np.random.normal(0, 0.01, len(dates))))
        
        if 'volume' in fields:
            # 成交量
            base_volume = 1000000 + (hash(stock_code) % 10000000)
            data['volume'] = base_volume * (1 + np.abs(returns) * 10) * np.random.uniform(0.5, 2, len(dates))
        
        if 'amount' in fields:
            # 成交额
            data['amount'] = data.get('volume', np.random.uniform(1000000, 10000000, len(dates))) * prices
        
        if 'turnover' in fields:
            # 换手率
            data['turnover'] = np.random.uniform(1, 10, len(dates))
        
        if 'pct_chg' in fields:
            # 涨跌幅
            data['pct_chg'] = returns * 100
        
        # 创建DataFrame
        df = pd.DataFrame(data, index=dates)
        df.index.name = 'Date'
        
        return df
    
    def fetch_financial_data(self, 
                            stock_codes: List[str],
                            fields: List[str],
                            trade_date: str = None) -> pd.DataFrame:
        """
        获取财务数据
        
        Parameters:
        -----------
        stock_codes : list
            股票代码列表
        fields : list
            财务字段列表
        trade_date : str, optional
            交易日期，格式'YYYYMMDD'
            
        Returns:
        --------
        pd.DataFrame : 财务数据
        """
        if self.use_mock_data or not self.wind_initialized:
            return self._generate_mock_financial_data(stock_codes, fields, trade_date)
        
        try:
            return self._fetch_wind_financial_data(stock_codes, fields, trade_date)
        except Exception as e:
            print(f"Wind财务数据获取失败: {e}")
            return self._generate_mock_financial_data(stock_codes, fields, trade_date)
    
    def _fetch_wind_financial_data(self, stock_codes: List[str], fields: List[str], trade_date: str) -> pd.DataFrame:
        """使用Wind API获取财务数据"""
        # 转换字段名
        wind_fields = self._convert_financial_to_wind_fields(fields)
        
        # 获取数据
        data = w.wss(
            codes=stock_codes,
            fields=','.join(wind_fields),
            options=f"tradeDate={trade_date}" if trade_date else ""
        )
        
        if data.ErrorCode != 0:
            raise Exception(f"Wind财务数据获取失败: {data.ErrorCode}")
        
        # 转换为DataFrame
        df = pd.DataFrame(data.Data, columns=data.Fields, index=data.Codes)
        df.index.name = 'Code'
        
        return df
    
    def _convert_financial_to_wind_fields(self, fields: List[str]) -> List[str]:
        """转换财务字段名为Wind格式"""
        if fields is None:
            return []
        field_mapping = {
            'market_cap': 'val_mv_ARD',
            'pe_ttm': 'pe_ttm',
            'pb_mrq': 'pb_mrq',
            'ps_ttm': 'ps_ttm',
            'industry': 'industry_sw',
            'beta': 'beta_252d'
        }
        
        return [field_mapping.get(field, field) for field in fields if field in field_mapping]
    
    def _generate_mock_financial_data(self, stock_codes: List[str], fields: List[str], trade_date: str) -> pd.DataFrame:
        """生成模拟财务数据"""
        np.random.seed(42)
        
        data = {}
        
        for field in fields:
            if field == 'market_cap':
                # 市值：对数正态分布
                data[field] = np.exp(np.random.normal(9, 1, len(stock_codes))) * 1e8
            elif field == 'pe_ttm':
                # 市盈率：正态分布
                data[field] = np.random.normal(20, 10, len(stock_codes))
                data[field] = np.clip(data[field], 5, 100)
            elif field == 'pb_mrq':
                # 市净率：正态分布
                data[field] = np.random.normal(2, 1, len(stock_codes))
                data[field] = np.clip(data[field], 0.5, 10)
            elif field == 'ps_ttm':
                # 市销率：正态分布
                data[field] = np.random.normal(3, 2, len(stock_codes))
                data[field] = np.clip(data[field], 0.5, 20)
            elif field == 'industry':
                # 行业：随机选择
                industries = ['银行', '地产', '科技', '医药', '消费', '制造', '能源', '金融']
                data[field] = np.random.choice(industries, len(stock_codes))
            elif field == 'beta':
                # Beta：正态分布
                data[field] = np.random.normal(1.0, 0.3, len(stock_codes))
                data[field] = np.clip(data[field], 0.3, 2.5)
            else:
                # 其他字段：随机数
                data[field] = np.random.normal(0, 1, len(stock_codes))
        
        # 创建DataFrame
        df = pd.DataFrame(data, index=stock_codes)
        df.index.name = 'Code'
        
        return df
    
    def fetch_market_data(self, 
                         start_date: str,
                         end_date: str,
                         market_index: str = '000300.SH') -> pd.DataFrame:
        """
        获取市场数据
        
        Parameters:
        -----------
        start_date : str
            开始日期
        end_date : str
            结束日期
        market_index : str
            市场指数代码
            
        Returns:
        --------
        pd.DataFrame : 市场数据
        """
        return self.fetch_stock_data(market_index, start_date, end_date, 
                                   ['open', 'high', 'low', 'close', 'volume', 'amount'])
    
    def close_apis(self):
        """关闭API连接"""
        if self.wind_initialized and WIND_AVAILABLE:
            try:
                w.stop()
                print("Wind API已关闭")
            except:
                pass
        
        # XtQuant不需要显式关闭
        if self.xtquant_initialized:
            print("XtQuant API已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close_apis()


# 使用示例
if __name__ == "__main__":
    # 创建数据获取器
    with MonsterStockDataFetcher(use_mock_data=True) as fetcher:
        # 获取股票数据
        print("获取股票数据...")
        stock_data = fetcher.fetch_stock_data(
            stock_code='000001.SZ',
            start_date='20240101',
            end_date='20241231',
            fields=['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover']
        )
        
        print(f"股票数据形状: {stock_data.shape}")
        print("\n前5行数据:")
        print(stock_data.head())
        
        # 获取财务数据
        print("\n获取财务数据...")
        financial_data = fetcher.fetch_financial_data(
            stock_codes=['000001.SZ', '000002.SZ', '600000.SH'],
            fields=['market_cap', 'pe_ttm', 'pb_mrq', 'industry', 'beta'],
            trade_date='20241201'
        )
        
        print(f"财务数据形状: {financial_data.shape}")
        print("\n财务数据:")
        print(financial_data)
        
        # 获取市场数据
        print("\n获取市场数据...")
        market_data = fetcher.fetch_market_data(
            start_date='20240101',
            end_date='20241231'
        )
        
        print(f"市场数据形状: {market_data.shape}")
        print("\n前5行市场数据:")
        print(market_data.head())
