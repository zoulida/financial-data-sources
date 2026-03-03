# -*- coding: utf-8 -*-
"""
调试tick数据获取
"""

import sys
import numpy as np
from pathlib import Path

# 添加路径
TOOLS_PATH = Path(r"D:\pythonworkspace\zldtools")
if TOOLS_PATH.exists() and str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

from xtquant import xtdata


def debug_tick_data():
    """调试tick数据获取"""
    print("调试tick数据获取...")
    
    # 测试几只股票
    test_codes = ['000001.SZ', '000002.SZ', '600000.SH']
    
    try:
        print(f"测试股票：{test_codes}")
        tick_data = xtdata.get_market_data(
            stock_list=test_codes,
            period='tick',
            count=1
        )
        
        print(f"返回数据类型：{type(tick_data)}")
        print(f"返回数据键：{list(tick_data.keys()) if isinstance(tick_data, dict) else 'Not a dict'}")
        
        for code in test_codes:
            if code in tick_data:
                tick_info = tick_data[code]
                print(f"\n{code}:")
                print(f"  数据类型：{type(tick_info)}")
                
                if isinstance(tick_info, dict):
                    print(f"  字段：{list(tick_info.keys())}")
                    if 'amount' in tick_info:
                        print(f"  amount: {tick_info['amount']}")
                    if 'lastPrice' in tick_info:
                        print(f"  lastPrice: {tick_info['lastPrice']}")
                elif hasattr(tick_info, '__len__') and len(tick_info) > 0:
                    # numpy数组格式
                    print(f"  数组长度：{len(tick_info)}")
                    if len(tick_info) > 0:
                        # 获取最新的一条数据
                        latest_data = tick_info[-1]
                        print(f"  最新数据类型：{type(latest_data)}")
                        if isinstance(latest_data, (tuple, list, np.ndarray)):
                            print(f"  数据长度：{len(latest_data)}")
                            if len(latest_data) >= 7:  # amount通常在索引6的位置
                                amount = latest_data[6]
                                print(f"  amount (索引6): {amount}")
                            if len(latest_data) >= 2:  # price通常在索引1的位置
                                price = latest_data[1]
                                print(f"  price (索引1): {price}")
                        else:
                            print(f"  数据内容：{latest_data}")
                else:
                    print(f"  数据内容：{tick_info}")
            else:
                print(f"\n{code}: 无数据")
                
    except Exception as e:
        print(f"获取tick数据失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_tick_data()
