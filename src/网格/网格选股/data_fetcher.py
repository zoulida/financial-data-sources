"""
网格选股数据获取模块
负责从 XtQuant 获取标的的后复权日线数据

功能：
- 获取单只标的的后复权日线数据
- 批量获取多只标的数据
- 支持数据缓存和异常处理

依赖：pip install pandas numpy xtquant

作者：AI Assistant
创建时间：2025-11-02
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import time
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
# 当前文件: src/网格/网格选股/data_fetcher.py
# parents[3] = 项目根目录
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "md" / "合并下载数据"))

# 导入合并下载数据模块
try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData, batchDownloadDayData  # type: ignore
    DOWNLOAD_MODULE_AVAILABLE = True
except ImportError:
    print("[ERROR] 错误：无法导入合并下载数据模块，请确保路径正确")
    print(f"   尝试导入路径: {project_root / 'md' / '合并下载数据'}")
    getDayData = None
    batchDownloadDayData = None
    DOWNLOAD_MODULE_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.WARNING,  # 只显示警告和错误
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_day_data_with_timeout(stock_code: str, start_date: str, end_date: str,
                                is_download: int = 0, dividend_type: str = "front",
                                timeout: int = 5, max_retries: int = 3) -> pd.DataFrame:
    """
    带超时和重试机制的数据获取函数
    
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            is_download: 是否重新下载（0=从缓存读取，1=重新下载）
            dividend_type: 复权类型（'front'=前复权，'back'=后复权，'none'=不复权）
            timeout: 超时时间（秒），默认5秒
            max_retries: 最大重试次数，默认3次
        
    Returns:
        pd.DataFrame: 股票数据，包含 date, open, high, low, close, volume, amount 列
        
    Raises:
        TimeoutError: 超时且重试次数用完
        Exception: 其他异常
    """
    if getDayData is None:
        raise RuntimeError("合并下载数据模块未导入")
    
    executor = None
    for attempt in range(max_retries):
        future = None
        try:
            start_time = time.time()
            
            # 创建线程池执行器
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(
                getDayData,
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                is_download=is_download,
                dividend_type=dividend_type
            )
            
            result = future.result(timeout=timeout)
            elapsed = time.time() - start_time
            
            # 成功后关闭执行器
            executor.shutdown(wait=False)
            return result
                
        except Exception as e:
            elapsed = time.time() - start_time
            error_type = type(e).__name__
            
            # 尝试取消未完成的任务
            if future and not future.done():
                future.cancel()
            
            # 强制关闭执行器，不等待
            if executor:
                executor.shutdown(wait=False)
                executor = None
            
            # 检查是否是超时异常
            is_timeout = 'timeout' in error_type.lower() or 'Timeout' in str(type(e))
            
            if attempt < max_retries - 1:
                logger.warning(f"⚠ {stock_code} {error_type} ({elapsed:.1f}s), 1秒后重试...")
                time.sleep(1)
                continue
            else:
                logger.error(f"✗ {stock_code} 失败 {error_type} (重试{max_retries}次)")
                if is_timeout:
                    raise TimeoutError(f"{stock_code} 数据获取超时（{max_retries}次尝试后放弃）")
                else:
                    raise Exception(f"{stock_code} 数据获取失败: {str(e)}")
    
    return pd.DataFrame()


class DataFetcher:
    """数据获取器（使用合并下载数据模块）"""
    
    def __init__(self, start_date="20241101", end_date=None):
        """
        初始化数据获取器
        
        Args:
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD，默认为当前日期
        """
        if not DOWNLOAD_MODULE_AVAILABLE:
            raise RuntimeError("合并下载数据模块未导入，无法获取数据")
        
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y%m%d")
        
        print(f"[数据获取器] 初始化完成")
        print(f"  数据区间: {self.start_date} ~ {self.end_date}")
        print(f"  复权方式: 前复权（注：合并下载数据模块目前仅支持前复权）")
        print(f"  数据源: 合并下载数据模块 (getDayData)")
    
    def get_single_stock_data(self, code, min_days=252):
        """
        获取单只标的的后复权日线数据
        
        Args:
            code: 标的代码，如 '159001.SZ'
            min_days: 最少需要的交易日数量，默认252天
            
        Returns:
            pd.DataFrame: 包含以下列的数据框
                - date: 交易日期（列）
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                - amount: 成交额
            None: 获取失败或数据不足时返回 None
        """
        try:
            # 使用 getDayData 获取前复权数据（注：合并下载数据模块目前仅支持前复权）
            df = get_day_data_with_timeout(
                stock_code=code,
                start_date=self.start_date,
                end_date=self.end_date,
                is_download=0,  # 优先从缓存读取
                dividend_type='front',  # 前复权
                timeout=5,  # 超时5秒
                max_retries=3  # 最多重试3次
            )
            
            # 检查数据是否有效
            if df is None or df.empty:
                return None
            
            # 删除缺失值
            df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
            
            # 检查数据量是否足够
            if len(df) < min_days:
                return None
            
            # 确保有必需的列
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                return None
            
            return df
            
        except TimeoutError:
            # 超时静默失败
            return None
        except Exception as e:
            # 其他异常静默失败
            return None
    
    def get_batch_stock_data(self, code_list, min_days=252, show_progress=False):
        """
        批量获取多只标的的后复权日线数据
        
        Args:
            code_list: 标的代码列表，如 ['159001.SZ', '510300.SH']
            min_days: 最少需要的交易日数量，默认252天
            show_progress: 是否显示进度条
            
        Returns:
            dict: {code: DataFrame} 格式的字典
                - key: 标的代码
                - value: 包含 OHLCV 数据的 DataFrame
        """
        results = {}
        
        if show_progress:
            from tqdm import tqdm
            iterator = tqdm(code_list, desc="批量获取数据")
        else:
            iterator = code_list
        
        for code in iterator:
            df = self.get_single_stock_data(code, min_days=min_days)
            if df is not None:
                results[code] = df
        
        return results
    
    def validate_data(self, df, required_fields=None):
        """
        验证数据的完整性
        
        Args:
            df: 数据框
            required_fields: 必需的字段列表，默认为 ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if df is None or len(df) == 0:
            return False, "数据为空"
        
        if required_fields is None:
            required_fields = ['open', 'high', 'low', 'close', 'volume']
        
        # 检查必需字段
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            return False, f"缺少字段: {missing_fields}"
        
        # 检查是否有缺失值
        if df[required_fields].isnull().any().any():
            return False, "存在缺失值"
        
        # 检查是否有异常值（价格<=0）
        price_fields = ['open', 'high', 'low', 'close']
        for field in price_fields:
            if field in df.columns:
                if (df[field] <= 0).any():
                    return False, f"{field} 存在非正值"
        
        return True, "数据有效"
    
    def get_data_info(self, df):
        """
        获取数据信息
        
        Args:
            df: 数据框
            
        Returns:
            dict: 数据信息字典
        """
        if df is None or len(df) == 0:
            return None
        
        # getDayData 返回的 DataFrame 有 'date' 列
        if 'date' in df.columns:
            start_date = df['date'].iloc[0]
            end_date = df['date'].iloc[-1]
        else:
            # 如果没有 date 列，尝试使用索引
            start_date = df.index[0] if hasattr(df.index[0], 'strftime') else str(df.index[0])
            end_date = df.index[-1] if hasattr(df.index[-1], 'strftime') else str(df.index[-1])
        
        info = {
            'total_days': len(df),
            'start_date': start_date if isinstance(start_date, str) else str(start_date),
            'end_date': end_date if isinstance(end_date, str) else str(end_date),
            'close_min': df['close'].min(),
            'close_max': df['close'].max(),
            'close_mean': df['close'].mean(),
            'volume_mean': df['volume'].mean()
        }
        
        return info


