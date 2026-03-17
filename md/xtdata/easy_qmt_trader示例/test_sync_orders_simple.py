#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单测试 sync_orders 方法
"""

import sys
import os
import pandas as pd
from datetime import datetime

# 添加路径以便导入模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_sync_orders_method():
    """测试 sync_orders 方法的功能"""
    print("=" * 50)
    print("测试 sync_orders 方法")
    print("=" * 50)
    
    try:
        # 导入模块
        from easy_qmt_trader_zld import easy_qmt_trader
        print("✅ 成功导入 easy_qmt_trader 模块")
        
        # 检查类是否有 sync_orders 方法
        if hasattr(easy_qmt_trader, 'sync_orders'):
            print("✅ easy_qmt_trader 类包含 sync_orders 方法")
            
            # 查看方法签名
            import inspect
            sig = inspect.signature(easy_qmt_trader.sync_orders)
            print(f"📋 方法签名: sync_orders{sig}")
            
            # 查看方法文档
            doc = easy_qmt_trader.sync_orders.__doc__
            if doc:
                print("📖 方法文档:")
                print(doc.strip())
            
        else:
            print("❌ easy_qmt_trader 类不包含 sync_orders 方法")
            return
        
        # 创建实例（但不连接）
        print("\n🔧 创建交易实例...")
        trader = easy_qmt_trader(
            path=r'D:\国金QMT\userdata_mini',
            account='55009640',
            session_id=123456
        )
        print("✅ 交易实例创建成功")
        
        # 检查实例属性
        print(f"📊 latest_orders 初始状态: {type(trader.latest_orders)}")
        print(f"📊 latest_orders 是否为空: {trader.latest_orders.empty}")
        
        # 测试 _ensure_connected 方法
        print("\n🔍 测试连接检查...")
        connected = trader._ensure_connected()
        print(f"📌 连接状态检查结果: {connected}")
        
        # 尝试调用 sync_orders（预期会失败，因为没有连接）
        print("\n📡 尝试调用 sync_orders（无连接状态）...")
        result = trader.sync_orders()
        print(f"📊 返回结果类型: {type(result)}")
        print(f"📊 返回结果是否为空: {result.empty}")
        
        print("\n✅ sync_orders 方法测试完成")
        
    except ImportError as e:
        print(f"❌ 导入模块失败: {str(e)}")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


def test_mock_orders():
    """使用模拟数据测试委托数据处理"""
    print("\n" + "=" * 50)
    print("测试委托数据处理（模拟数据）")
    print("=" * 50)
    
    # 创建模拟委托数据
    mock_data = [
        {
            "账号类型": "STOCK",
            "资金账号": "55009640",
            "证券代码": "600031.SH",
            "订单编号": "12345",
            "委托类型": "买入",
            "委托数量": 1000,
            "成交数量": 500,
            "委托价格": 10.50,
            "委托状态": "部分成交",
            "策略名称": "test_strategy",
            "备注": "测试买入"
        },
        {
            "账号类型": "STOCK", 
            "资金账号": "55009640",
            "证券代码": "000001.SZ",
            "订单编号": "12346",
            "委托类型": "卖出",
            "委托数量": 500,
            "成交数量": 500,
            "委托价格": 15.20,
            "委托状态": "已成",
            "策略名称": "test_strategy",
            "备注": "测试卖出"
        }
    ]
    
    # 创建 DataFrame
    orders_df = pd.DataFrame(mock_data)
    
    print("📊 模拟委托数据:")
    print(orders_df.to_string())
    
    # 测试数据筛选
    print(f"\n📈 委托状态统计:")
    status_counts = orders_df['委托状态'].value_counts()
    for status, count in status_counts.items():
        print(f"  {status}: {count} 条")
    
    # 筛选未成交委托
    pending_orders = orders_df[orders_df['委托状态'].isin(['已报', '部分成交'])]
    print(f"\n⏳ 未成交委托 ({len(pending_orders)} 条):")
    if not pending_orders.empty:
        print(pending_orders[['证券代码', '委托类型', '委托数量', '成交数量', '委托价格']].to_string())
    
    # 筛选已成交委托
    completed_orders = orders_df[orders_df['委托状态'] == '已成']
    print(f"\n✅ 已成交委托 ({len(completed_orders)} 条):")
    if not completed_orders.empty:
        print(completed_orders[['证券代码', '委托类型', '委托数量', '成交数量', '委托价格']].to_string())
    
    print("\n✅ 数据处理测试完成")


if __name__ == "__main__":
    test_sync_orders_method()
    test_mock_orders()
