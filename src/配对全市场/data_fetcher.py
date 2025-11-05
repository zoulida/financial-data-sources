"""
数据获取模块

使用Wind API获取股票、ETF、可转债的列表和历史价格数据。
支持缓存机制，避免重复获取。
"""

import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from WindPy import w
from tqdm import tqdm

# 添加 zldtools 路径
TOOLS_PATH = Path(r"D:\pythonworkspace\zldtools")
if TOOLS_PATH.exists() and str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

# 添加项目根目录路径（用于导入合并下载数据和get_date_range）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.shelveTool import shelve_me_week
from tools.tradeCal import getLastOpenDay

from config import Config

# 先定义logger，然后再使用
logger = logging.getLogger(__name__)

# 导入合并下载数据模块
try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayDataWithTimeout
    GET_DAY_DATA_AVAILABLE = True
except ImportError:
    logger.warning("无法导入合并下载数据模块，将使用Wind API获取价格数据")
    getDayDataWithTimeout = None
    GET_DAY_DATA_AVAILABLE = False

# 导入日期范围获取工具
try:
    from md.获取enddate.get_date_range import get_date_range
    GET_DATE_RANGE_AVAILABLE = True
except ImportError:
    logger.warning("无法导入get_date_range模块，将使用默认日期计算方式")
    get_date_range = None
    GET_DATE_RANGE_AVAILABLE = False


# ==================== 缓存函数（使用shelve装饰器） ====================

@shelve_me_week
def _fetch_stock_universe_with_marketcap() -> pd.DataFrame:
    """
    获取股票池并附带市值和名称（带缓存）
    使用Wind板块成分股功能获取A股全部股票
    
    Returns:
        包含代码、名称、市值的DataFrame
    """
    # 启动Wind连接
    w.start()
    
    logger.info("正在从Wind获取A股全部股票...")
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 获取A股全部股票（板块ID: a001010100000000）
    data = w.wset("sectorconstituent", f"date={today};sectorid=a001010100000000")
    
    if data.ErrorCode != 0:
        raise Exception(f"Wind API错误: ErrorCode={data.ErrorCode}")
    
    # 构建DataFrame (Data[1]是代码, Data[2]是名称)
    df = pd.DataFrame({
        'code': data.Data[1],
        'name': data.Data[2]
    })
    
    logger.info(f"获取到 {len(df)} 只A股，正在查询市值...")
    
    # 获取市值（使用昨天的日期，今天的数据可能未更新）
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    codes = df['code'].tolist()
    
    # 分批查询市值（每批500只）
    batch_size = 500
    market_caps = []
    
    # 计算批次数量
    num_batches = (len(codes) + batch_size - 1) // batch_size
    
    for i in tqdm(range(0, len(codes), batch_size), desc="查询股票市值", total=num_batches, unit="批"):
        batch_codes = codes[i:i+batch_size]
        
        cap_data = w.wss(
            batch_codes,
            "mkt_cap_ard",
            f"unit=1;tradeDate={yesterday}"
        )
        
        if cap_data.ErrorCode == 0:
            # mkt_cap_ard返回的市值单位为元，无需转换
            market_caps.extend(cap_data.Data[0])
        else:
            logger.warning(f"查询第 {i//batch_size + 1} 批失败")
            market_caps.extend([np.nan] * len(batch_codes))
    
    df['market_cap'] = market_caps
    
    # 删除市值为空的记录
    result_df = df.dropna(subset=['market_cap'])
    
    # 按市值排序
    result_df = result_df.sort_values('market_cap', ascending=False).reset_index(drop=True)
    
    logger.info(f"获取到 {len(result_df)} 只股票的市值数据")
    
    return result_df


