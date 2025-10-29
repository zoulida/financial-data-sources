#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
筛选前60名窄基指数
剔除港股通指数、综合指数，只保留窄基指数
"""

import pandas as pd
import os

def filter_narrow_indices(n=60):
    """
    筛选前N名窄基指数
    
    Args:
        n: 前N名
        
    Returns:
        筛选后的窄基指数列表
    """
    # 读取指数基金规模数据
    df = pd.read_csv('../求基金规模/指数基金规模汇总.csv')
    
    print(f"原始数据: {len(df)} 个指数")
    
    # 1. 排除港股通相关的指数
    df_filtered = df[
        ~df['跟踪指数名称'].str.contains('港股通', na=False)
    ]
    print(f"剔除港股通后: {len(df_filtered)} 个指数")
    
    # 2. 排除综合指数（包含数字的综合指数）
    # 综合指数通常包含：沪深300、中证500、中证1000、上证50、创业板指等
    comprehensive_indices = [
        '沪深300', '中证500', '中证1000', '上证50', '创业板指', '科创50',
        '上证180', '上证380', '上证指数', '深证成指', '深证100', '深证300',
        '中证800', '中证A100', '中证A500', '中证A50', '中证2000', '中证200',
        '创业板50', '创业板300', '创业板综', '创业板200', '创业板100',
        '科创100', '科创200', '科创综指', '科创成长', '科创价格', '科创信息',
        '科创生物', '科创材料', '科创机械', '科创能', '科创AI', '科创半导体',
        '科创芯片', '科创新药', '科创芯片设计', '科创半导体材料设备',
        '上证中盘', '上证小盘', '上证大盘', '上证超大盘', '上证商品', '上证资源',
        '深证50', '深证100R', '深证F60', '深证F120', '深证主板50',
        '全指医药', '全指信息', '全指可选', '全指公用', '全指能源', '全指材料',
        '800消费', '800医卫', '800信息', '800通信', '800医药', '800金融',
        '800能源', '800金地', '800有色', '800银行', '800汽车', '800现金流',
        '300医药', '300非银', '300价值', '300成长', '300金融', '300红利低波',
        '300现金流', '300ESG', '300质量低波', '300成长创新', '300等权',
        '1000价值稳健', '1000成长创新', '500质量成长', '500SNLV', '500现金流',
        '500价值稳健', '500成长创新', '500等权', '500信息', '500红利低波',
        '2000', '200', '100', '50', '30', '20', '10'
    ]
    
    # 排除综合指数
    df_narrow = df_filtered[
        ~df_filtered['跟踪指数名称'].isin(comprehensive_indices)
    ]
    print(f"剔除综合指数后: {len(df_narrow)} 个指数")
    
    # 3. 进一步筛选：排除包含"综合"、"全指"、"全市场"等词汇的指数
    exclude_keywords = ['综合', '全指', '全市场', '全A', '全股', '全行业', '全板块']
    for keyword in exclude_keywords:
        df_narrow = df_narrow[
            ~df_narrow['跟踪指数名称'].str.contains(keyword, na=False)
        ]
    
    print(f"剔除综合类关键词后: {len(df_narrow)} 个指数")
    
    # 4. 按基金规模排序，取前N名
    df_narrow = df_narrow.sort_values('基金规模(亿元)', ascending=False)
    top_n = df_narrow.head(n)
    
    print(f"\n筛选结果：前{n}名窄基指数")
    print("=" * 80)
    for idx, row in top_n.iterrows():
        print(f"{row['跟踪指数代码']} - {row['跟踪指数名称']} - {row['基金规模(亿元)']:.2f}亿")
    
    # 保存结果到当前目录
    output_file = 'zhaiji_top_indices_list.csv'
    top_n.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存到: {os.path.abspath(output_file)}")
    
    # 统计信息
    print(f"\n统计信息:")
    print(f"  总基金规模: {top_n['基金规模(亿元)'].sum():.2f}亿元")
    print(f"  平均基金规模: {top_n['基金规模(亿元)'].mean():.2f}亿元")
    print(f"  最大基金规模: {top_n['基金规模(亿元)'].max():.2f}亿元")
    print(f"  最小基金规模: {top_n['基金规模(亿元)'].min():.2f}亿元")
    
    return top_n

if __name__ == "__main__":
    filter_narrow_indices(60)
