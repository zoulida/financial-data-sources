"""市场数据获取模块 - 使用XtQuant获取行情数据并计算波动率."""

from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from tqdm import tqdm
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, TimeoutError
import time
import logging

# 添加合并下载数据模块的路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "md" / "合并下载数据"))
sys.path.insert(0, str(project_root))

try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData, batchDownloadDayData
except ImportError:
    print("警告: 无法导入合并下载数据模块，请确保路径正确")
    getDayData = None
    batchDownloadDayData = None

from tools.shelveTool import shelve_me_today

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_day_data_with_timeout(stock_code: str, start_date: str, end_date: str, 
                                is_download: int = 0, dividend_type: str = "front",
                                timeout: int = 3, max_retries: int = 3) -> pd.DataFrame:
    """
    带超时和重试机制的数据获取函数.
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        is_download: 是否重新下载
        dividend_type: 复权类型
        timeout: 超时时间（秒），默认3秒
        max_retries: 最大重试次数，默认3次
        
    Returns:
        pd.DataFrame: 股票数据
        
    Raises:
        TimeoutError: 超时且重试次数用完
        Exception: 其他异常
    """
    executor = None
    for attempt in range(max_retries):
        future = None
        try:
            if attempt == 0:
                # 只在第一次尝试时打印
                logger.info(f">>> {stock_code} 开始获取")
            else:
                logger.warning(f">>> {stock_code} 重试第 {attempt + 1} 次")
            
            start_time = time.time()
            
            # 创建线程池执行器（不使用上下文管理器，避免退出时阻塞）
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
            # logger.info(f"✓ {stock_code} 成功 ({elapsed:.2f}s)")  # 成功不打印，减少日志
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


