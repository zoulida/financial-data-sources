#!/usr/bin/env python3
"""
测试基于base_trader_zld的订单状态同步功能
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

def test_order_sync():
    print("测试订单状态同步功能...")
    
    try:
        # 创建交易器
        trader = build_qmt_trader_with_callback(
            on_filled=test_callback,
            path=r"D:\国金证券QMT交易端\userdata_mini",
            account="8886063599",
            account_type="STOCK",
            session_id=123456
        )
        
        if trader and hasattr(trader, "_connected") and trader._connected:
            print("交易器连接成功，开始测试订单查询...")
            
            # 测试查询所有订单
            orders = trader.get_orders()
            print(f"\n=== 所有订单 ({len(orders)}个) ===")
            for i, order in enumerate(orders):
                print(f"订单{i+1}: ID={order.get('order_id')}, 代码={order.get('stock_code')}, "
                      f"状态={order.get('order_status')}, 类型={order.get('order_type')}, "
                      f"数量={order.get('order_volume')}, 成交={order.get('traded_volume')}, "
                      f"价格={order.get('price')}, 备注={order.get('order_remark')}")
            
            # 测试查询未成交订单
            unfilled_orders = trader.get_unfilled_orders()
            print(f"\n=== 未成交订单 ({len(unfilled_orders)}个) ===")
            for i, order in enumerate(unfilled_orders):
                print(f"未成交{i+1}: ID={order.get('order_id')}, 代码={order.get('stock_code')}, "
                      f"状态={order.get('order_status')} ({order.get('status_desc')}), "
                      f"数量={order.get('order_volume')}, 成交={order.get('traded_volume')}, "
                      f"价格={order.get('price')}")
            
            # 测试查询持仓
            positions = trader.get_positions()
            print(f"\n=== 持仓 ({len(positions)}个) ===")
            for i, position in enumerate(positions):
                print(f"持仓{i+1}: 代码={position.get('stock_code')}, "
                      f"数量={position.get('volume')}, 可用={position.get('can_use_volume')}, "
                      f"市值={position.get('market_value')}")
            
            print("\n订单状态同步测试完成！")
        else:
            print("交易器连接失败，无法测试订单查询功能")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_order_sync()
