#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
获取当日委托的完整示例
"""

import sys
import os
import pandas as pd
from datetime import datetime

# 添加路径以便导入模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from easy_qmt_trader_zld import easy_qmt_trader


def get_today_orders_demo():
    """获取当日委托的完整演示"""
    
    print("=" * 60)
    print("获取当日委托完整示例")
    print("=" * 60)
    
    # 配置参数（请根据实际情况修改）
    QMT_PATH = r'D:\国金证券QMT交易端\userdata_mini'  # QMT 用户数据路径
    ACCOUNT = '8886063599'                    # 资金账号
    SESSION_ID = 123456                     # 会话ID
    
    print(f"QMT 路径: {QMT_PATH}")
    print(f"资金账号: {ACCOUNT}")
    print(f"会话ID: {SESSION_ID}")
    
    # 初始化交易接口
    trader = easy_qmt_trader(
        path=QMT_PATH,
        account=ACCOUNT,
        session_id=SESSION_ID
    )
    
    try:
        # 1. 连接到交易系统
        print("\n[步骤1] 连接交易系统...")
        connect_result = trader.connect()
        
        if connect_result != 0:
            print(f"连接失败，错误码: {connect_result}")
            print("请确保:")
            print("1. QMT 客户端已启动")
            print("2. 路径配置正确")
            print("3. 账号配置正确")
            return
        
        print("连接成功！")
        
        # 2. 获取当日委托
        print("\n[步骤2] 获取当日委托...")
        orders_df = trader.sync_orders()
        
        if orders_df.empty:
            print("当前无委托数据")
            return
        
        print(f"成功获取到 {len(orders_df)} 条委托记录")
        
        # 3. 分析委托状态
        print("\n[步骤3] 委托状态分析:")
        status_summary = orders_df['委托状态'].value_counts()
        print("委托状态统计:")
        for status, count in status_summary.items():
            print(f"  {status}: {count} 条")
        
        # 4. 按状态分类显示
        print("\n[步骤4] 委托详情:")
        
        # 4.1 未成交委托
        pending_orders = orders_df[orders_df['委托状态'].isin(['已报', '部分成交'])]
        if not pending_orders.empty:
            print(f"\n未成交委托 ({len(pending_orders)} 条):")
            display_cols = ['证券代码', '委托类型', '委托数量', '成交数量', '委托价格', '委托状态']
            print(pending_orders[display_cols].to_string(index=False))
        else:
            print("\n无未成交委托")
        
        # 4.2 已成交委托
        completed_orders = orders_df[orders_df['委托状态'] == '已成']
        if not completed_orders.empty:
            print(f"\n已成交委托 ({len(completed_orders)} 条):")
            display_cols = ['证券代码', '委托类型', '委托数量', '成交数量', '委托价格']
            print(completed_orders[display_cols].to_string(index=False))
        
        # 4.3 已撤销委托
        cancelled_orders = orders_df[orders_df['委托状态'] == '已撤']
        if not cancelled_orders.empty:
            print(f"\n已撤销委托 ({len(cancelled_orders)} 条):")
            display_cols = ['证券代码', '委托类型', '委托数量', '成交数量', '委托价格']
            print(cancelled_orders[display_cols].to_string(index=False))
        
        # 5. 保存委托数据
        print("\n[步骤5] 保存委托数据...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"当日委托_{timestamp}.csv"
        orders_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"委托数据已保存到: {csv_filename}")
        
        # 6. 计算统计信息
        print("\n[步骤6] 委托统计:")
        total_buy_amount = orders_df[orders_df['委托类型'] == '买入']['委托数量'].sum()
        total_sell_amount = orders_df[orders_df['委托类型'] == '卖出']['委托数量'].sum()
        total_traded_buy = orders_df[orders_df['委托类型'] == '买入']['成交数量'].sum()
        total_traded_sell = orders_df[orders_df['委托类型'] == '卖出']['成交数量'].sum()
        
        print(f"总委托买入数量: {total_buy_amount}")
        print(f"总委托卖出数量: {total_sell_amount}")
        print(f"总成交买入数量: {total_traded_buy}")
        print(f"总成交卖出数量: {total_traded_sell}")
        
        # 7. 按股票分组统计
        print("\n[步骤7] 按股票统计:")
        stock_stats = orders_df.groupby('证券代码').agg({
            '委托数量': 'sum',
            '成交数量': 'sum',
            '委托价格': 'mean'
        }).round(2)
        print(stock_stats.to_string())
        
        print("\n" + "=" * 60)
        print("当日委托获取完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


def get_orders_by_status():
    """按状态获取委托的便捷函数"""
    
    print("\n" + "=" * 60)
    print("按状态获取委托示例")
    print("=" * 60)
    
    # 初始化交易接口
    trader = easy_qmt_trader(
        path=r'D:\国金QMT\userdata_mini',
        account='55009640',
        session_id=123456
    )
    
    try:
        # 连接
        if trader.connect() != 0:
            print("连接失败")
            return
        
        # 获取所有委托
        all_orders = trader.sync_orders()
        
        if all_orders.empty:
            print("无委托数据")
            return
        
        # 定义状态映射
        status_map = {
            'pending': ['已报', '部分成交'],
            'completed': ['已成'],
            'cancelled': ['已撤']
        }
        
        # 按状态获取委托
        for status_name, status_list in status_map.items():
            orders = all_orders[all_orders['委托状态'].isin(status_list)]
            print(f"\n{status_name.upper()} 委托 ({len(orders)} 条):")
            if not orders.empty:
                display_cols = ['证券代码', '委托类型', '委托数量', '成交数量', '委托价格', '委托状态']
                print(orders[display_cols].to_string(index=False))
        
    except Exception as e:
        print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    # 运行完整示例
    get_today_orders_demo()
    
    print("\n" + "=" * 80 + "\n")
    
    # 运行按状态获取示例
    get_orders_by_status()
