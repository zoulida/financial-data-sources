#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SHFE期货数据获取
"""

from xtquant import xtdata
import pandas as pd
from datetime import datetime

def test_shfe_futures():
    """测试SHFE期货数据获取"""
    print("=== 测试SHFE期货数据获取 ===")
    
    futures_codes = [
        "AU0.SHFE", "AU2406.SHFE", "AU2412.SHFE", "AU2501.SHFE",
        "AG0.SHFE", "AG2406.SHFE", "AG2412.SHFE", "AG2501.SHFE",
        "CU0.SHFE", "CU2406.SHFE", "CU2412.SHFE", "CU2501.SHFE",
        "AL0.SHFE", "AL2406.SHFE", "AL2412.SHFE", "AL2501.SHFE"
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

if __name__ == "__main__":
    print("开始测试SHFE期货数据获取...")
    test_shfe_futures()
    print("\n测试完成！")
