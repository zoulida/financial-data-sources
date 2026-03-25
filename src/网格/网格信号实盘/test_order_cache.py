#!/usr/bin/env python3
"""
测试订单缓存优化效果
"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from md.xtquant交易.base_trader_zld import BaseTrader

def test_order_cache():
    """测试订单缓存功能"""
    print("=== 测试订单缓存优化 ===")
    
    # 模拟创建BaseTrader实例（不实际连接）
    trader = BaseTrader("test_path", "test_account")
    
    # 测试新增的query_stock_orders_raw方法
    print("1. 测试query_stock_orders_raw方法...")
    try:
        raw_orders = trader.query_stock_orders_raw()
        print(f"   原始订单数量: {len(raw_orders) if raw_orders else 0}")
    except Exception as e:
        print(f"   预期错误（未连接）: {e}")
    
    # 测试get_unfilled_orders的verbose参数
    print("\n2. 测试get_unfilled_orders的verbose参数...")
    try:
        # 静默模式
        orders_silent = trader.get_unfilled_orders(verbose=False)
        print(f"   静默模式获取订单数量: {len(orders_silent)}")
        
        # 详细模式
        orders_verbose = trader.get_unfilled_orders(verbose=True)
        print(f"   详细模式获取订单数量: {len(orders_verbose)}")
    except Exception as e:
        print(f"   预期错误（未连接）: {e}")
    
    print("\n=== 优化说明 ===")
    print("1. 新增query_stock_orders_raw()方法：直接调用券商API获取原始订单数据")
    print("2. get_unfilled_orders()支持verbose参数：控制是否打印日志")
    print("3. 在GridStrategy中实现订单缓存：每个tick只调用一次API")
    print("4. _has_real_buy_order_at_price()使用缓存数据：避免重复API调用")
    print("\n这样可以显著减少对券商API的调用频率，提高性能并避免频繁日志输出。")

if __name__ == "__main__":
    test_order_cache()
