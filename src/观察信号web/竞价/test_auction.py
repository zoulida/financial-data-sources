# -*- coding: utf-8 -*-
"""
竞价监控测试脚本
用于快速测试功能
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加路径
TOOLS_PATH = Path(r"D:\pythonworkspace\zldtools")
if TOOLS_PATH.exists() and str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

try:
    from tools.tradeCal import is_open_day
    from xtquant import xtdata
except ImportError as e:
    print(f"导入错误：{e}")
    sys.exit(1)


def test_get_a_share_codes():
    """测试获取A股代码"""
    print("测试：获取A股代码列表")
    try:
        codes = xtdata.get_stock_list_in_sector("沪深A股")
        codes = [c for c in codes if not (c.startswith(('688', '689', '83', '87')))]
        print(f"成功获取 {len(codes)} 只A股")
        print(f"前5只：{codes[:5]}")
        return codes[:10]  # 返回前10只用于测试
    except Exception as e:
        print(f"失败：{e}")
        return []


def test_is_trading_day():
    """测试判断交易日"""
    print("\n测试：判断交易日")
    today = datetime.now().strftime("%Y%m%d")
    is_trading = is_open_day(today)
    print(f"今天 {today} 是否交易日：{'是' if is_trading else '否'}")
    return is_trading


def test_tick_data(codes):
    """测试获取tick数据"""
    print("\n测试：获取tick数据")
    if not codes:
        print("没有股票代码，跳过测试")
        return
    
    try:
        # 只测试前3只股票
        test_codes = codes[:3]
        print(f"测试股票：{test_codes}")
        
        tick_data = xtdata.get_market_data(
            stock_list=test_codes,
            period='tick',
            count=1
        )
        
        for code in test_codes:
            if code in tick_data and not tick_data[code].empty:
                print(f"{code}: 获取到tick数据")
                print(f"  字段：{list(tick_data[code].columns)}")
                if 'amount' in tick_data[code].iloc[-1]:
                    amount = tick_data[code].iloc[-1]['amount']
                    print(f"  amount: {amount}")
            else:
                print(f"{code}: 无数据")
                
    except Exception as e:
        print(f"获取tick数据失败：{e}")


def main():
    """主测试函数"""
    print("=" * 50)
    print("竞价监控功能测试")
    print("=" * 50)
    
    # 测试1：获取A股代码
    codes = test_get_a_share_codes()
    
    # 测试2：判断交易日
    is_trading = test_is_trading_day()
    
    # 测试3：获取tick数据（如果是交易时间）
    current_hour = datetime.now().hour
    if 9 <= current_hour <= 15:  # 交易时间段
        test_tick_data(codes)
    else:
        print(f"\n当前时间 {current_hour} 点不在交易时间内，跳过tick数据测试")
    
    print("\n测试完成")


if __name__ == "__main__":
    main()
