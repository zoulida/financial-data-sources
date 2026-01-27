"""
测试不同数据源的交易日历一致性
"""
import pandas as pd
from datetime import datetime

# 导入我们的日历模块
from szse_calendar import (
    get_pandas_market_calendars, 
    get_akshare_calendar, 
    get_szse_calendar_api,
    get_szse_calendar
)

def test_calendar_sources(year=2025):
    """测试不同数据源的交易日历"""
    print(f"=== 测试{year}年不同数据源的交易日历 ===\n")
    
    # 测试pandas_market_calendars
    print("1. pandas_market_calendars:")
    df1 = get_pandas_market_calendars(year)
    if not df1.empty:
        print(f"   获取到{len(df1)}个交易日")
        print(f"   范围: {df1['date'].min()} 到 {df1['date'].max()}")
    else:
        print("   获取失败")
    print()
    
    # 测试akshare
    print("2. akshare:")
    df2 = get_akshare_calendar(year)
    if not df2.empty:
        print(f"   获取到{len(df2)}个交易日")
        print(f"   范围: {df2['date'].min()} 到 {df2['date'].max()}")
    else:
        print("   获取失败")
    print()
    
    # 测试深交所API
    print("3. 深交所API:")
    df3 = get_szse_calendar_api(year)
    if not df3.empty:
        print(f"   获取到{len(df3)}个交易日")
        print(f"   范围: {df3['date'].min()} 到 {df3['date'].max()}")
    else:
        print("   获取失败")
    print()
    
    # 比较数据源一致性
    if not df1.empty and not df2.empty:
        set1 = set(df1['date'])
        set2 = set(df2['date'])
        
        print("4. 数据源比较:")
        print(f"   pandas_market_calendars: {len(set1)}天")
        print(f"   akshare: {len(set2)}天")
        
        # 计算差异
        only_in_pandas = set1 - set2
        only_in_akshare = set2 - set1
        common = set1 & set2
        
        print(f"   共同交易日: {len(common)}天")
        print(f"   仅在pandas_market_calendars: {len(only_in_pandas)}天")
        print(f"   仅在akshare: {len(only_in_akshare)}天")
        
        if only_in_pandas:
            print(f"   仅在pandas_market_calendars的日期: {sorted(list(only_in_pandas))[:5]}...")
        if only_in_akshare:
            print(f"   仅在akshare的日期: {sorted(list(only_in_akshare))[:5]}...")
    
    print("\n" + "="*50)

def test_main_function():
    """测试主函数"""
    print("=== 测试主函数get_szse_calendar ===\n")
    
    for year in [2024, 2025, 2026]:
        print(f"测试{year}年:")
        df = get_szse_calendar(year)
        if not df.empty:
            print(f"  成功获取{len(df)}个交易日")
            print(f"  范围: {df['date'].min()} 到 {df['date'].max()}")
        else:
            print("  获取失败")
        print()

if __name__ == "__main__":
    # 测试2025年的数据源
    test_calendar_sources(2025)
    
    # 测试主函数
    test_main_function()
