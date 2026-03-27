#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试download_history_data接口获取期货数据
"""

from xtquant import xtdata
import pandas as pd
from datetime import datetime

def test_download_futures():
    """测试下载期货数据"""
    print("=== 测试download_history_data接口获取期货数据 ===")
    
    futures_codes = [
        "AU2406.SHFE", "AG2406.SHFE", "CU2406.SHFE", "AL2406.SHFE",
        "AU2412.SHFE", "AG2412.SHFE", "CU2412.SHFE", "AL2412.SHFE",
        "AU2501.SHFE", "AG2501.SHFE", "CU2501.SHFE", "AL2501.SHFE"
    ]
    
    for code in futures_codes:
        try:
            print(f"\n尝试下载期货数据: {code}")
            
            # 先下载历史数据
            result = xtdata.download_history_data(
                stock_code=code,
                period='1d',
                start_time='20230101',
                end_time='20241019'
            )
            
            print(f"下载结果: {result}")
            
            # 然后尝试获取数据
            data = xtdata.get_market_data_ex(
                field_list=['close'],
                stock_list=[code],
                period='1d',
                start_time='20230101',
                end_time='20241019',
                count=10  # 只获取最近10天
            )
            
            if data and code in data:
                df = data[code]
                print(f"✅ {code}: 数据形状 {df.shape}, 列名 {df.columns.tolist()}")
                if not df.empty:
                    print(f"   最新数据: {df.tail(3)}")
                    return code, df  # 找到有效数据就返回
                else:
                    print(f"   ❌ 数据为空")
            else:
                print(f"❌ {code}: 未获取到数据")
                
        except Exception as e:
            print(f"❌ {code}: 错误 {e}")
    
    return None, None

if __name__ == "__main__":
    print("开始测试download_history_data接口...")
    
    successful_code, successful_data = test_download_futures()
    
    if successful_code:
        print(f"\n🎉 找到有效的期货代码: {successful_code}")
        print(f"数据点数: {len(successful_data)}")
    else:
        print("\n❌ 未找到任何有效的期货数据")
    
    print("\n测试完成！")
