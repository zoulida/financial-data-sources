#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试获取当日委托功能
"""

import sys
import os
import pandas as pd
from datetime import datetime

# 添加路径以便导入模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from easy_qmt_trader_zld import easy_qmt_trader


def test_get_today_orders():
    """测试获取当日委托"""
    
    print("=" * 50)
    print("测试获取当日委托功能")
    print("=" * 50)
    
    # 初始化交易接口 (请根据实际情况修改参数)
    trader = easy_qmt_trader(
        path=r'D:\国金QMT\userdata_mini',  # 请修改为实际路径
        account='55009640',                # 请修改为实际账号
        session_id=123456
    )
    
    try:
        # 连接到交易系统
        print("正在连接交易系统...")
        connect_result = trader.connect()
        
        if connect_result != 0:
            print(f"连接失败，错误码: {connect_result}")
            return
        
        print("连接成功！")
        
        # 获取当日委托
        print("\n正在获取当日委托...")
        orders_df = trader.sync_orders()
        
        if not orders_df.empty:
            print(f"\n✅ 成功获取到 {len(orders_df)} 条委托记录:")
            print("-" * 80)
            
            # 显示委托信息
            for idx, order in orders_df.iterrows():
                print(f"委托 {idx + 1}:")
                print(f"  证券代码: {order['证券代码']}")
                print(f"  订单编号: {order['订单编号']}")
                print(f"  委托类型: {order['委托类型']}")
                print(f"  委托数量: {order['委托数量']}")
                print(f"  成交数量: {order['成交数量']}")
                print(f"  委托价格: {order['委托价格']}")
                print(f"  委托状态: {order['委托状态']}")
                print(f"  策略名称: {order['策略名称']}")
                print(f"  备注: {order['备注']}")
                print("-" * 40)
        else:
            print("❌ 当前无委托数据")
        
        # 显示完整的 DataFrame
        print("\n📊 完整委托数据:")
        print(orders_df.to_string())
        
        # 保存到 CSV 文件
        if not orders_df.empty:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"当日委托_{timestamp}.csv"
            orders_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"\n💾 委托数据已保存到: {csv_filename}")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n测试完成")


def test_get_orders_with_filter():
    """测试获取委托并筛选特定状态"""
    
    print("=" * 50)
    print("测试获取委托并筛选特定状态")
    print("=" * 50)
    
    # 初始化交易接口
    trader = easy_qmt_trader(
        path=r'D:\国金QMT\userdata_mini',  # 请修改为实际路径
        account='55009640',                # 请修改为实际账号
        session_id=123456
    )
    
    try:
        # 连接
        connect_result = trader.connect()
        if connect_result != 0:
            print(f"连接失败，错误码: {connect_result}")
            return
        
        # 获取所有委托
        orders_df = trader.sync_orders()
        
        if not orders_df.empty:
            print(f"\n📈 委托状态统计:")
            status_counts = orders_df['委托状态'].value_counts()
            for status, count in status_counts.items():
                print(f"  {status}: {count} 条")
            
            # 筛选未成交委托
            pending_orders = orders_df[orders_df['委托状态'].isin(['已报', '部分成交'])]
            if not pending_orders.empty:
                print(f"\n⏳ 未成交委托 ({len(pending_orders)} 条):")
                print(pending_orders[['证券代码', '委托类型', '委托数量', '成交数量', '委托价格']].to_string())
            else:
                print("\n✅ 无未成交委托")
            
            # 筛选已成交委托
            completed_orders = orders_df[orders_df['委托状态'] == '已成']
            if not completed_orders.empty:
                print(f"\n✅ 已成交委托 ({len(completed_orders)} 条):")
                print(completed_orders[['证券代码', '委托类型', '委托数量', '成交数量', '委托价格']].to_string())
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")


if __name__ == "__main__":
    # 运行基本测试
    test_get_today_orders()
    
    print("\n" + "=" * 80 + "\n")
    
    # 运行筛选测试
    test_get_orders_with_filter()