class MarketDataFetcher:
    """市场数据获取类，用于获取行情数据并计算波动率."""

    def __init__(self) -> None:
        """初始化市场数据获取器."""
        if getDayData is None:
            raise ImportError("无法导入合并下载数据模块")
        print("市场数据获取器初始化成功")

    @shelve_me_today
    def calculate_volatility(
        self, stock_codes: List[str], period_days: int = 252
    ) -> pd.DataFrame:
        """
        计算股票的年化波动率（基于过去52周/约252个交易日）.
        
        日期规则：
        - 开始日期：固定为 2024年11月01日
        - 结束日期：21点之前为昨天，21点之后为今天
        
        缓存策略: 按天缓存（每天更新一次）

        Args:
            stock_codes: 股票代码列表
            period_days: 计算周期（交易日数），默认252天约为1年

        Returns:
            pd.DataFrame: 包含股票代码和年化波动率的DataFrame
        """
        print(f"\n正在计算 {len(stock_codes)} 只股票的 {period_days} 日年化波动率...")
        
        # 固定开始日期
        start_date = "20241101"
        
        # 结束日期：根据当前时间判断
        now = datetime.now()
        current_hour = now.hour
        if current_hour < 21:  # 21点之前用昨天
            end_date = (now - timedelta(days=1)).strftime("%Y%m%d")
        else:  # 21点之后用今天
            end_date = now.strftime("%Y%m%d")
        
        print(f"数据区间: {start_date} - {end_date}")
        
        volatility_data = []
        
        # 使用 getDayData 逐个下载
        print("下载行情数据...")
        print(f"提示: 成功的股票不显示日志，只显示超时/失败的股票\n")
        
        for idx, code in enumerate(tqdm(stock_codes, desc="下载并计算波动率"), 1):
            try:
                df = get_day_data_with_timeout(
                    stock_code=code,
                    start_date=start_date,
                    end_date=end_date,
                    is_download=0,  # 优先使用缓存
                    dividend_type="front",
                    timeout=2,  # 超时2秒
                    max_retries=3  # 最多重试2次
                )
                
                if df is None or df.empty or len(df) < 50:
                    # 数据不足，设置为0
                    volatility_data.append(
                        {
                            "stock_code": code,
                            "volatility_annual": 0.0,
                            "trading_days": 0,
                        }
                    )
                    continue
                
                # 取最近period_days个交易日（如果不足就全部使用）
                df_recent = df.tail(period_days).copy()
                
                # 计算日收益率
                df_recent["returns"] = df_recent["close"].pct_change()
                
                # 计算年化波动率 = 日波动率 * sqrt(252)
                daily_volatility = df_recent["returns"].std()
                annual_volatility = daily_volatility * np.sqrt(252)
                
                volatility_data.append(
                    {
                        "stock_code": code,
                        "volatility_annual": annual_volatility,
                        "trading_days": len(df_recent),
                    }
                )
            except TimeoutError as e:
                logger.error(f"**超时跳过** {code}: {str(e)}")
                # 超时也保留，设置为0
                volatility_data.append(
                    {
                        "stock_code": code,
                        "volatility_annual": 0.0,
                        "trading_days": 0,
                    }
                )
                continue
            except Exception as e:
                logger.error(f"**异常跳过** {code}: {str(e)[:100]}")
                # 出错也保留，设置为0
                volatility_data.append(
                    {
                        "stock_code": code,
                        "volatility_annual": 0.0,
                        "trading_days": 0,
                    }
                )
                continue
        
        result_df = pd.DataFrame(volatility_data)
        # 填充缺失值
        result_df["volatility_annual"] = result_df["volatility_annual"].fillna(0)
        
        success_count = (result_df["volatility_annual"] > 0).sum()
        print(f"成功计算 {success_count} 只股票的波动率")
        if len(result_df) - success_count > 0:
            print(f"  其中 {len(result_df) - success_count} 只股票数据不足（已设置为0）")
        return result_df

    def calculate_avg_amount(
        self, stock_codes: List[str], period_days: int = 252
    ) -> pd.DataFrame:
        """
        计算股票的日均成交额（用于流动性筛选）.

        Args:
            stock_codes: 股票代码列表
            period_days: 计算周期（交易日数）

        Returns:
            pd.DataFrame: 包含股票代码和日均成交额的DataFrame
        """
        print(f"\n正在计算 {len(stock_codes)} 只股票的日均成交额...")
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=int(period_days * 1.5))).strftime(
            "%Y%m%d"
        )
        
        amount_data = []
        
        # 批量下载
        print("批量下载行情数据...")
        try:
            data_dict = batchDownloadDayData(
                stock_codes=stock_codes,
                start_date=start_date,
                end_date=end_date,
                dividend_type="front",
                need_download=1,
            )
        except Exception as e:
            print(f"批量下载失败: {e}")
            return pd.DataFrame()
        
        # 计算日均成交额
        for code, df in tqdm(data_dict.items(), desc="计算日均成交额"):
            try:
                if df is None or df.empty:
                    continue
                
                df_recent = df.tail(period_days)
                avg_amount = df_recent["amount"].mean()
                
                amount_data.append(
                    {"stock_code": code, "avg_amount": avg_amount, "trading_days": len(df_recent)}
                )
            except Exception:
                continue
        
        result_df = pd.DataFrame(amount_data)
        print(f"成功计算 {len(result_df)} 只股票的日均成交额")
        return result_df

    def get_latest_close_price(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取股票最新收盘价.

        Args:
            stock_codes: 股票代码列表

        Returns:
            pd.DataFrame: 包含股票代码和最新收盘价的DataFrame
        """
        print(f"\n正在获取 {len(stock_codes)} 只股票的最新收盘价...")
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        
        price_data = []
        
        for code in tqdm(stock_codes, desc="获取收盘价"):
            try:
                df = get_day_data_with_timeout(
                    stock_code=code,
                    start_date=start_date,
                    end_date=end_date,
                    is_download=0,  # 优先从缓存读取
                    dividend_type="front",
                    timeout=2,  # 超时2秒
                    max_retries=2  # 最多重试2次
                )
                
                if df is not None and not df.empty:
                    latest_close = df.iloc[-1]["close"]
                    latest_date = df.iloc[-1]["date"]
                    price_data.append(
                        {
                            "stock_code": code,
                            "latest_close": latest_close,
                            "latest_date": latest_date,
                        }
                    )
            except Exception:
                continue
        
        result_df = pd.DataFrame(price_data)
        print(f"成功获取 {len(result_df)} 只股票的收盘价")
        return result_df


def main() -> None:
    """测试市场数据获取功能."""
    fetcher = MarketDataFetcher()
    
    # 测试股票列表
    test_stocks = ["600519.SH", "000001.SZ", "600036.SH"]
    
    # 测试波动率计算
    vol_df = fetcher.calculate_volatility(test_stocks, period_days=252)
    print("\n波动率数据:")
    print(vol_df)
    
    # 测试成交额计算
    amt_df = fetcher.calculate_avg_amount(test_stocks, period_days=252)
    print("\n日均成交额数据:")
    print(amt_df)
    
    # 测试收盘价获取
    price_df = fetcher.get_latest_close_price(test_stocks)
    print("\n最新收盘价数据:")
    print(price_df)


if __name__ == "__main__":
    main()