@shelve_me_week
def _fetch_etf_universe() -> pd.DataFrame:
    """
    获取基金池（带缓存）
    使用Wind板块成分股功能获取全部基金
    
    Returns:
        包含基金代码、名称、日均成交额的DataFrame
    """
    w.start()
    
    logger.info("开始获取基金池数据...")
    
    # 获取所有基金（板块ID: 1000052032000000）
    today = datetime.now().strftime('%Y-%m-%d')
    data = w.wset("sectorconstituent", f"date={today};sectorid=1000052032000000")
    
    if data.ErrorCode != 0:
        raise Exception(f"Wind API错误: ErrorCode={data.ErrorCode}")
    
    # 构建DataFrame (Data[1]是代码, Data[2]是名称)
    df = pd.DataFrame({
        'code': data.Data[1],
        'name': data.Data[2]
    })
    
    logger.info(f"获取到 {len(df)} 只基金，正在查询成交额...")
    
    # 获取上个交易日
    last_trade_day = getLastOpenDay(datetime.now().strftime('%Y%m%d'))
    # 转换为带横杠的格式
    last_trade_day_fmt = f"{last_trade_day[:4]}-{last_trade_day[4:6]}-{last_trade_day[6:]}"
    
    codes = df['code'].tolist()
    
    # 分批查询（每批100只，wsd对批量查询有限制）
    batch_size = 100
    avg_amounts = []
    
    # 计算批次数量
    num_batches = (len(codes) + batch_size - 1) // batch_size
    
    for i in tqdm(range(0, len(codes), batch_size), desc="查询基金成交额", total=num_batches, unit="批"):
        batch_codes = codes[i:i+batch_size]
        
        # 使用wsd获取单日成交额
        amt_data = w.wsd(
            ",".join(batch_codes),
            "amt",
            last_trade_day_fmt,
            last_trade_day_fmt,
            "unit=1"
        )
        
        if amt_data.ErrorCode == 0:
            # wsd返回的Data[0]是amt字段的所有基金数据（单位：元）
            avg_amounts.extend(amt_data.Data[0])
        else:
            logger.warning(f"查询第 {i//batch_size + 1} 批失败")
            avg_amounts.extend([np.nan] * len(batch_codes))
    
    df['avg_amount'] = avg_amounts
    
    logger.info(f"基金数据获取完成")
    
    return df


@shelve_me_week
def _fetch_convertible_bond_universe() -> pd.DataFrame:
    """
    获取可转债池（带缓存）
    使用Wind板块成分股功能获取全部可转债
    
    Returns:
        包含可转债代码、名称、剩余规模、日均成交额的DataFrame
    """
    w.start()
    
    logger.info("开始获取可转债池数据...")
    
    # 获取所有可转债（板块ID: 1000073208000000）
    today = datetime.now().strftime('%Y-%m-%d')
    data = w.wset("sectorconstituent", f"date={today};sectorid=1000073208000000")
    
    if data.ErrorCode != 0:
        raise Exception(f"Wind API错误: ErrorCode={data.ErrorCode}")
    
    # 构建DataFrame (Data[1]是代码, Data[2]是名称)
    df = pd.DataFrame({
        'code': data.Data[1],
        'name': data.Data[2]
    })
    
    logger.info(f"获取到 {len(df)} 只可转债，正在查询成交额和债券余额...")
    
    # 获取上个交易日
    last_trade_day = getLastOpenDay(datetime.now().strftime('%Y%m%d'))
    
    codes = df['code'].tolist()
    
    # 使用wss一次性获取成交额和债券余额
    data = w.wss(
        codes,
        "amt,outstandingbalance",
        f"unit=1;tradeDate={last_trade_day};cycle=D"
    )
    
    if data.ErrorCode != 0:
        raise Exception(f"Wind API错误: ErrorCode={data.ErrorCode}")
    
    # Data[0]是amt（成交额，单位：元），Data[1]是outstandingbalance（债券余额，单位：亿元）
    df['avg_amount'] = data.Data[0]  # 成交额，单位已是元，无需转换
    # 债券余额从亿元转换为元
    df['carrying_value'] = [x * 1e8 if x is not None else np.nan for x in data.Data[1]]
    
    logger.info(f"可转债数据获取完成")
    
    return df


