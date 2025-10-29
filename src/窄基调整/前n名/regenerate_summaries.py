#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新生成汇总报告
"""

import pandas as pd
import numpy as np

def generate_summary_reports():
    """生成汇总报告"""
    
    # 读取详细数据
    df = pd.read_csv('all_stocks_performance_detail.csv')
    
    print("正在生成汇总报告...")
    
    # 1. 按指数汇总统计
    print("1. 生成按指数汇总统计...")
    index_summary = df.groupby('index_name').agg({
        'stock_code': 'count',
        'cumulative_return': ['mean', 'std', 'min', 'max'],
        'win_rate': 'mean',
        'volatility': 'mean'
    }).round(2)
    
    # 计算正收益股票数量和占比
    positive_counts = df.groupby('index_name').apply(
        lambda x: (x['cumulative_return'] > 0).sum()
    )
    positive_rates = df.groupby('index_name').apply(
        lambda x: (x['cumulative_return'] > 0).mean() * 100
    )
    
    # 重新整理数据
    index_summary_clean = pd.DataFrame({
        'index_name': index_summary.index,
        'stock_count': index_summary[('stock_code', 'count')],
        'avg_cumulative_return': index_summary[('cumulative_return', 'mean')],
        'std_cumulative_return': index_summary[('cumulative_return', 'std')],
        'min_return': index_summary[('cumulative_return', 'min')],
        'max_return': index_summary[('cumulative_return', 'max')],
        'avg_win_rate': index_summary[('win_rate', 'mean')],
        'avg_volatility': index_summary[('volatility', 'mean')],
        'positive_return_count': positive_counts.values,
        'positive_return_rate': positive_rates.values
    })
    
    index_summary_clean.to_csv('indices_summary_report.csv', index=False, encoding='utf-8-sig')
    print(f"  已生成 indices_summary_report.csv，包含 {len(index_summary_clean)} 个指数")
    
    # 2. 按窗口类型分指数对比
    print("2. 生成按窗口类型分指数对比...")
    
    # 数据截止日统计
    cutoff_stats = df[df['window_type'] == 'cutoff_date'].groupby('index_name').agg({
        'stock_code': 'count',
        'cumulative_return': 'mean',
        'win_rate': 'mean'
    })
    
    cutoff_positive = df[df['window_type'] == 'cutoff_date'].groupby('index_name').apply(
        lambda x: (x['cumulative_return'] > 0).mean() * 100
    )
    
    # 生效日统计
    effective_stats = df[df['window_type'] == 'effective_date'].groupby('index_name').agg({
        'stock_code': 'count',
        'cumulative_return': 'mean',
        'win_rate': 'mean'
    })
    
    effective_positive = df[df['window_type'] == 'effective_date'].groupby('index_name').apply(
        lambda x: (x['cumulative_return'] > 0).mean() * 100
    )
    
    # 合并数据
    window_comparison = pd.DataFrame({
        'index_name': cutoff_stats.index,
        'stock_count': cutoff_stats['stock_code'],
        'cutoff_avg_return': cutoff_stats['cumulative_return'].round(2),
        'cutoff_win_rate': cutoff_stats['win_rate'].round(2),
        'cutoff_positive_rate': cutoff_positive.round(2),
        'effective_avg_return': effective_stats['cumulative_return'].round(2),
        'effective_win_rate': effective_stats['win_rate'].round(2),
        'effective_positive_rate': effective_positive.round(2)
    })
    
    # 添加指数代码
    index_codes = df.groupby('index_name')['index_code'].first()
    window_comparison['index_code'] = window_comparison['index_name'].map(index_codes)
    
    # 重新排列列顺序
    window_comparison = window_comparison[['index_name', 'index_code', 'stock_count', 
                                         'cutoff_avg_return', 'cutoff_win_rate', 'cutoff_positive_rate',
                                         'effective_avg_return', 'effective_win_rate', 'effective_positive_rate']]
    
    window_comparison.to_csv('window_analysis_summary.csv', index=False, encoding='utf-8-sig')
    print(f"  已生成 window_analysis_summary.csv，包含 {len(window_comparison)} 个指数")
    
    # 3. 整体统计
    print("3. 生成整体统计...")
    cutoff_data = df[df['window_type'] == 'cutoff_date']
    effective_data = df[df['window_type'] == 'effective_date']
    
    overall_stats = pd.DataFrame({
        'window_type': ['cutoff_date', 'effective_date'],
        'stock_count': [len(cutoff_data), len(effective_data)],
        'avg_cumulative_return': [cutoff_data['cumulative_return'].mean(), effective_data['cumulative_return'].mean()],
        'avg_win_rate': [cutoff_data['win_rate'].mean(), effective_data['win_rate'].mean()],
        'positive_return_rate': [(cutoff_data['cumulative_return'] > 0).mean() * 100, 
                                (effective_data['cumulative_return'] > 0).mean() * 100],
        'avg_volatility': [cutoff_data['volatility'].mean(), effective_data['volatility'].mean()]
    }).round(2)
    
    overall_stats.to_csv('overall_statistics.csv', index=False, encoding='utf-8-sig')
    print(f"  已生成 overall_statistics.csv")
    
    print("\n汇总报告生成完成！")
    print("文件列表:")
    print("  - indices_summary_report.csv: 按指数汇总统计")
    print("  - window_analysis_summary.csv: 按窗口类型分指数对比")
    print("  - overall_statistics.csv: 整体统计")
    
    return window_comparison, index_summary_clean, overall_stats

if __name__ == "__main__":
    generate_summary_reports()
