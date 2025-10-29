#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成分析报告
"""

import pandas as pd
import numpy as np

def generate_report():
    # 读取数据
    df = pd.read_csv('all_stocks_performance_detail.csv')

    print('=' * 80)
    print('指数调整新纳入股票表现分析报告')
    print('=' * 80)

    # 按窗口类型分析
    print('\n1. 按窗口类型分析:')
    window_stats = df.groupby('window_type').agg({
        'cumulative_return': ['count', 'mean', 'std', 'min', 'max'],
        'win_rate': ['mean', 'std'],
        'volatility': ['mean', 'std']
    }).round(2)

    print(window_stats)

    # 按指数分析
    print('\n2. 按指数分析 (前10个):')
    index_stats = df.groupby('index_name').agg({
        'cumulative_return': ['count', 'mean'],
        'win_rate': 'mean'
    }).round(2)

    index_stats = index_stats.sort_values(('cumulative_return', 'mean'), ascending=False)
    print(index_stats.head(10))

    # 数据截止日 vs 生效日对比
    print('\n3. 数据截止日 vs 生效日对比:')
    cutoff_data = df[df['window_type'] == 'cutoff_date']
    effective_data = df[df['window_type'] == 'effective_date']

    print('数据截止日:')
    print(f'  平均累计收益率: {cutoff_data["cumulative_return"].mean():.2f}%')
    print(f'  平均胜率: {cutoff_data["win_rate"].mean():.2f}%')
    print(f'  样本数量: {len(cutoff_data)}')

    print('\n生效日:')
    print(f'  平均累计收益率: {effective_data["cumulative_return"].mean():.2f}%')
    print(f'  平均胜率: {effective_data["win_rate"].mean():.2f}%')
    print(f'  样本数量: {len(effective_data)}')

    # 收益率分布
    print('\n4. 收益率分布分析:')
    print('数据截止日收益率分布:')
    print(f'  正收益股票占比: {(cutoff_data["cumulative_return"] > 0).mean()*100:.1f}%')
    print(f'  收益率>5%的股票占比: {(cutoff_data["cumulative_return"] > 5).mean()*100:.1f}%')
    print(f'  收益率>10%的股票占比: {(cutoff_data["cumulative_return"] > 10).mean()*100:.1f}%')

    print('\n生效日收益率分布:')
    print(f'  正收益股票占比: {(effective_data["cumulative_return"] > 0).mean()*100:.1f}%')
    print(f'  收益率>5%的股票占比: {(effective_data["cumulative_return"] > 5).mean()*100:.1f}%')
    print(f'  收益率>10%的股票占比: {(effective_data["cumulative_return"] > 10).mean()*100:.1f}%')

    # 关键发现
    print('\n5. 关键发现:')
    cutoff_positive = (cutoff_data["cumulative_return"] > 0).mean() * 100
    effective_positive = (effective_data["cumulative_return"] > 0).mean() * 100
    
    print(f'  数据截止日正收益股票占比: {cutoff_positive:.1f}%')
    print(f'  生效日正收益股票占比: {effective_positive:.1f}%')
    print(f'  差异: {cutoff_positive - effective_positive:.1f}个百分点')
    
    if cutoff_positive > effective_positive:
        print('  结论: 数据截止日附近的表现明显优于生效日')
    else:
        print('  结论: 生效日附近的表现优于数据截止日')

if __name__ == "__main__":
    generate_report()