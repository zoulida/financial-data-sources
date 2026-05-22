# -*- coding: utf-8 -*-
"""
测试 xtquant 数据接口
"""
import sys
import os
import pandas as pd
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 测试结果记录
test_results = []

def record_test(test_name, passed, message=""):
    """记录测试结果"""
    test_results.append({
        'name': test_name,
        'passed': passed,
        'message': message
    })

print("=" * 60)
print("开始测试 xtquant 数据接口")
print("=" * 60)

# 测试1: 基础股票池获取
print("\n[测试1] 基础股票池获取")
print("-" * 60)
try:
    from src.基础筛选.filterStocks import get_universe_with_basics
    
    df = get_universe_with_basics(max_price=18.0, max_mcap=200.0)
    print(f"[OK] 成功获取股票池")
    print(f"  股票数量: {len(df)}")
    print(f"  列名: {list(df.columns)}")
    if len(df) > 0:
        print(f"  前3只股票:")
        print(df.head(3).to_string(index=False))
    record_test("基础股票池获取", True, f"获取到 {len(df)} 只股票")
except Exception as e:
    print(f"[FAIL] 失败: {e}")
    record_test("基础股票池获取", False, str(e))

# 测试2: 日期范围获取
print("\n[测试2] 日期范围获取")
print("-" * 60)
try:
    from md.获取enddate.get_date_range import get_date_range, get_date_range_formatted
    
    start_date, end_date, reason = get_date_range()
    print(f"[OK] 成功获取日期范围 (YYYYMMDD格式)")
    print(f"  开始日期: {start_date}")
    print(f"  结束日期: {end_date}")
    print(f"  原因: {reason}")
    
    start_date_dash, end_date_dash, reason_dash = get_date_range_formatted(with_dash=True)
    print(f"[OK] 成功获取日期范围 (YYYY-MM-DD格式)")
    print(f"  开始日期: {start_date_dash}")
    print(f"  结束日期: {end_date_dash}")
    record_test("日期范围获取", True, f"{start_date} ~ {end_date}")
except Exception as e:
    print(f"[FAIL] 失败: {e}")
    record_test("日期范围获取", False, str(e))

# 测试3: K线数据获取（单只股票）
print("\n[测试3] K线数据获取 - 单只股票")
print("-" * 60)
try:
    from md.合并下载数据.合并下载数据 import getDayData
    
    # 使用贵州茅台作为测试
    test_code = "600519.SH"
    df_kline = getDayData(
        stock_code=test_code,
        start_date="20240101",
        end_date="20241231",
        is_download=0,  # 从缓存读取
        dividend_type='front'
    )
    
    if df_kline is not None and len(df_kline) > 0:
        print(f"[OK] 成功获取 {test_code} K线数据")
        print(f"  数据行数: {len(df_kline)}")
        print(f"  列名: {list(df_kline.columns)}")
        print(f"  日期范围: {df_kline['date'].min()} ~ {df_kline['date'].max()}")
        print(f"  最近5天数据:")
        print(df_kline.tail(5).to_string(index=False))
        record_test("K线数据获取-单只股票", True, f"{test_code} 获取 {len(df_kline)} 条数据")
    else:
        print(f"[FAIL] 未获取到数据")
        record_test("K线数据获取-单只股票", False, "未获取到数据")
except Exception as e:
    print(f"[FAIL] 失败: {e}")
    record_test("K线数据获取-单只股票", False, str(e))

# 测试4: 批量K线数据获取
print("\n[测试4] K线数据获取 - 批量股票")
print("-" * 60)
try:
    from md.合并下载数据.合并下载数据 import batchDownloadDayData
    
    test_codes = ["600519.SH", "600036.SH", "000001.SZ"]
    data_dict = batchDownloadDayData(
        stock_codes=test_codes,
        start_date="20240101",
        end_date="20241231",
        dividend_type='front',
        need_download=0  # 从缓存读取
    )
    
    print(f"[OK] 成功批量获取K线数据")
    print(f"  请求股票数: {len(test_codes)}")
    print(f"  返回股票数: {len(data_dict)}")
    
    success_count = 0
    for code, df in data_dict.items():
        if df is not None and len(df) > 0:
            print(f"  {code}: {len(df)} 条数据")
            success_count += 1
        else:
            print(f"  {code}: 无数据")
    
    record_test("K线数据获取-批量股票", True, f"成功获取 {success_count}/{len(test_codes)} 只股票")
            
except Exception as e:
    print(f"[FAIL] 失败: {e}")
    record_test("K线数据获取-批量股票", False, str(e))

# 测试5: xtdata 基础连接测试
print("\n[测试5] xtdata 基础连接测试")
print("-" * 60)
try:
    from xtquant import xtdata
    
    # 测试获取市场列表
    stock_list = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"[OK] xtdata 连接正常")
    print(f"  沪深A股总数: {len(stock_list)}")
    print(f"  示例代码: {stock_list[:5]}")
    record_test("xtdata实时连接", True, f"获取到 {len(stock_list)} 只股票")
    
except Exception as e:
    print(f"[FAIL] 失败: {e}")
    record_test("xtdata实时连接", False, str(e))

# 打印测试汇总
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)

passed_count = sum(1 for t in test_results if t['passed'])
failed_count = len(test_results) - passed_count

print(f"\n总测试数: {len(test_results)}")
print(f"通过: {passed_count}")
print(f"失败: {failed_count}")
print(f"通过率: {passed_count/len(test_results)*100:.1f}%")

print("\n详细结果:")
print("-" * 60)
for i, result in enumerate(test_results, 1):
    status = "[PASS]" if result['passed'] else "[FAIL]"
    print(f"{i}. {status} {result['name']}")
    if result['message']:
        print(f"   {result['message']}")

print("\n" + "=" * 60)
if failed_count == 0:
    print("所有测试通过!")
else:
    print(f"有 {failed_count} 个测试失败，请检查上述详细信息")
print("=" * 60)
