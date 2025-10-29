#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取中证全指指数的全部成分股作为初始池
覆盖沪深市场绝大部分A股，剔除ST、*ST及上市不足3个月的新股等
"""

import pandas as pd
from datetime import datetime, timedelta
import time
from wind_api_utils import init_wind_api, close_wind_api, get_index_constituents, get_stock_basic_info, get_stock_turnover_data

def filter_stocks(df_info):
    """
    过滤不合格股票
    
    Args:
        df_info (pd.DataFrame): 股票信息数据
    
    Returns:
        pd.DataFrame: 过滤后的股票数据
    """
    print("过滤不合格股票...")
    print(f"   原始股票数: {len(df_info)}")
    print(f"   可用字段: {list(df_info.columns)}")
    
    # 1. 过滤已摘牌股票（如果DELIST_DATE字段存在）
    if 'DELIST_DATE' in df_info.columns:
        # Wind API中，未摘牌股票的DELIST_DATE通常是1899-12-30或空值
        delist_dates = pd.to_datetime(df_info['DELIST_DATE'], errors='coerce')
        current_time = pd.Timestamp.now()
        
        # 保留未摘牌股票：空值 或 1899-12-30 或 摘牌日期在未来
        df_filtered = df_info[
            (df_info['DELIST_DATE'].isna()) |  # 空值表示未摘牌
            (delist_dates == pd.Timestamp('1899-12-30')) |  # Wind API默认值表示未摘牌
            (delist_dates > current_time)  # 摘牌日期在未来
        ].copy()
        print(f"   剔除摘牌股票后: {len(df_filtered)} 只")
    else:
        print("   ⚠ 未找到DELIST_DATE字段，跳过摘牌股票过滤")
        df_filtered = df_info.copy()
    
    # 2. 过滤ST股票（如果SEC_NAME字段存在）
    if 'SEC_NAME' in df_filtered.columns:
        df_filtered = df_filtered[
            ~df_filtered['SEC_NAME'].str.contains('ST', na=False) &
            ~df_filtered['SEC_NAME'].str.contains('退', na=False)
        ]
        print(f"   剔除ST股票后: {len(df_filtered)} 只")
    else:
        print("   ⚠ 未找到SEC_NAME字段，跳过ST股票过滤")
    
    # 3. 过滤上市不足3个月的新股（如果IPO_DATE字段存在）
    if 'IPO_DATE' in df_filtered.columns:
        # 计算上市天数
        df_filtered['ipo_date_dt'] = pd.to_datetime(df_filtered['IPO_DATE'], errors='coerce')
        df_filtered['days_listed'] = (pd.Timestamp.now() - df_filtered['ipo_date_dt']).dt.days
        
        # 保留上市满3个月（90天）的股票
        df_filtered = df_filtered[df_filtered['days_listed'] >= 90].copy()
        print(f"   剔除上市不足3个月的股票后: {len(df_filtered)} 只")
    else:
        print("   ⚠ 未找到IPO_DATE字段，跳过新股过滤")
        df_filtered['days_listed'] = 999  # 设置默认值
    
    # 4. 选择可用的列并重命名
    available_columns = []
    column_mapping = {}
    
    if 'WINDCODE' in df_filtered.columns:
        available_columns.append('WINDCODE')
        column_mapping['WINDCODE'] = '股票代码'
    elif 'wind_code' in df_filtered.columns:
        available_columns.append('wind_code')
        column_mapping['wind_code'] = '股票代码'
    
    if 'SEC_NAME' in df_filtered.columns:
        available_columns.append('SEC_NAME')
        column_mapping['SEC_NAME'] = '股票简称'
    
    if 'IPO_DATE' in df_filtered.columns:
        available_columns.append('IPO_DATE')
        column_mapping['IPO_DATE'] = '上市日期'
    
    if 'MKT' in df_filtered.columns:
        available_columns.append('MKT')
        column_mapping['MKT'] = '上市板'
    
    if 'days_listed' in df_filtered.columns:
        available_columns.append('days_listed')
        column_mapping['days_listed'] = '上市天数'
    
    # 只选择存在的列
    df_filtered = df_filtered[available_columns].copy()
    df_filtered.columns = [column_mapping[col] for col in available_columns]
    
    return df_filtered

def filter_by_liquidity(df_info, cutoff_percent=0.2):
    """
    按流动性筛选股票，剔除成交金额排名后20%的股票
    
    Args:
        df_info (pd.DataFrame): 股票信息数据
        cutoff_percent (float): 剔除比例，默认0.2（20%）
    
    Returns:
        pd.DataFrame: 流动性筛选后的股票数据
    """
    print(f"按流动性筛选股票，剔除成交金额排名后{cutoff_percent*100:.0f}%...")
    print(f"   筛选前股票数: {len(df_info)}")
    
    # 获取股票代码
    if '股票代码' in df_info.columns:
        stock_codes = df_info['股票代码'].tolist()
    elif 'WINDCODE' in df_info.columns:
        stock_codes = df_info['WINDCODE'].tolist()
    elif 'wind_code' in df_info.columns:
        stock_codes = df_info['wind_code'].tolist()
    else:
        print("   ✗ 未找到股票代码字段，跳过流动性筛选")
        return df_info
    
    # 获取成交金额数据
    df_turnover = get_stock_turnover_data(stock_codes)
    if df_turnover is None:
        print("   ✗ 获取成交金额数据失败，跳过流动性筛选")
        return df_info
    
    # 合并数据
    if '股票代码' in df_info.columns:
        df_merged = df_info.merge(df_turnover, left_on='股票代码', right_index=True, how='left')
    elif 'WINDCODE' in df_info.columns:
        df_merged = df_info.merge(df_turnover, left_on='WINDCODE', right_index=True, how='left')
    else:
        df_merged = df_info.merge(df_turnover, left_on='wind_code', right_index=True, how='left')
    
    # 检查成交金额字段
    if 'AMT_AVG_1Y' not in df_merged.columns:
        print("   ✗ 未找到成交金额字段，跳过流动性筛选")
        return df_info
    
    # 处理缺失值：将缺失的成交金额设为0
    df_merged['AMT_AVG_1Y'] = df_merged['AMT_AVG_1Y'].fillna(0)
    
    # 按成交金额排序
    df_merged = df_merged.sort_values('AMT_AVG_1Y', ascending=False)
    
    # 计算保留数量（保留前80%）
    keep_count = int(len(df_merged) * (1 - cutoff_percent))
    df_liquidity_filtered = df_merged.head(keep_count).copy()
    
    print(f"   筛选后股票数: {len(df_liquidity_filtered)}")
    print(f"   剔除股票数: {len(df_merged) - len(df_liquidity_filtered)}")
    
    # 显示成交金额统计
    if len(df_liquidity_filtered) > 0:
        print(f"   成交金额统计:")
        print(f"     最大值: {df_liquidity_filtered['AMT_AVG_1Y'].max():.2f} 万元")
        print(f"     最小值: {df_liquidity_filtered['AMT_AVG_1Y'].min():.2f} 万元")
        print(f"     平均值: {df_liquidity_filtered['AMT_AVG_1Y'].mean():.2f} 万元")
        print(f"     中位数: {df_liquidity_filtered['AMT_AVG_1Y'].median():.2f} 万元")
    
    return df_liquidity_filtered

def save_results(df_filtered):
    """
    保存结果到CSV文件
    
    Args:
        df_filtered (pd.DataFrame): 过滤后的股票数据
    
    Returns:
        str: 输出文件名
    """
    print("保存结果...")
    output_file = f"中证全指成分股_{datetime.now().strftime('%Y%m%d')}.csv"
    df_filtered.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"   ✓ 数据已保存到: {output_file}")
    return output_file

def show_statistics(df_filtered):
    """
    显示统计信息
    
    Args:
        df_filtered (pd.DataFrame): 过滤后的股票数据
    """
    print("统计信息:")
    print(f"   最终股票数量: {len(df_filtered)}")
    print(f"   可用字段: {list(df_filtered.columns)}")
    
    # 按上市板分布（如果上市板字段存在）
    if '上市板' in df_filtered.columns:
        print(f"\n   按上市板分布:")
        print(df_filtered['上市板'].value_counts().to_string())
    else:
        print(f"\n   ⚠ 未找到上市板字段，跳过上市板统计")
    
    # 按上市天数分布（如果上市天数字段存在）
    if '上市天数' in df_filtered.columns:
        print(f"\n   按上市天数分布:")
        df_filtered['上市天数区间'] = pd.cut(df_filtered['上市天数'], 
                                          bins=[0, 365, 1095, 3650, 999999],
                                          labels=['3个月-1年', '1-3年', '3-10年', '10年以上'])
        print(df_filtered['上市天数区间'].value_counts().to_string())
    else:
        print(f"\n   ⚠ 未找到上市天数字段，跳过上市天数统计")
    
    # 流动性统计（如果成交金额字段存在）
    if 'AMT_AVG_1Y' in df_filtered.columns:
        print(f"\n   流动性统计（最近一年日均成交金额）:")
        print(f"     最大值: {df_filtered['AMT_AVG_1Y'].max():.2f} 万元")
        print(f"     最小值: {df_filtered['AMT_AVG_1Y'].min():.2f} 万元")
        print(f"     平均值: {df_filtered['AMT_AVG_1Y'].mean():.2f} 万元")
        print(f"     中位数: {df_filtered['AMT_AVG_1Y'].median():.2f} 万元")
        
        # 按成交金额区间分布
        df_filtered['成交金额区间'] = pd.cut(df_filtered['AMT_AVG_1Y'], 
                                        bins=[0, 1000, 5000, 10000, 50000, float('inf')],
                                        labels=['<1千万', '1-5千万', '5千万-1亿', '1-5亿', '>5亿'])
        print(f"\n   按成交金额区间分布:")
        print(df_filtered['成交金额区间'].value_counts().to_string())
    else:
        print(f"\n   ⚠ 未找到成交金额字段，跳过流动性统计")
    
    # 显示前20只股票
    print(f"\n   前20只股票预览:")
    display_columns = ['股票代码', '股票简称']
    if '上市板' in df_filtered.columns:
        display_columns.append('上市板')
    if 'AMT_AVG_1Y' in df_filtered.columns:
        display_columns.append('AMT_AVG_1Y')
    print(df_filtered[display_columns].head(20).to_string())

def get_csi_all_index_constituents():
    """
    获取中证全指指数的全部成分股
    
    中证全指指数: 000985.CSI
    本函数获取该指数的所有成分股并过滤不合格股票
    """
    print("=" * 80)
    print("获取中证全指指数成分股")
    print("=" * 80)
    
    # 1. 初始化Wind API
    print("\n1. 初始化Wind API...")
    if not init_wind_api():
        return None
    
    # 2. 设置指数代码
    index_code = "000985.CSI"  # 中证全指指数
    
    print(f"\n2. 获取指数: {index_code} (中证全指指数)")
    
    # 3. 获取当前成分股
    df_constituents = get_index_constituents(index_code)
    if df_constituents is None:
        close_wind_api()
        return None
    
    # 4. 获取股票基本信息用于过滤
    print("\n3. 获取股票基本信息以进行过滤...")
    stock_codes = df_constituents['wind_code'].tolist()
    df_info = get_stock_basic_info(stock_codes)
    if df_info is None:
        close_wind_api()
        return None
    
    # 5. 过滤不合格股票
    print("\n4. 过滤不合格股票...")
    df_filtered = filter_stocks(df_info)
    
    # 6. 流动性筛选
    print("\n5. 流动性筛选...")
    df_liquidity_filtered = filter_by_liquidity(df_filtered)
    
    # 7. 保存结果
    print("\n6. 保存结果...")
    output_file = save_results(df_liquidity_filtered)
    
    # 8. 显示统计信息
    print("\n7. 统计信息:")
    show_statistics(df_liquidity_filtered)
    
    # 9. 关闭Wind API
    print("\n8. 关闭Wind API...")
    close_wind_api()
    
    print("\n" + "=" * 80)
    print("处理完成！")
    print("=" * 80)
    
    return df_liquidity_filtered


if __name__ == "__main__":
    result = get_csi_all_index_constituents()
    
    if result is not None:
        print(f"\n✓ 成功获取并过滤 {len(result)} 只成分股")
    else:
        print("\n✗ 获取失败")

