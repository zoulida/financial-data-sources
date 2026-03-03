# -*- coding: utf-8 -*-
"""
测试get_full_tick数据格式
"""

import sys
from pathlib import Path

# 添加路径
TOOLS_PATH = Path(r"D:\pythonworkspace\zldtools")
if TOOLS_PATH.exists() and str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

from xtquant import xtdata


def test_full_tick():
    """测试get_full_tick数据格式"""
    print("测试get_full_tick数据格式...")
    
    try:
        full_tick = xtdata.get_full_tick(['SH', 'SZ'])
        print(f"数据类型：{type(full_tick)}")
        print(f"数据长度：{len(full_tick)}")
        
        # 查看前几个股票的数据
        stock_codes = list(full_tick.keys())[:5]
        
        for code in stock_codes:
            tick_info = full_tick[code]
            print(f"\n{code}:")
            print(f"  数据类型：{type(tick_info)}")
            
            if isinstance(tick_info, dict):
                print(f"  字段：{list(tick_info.keys())}")
                if 'amount' in tick_info:
                    print(f"  amount: {tick_info['amount']}")
                if 'lastPrice' in tick_info:
                    print(f"  lastPrice: {tick_info['lastPrice']}")
            elif hasattr(tick_info, '__len__'):
                print(f"  数据长度：{len(tick_info)}")
                if len(tick_info) >= 7:
                    amount = tick_info[6]
                    print(f"  amount (索引6): {amount}")
                if len(tick_info) >= 2:
                    price = tick_info[1]
                    print(f"  price (索引1): {price}")
            else:
                print(f"  数据内容：{tick_info}")
                
        # 统计有数据的股票数量
        data_count = 0
        total_amount = 0
        
        for code, tick_info in full_tick.items():
            if isinstance(tick_info, dict) and 'amount' in tick_info:
                amount = tick_info['amount']
                if amount > 0:
                    data_count += 1
                    total_amount += amount
            elif hasattr(tick_info, '__len__') and len(tick_info) >= 7:
                amount = tick_info[6]
                if amount > 0:
                    data_count += 1
                    total_amount += amount
        
        print(f"\n=== 统计结果 ===")
        print(f"总股票数：{len(full_tick)}")
        print(f"有成交股票：{data_count}")
        print(f"总成交额：{total_amount:,.0f}")
        
    except Exception as e:
        print(f"获取数据失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_full_tick()
