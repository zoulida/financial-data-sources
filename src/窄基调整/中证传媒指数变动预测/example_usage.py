#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用示例：展示如何使用各个独立函数
"""

from wind_api_utils import (
    init_wind_api, close_wind_api, 
    get_index_constituents, get_stock_basic_info,
    get_stock_quotes, get_realtime_quotes, get_tick_data,
    get_stock_history_quotes, get_batch_stock_history_quotes, 
    test_wind_connection
)
from get_995000_constituents import filter_stocks, save_results, show_statistics
import pandas as pd

def example_get_index_constituents():
    """示例：获取指数成分股"""
    print("=" * 60)
    print("示例1：获取指数成分股")
    print("=" * 60)
    
    # 初始化API
    if not init_wind_api():
        return
    
    # 获取中证全指指数成分股
    df = get_index_constituents("000985.CSI")
    if df is not None:
        print(f"获取到 {len(df)} 只成分股")
        print("前5只股票：")
        print(df.head())
    
    close_wind_api()

def example_get_stock_info():
    """示例：获取股票基本信息"""
    print("\n" + "=" * 60)
    print("示例2：获取股票基本信息")
    print("=" * 60)
    
    # 初始化API
    if not init_wind_api():
        return
    
    # 测试股票代码
    test_stocks = ["000001.SZ", "000002.SZ", "600000.SH"]
    
    # 获取基本信息
    df = get_stock_basic_info(test_stocks, batch_size=3)
    if df is not None:
        print("股票基本信息：")
        print(df)
    
    close_wind_api()

def example_get_stock_quotes():
    """示例：获取股票行情数据（使用迅投接口）"""
    print("\n" + "=" * 60)
    print("示例3：获取股票行情数据（迅投接口）")
    print("=" * 60)
    
    # 测试股票代码
    test_stocks = ["000001.SZ", "000002.SZ", "600000.SH"]
    
    # 获取行情数据
    df = get_stock_quotes(test_stocks)
    if df is not None:
        print("股票行情数据：")
        print(df)
    else:
        print("未获取到数据，请检查迅投xtdata模块")

def example_get_realtime_quotes():
    """示例：获取股票实时行情数据（使用迅投接口）"""
    print("\n" + "=" * 60)
    print("示例4：获取股票实时行情数据（迅投接口）")
    print("=" * 60)
    
    # 测试股票代码
    test_stocks = ["000001.SZ", "000002.SZ", "600000.SH"]
    
    # 获取实时行情数据
    df = get_realtime_quotes(test_stocks)
    if df is not None:
        print("股票实时行情数据：")
        print(df)
    else:
        print("未获取到数据，请检查迅投xtdata模块")

def example_get_tick_data():
    """示例：获取股票tick数据（使用迅投接口）"""
    print("\n" + "=" * 60)
    print("示例5：获取股票tick数据（迅投接口）")
    print("=" * 60)
    
    # 测试股票代码
    test_stocks = ["000001.SZ", "000002.SZ"]
    
    # 获取tick数据
    tick_dict = get_tick_data(test_stocks, count=10)
    if tick_dict:
        print(f"成功获取 {len(tick_dict)} 只股票的tick数据：")
        for code, df in tick_dict.items():
            print(f"\n{code}: {len(df)} 条tick记录")
            print(df.head())
    else:
        print("未获取到数据，请检查迅投xtdata模块")

def example_get_history_quotes():
    """示例：获取历史行情数据（使用迅投接口）"""
    print("\n" + "=" * 60)
    print("示例6：获取历史行情数据（迅投接口）")
    print("=" * 60)
    
    # 获取平安银行最近30天的历史数据
    df = get_stock_history_quotes(
        "000001.SZ", 
        start_date="20241001", 
        end_date="20241024",
        dividend_type='front'
    )
    if df is not None:
        print("平安银行历史行情数据：")
        print(df.head())
    else:
        print("未获取到数据，请检查迅投数据模块路径")

def example_get_batch_history_quotes():
    """示例：批量获取历史行情数据（使用迅投接口）"""
    print("\n" + "=" * 60)
    print("示例7：批量获取历史行情数据（迅投接口）")
    print("=" * 60)
    
    # 测试股票代码
    test_stocks = ["000001.SZ", "000002.SZ", "600000.SH"]
    
    # 批量获取历史数据
    data_dict = get_batch_stock_history_quotes(
        test_stocks,
        start_date="20241001",
        end_date="20241024",
        dividend_type='front'
    )
    
    if data_dict:
        print(f"成功获取 {len(data_dict)} 只股票的历史数据：")
        for code, df in data_dict.items():
            print(f"\n{code}: {len(df)} 条记录")
            print(df.head())
    else:
        print("未获取到数据，请检查迅投数据模块路径")

def example_complete_workflow():
    """示例：完整工作流程"""
    print("\n" + "=" * 60)
    print("示例8：完整工作流程")
    print("=" * 60)
    
    # 初始化API
    if not init_wind_api():
        return
    
    try:
        # 1. 获取指数成分股
        print("1. 获取指数成分股...")
        df_constituents = get_index_constituents("000985.CSI")
        if df_constituents is None:
            return
        
        # 2. 获取股票基本信息（只取前10只作为示例）
        print("\n2. 获取股票基本信息...")
        stock_codes = df_constituents['wind_code'].head(10).tolist()
        df_info = get_stock_basic_info(stock_codes, batch_size=5)
        if df_info is None:
            return
        
        # 3. 过滤股票
        print("\n3. 过滤股票...")
        df_filtered = filter_stocks(df_info)
        
        # 4. 显示统计信息
        print("\n4. 统计信息...")
        show_statistics(df_filtered)
        
        # 5. 保存结果
        print("\n5. 保存结果...")
        output_file = save_results(df_filtered)
        print(f"结果已保存到: {output_file}")
        
    finally:
        close_wind_api()

def main():
    """主函数"""
    print("Wind API 使用示例")
    print("=" * 80)
    
    # 首先测试连接
    print("测试Wind API连接...")
    if not test_wind_connection():
        print("Wind API连接失败，请检查配置")
        return
    
    print("Wind API连接正常，开始示例演示...")
    
    # 运行各个示例
    example_get_index_constituents()
    example_get_stock_info()
    example_get_stock_quotes()
    example_get_realtime_quotes()
    example_get_tick_data()
    example_get_history_quotes()
    example_get_batch_history_quotes()
    example_complete_workflow()
    
    print("\n" + "=" * 80)
    print("所有示例演示完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
