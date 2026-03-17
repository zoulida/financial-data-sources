#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理重复订单脚本
用于清理网格策略产生的重复订单
"""

import sys
import os
# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.网格.网格信号实盘.trader import build_qmt_trader_with_callback

def cleanup_orders(stock_code="513030.SH"):
    """清理指定股票的所有挂单"""
    print(f"开始清理 {stock_code} 的重复订单...")
    
    def dummy_callback(event):
        pass
    
    try:
        # 创建交易器
        trader = build_qmt_trader_with_callback(
            on_filled=dummy_callback,
            path=r"D:\国金证券QMT交易端\userdata_mini",
            account="8886063599",
            account_type="STOCK",
            session_id=123456
        )
        
        if not trader or not hasattr(trader, '_connected') or not trader._connected:
            print("交易器连接失败")
            return
        
        # 获取所有订单
        orders = trader.get_orders()
        print(f"查询到 {len(orders)} 个订单")
        
        # 按价格和方向分组
        price_side_groups = {}
        for order in orders:
            if order.get('stock_code') != stock_code.replace('.SH', '').replace('.SZ', ''):
                continue
                
            order_id = order.get('order_id')
            order_status = order.get('order_status')
            order_type = order.get('order_type')
            price = order.get('price', 0)
            qty = order.get('order_volume', 0)
            traded_qty = order.get('traded_volume', 0)
            
            # 只处理未成交的订单
            if order_status == 56:  # 已成交
                continue
                
            # 判断买卖方向
            if order_type == 23:
                side = "BUY"
            elif order_type == 24:
                side = "SELL"
            else:
                continue
            
            # 保留6位小数
            price_key = round(price, 6)
            key = (price_key, side)
            
            if key not in price_side_groups:
                price_side_groups[key] = []
            price_side_groups[key].append({
                'order_id': order_id,
                'qty': qty - traded_qty,
                'price': price
            })
        
        # 对每个价格方向组，只保留一个订单，取消其他重复订单
        total_cancelled = 0
        for (price, side), orders_list in price_side_groups.items():
            if len(orders_list) <= 1:
                continue
                
            print(f"\n价格 {price} {side} 有 {len(orders_list)} 个重复订单:")
            for i, order in enumerate(orders_list):
                print(f"  {i+1}. 订单ID: {order['order_id']}, 数量: {order['qty']}")
            
            # 保留第一个，取消其他的
            for i in range(1, len(orders_list)):
                order_id = orders_list[i]['order_id']
                try:
                    result = trader.cancel_order(stock_code, order_id)
                    if result == 0:
                        print(f"  ✅ 已取消订单: {order_id}")
                        total_cancelled += 1
                    else:
                        print(f"  ❌ 取消订单失败: {order_id}, 错误码: {result}")
                except Exception as e:
                    print(f"  ❌ 取消订单异常: {order_id}, 错误: {e}")
        
        print(f"\n清理完成！共取消 {total_cancelled} 个重复订单")
        
    except Exception as e:
        print(f"清理失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_orders()
