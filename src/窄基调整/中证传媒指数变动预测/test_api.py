#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Wind API连接和指数成分股获取
"""

import pandas as pd
from datetime import datetime
from wind_api_utils import init_wind_api, close_wind_api, get_index_constituents, get_stock_basic_info, test_wind_connection

def test_wind_api():
    """测试Wind API连接"""
    print("=" * 80)
    print("测试Wind API连接和指数成分股获取")
    print("=" * 80)
    
    # 0. 快速连接测试
    print("\n0. 快速连接测试...")
    if not test_wind_connection():
        print("快速连接测试失败，跳过详细测试")
        return
    
    # 1. 测试Wind API初始化
    print("\n1. 测试Wind API初始化...")
    if not init_wind_api():
        return
    
    # 2. 测试获取指数成分股
    print("\n2. 测试获取指数成分股...")
    
    # 测试多个可能的指数代码
    test_indices = [
        "000985.CSI",  # 中证全指指数
        "000985.SH",   # 中证全指指数（上海）
        "000985.SZ",   # 中证全指指数（深圳）
    ]
    
    for index_code in test_indices:
        print(f"\n   尝试: {index_code}")
        
        df_constituents = get_index_constituents(index_code)
        if df_constituents is not None:
            print(f"   ✓ 获取成功!")
            print(f"   字段数: {len(df_constituents.columns)}")
            print(f"   记录数: {len(df_constituents)}")
            print(f"   字段列表: {list(df_constituents.columns)}")
            
            print(f"\n   前5条记录:")
            print(df_constituents.head().to_string())
            break
        else:
            print(f"   ✗ 未获取到数据")
    
    # 3. 测试获取股票基本信息
    print("\n3. 测试获取股票基本信息...")
    
    # 测试股票代码
    test_stocks = ["000001.SZ", "000002.SZ", "600000.SH"]
    
    df_info = get_stock_basic_info(test_stocks, batch_size=3)
    if df_info is not None:
        print(f"   ✓ 获取成功!")
        print(f"\n   股票信息:")
        print(df_info.to_string())
    else:
        print(f"   ✗ 获取失败")
    
    # 4. 关闭Wind API
    print("\n4. 关闭Wind API...")
    close_wind_api()
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)

if __name__ == "__main__":
    test_wind_api()

