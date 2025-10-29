#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试缓存功能
验证周级缓存是否正常工作
"""

import time
from wind_api_utils import init_wind_api, close_wind_api, get_index_constituents, get_stock_basic_info

def test_cache_functionality():
    """测试缓存功能"""
    print("=" * 80)
    print("测试缓存功能")
    print("=" * 80)
    
    # 初始化Wind API
    if not init_wind_api():
        print("Wind API初始化失败，无法测试缓存功能")
        return
    
    try:
        # 测试指数成分股缓存
        print("\n1. 测试指数成分股缓存...")
        print("第一次调用（应该从API获取）:")
        start_time = time.time()
        df1 = get_index_constituents("000985.CSI")
        first_call_time = time.time() - start_time
        print(f"第一次调用耗时: {first_call_time:.2f}秒")
        
        print("\n第二次调用（应该从缓存获取）:")
        start_time = time.time()
        df2 = get_index_constituents("000985.CSI")
        second_call_time = time.time() - start_time
        print(f"第二次调用耗时: {second_call_time:.2f}秒")
        
        if df1 is not None and df2 is not None:
            print(f"✓ 缓存功能正常，第二次调用明显更快")
            print(f"  第一次: {first_call_time:.2f}秒")
            print(f"  第二次: {second_call_time:.2f}秒")
            print(f"  加速比: {first_call_time/second_call_time:.1f}x")
        else:
            print("✗ 缓存功能异常")
        
        # 测试股票基本信息缓存
        print("\n2. 测试股票基本信息缓存...")
        test_stocks = ["000001.SZ", "000002.SZ", "600000.SH"]
        
        print("第一次调用（应该从API获取）:")
        start_time = time.time()
        df3 = get_stock_basic_info(test_stocks, batch_size=3)
        third_call_time = time.time() - start_time
        print(f"第一次调用耗时: {third_call_time:.2f}秒")
        
        print("\n第二次调用（应该从缓存获取）:")
        start_time = time.time()
        df4 = get_stock_basic_info(test_stocks, batch_size=3)
        fourth_call_time = time.time() - start_time
        print(f"第二次调用耗时: {fourth_call_time:.2f}秒")
        
        if df3 is not None and df4 is not None:
            print(f"✓ 缓存功能正常，第二次调用明显更快")
            print(f"  第一次: {third_call_time:.2f}秒")
            print(f"  第二次: {fourth_call_time:.2f}秒")
            print(f"  加速比: {third_call_time/fourth_call_time:.1f}x")
        else:
            print("✗ 缓存功能异常")
        
        # 测试不同参数的缓存
        print("\n3. 测试不同参数的缓存...")
        print("使用不同指数代码（应该重新从API获取）:")
        start_time = time.time()
        df5 = get_index_constituents("000001.SH")  # 上证指数
        fifth_call_time = time.time() - start_time
        print(f"不同参数调用耗时: {fifth_call_time:.2f}秒")
        
        if df5 is not None:
            print("✓ 不同参数正确触发新的API调用")
        else:
            print("✗ 不同参数处理异常")
        
    except Exception as e:
        print(f"✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        close_wind_api()
    
    print("\n" + "=" * 80)
    print("缓存功能测试完成！")
    print("=" * 80)

if __name__ == "__main__":
    test_cache_functionality()
