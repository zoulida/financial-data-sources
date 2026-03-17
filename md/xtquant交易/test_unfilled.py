"""
Test Unfilled Orders Function
============================

专门测试未成交订单查询功能
"""

from base_trader import BaseTrader, BaseTraderCallback


def test_unfilled_orders():
    """测试未成交订单功能"""
    print("=== 测试未成交订单功能 ===")
    
    # 创建交易实例
    trader = BaseTrader(
        path=r'D:\国金证券QMT交易端\userdata_mini',
        account='8886063599',
        session_id=123456
    )
    
    # 连接
    if trader.connect() != 0:
        print("连接失败")
        return
    
    # 注册回调
    callback = BaseTraderCallback()
    trader.register_callback(callback)
    
    # 订阅
    trader.subscribe()
    
    print("\n=== 所有委托状态分析 ===")
    
    # 获取所有委托
    all_orders = trader.get_orders()
    
    if all_orders:
        # 统计各种状态
        status_count = {}
        for order in all_orders:
            status = order['order_status']
            status_count[status] = status_count.get(status, 0) + 1
        
        print("委托状态统计:")
        for status, count in sorted(status_count.items()):
            desc = trader._get_order_status_desc(status)
            print(f"  状态码 {status}: {count} 条 - {desc}")
        
        print(f"\n总委托数量: {len(all_orders)}")
        
        # 显示未成交订单
        print("\n=== 未成交订单详情 ===")
        unfilled_orders = trader.get_unfilled_orders()
        
        if unfilled_orders:
            print(f"找到 {len(unfilled_orders)} 条未成交订单:")
            for i, order in enumerate(unfilled_orders, 1):
                value = order['order_volume'] * order['price']
                print(f"{i}. {order['stock_code']} "
                      f"{order['order_volume']}股@{order['price']:.3f} "
                      f"状态:{order['status_desc']} "
                      f"金额:{value:.2f}")
            
            total_unfilled_value = sum(
                order['order_volume'] * order['price'] 
                for order in unfilled_orders
            )
            print(f"\n未成交总金额: {total_unfilled_value:.2f}")
        else:
            print("当前没有未成交订单")
            
        # 显示部分成交订单
        print("\n=== 部分成交订单 ===")
        partial_orders = [
            order for order in all_orders 
            if 0 < order['traded_volume'] < order['order_volume']
        ]
        
        if partial_orders:
            print(f"找到 {len(partial_orders)} 条部分成交订单:")
            for i, order in enumerate(partial_orders, 1):
                remaining = order['order_volume'] - order['traded_volume']
                value = remaining * order['price']
                status_desc = trader._get_order_status_desc(order['order_status'])
                print(f"{i}. {order['stock_code']} "
                      f"剩余{remaining}股@{order['price']:.3f} "
                      f"状态:{status_desc} "
                      f"剩余金额:{value:.2f}")
        else:
            print("当前没有部分成交订单")
    
    else:
        print("今日无委托记录")
    
    # 停止
    trader.stop()
    print("\n测试完成")


if __name__ == "__main__":
    test_unfilled_orders()
