"""诊断工具：帮助定位导致程序卡住的股票."""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "md" / "合并下载数据"))
sys.path.insert(0, str(project_root))

from source.实盘.xuntou.datadownload.合并下载数据 import getDayData
import signal
from datetime import datetime, timedelta


class TimeoutException(Exception):
    """超时异常."""
    pass


def timeout_handler(signum, frame):
    """超时处理函数."""
    raise TimeoutException("操作超时")


def test_single_stock(stock_code: str, start_date: str = None, end_date: str = None, timeout_seconds: int = 5):
    """
    测试单只股票的数据获取是否会卡住.
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期，默认为一年前
        end_date: 结束日期，默认为今天
        timeout_seconds: 超时秒数
    """
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    print(f"\n测试股票: {stock_code}")
    print(f"日期范围: {start_date} - {end_date}")
    print(f"超时设置: {timeout_seconds} 秒")
    print("-" * 50)
    
    # 设置超时信号（仅Linux/Mac）
    if sys.platform != 'win32':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
    
    try:
        print(f"开始获取数据...")
        df = getDayData(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            is_download=0,
            dividend_type="front"
        )
        
        if sys.platform != 'win32':
            signal.alarm(0)  # 取消超时
        
        if df is not None and not df.empty:
            print(f"✓ 成功获取数据，共 {len(df)} 行")
            print(f"  最后日期: {df.iloc[-1]['date']}")
            return True
        else:
            print(f"✗ 数据为空")
            return False
            
    except TimeoutException:
        print(f"✗ 超时 - 该股票可能导致卡住！")
        return False
    except Exception as e:
        if sys.platform != 'win32':
            signal.alarm(0)
        print(f"✗ 出错: {e}")
        return False


def test_stock_list(stock_codes: list, timeout_seconds: int = 5):
    """
    批量测试股票列表，找出导致卡住的股票.
    
    Args:
        stock_codes: 股票代码列表
        timeout_seconds: 每只股票的超时秒数
    """
    print(f"\n开始测试 {len(stock_codes)} 只股票...")
    print("=" * 50)
    
    problematic_stocks = []
    
    for idx, code in enumerate(stock_codes, 1):
        print(f"\n[{idx}/{len(stock_codes)}]", end=" ")
        success = test_single_stock(code, timeout_seconds=timeout_seconds)
        
        if not success:
            problematic_stocks.append(code)
    
    print("\n" + "=" * 50)
    print(f"\n测试完成!")
    print(f"成功: {len(stock_codes) - len(problematic_stocks)} 只")
    print(f"失败/超时: {len(problematic_stocks)} 只")
    
    if problematic_stocks:
        print(f"\n问题股票列表:")
        for code in problematic_stocks:
            print(f"  - {code}")


if __name__ == "__main__":
    # 测试示例
    print("诊断工具：检测导致程序卡住的股票")
    print("=" * 50)
    
    # 测试单只股票
    test_single_stock("600519.SH", timeout_seconds=3)
    
    # 如果需要批量测试，取消下面的注释
    # test_stocks = ["600519.SH", "000001.SZ", "600036.SH"]
    # test_stock_list(test_stocks, timeout_seconds=3)

