#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中证传媒指数成份股预测分析
基于选样方法分析样本空间，预测最有可能新纳入的股票
"""

import pandas as pd
import numpy as np
from wind_api_utils import init_wind_api, close_wind_api, get_index_constituents
from datetime import datetime, timedelta
import sys
import os

# 添加合并下载数据模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from source.实盘.xuntou.datadownload.合并下载数据 import getDayData, batchDownloadDayData

def load_sample_space():
    """加载CICS传媒样本空间数据"""
    print("加载CICS传媒样本空间数据...")
    df = pd.read_csv('CICS传媒.csv')
    print(f"样本空间总股票数: {len(df)}")
    return df

def get_current_constituents():
    """获取中证传媒指数当前成份股"""
    print("获取中证传媒指数当前成份股...")
    if not init_wind_api():
        return None
    
    df = get_index_constituents('399971.SZ')
    close_wind_api()
    
    if df is not None:
        print(f"当前成份股数量: {len(df)}")
        return df
    return None

def get_enhanced_market_data(df_sample, days=60):
    """获取增强的行情数据（使用合并下载数据模块）"""
    print(f"\n获取最近{days}天的增强行情数据...")
    
    # 设置日期范围
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    
    # 获取股票代码列表
    stock_codes = df_sample['代码'].tolist()
    
    print(f"正在获取 {len(stock_codes)} 只股票的历史数据...")
    
    try:
        # 使用批量下载获取历史数据
        data_dict = batchDownloadDayData(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            dividend_type='front',
            need_download=0,  # 优先从缓存读取
            batchNum=1
        )
        
        print(f"成功获取 {len(data_dict)} 只股票的历史数据")
        
        # 计算增强指标
        enhanced_data = []
        for code, df in data_dict.items():
            if df is not None and not df.empty:
                # 计算平均成交额
                avg_amount = df['amount'].mean() if 'amount' in df.columns else 0
                # 计算平均换手率（需要流通股本数据，这里用成交额/流通市值估算）
                sample_row = df_sample[df_sample['代码'] == code]
                if not sample_row.empty:
                    market_cap = sample_row.iloc[0]['流通市值']
                    avg_turnover = (avg_amount / market_cap) if market_cap > 0 else 0
                else:
                    avg_turnover = 0
                
                # 计算波动率
                if 'close' in df.columns and len(df) > 1:
                    returns = df['close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
                else:
                    volatility = 0
                
                enhanced_data.append({
                    '代码': code,
                    '平均成交额': avg_amount,
                    '平均换手率': avg_turnover,
                    '年化波动率': volatility,
                    '数据天数': len(df)
                })
        
        enhanced_df = pd.DataFrame(enhanced_data)
        return enhanced_df
        
    except Exception as e:
        print(f"获取增强行情数据失败: {e}")
        return None

def analyze_sample_space(df_sample):
    """分析样本空间数据"""
    print("\n分析样本空间数据...")
    
    # 基本统计信息
    print(f"样本空间总股票数: {len(df_sample)}")
    print(f"行业分布:")
    industry_counts = df_sample['Wind四级行业'].value_counts()
    print(industry_counts)
    
    # 市值分析
    print(f"\n市值分析:")
    print(f"流通市值范围: {df_sample['流通市值'].min():.2e} - {df_sample['流通市值'].max():.2e}")
    print(f"总市值范围: {df_sample['总市值1'].min():.2e} - {df_sample['总市值1'].max():.2e}")
    
    # 流动性分析（基于成交额）
    print(f"\n流动性分析:")
    print(f"成交额范围: {df_sample['成交额'].min():.2e} - {df_sample['成交额'].max():.2e}")
    print(f"换手率范围: {df_sample['换手率'].min():.4f} - {df_sample['换手率'].max():.4f}")
    
    return df_sample

def apply_selection_criteria(df_sample, current_constituents, enhanced_data=None):
    """
    根据中证传媒指数真实选样方法进行筛选：
    1. 对样本空间内证券按照过去一年的日均成交金额由高到低排名，剔除排名后20%的证券
    2. 在剩余待选样本中，按照过去一年日均总市值由高到低排名，选取排名前50的证券作为指数样本
    """
    print("\n应用中证传媒指数真实选样标准...")
    
    # 创建副本
    df_filtered = df_sample.copy()
    
    # 1. 排除ST股票
    st_mask = df_filtered['名称'].str.contains('ST|退', na=False)
    df_filtered = df_filtered[~st_mask]
    print(f"排除ST股票后: {len(df_filtered)} 只")
    
    # 2. 第一步：按过去一年日均成交金额排名，剔除后20%
    print("\n第一步：按过去一年日均成交金额排名，剔除后20%...")
    
    if enhanced_data is not None:
        # 使用增强数据中的平均成交额
        df_filtered = df_filtered.merge(enhanced_data, on='代码', how='left')
        df_filtered['日均成交金额'] = df_filtered['平均成交额'].fillna(df_filtered['成交额'])
        print("使用增强行情数据中的平均成交额")
    else:
        # 使用当日成交额作为近似值（实际应该用过去一年日均成交金额）
        df_filtered['日均成交金额'] = df_filtered['成交额']
        print("使用当日成交额作为近似值（注意：实际应使用过去一年日均成交金额）")
    
    # 按日均成交金额排名
    df_filtered = df_filtered.sort_values('日均成交金额', ascending=False)
    
    # 剔除排名后20%
    keep_count = int(len(df_filtered) * 0.8)
    df_filtered = df_filtered.head(keep_count)
    print(f"按日均成交金额剔除后20%后: {len(df_filtered)} 只")
    
    # 3. 第二步：按过去一年日均总市值排名，选取前50只
    print("\n第二步：按过去一年日均总市值排名，选取前50只...")
    
    # 按总市值排名（使用总市值1字段）
    df_filtered = df_filtered.sort_values('总市值1', ascending=False)
    
    # 选取前50只
    top_50 = df_filtered.head(50)
    print(f"按总市值选取前50只: {len(top_50)} 只")
    
    # 添加排名信息
    top_50['成交金额排名'] = range(1, len(top_50) + 1)
    top_50['总市值排名'] = range(1, len(top_50) + 1)
    
    # 计算综合评分（用于排序显示，不是选样标准）
    # 标准化各项指标
    top_50['成交金额_norm'] = (top_50['日均成交金额'] - top_50['日均成交金额'].min()) / (top_50['日均成交金额'].max() - top_50['日均成交金额'].min())
    top_50['总市值_norm'] = (top_50['总市值1'] - top_50['总市值1'].min()) / (top_50['总市值1'].max() - top_50['总市值1'].min())
    
    # 综合评分：成交金额50% + 总市值50%（仅用于显示排序）
    top_50['综合评分'] = (
        top_50['成交金额_norm'] * 0.5 +
        top_50['总市值_norm'] * 0.5
    )
    
    # 按综合评分排序（用于显示）
    top_50 = top_50.sort_values('综合评分', ascending=False)
    
    return top_50

def analyze_constituent_changes(df_sample, current_constituents, top_n=70):
    """分析成份股变化，提供详细的状态标记"""
    print(f"\n分析成份股变化，提供前{top_n}名总市值列表...")
    
    # 获取当前成份股代码
    current_codes = set(current_constituents['wind_code'].tolist())
    
    # 为每只股票标记状态
    df_sample = df_sample.copy()
    df_sample['状态'] = '未纳入'  # 默认状态
    
    # 添加日均成交金额字段（如果不存在）
    if '日均成交金额' not in df_sample.columns:
        df_sample['日均成交金额'] = df_sample['成交额']  # 使用当日成交额作为近似值
    
    # 添加日均总市值字段（如果不存在）
    if '日均总市值' not in df_sample.columns:
        df_sample['日均总市值'] = df_sample['总市值1']  # 使用当前总市值作为近似值
    
    # 不需要综合评分，直接按总市值排序
    
    # 获取前70名（按日均总市值排序）
    df_all_sorted = df_sample.sort_values('日均总市值', ascending=False)
    top_70 = df_all_sorted.head(top_n).copy()
    
    # 获取前50名（指数成份股）
    top_50 = top_70.head(50)
    predicted_codes = set(top_50['代码'].tolist())
    
    # 标记前50名中的股票状态
    for i, (_, row) in enumerate(top_50.iterrows()):
        if row['代码'] in current_codes:
            top_50.loc[top_50.index[i], '状态'] = '保持'
        else:
            top_50.loc[top_50.index[i], '状态'] = '纳入'
    
    # 找出被剔除的股票（当前成份股中不在前50名的）
    removed_stocks = []
    for code in current_codes:
        if code not in predicted_codes:
            # 找到被剔除的股票信息
            removed_info = df_sample[df_sample['代码'] == code]
            if not removed_info.empty:
                removed_stocks.append(removed_info.iloc[0])
    
    # 添加被剔除的股票到结果中
    if removed_stocks:
        removed_df = pd.DataFrame(removed_stocks)
        removed_df['状态'] = '剔除'
        # 合并结果
        all_results = pd.concat([top_50, removed_df], ignore_index=True)
    else:
        all_results = top_50
    
    # 标记前70名中不在前50名的股票为"未纳入"
    for i, (_, row) in enumerate(top_70.iterrows()):
        if i >= 50:  # 前50名之后的股票
            if row['代码'] not in current_codes:  # 且不是当前成份股
                # 添加到结果中
                unselected_df = pd.DataFrame([row])
                unselected_df['状态'] = '未纳入'
                all_results = pd.concat([all_results, unselected_df], ignore_index=True)
    
    # 按日均总市值重新排序
    all_results = all_results.sort_values('日均总市值', ascending=False)
    
    # 重新标记未纳入的股票（在样本空间中但不在前70名且不是当前成份股的）
    sample_codes = set(df_sample['代码'].tolist())
    all_codes = set(all_results['代码'].tolist())
    for code in sample_codes:
        if code not in all_codes and code not in current_codes:
            # 这是未纳入的股票
            unselected_info = df_sample[df_sample['代码'] == code]
            if not unselected_info.empty:
                unselected_df = pd.DataFrame([unselected_info.iloc[0]])
                unselected_df['状态'] = '未纳入'
                all_results = pd.concat([all_results, unselected_df], ignore_index=True)
    
    return all_results

def display_results(all_results, current_constituents):
    """显示预测结果"""
    print("\n" + "="*100)
    print("中证传媒指数成份股预测结果（按总市值排名）")
    print("="*100)
    
    print(f"\n当前成份股数量: {len(current_constituents)}")
    print(f"前70名总市值股票列表（按日均总市值由高到低排名）:")
    print("-" * 100)
    print(f"{'排名':<4} {'代码':<12} {'名称':<12} {'行业':<15} {'日均总市值(亿)':<12} {'日均成交(亿)':<12} {'状态':<8}")
    print("-" * 100)
    
    # 只显示前70名
    top_70_display = all_results.head(70)
    for i, (_, row) in enumerate(top_70_display.iterrows(), 1):
        print(f"{i:<4} {row['代码']:<12} {row['名称']:<12} "
              f"{row['Wind四级行业']:<15} "
              f"{row['日均总市值']/1e8:.1f}亿{'':<4} "
              f"{row['日均成交金额']/1e8:.1f}亿{'':<4} "
              f"{row['状态']:<8}")
    
    # 统计前70名各种状态的数量
    top_70_status = all_results.head(70)
    status_counts = top_70_status['状态'].value_counts()
    print(f"\n状态统计（前70名）:")
    for status, count in status_counts.items():
        print(f"  {status}: {count} 只")
    
    # 显示纳入的股票（按日均总市值排序）
    new_stocks = all_results[all_results['状态'] == '纳入'].sort_values('日均总市值', ascending=False)
    if len(new_stocks) > 0:
        print(f"\n纳入的股票（按日均总市值排序）:")
        print("-" * 100)
        for i, (_, row) in enumerate(new_stocks.iterrows(), 1):
            print(f"{i:2d}. {row['代码']} {row['名称']:<12} "
                  f"行业: {row['Wind四级行业']:<15} "
                  f"日均总市值: {row['日均总市值']/1e8:.1f}亿 "
                  f"日均成交: {row['日均成交金额']/1e8:.1f}亿")
    
    # 显示被剔除的股票（按日均总市值排序）
    removed_stocks = all_results[all_results['状态'] == '剔除'].sort_values('日均总市值', ascending=False)
    if len(removed_stocks) > 0:
        print(f"\n被剔除的股票（按日均总市值排序）:")
        print("-" * 100)
        for i, (_, row) in enumerate(removed_stocks.iterrows(), 1):
            print(f"{i:2d}. {row['代码']} {row['名称']:<12} "
                  f"行业: {row['Wind四级行业']:<15} "
                  f"日均总市值: {row['日均总市值']/1e8:.1f}亿 "
                  f"日均成交: {row['日均成交金额']/1e8:.1f}亿")
    
    print(f"\n行业分布分析（前70名）:")
    industry_dist = all_results['Wind四级行业'].value_counts()
    for industry, count in industry_dist.items():
        print(f"  {industry}: {count} 只")
    
    print(f"\n市值分布（前70名）:")
    print(f"  平均日均总市值: {all_results['日均总市值'].mean()/1e8:.1f} 亿")
    print(f"  中位数日均总市值: {all_results['日均总市值'].median()/1e8:.1f} 亿")
    print(f"  平均日均成交额: {all_results['日均成交金额'].mean()/1e8:.1f} 亿")

def main():
    """主函数"""
    print("中证传媒指数成份股预测分析（使用增强行情数据）")
    print("="*60)
    
    try:
        # 1. 加载样本空间数据
        df_sample = load_sample_space()
        
        # 2. 获取当前成份股
        current_constituents = get_current_constituents()
        if current_constituents is None:
            print("获取当前成份股失败")
            return
        
        # 3. 分析样本空间
        df_sample = analyze_sample_space(df_sample)
        
        # 4. 获取增强行情数据（过去一年）
        enhanced_data = get_enhanced_market_data(df_sample, days=365)
        
        # 5. 应用选样标准（使用增强数据）
        df_ranked = apply_selection_criteria(df_sample, current_constituents, enhanced_data)
        
        # 6. 分析成份股变化（传递完整的样本空间数据）
        all_results = analyze_constituent_changes(df_sample, current_constituents, top_n=70)
        
        # 7. 显示结果
        display_results(all_results, current_constituents)
        
        # 8. 保存当前成份股
        current_file = f"中证传媒指数当前成份股_{datetime.now().strftime('%Y%m%d')}.csv"
        current_constituents.to_csv(current_file, index=False, encoding='utf-8-sig')
        print(f"\n当前成份股已保存到: {current_file}")
        
        # 9. 保存预测结果
        output_file = f"中证传媒指数预测结果_增强版_{datetime.now().strftime('%Y%m%d')}.csv"
        all_results.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"预测结果已保存到: {output_file}")
        
        # 10. 保存增强数据（如果有）
        if enhanced_data is not None:
            enhanced_file = f"增强行情数据_{datetime.now().strftime('%Y%m%d')}.csv"
            enhanced_data.to_csv(enhanced_file, index=False, encoding='utf-8-sig')
            print(f"增强行情数据已保存到: {enhanced_file}")
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
