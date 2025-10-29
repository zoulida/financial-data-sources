#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新纳入股票表现分析脚本
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from analyze_newly_included_stocks import NewlyIncludedStockAnalyzer

def test_data_loading():
    """
    测试数据加载功能
    """
    print("测试数据加载功能...")
    
    # 初始化分析器
    analyzer = NewlyIncludedStockAnalyzer('930997_changes_20240101_20251024.csv')
    
    # 加载和筛选数据
    newly_included = analyzer.load_and_filter_data()
    
    if newly_included is not None and len(newly_included) > 0:
        print(f"OK 成功加载 {len(newly_included)} 条新纳入股票记录")
        
        # 显示前几条记录
        print("\n前5条记录:")
        print(newly_included[['tradecode', 'tradename', 'tradedate', 'cutoff_date']].head())
        
        # 显示日期映射
        print("\n日期映射:")
        date_mapping = newly_included[['tradedate', 'cutoff_date']].drop_duplicates()
        for _, row in date_mapping.iterrows():
            print(f"生效日: {row['tradedate']} → 数据截止日: {row['cutoff_date'].strftime('%Y-%m-%d')}")
        
        return True
    else:
        print("x 数据加载失败")
        return False

def test_trading_calendar():
    """
    测试交易日历获取功能
    """
    print("\n测试交易日历获取功能...")
    
    analyzer = NewlyIncludedStockAnalyzer('930997_changes_20240101_20251024.csv')
    
    # 测试获取交易日历
    trading_days = analyzer.get_trading_calendar('2024-04-01', '2024-05-31')
    
    if trading_days and len(trading_days) > 0:
        print(f"OK 成功获取 {len(trading_days)} 个交易日")
        print(f"前5个交易日: {trading_days[:5]}")
        print(f"后5个交易日: {trading_days[-5:]}")
        return True
    else:
        print("x 交易日历获取失败")
        return False

def test_window_calculation():
    """
    测试交易日窗口计算功能
    """
    print("\n测试交易日窗口计算功能...")
    
    analyzer = NewlyIncludedStockAnalyzer('930997_changes_20240101_20251024.csv')
    
    # 获取交易日历
    trading_days = analyzer.get_trading_calendar('2024-04-01', '2024-05-31')
    
    if trading_days:
        # 测试窗口计算
        center_date = '2024-04-30'
        window = analyzer.get_trading_window(center_date, trading_days, 5, 5)
        
        if window and len(window) > 0:
            print(f"OK 成功计算交易日窗口，共 {len(window)} 个交易日")
            print(f"窗口日期: {window}")
            return True
        else:
            print("x 交易日窗口计算失败")
            return False
    else:
        print("x 无法获取交易日历，跳过窗口测试")
        return False

def main():
    """
    主测试函数
    """
    print("=" * 60)
    print("新纳入股票表现分析脚本测试")
    print("=" * 60)
    
    # 检查CSV文件是否存在
    csv_file = '930997_changes_20240101_20251024.csv'
    if not os.path.exists(csv_file):
        print(f"x CSV文件不存在: {csv_file}")
        return
    
    # 运行测试
    tests = [
        test_data_loading,
        test_trading_calendar,
        test_window_calculation
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"x 测试失败: {e}")
    
    print(f"\n测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("OK 所有测试通过！可以运行完整分析。")
        print("\n运行完整分析请执行:")
        print("python analyze_newly_included_stocks.py")
    else:
        print("x 部分测试失败，请检查配置。")

if __name__ == "__main__":
    main()
