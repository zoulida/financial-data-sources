"""测试单个股票数据获取，用于诊断卡顿问题."""

import sys
from pathlib import Path
import time

# 添加路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "md" / "合并下载数据"))
sys.path.insert(0, str(project_root))

from source.实盘.xuntou.datadownload.合并下载数据 import getDayData

def test_stock(stock_code: str, timeout: int = 5):
    """
    测试单个股票数据获取.
    
    Args:
        stock_code: 股票代码
        timeout: 超时时间（秒）
    """
    print(f"\n{'='*60}")
    print(f"测试股票: {stock_code}")
    print(f"超时设置: {timeout}秒")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    try:
        print(f"[{time.strftime('%H:%M:%S')}] 开始获取数据...")
        
        df = getDayData(
            stock_code=stock_code,
            start_date="20241101",
            end_date="20251031",
            is_download=0,
            dividend_type="front"
        )
        
        elapsed = time.time() - start_time
        print(f"[{time.strftime('%H:%M:%S')}] 成功获取数据！")
        print(f"耗时: {elapsed:.2f}秒")
        print(f"数据行数: {len(df)}")
        print(f"数据列: {list(df.columns)}")
        
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{time.strftime('%H:%M:%S')}] 获取数据失败！")
        print(f"耗时: {elapsed:.2f}秒")
        print(f"错误: {e}")
        
        import traceback
        traceback.print_exc()
        
        return False


if __name__ == "__main__":
    # 测试列表：包含一些可能有问题的股票
    test_stocks = [
        "300390.SZ",  # 从终端输出看最后处理的股票
        "000001.SZ",  # 平安银行
        "600519.SH",  # 贵州茅台
    ]
    
    print("\n" + "="*60)
    print("股票数据获取诊断工具")
    print("="*60)
    
    # 如果命令行提供了股票代码，使用命令行参数
    if len(sys.argv) > 1:
        test_stocks = [sys.argv[1]]
    
    results = {}
    for stock in test_stocks:
        result = test_stock(stock, timeout=10)
        results[stock] = result
        time.sleep(1)  # 避免请求过快
    
    # 打印汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    for stock, success in results.items():
        status = "✓ 成功" if success else "✗ 失败"
        print(f"{stock}: {status}")

