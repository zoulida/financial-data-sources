# -*- coding: utf-8 -*-
"""
测试批量获取tick数据
"""

import sys
import numpy as np
from pathlib import Path

# 添加路径
TOOLS_PATH = Path(r"D:\pythonworkspace\zldtools")
if TOOLS_PATH.exists() and str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

from xtquant import xtdata


def test_batch_size():
    """测试不同批量大小的数据获取"""
    print("测试批量获取tick数据...")
    
    # 获取A股代码
    try:
        all_codes = xtdata.get_stock_list_in_sector("沪深A股")
        all_codes = [c for c in all_codes if not (c.startswith(('688', '689', '83', '87')))]
        print(f"总股票数：{len(all_codes)}")
    except Exception as e:
        print(f"获取股票代码失败：{e}")
        return
    
    # 测试不同批量大小
    batch_sizes = [10, 50, 100, 500, 1000]
    
    for batch_size in batch_sizes:
        print(f"\n=== 测试批量大小：{batch_size} ===")
        test_codes = all_codes[:batch_size]
        
        try:
            tick_data = xtdata.get_market_data(
                stock_list=test_codes,
                period='tick',
                count=1
            )
            
            # 统计有数据的股票
            data_count = 0
            total_amount = 0
            
            for code in test_codes:
                if code in tick_data:
                    tick_info = tick_data[code]
                    if hasattr(tick_info, '__len__') and len(tick_info) > 0:
                        latest_data = tick_info[-1]
                        if isinstance(latest_data, (tuple, list)) or hasattr(latest_data, '__len__'):
                            if len(latest_data) >= 7:
                                amount = latest_data[6]
                                if amount > 0:
                                    data_count += 1
                                    total_amount += amount
            
            print(f"  有数据股票：{data_count}/{batch_size}")
            print(f"  总金额：{total_amount:,.0f}")
            
        except Exception as e:
            print(f"  获取失败：{e}")


def test_specific_stocks():
    """测试特定股票"""
    print("\n=== 测试特定活跃股票 ===")
    
    # 一些常见的活跃股票
    active_stocks = [
        '000001.SZ', '000002.SZ', '000858.SZ', '002415.SZ', '300015.SZ',
        '600000.SH', '600036.SH', '600519.SH', '600887.SH', '601318.SH'
    ]
    
    try:
        tick_data = xtdata.get_market_data(
            stock_list=active_stocks,
            period='tick',
            count=1
        )
        
        print("活跃股票数据：")
        for code in active_stocks:
            if code in tick_data:
                tick_info = tick_data[code]
                if hasattr(tick_info, '__len__') and len(tick_info) > 0:
                    latest_data = tick_info[-1]
                    if isinstance(latest_data, (tuple, list)) or hasattr(latest_data, '__len__'):
                        if len(latest_data) >= 7:
                            amount = latest_data[6]
                            price = latest_data[1] if len(latest_data) >= 2 else 0
                            print(f"  {code}: 价格={price}, 成交额={amount:,.0f}")
                        else:
                            print(f"  {code}: 数据长度不足")
                    else:
                        print(f"  {code}: 数据格式异常")
                else:
                    print(f"  {code}: 无数据")
            else:
                print(f"  {code}: 未返回")
                
    except Exception as e:
        print(f"获取活跃股票数据失败：{e}")


if __name__ == "__main__":
    test_batch_size()
    test_specific_stocks()
