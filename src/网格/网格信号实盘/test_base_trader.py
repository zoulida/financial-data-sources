#!/usr/bin/env python3
"""
测试base_trader_zld集成的脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.网格.网格信号实盘.trader import build_qmt_trader_with_callback

def test_callback(event):
    """测试成交回调"""
    print(f"收到成交回调: {event}")

def main():
    print("测试base_trader_zld集成...")
    
    # 测试交易器构建
    try:
        trader = build_qmt_trader_with_callback(
            on_filled=test_callback,
            path=r"D:\国金证券QMT交易端\userdata_mini",
            account="8886063599",
            account_type="STOCK",
            session_id=123456
        )
        
        print(f"交易器创建成功: {type(trader)}")
        print(f"交易器方法: {[method for method in dir(trader) if not method.startswith('_')]}")
        
        # 测试查询功能（如果已连接）
        if hasattr(trader, '_connected') and trader._connected:
            positions = trader.get_positions()
            print(f"持仓查询结果: {len(positions)} 个持仓")
            
            orders = trader.get_orders()
            print(f"委托查询结果: {len(orders)} 个委托")
        else:
            print("交易器未连接，跳过查询测试")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
