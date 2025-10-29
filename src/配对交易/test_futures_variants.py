#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试各种期货代码格式
"""

from xtquant import xtdata
import pandas as pd
from datetime import datetime, timedelta

def test_futures_variants():
    """测试各种期货代码格式"""
    print("=== 测试各种期货代码格式 ===")
    
    # 尝试不同的时间范围
    time_ranges = [
        ('20230101', '20231231'),  # 2023年
        ('20220101', '20221231'),  # 2022年
        ('20210101', '20211231'),  # 2021年
        ('20200101', '20201231'),  # 2020年
    ]
    
    # 尝试不同的代码格式
    code_formats = [
        # 主力合约格式
        "AU0.SHFE", "AG0.SHFE", "CU0.SHFE", "AL0.SHFE",
        # 具体月份格式
        "AU2406.SHFE", "AG2406.SHFE", "CU2406.SHFE", "AL2406.SHFE",
        "AU2412.SHFE", "AG2412.SHFE", "CU2412.SHF", "AL2412.SHF",
        # 其他可能格式
        "AU0.SHF", "AG0.SHF", "CU0.SHF", "AL0.SHF",
        "AU0.SH", "AG0.SH", "CU0.SH", "AL0.SH",
        # 不带后缀
        "AU0", "AG0", "CU0", "AL0",
        # 其他交易所
        "AU0.DCE", "AG0.DCE", "CU0.DCE", "AL0.DCE",
    ]
    
    for start_date, end_date in time_ranges:
        print(f"\n=== 测试时间范围: {start_date} - {end_date} ===")
        
        for code in code_formats:
            try:
                data = xtdata.get_market_data_ex(
                    field_list=['close'],
                    stock_list=[code],
                    period='1d',
                    start_time=start_date,
                    end_time=end_date,
                    count=5  # 只获取5天
                )
                
                if data and code in data and not data[code].empty:
                    df = data[code]
                    print(f"✅ {code}: 数据形状 {df.shape}, 最新数据: {df.tail(2).values.flatten()}")
                    return code, df  # 找到有效数据就返回
                else:
                    print(f"❌ {code}: 无数据")
                    
            except Exception as e:
                print(f"❌ {code}: 错误 {str(e)[:50]}...")
    
    return None, None

def test_futures_list():
    """测试获取期货列表"""
    print("\n=== 测试获取期货列表 ===")
    try:
        # 尝试获取期货列表
        futures_list = xtdata.get_stock_list_in_sector('期货')
        if futures_list:
            print(f"✅ 获取到期货列表，共{len(futures_list)}个")
            print("前10个期货代码:", futures_list[:10])
            return futures_list
        else:
            print("❌ 无法获取期货列表")
    except Exception as e:
        print(f"❌ 获取期货列表失败: {e}")
    
    return None

if __name__ == "__main__":
    print("开始测试期货数据获取...")
    
    # 测试期货列表
    futures_list = test_futures_list()
    
    # 测试各种代码格式
    successful_code, successful_data = test_futures_variants()
    
    if successful_code:
        print(f"\n🎉 找到有效的期货代码: {successful_code}")
    else:
        print("\n❌ 未找到任何有效的期货数据")
    
    print("\n测试完成！")
