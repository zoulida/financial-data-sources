#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
筛选前N名指数，排除港股通
"""

import pandas as pd

def filter_top_indices(n=20):
    """
    筛选前N名指数，排除港股通
    
    Args:
        n: 前N名
        
    Returns:
        筛选后的指数列表
    """
    # 读取指数基金规模数据
    df = pd.read_csv('../求基金规模/指数基金规模汇总.csv')
    
    # 排除港股通相关的指数
    df_filtered = df[
        ~df['跟踪指数名称'].str.contains('港股通', na=False)
    ]
    
    # 取前N名
    top_n = df_filtered.head(n)
    
    print(f"筛选结果：前{n}名指数（排除港股通）")
    print("=" * 60)
    for idx, row in top_n.iterrows():
        print(f"{row['跟踪指数代码']} - {row['跟踪指数名称']} - {row['基金规模(亿元)']:.2f}亿")
    
    # 保存结果
    output_file = 'top_indices_list.csv'
    top_n.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存到: {output_file}")
    
    return top_n

if __name__ == "__main__":
    filter_top_indices(20)
