#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试订单查询功能
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

def debug_orders():
    print("调试订单查询功能...")
    
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
            print("交易器连接成功")
            
            # 查询所有订单
            print("\n=== 查询所有订单 ===")
            orders = trader.get_orders()
            print(f"总订单数: {len(orders)}")
            
            target_stock = "513030.SH"
            target_orders = []
            
            for i, order in enumerate(orders):
                stock_code = order.get('stock_code', '')
                order_status = order.get('order_status')
                order_volume = order.get('order_volume', 0)
                traded_volume = order.get('traded_volume', 0)
                order_price = order.get('price', 0)
                order_type = order.get('order_type')
                order_remark = order.get('order_remark', '')
                
                print(f"订单{i+1}: {stock_code} 状态={order_status} 类型={order_type} "
                      f"数量={order_volume} 成交={traded_volume} 价格={order_price} 备注={order_remark}")
                
                # 检查是否为目标股票
                if stock_code == target_stock or stock_code == target_stock.replace('.SH', ''):
                    target_orders.append(order)
            
            print(f"\n=== 目标股票 {target_stock} 订单 ===")
            print(f"目标订单数: {len(target_orders)}")
            
            for order in target_orders:
                order_id = order.get('order_id')
                order_status = order.get('order_status')
                order_volume = order.get('order_volume', 0)
                traded_volume = order.get('traded_volume', 0)
                remaining = order_volume - traded_volume
                
                print(f"  ID={order_id} 状态={order_status} 剩余={remaining} "
                      f"(总量={order_volume} 成交={traded_volume})")
                
                # 判断订单状态
                if order_status == 56:
                    print(f"    已成交")
                elif remaining > 0:
                    print(f"    未成交")
                else:
                    print(f"    其他状态")
            
            # 查询未成交订单
            print(f"\n=== 查询未成交订单 ===")
            unfilled_orders = trader.get_unfilled_orders()
            print(f"未成交订单数: {len(unfilled_orders)}")
            
            for order in unfilled_orders:
                stock_code = order.get('stock_code', '')
                if stock_code == target_stock or stock_code == target_stock.replace('.SH', ''):
                    print(f"  未成交: {order}")
            
        else:
            print("交易器连接失败")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_orders()