#@shelve_me_week
def _fetch_price_data(code: str, start_date: str, end_date: str, dividend_type: str) -> pd.Series:
    """
    获取单个标的的历史价格数据（带缓存）
    
    Args:
        code: 标的代码（Wind格式）
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        dividend_type: 复权类型
        
    Returns:
        收盘价序列
    """
    # 优先使用 getDayDataWithTimeout，如果不可用则使用 Wind API
    if GET_DAY_DATA_AVAILABLE and getDayDataWithTimeout is not None:
        try:
            # 转换代码格式：Wind格式（.OF后缀）转换为XtQuant格式（.SH/.SZ）
            xtquant_code = code
            if code.endswith('.OF'):
                # 基金代码：去掉.OF后缀，提取数字部分
                code_num = code.replace('.OF', '')
                # 根据第一位数字判断交易所：1开头→深交所(.SZ)，5开头→上交所(.SH)
                if code_num.startswith('1'):
                    xtquant_code = f"{code_num}.SZ"
                elif code_num.startswith('5'):
                    xtquant_code = f"{code_num}.SH"
                else:
                    logger.warning(f"无法识别基金代码市场: {code}，尝试使用原代码")
                    xtquant_code = code_num  # 如果无法识别，至少去掉.OF后缀
            elif code.endswith('.SH') or code.endswith('.SZ'):
                # 已经是XtQuant格式，直接使用
                xtquant_code = code
            else:
                # 其他格式（如股票代码），尝试根据前缀判断
                # 00、30开头 → 深交所
                if code.startswith('00') or code.startswith('30'):
                    xtquant_code = f"{code}.SZ"
                # 60开头 → 上交所
                elif code.startswith('60'):
                    xtquant_code = f"{code}.SH"
                # 68开头 → 科创板（上交所）
                elif code.startswith('68'):
                    xtquant_code = f"{code}.SH"
                else:
                    # 无法识别，尝试使用原代码
                    xtquant_code = code
            
            # 使用 getDayDataWithTimeout 获取数据
            df = getDayDataWithTimeout(
                stock_code=xtquant_code,
                start_date=start_date,
                end_date=end_date,
                is_download=0,  # 从缓存读取
                dividend_type=dividend_type
            )
            
            if df is None or len(df) == 0:
                logger.warning(f"getDayDataWithTimeout返回空数据: {code} (转换后: {xtquant_code})")
                return None
            
            # 将DataFrame转换为Series（使用close列）
            # date列转换为日期索引
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                price_series = pd.Series(df['close'].values, index=df['date'], name=code)
            else:
                # 如果没有date列，使用索引
                price_series = pd.Series(df['close'].values, index=df.index, name=code)
            
            price_series = price_series.dropna()
            
            if code != xtquant_code:
                logger.debug(f"获取价格数据: {code} (转换后: {xtquant_code}), 共 {len(price_series)} 条")
            else:
                logger.debug(f"获取价格数据: {code}, 共 {len(price_series)} 条")
            
            return price_series
            
        except Exception as e:
            logger.warning(f"getDayDataWithTimeout获取数据失败: {code} (转换后: {xtquant_code}), 错误: {e}, 尝试使用Wind API")
            # 如果失败，fallback到Wind API
    
    # 使用Wind API作为备选方案
    w.start()
    
    data = w.wsd(
        code,
        "close",
        start_date,
        end_date,
        f"Days=Trading;PriceAdj={dividend_type[0].upper()}"
    )
    
    if data.ErrorCode != 0:
        logger.error(f"获取价格数据失败: {code}, ErrorCode={data.ErrorCode}")
        return None
    
    # 构建Series
    price_series = pd.Series(data.Data[0], index=data.Times, name=code)
    price_series = price_series.dropna()
    
    logger.debug(f"获取价格数据: {code}, 共 {len(price_series)} 条")
    
    return price_series


# ==================== DataFetcher 类 ====================

