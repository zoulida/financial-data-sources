#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试单只股票获取，查看详细错误信息
"""

import pandas as pd
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData
    USE_PROJECT_MODULE = True
    print("使用项目数据下载模块")
except ImportError as e:
    USE_PROJECT_MODULE = False
    print(f"项目数据下载模块不可用: {e}")

def test_get_stock_data():
    """测试获取单只股票数据"""
    
    stock_code = "000625.SZ"
    start_date = "20250423"
    end_date = "20250507"
    
    print("=" * 80)
    print("测试获取股票数据")
    print("=" * 80)
    print(f"股票代码: {stock_code}")
    print(f"开始日期: {start_date}")
    print(f"结束日期: {end_date}")
    print()
    
    if USE_PROJECT_MODULE:
        try:
            print("尝试从缓存读取...")
            df = getDayData(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                is_download=0,  # 从缓存读取
                dividend_type='front'
            )
            
            print(f"返回数据: {df}")
            print(f"数据类型: {type(df)}")
            
            if df is not None:
                print(f"数据行数: {len(df)}")
                print(f"数据列名: {df.columns.tolist()}")
                print("\n前5行数据:")
                print(df.head())
                
                # 检查日期列
                if 'date' in df.columns:
                    print(f"\n日期列数据类型: {df['date'].dtype}")
                    print(f"日期范围: {df['date'].min()} 至 {df['date'].max()}")
                else:
                    print("\n警告: 数据中没有'date'列")
                    print(f"索引: {df.index}")
            
        except Exception as e:
            print(f"获取数据失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("项目模块不可用，无法测试")

if __name__ == "__main__":
    test_get_stock_data()
