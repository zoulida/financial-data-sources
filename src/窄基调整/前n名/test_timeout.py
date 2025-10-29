#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试超时机制
"""

import sys
import os
import time

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData
    USE_PROJECT_MODULE = True
    print("使用项目数据下载模块")
except ImportError as e:
    USE_PROJECT_MODULE = False
    print(f"项目数据下载模块不可用: {e}")

def test_timeout():
    """测试超时机制"""
    if not USE_PROJECT_MODULE:
        print("项目模块不可用，无法测试")
        return
    
    print("测试超时机制...")
    
    # 测试正常情况
    print("\n1. 测试正常情况:")
    start_time = time.time()
    try:
        df = getDayData(
            stock_code="000001.SZ",
            start_date="20250101",
            end_date="20250110",
            is_download=0,
            dividend_type='front'
        )
        end_time = time.time()
        print(f"  成功获取数据，耗时: {end_time - start_time:.2f}秒")
        if df is not None:
            print(f"  数据行数: {len(df)}")
    except Exception as e:
        print(f"  获取失败: {e}")
    
    # 测试异常股票代码
    print("\n2. 测试异常股票代码:")
    start_time = time.time()
    try:
        df = getDayData(
            stock_code="999999.SZ",  # 不存在的股票
            start_date="20250101",
            end_date="20250110",
            is_download=0,
            dividend_type='front'
        )
        end_time = time.time()
        print(f"  耗时: {end_time - start_time:.2f}秒")
        if df is not None:
            print(f"  数据行数: {len(df)}")
        else:
            print("  返回None")
    except Exception as e:
        print(f"  获取失败: {e}")

if __name__ == "__main__":
    test_timeout()