class DataFetcher:
    """数据获取器"""
    
    def __init__(self):
        """初始化数据获取器"""
        self.wind_started = False
        logger.info("数据获取器初始化完成")
    
    def _ensure_wind_started(self):
        """确保Wind连接已启动"""
        if not self.wind_started:
            logger.info("正在启动Wind连接...")
            w.start()
            self.wind_started = True
            logger.info("Wind连接已启动")
    
    def _stop_wind(self):
        """停止Wind连接"""
        if self.wind_started:
            w.stop()
            self.wind_started = False
            logger.info("Wind连接已关闭")
    
    def get_stock_universe(self) -> pd.DataFrame:
        """
        获取股票池（按市值排序前N只）
        
        Returns:
            包含股票代码、名称、市值的DataFrame
        """
        logger.info("开始获取股票池数据...")
        
        # 使用缓存函数获取全部A股市值数据
        result_df = _fetch_stock_universe_with_marketcap()
        
        # 按市值排序并取前N只
        top_n = Config.DataFilter.STOCK_TOP_N
        result_df = result_df.head(top_n).reset_index(drop=True)
        
        logger.info(f"筛选出市值前 {len(result_df)} 只股票")
        
        return result_df
    
    def get_etf_universe(self) -> pd.DataFrame:
        """
        获取ETF池（日均成交额>1000万）
        
        Returns:
            包含ETF代码、名称、日均成交额的DataFrame
        """
        # 使用缓存函数获取ETF数据
        df = _fetch_etf_universe()
        
        # 筛选日均成交额>1000万的ETF
        min_amount = Config.DataFilter.ETF_MIN_AVG_AMOUNT
        result_df = df[df['avg_amount'] > min_amount].reset_index(drop=True)
        
        logger.info(f"筛选出日均成交额>{min_amount/1e7:.0f}亿的ETF {len(result_df)} 只")
        
        return result_df
    
    def get_convertible_bond_universe(self) -> pd.DataFrame:
        """
        获取可转债池（剩余规模>3亿且日均成交额>1000万）
        
        Returns:
            包含可转债代码、名称、剩余规模、日均成交额的DataFrame
        """
        # 使用缓存函数获取可转债数据
        df = _fetch_convertible_bond_universe()
        
        # 筛选条件
        min_size = Config.DataFilter.CONVERTIBLE_BOND_MIN_SIZE
        min_amount = Config.DataFilter.CONVERTIBLE_BOND_MIN_AMOUNT
        
        result_df = df[
            (df['carrying_value'] > min_size) & 
            (df['avg_amount'] > min_amount)
        ].reset_index(drop=True)
        
        logger.info(f"筛选出符合条件的可转债 {len(result_df)} 只")
        
        return result_df
    
    def get_price_data(self, code: str, days: int = None) -> pd.Series:
        """
        获取单个标的的历史价格数据
        
        Args:
            code: 标的代码
            days: 回溯天数，默认使用配置中的值
            
        Returns:
            收盘价序列，索引为日期
        """
        if days is None:
            days = Config.HistoricalData.LOOKBACK_DAYS
        
        # 根据配置的日期模式选择日期获取方式
        date_mode = Config.HistoricalData.DATE_MODE
        
        if date_mode == 'auto':
            # 自动模式：使用get_date_range获取开始和结束日期
            if GET_DATE_RANGE_AVAILABLE and get_date_range is not None:
                try:
                    start_date, end_date, reason = get_date_range()
                    logger.debug(f"自动模式：使用get_date_range获取日期范围: {start_date} 到 {end_date} ({reason})")
                except Exception as e:
                    logger.warning(f"get_date_range获取日期失败: {e}, 使用默认计算方式")
                    end_date = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=days+100)).strftime('%Y%m%d')
            else:
                logger.warning("get_date_range不可用，自动模式降级为默认计算方式")
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=days+100)).strftime('%Y%m%d')
        elif date_mode == 'manual':
            # 手动模式：从配置中读取开始和结束日期
            start_date = Config.HistoricalData.START_DATE
            end_date = Config.HistoricalData.END_DATE
            logger.debug(f"手动模式：使用配置的日期范围: {start_date} 到 {end_date}")
        else:
            # 未知模式，使用默认计算方式
            logger.warning(f"未知的日期模式: {date_mode}, 使用默认计算方式")
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days+100)).strftime('%Y%m%d')
        
        # 获取数据（使用缓存函数）
        dividend_type = Config.HistoricalData.DIVIDEND_TYPE
        price_series = _fetch_price_data(code, start_date, end_date, dividend_type)
        
        if price_series is None:
            return None
        
        # 只保留最近days天的交易数据（交易日天数，不是自然日）
        if len(price_series) > days:
            price_series = price_series.tail(days)
        
        logger.debug(f"获取价格数据: {code}, 共 {len(price_series)} 条")
        
        return price_series
    
    def get_batch_price_data(self, codes: List[str], days: int = None) -> Dict[str, pd.Series]:
        """
        批量获取价格数据
        
        Args:
            codes: 标的代码列表
            days: 回溯天数，默认使用配置中的值
            
        Returns:
            代码到价格序列的字典
        """
        logger.info(f"开始批量获取价格数据，共 {len(codes)} 只标的...")
        
        result = {}
        failed = []
        
        # 使用tqdm显示进度条
        for code in tqdm(codes, desc="获取价格数据", unit="只", ncols=100):
            try:
                price_data = self.get_price_data(code, days)
                if price_data is not None and len(price_data) > 0:
                    result[code] = price_data
                else:
                    failed.append(code)
            except Exception as e:
                logger.warning(f"获取价格数据失败: {code}, 错误: {e}")
                failed.append(code)
        
        logger.info(f"批量获取完成，成功: {len(result)}, 失败: {len(failed)}")
        
        if failed:
            logger.warning(f"失败的标的: {failed[:10]}{'...' if len(failed) > 10 else ''}")
        
        return result
    
    def __del__(self):
        """析构函数，关闭Wind连接"""
        self._stop_wind()


if __name__ == '__main__':
    """数据获取器测试"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*80)
    print("数据获取器测试")
    print("="*80)
    
    fetcher = DataFetcher()
    
    # 测试1: 获取股票池
    print("\n测试1: 获取股票池")
    try:
        stocks = fetcher.get_stock_universe()
        print(f"获取到 {len(stocks)} 只股票")
        print("\n前10只股票:")
        print(stocks.head(10))
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试2: 获取ETF池
    print("\n测试2: 获取ETF池")
    try:
        etfs = fetcher.get_etf_universe()
        print(f"获取到 {len(etfs)} 只ETF")
        print("\n前10只ETF:")
        print(etfs.head(10))
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试3: 获取可转债池
    print("\n测试3: 获取可转债池")
    try:
        bonds = fetcher.get_convertible_bond_universe()
        print(f"获取到 {len(bonds)} 只可转债")
        print("\n前10只可转债:")
        print(bonds.head(10))
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试4: 获取价格数据
    print("\n测试4: 获取价格数据")
    try:
        if len(stocks) > 0:
            test_code = stocks.iloc[0]['code']
            prices = fetcher.get_price_data(test_code, days=100)
            print(f"获取 {test_code} 的价格数据，共 {len(prices)} 条")
            print(f"\n最近5天价格:")
            print(prices.tail())
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)

