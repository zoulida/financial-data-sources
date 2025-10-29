#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查分析进度
"""

import os
import glob
import pandas as pd

def check_progress():
    """检查分析进度"""
    print("=" * 60)
    print("分析进度检查")
    print("=" * 60)
    
    # 检查是否有结果文件
    if os.path.exists('all_stocks_performance_detail.csv'):
        df = pd.read_csv('all_stocks_performance_detail.csv')
        print(f"OK 已生成结果文件: all_stocks_performance_detail.csv")
        print(f"  包含 {len(df)} 条记录")
        
        # 按指数统计
        if 'index_name' in df.columns:
            index_stats = df.groupby('index_name').size()
            print(f"\n各指数分析结果:")
            for index, count in index_stats.items():
                print(f"  {index}: {count} 条记录")
        
        # 按窗口类型统计
        if 'window_type' in df.columns:
            window_stats = df.groupby('window_type').size()
            print(f"\n各窗口类型统计:")
            for window_type, count in window_stats.items():
                print(f"  {window_type}: {count} 条记录")
        
        return True
    else:
        print("x 尚未生成结果文件")
        
        # 检查变动文件数量
        change_files = glob.glob('*_changes.csv')
        print(f"\n找到 {len(change_files)} 个指数变动文件")
        
        # 统计总股票数量
        total_stocks = 0
        for file in change_files:
            try:
                df = pd.read_csv(file)
                newly_included = df[df['tradestatus'] == '纳入'].copy()
                total_stocks += len(newly_included)
            except:
                continue
        
        print(f"预计需要处理 {total_stocks} 只新纳入股票")
        print(f"每个股票2个窗口，总计 {total_stocks * 2} 个股票窗口")
        
        return False

if __name__ == "__main__":
    check_progress()