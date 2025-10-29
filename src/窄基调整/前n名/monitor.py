#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时监控分析进度
"""

import os
import time
import glob
import pandas as pd

def count_cached_files():
    """统计已缓存的股票数据文件"""
    cache_dir = r"F:\stockdata\getDayKlineData"
    if not os.path.exists(cache_dir):
        return 0, []
    
    # 查找所有CSV文件
    csv_files = []
    for root, dirs, files in os.walk(cache_dir):
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(os.path.join(root, file))
    
    return len(csv_files), csv_files

def check_recent_activity():
    """检查最近的活动"""
    cache_dir = r"F:\stockdata\getDayKlineData"
    if not os.path.exists(cache_dir):
        return "缓存目录不存在"
    
    # 查找最近修改的文件
    recent_files = []
    current_time = time.time()
    for root, dirs, files in os.walk(cache_dir):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(root, file)
                mtime = os.path.getmtime(file_path)
                if current_time - mtime < 60:  # 1分钟内修改的文件
                    recent_files.append((file, mtime))
    
    if recent_files:
        recent_files.sort(key=lambda x: x[1], reverse=True)
        return f"最近1分钟内有 {len(recent_files)} 个文件被修改"
    else:
        return "最近1分钟内无文件活动"

def monitor_progress():
    """监控分析进度"""
    print("=" * 60)
    print("实时进度监控")
    print("=" * 60)
    
    # 检查结果文件
    if os.path.exists('all_stocks_performance_detail.csv'):
        df = pd.read_csv('all_stocks_performance_detail.csv')
        print(f"OK 已生成结果文件: {len(df)} 条记录")
        return True
    
    # 统计缓存文件
    total_files, csv_files = count_cached_files()
    print(f"缓存文件总数: {total_files}")
    
    # 检查最近活动
    activity = check_recent_activity()
    print(f"最近活动: {activity}")
    
    # 显示最近的几个文件
    if csv_files:
        recent_files = sorted(csv_files, key=os.path.getmtime, reverse=True)[:5]
        print(f"\n最近修改的文件:")
        for file_path in recent_files:
            filename = os.path.basename(file_path)
            mtime = time.ctime(os.path.getmtime(file_path))
            print(f"  {filename} ({mtime})")
    
    return False

if __name__ == "__main__":
    monitor_progress()