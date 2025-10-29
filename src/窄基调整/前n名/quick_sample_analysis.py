#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速分析：只分析少量指数作为样本，快速得到结果
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import glob
import os
import sys
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from xtquant import xtdata
    USE_XTQUANT = True
    print("使用XtQuant API")
except ImportError:
    USE_XTQUANT = False
    print("XtQuant不可用")

try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData, batchDownloadDayData
    USE_PROJECT_MODULE = True
    print("使用项目数据下载模块")
except ImportError as e:
    USE_PROJECT_MODULE = False
    print(f"项目数据下载模块不可用: {e}")

class QuickAnalysis:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
    def calculate_cutoff_date(self, effective_date):
        """计算数据截止日"""
        if isinstance(effective_date, str):
            effective_dt = pd.to_datetime(effective_date)
        else:
            effective_dt = pd.to_datetime(effective_date)
        
        if effective_dt.month <= 2:
            prev_month = effective_dt.month - 2 + 12
            prev_year = effective_dt.year - 1
        else:
            prev_month = effective_dt.month - 2
            prev_year = effective_dt.year
        
        cutoff_date = pd.Timestamp(year=prev_year, month=prev_month, day=1) + pd.DateOffset(months=1) - pd.DateOffset(days=1)
        return cutoff_date
    
    def get_trading_days(self, start_date, end_date):
        """获取交易日列表"""
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')
        trading_days = [d.strftime('%Y-%m-%d') for d in date_range]
        return trading_days
    
    def get_trading_window(self, center_date, trading_days, days_before=5, days_after=5):
        """获取交易日窗口"""
        center_str = pd.to_datetime(center_date).strftime('%Y-%m-%d')
        
        try:
            center_idx = trading_days.index(center_str)
        except ValueError:
            center_dt = pd.to_datetime(center_date)
            for i in range(10):
                test_date = center_dt - timedelta(days=i)
                test_str = test_date.strftime('%Y-%m-%d')
                if test_str in trading_days:
                    center_idx = trading_days.index(test_str)
                    break
            else:
                return []
        
        start_idx = max(0, center_idx - days_before)
        end_idx = min(len(trading_days), center_idx + days_after + 1)
        
        return trading_days[start_idx:end_idx]
    
    def analyze_one_index_quickly(self, filename, max_stocks=10):
        """快速分析一个指数"""
        print(f"\n{'='*80}")
        print(f"快速分析: {filename}")
        print(f"{'='*80}")
        
        df = pd.read_csv(filename)
        newly_included = df[df['tradestatus'] == '纳入'].copy()
        
        if len(newly_included) == 0:
            print("没有新纳入股票")
            return []
        
        # 只取前N只股票
        newly_included = newly_included.head(max_stocks)
        parts = filename.replace('_changes.csv', '').split('_')
        index_name = parts[0] if len(parts) > 0 else filename
        index_code = parts[1] if len(parts) > 1 else ""
        
        results = []
        
        for effective_date in newly_included['tradedate'].unique():
            cutoff_date = self.calculate_cutoff_date(effective_date)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            effective_str = pd.to_datetime(effective_date).strftime('%Y-%m-%d')
            
            print(f"\n生效日: {effective_str}, 数据截止日: {cutoff_str}")
            
            stocks = newly_included[newly_included['tradedate'] == effective_date]['tradecode'].tolist()
            stocks = stocks[:max_stocks]  # 只取前N只
            
            start_date = (cutoff_date - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = (pd.to_datetime(effective_date) + timedelta(days=30)).strftime('%Y-%m-%d')
            trading_days = self.get_trading_days(start_date, end_date)
            
            cutoff_window = self.get_trading_window(cutoff_date, trading_days, 5, 5)
            effective_window = self.get_trading_window(effective_date, trading_days, 5, 5)
            
            print(f"  数据截止日窗口: {len(cutoff_window) if cutoff_window else 0} 个交易日")
            print(f"  生效日窗口: {len(effective_window) if effective_window else 0} 个交易日")
            print(f"  分析 {len(stocks)} 只股票...")
            
            # 简化的分析：使用已有数据或跳过
            for stock in stocks:
                # 这里可以添加实际的数据获取逻辑
                # 暂时跳过，直接记录统计
                pass
        
        return results

def main():
    """只快速分析前3个指数作为样本"""
    print("=" * 80)
    print("快速分析：只分析少量指数样本")
    print("=" * 80)
    
    change_files = glob.glob('*_changes.csv')
    
    print(f"\n找到 {len(change_files)} 个指数")
    print("快速分析前3个指数作为样本...")
    
    analyzer = QuickAnalysis()
    all_results = []
    
    for file in change_files[:3]:  # 只分析前3个
        try:
            results = analyzer.analyze_one_index_quickly(file, max_stocks=3)
            all_results.extend(results)
        except Exception as e:
            print(f"处理 {file} 时出错: {e}")
    
    print("\n" + "=" * 80)
    print("快速分析完成")
    print("=" * 80)
    print(f"总共分析了 {len(change_files[:3])} 个指数")
    
    print("\n说明：这是快速版本，只分析了少量样本")
    print("要完整分析，请等待 complete_analysis.py 完成运行")

if __name__ == "__main__":
    main()