def test_data_fetcher():
    """测试数据获取器"""
    print("="*80)
    print("测试数据获取模块（使用合并下载数据）")
    print("="*80)
    
    if not DOWNLOAD_MODULE_AVAILABLE:
        print("[ERROR] 错误：合并下载数据模块未导入，无法测试")
        return
    
    # 初始化数据获取器
    try:
        fetcher = DataFetcher(start_date="20241101")
    except Exception as e:
        print(f"[ERROR] 初始化失败: {e}")
        return
    
    # 测试单只标的
    print("\n[测试1] 获取单只标的数据...")
    test_code = "159001.SZ"
    df = fetcher.get_single_stock_data(test_code)
    
    if df is not None:
        print(f"[OK] 成功获取 {test_code} 的数据")
        print(f"   数据量: {len(df)} 天")
        print(f"   数据列: {list(df.columns)}")
        print(f"\n前5行数据:")
        print(df.head())
        
        # 验证数据
        is_valid, msg = fetcher.validate_data(df)
        print(f"\n数据验证: {'[OK] 通过' if is_valid else '[ERROR] 失败'} - {msg}")
        
        # 数据信息
        info = fetcher.get_data_info(df)
        if info:
            print(f"\n数据信息:")
            for k, v in info.items():
                print(f"  {k}: {v}")
    else:
        print(f"[ERROR] 获取 {test_code} 的数据失败")
    
    # 测试批量获取
    print("\n[测试2] 批量获取多只标的数据...")
    test_codes = ["159001.SZ", "510300.SH", "512880.SH"]
    results = fetcher.get_batch_stock_data(test_codes, show_progress=True)
    
    print(f"\n[OK] 成功获取 {len(results)}/{len(test_codes)} 只标的的数据")
    for code, df in results.items():
        print(f"  {code}: {len(df)} 天")
    
    print("\n" + "="*80)
    print("测试完成！")


if __name__ == "__main__":
    test_data_fetcher()

