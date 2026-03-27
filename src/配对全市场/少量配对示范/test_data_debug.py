#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取调试脚本
"""

from xtquant import xtdata
import pandas as pd
from datetime import datetime

def test_futures_data():
    """测试期货数据获取"""
    print("=== 测试期货数据获取 ===")
    
    futures_codes = [
        "AU0.SHF", "AG0.SHF", "CU0.SHF", "CU1.SHF", "AL0.SHF", "AL1.SHF",
        "AU0", "AG0", "CU0", "CU1", "AL0", "AL1",
        "AU0.SH", "AG0.SH", "CU0.SH", "CU1.SH", "AL0.SH", "AL1.SH"
    ]
    
    for code in futures_codes:
        try:
            print(f"\n尝试获取期货数据: {code}")
            data = xtdata.get_market_data_ex(
                field_list=['close'],
                stock_list=[code],
                period='1d',
                start_time='20240101',
                end_time='20241231',
                count=10  # 只获取最近10天
            )
            
            if data and code in data:
                df = data[code]
                print(f"✅ {code}: 数据形状 {df.shape}, 列名 {df.columns.tolist()}")
                if not df.empty:
                    print(f"   最新数据: {df.tail(3)}")
                else:
                    print(f"   ❌ 数据为空")
            else:
                print(f"❌ {code}: 未获取到数据")
                
        except Exception as e:
            print(f"❌ {code}: 错误 {e}")

def test_etf_data():
    """测试ETF数据获取"""
    print("\n=== 测试ETF数据获取 ===")
    
    etf_codes = [
        "518880.SH", "518800.SH", "510300.SH", "510500.SH", "159949.SZ", "512880.SH"
    ]
    
    for code in etf_codes:
        try:
            print(f"\n尝试获取ETF数据: {code}")
            data = xtdata.get_market_data_ex(
                field_list=['close'],
                stock_list=[code],
                period='1d',
                start_time='20240101',
                end_time='20241231',
                count=10  # 只获取最近10天
            )
            
            if data and code in data:
                df = data[code]
                print(f"✅ {code}: 数据形状 {df.shape}, 列名 {df.columns.tolist()}")
                if not df.empty:
                    print(f"   最新数据: {df.tail(3)}")
                else:
                    print(f"   ❌ 数据为空")
            else:
                print(f"❌ {code}: 未获取到数据")
                
        except Exception as e:
            print(f"❌ {code}: 错误 {e}")

def test_index_data():
    """测试指数数据获取"""
    print("\n=== 测试指数数据获取 ===")
    
    index_codes = [
        "000300.SH", "000852.SH", "000016.SH", "399303.SZ", "000905.SH"
    ]
    
    for code in index_codes:
        try:
            print(f"\n尝试获取指数数据: {code}")
            data = xtdata.get_market_data_ex(
                field_list=['close'],
                stock_list=[code],
                period='1d',
                start_time='20240101',
                end_time='20241231',
                count=10  # 只获取最近10天
            )
            
            if data and code in data:
                df = data[code]
                print(f"✅ {code}: 数据形状 {df.shape}, 列名 {df.columns.tolist()}")
                if not df.empty:
                    print(f"   最新数据: {df.tail(3)}")
                else:
                    print(f"   ❌ 数据为空")
            else:
                print(f"❌ {code}: 未获取到数据")
                
        except Exception as e:
            print(f"❌ {code}: 错误 {e}")

if __name__ == "__main__":
    print("开始数据获取调试...")
    
    # 测试期货数据
    test_futures_data()
    
    # 测试ETF数据
    test_etf_data()
    
    # 测试指数数据
    test_index_data()
    
    print("\n调试完成！")
