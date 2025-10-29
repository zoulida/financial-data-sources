#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的财务数据测试程序
逻辑：先尝试读取，如果本地没有数据再下载
"""

from xtquant.xtdata import get_financial_data, download_financial_data
import pandas as pd

def test_read_first():
    """
    先尝试读取数据
    """
    print("=" * 50)
    print("步骤1: 先尝试读取本地数据")
    print("=" * 50)
    
    try:
        print("正在尝试读取贵州茅台归母净利润数据...")
        
        df = get_financial_data(
            stock_list=['600519.SH'],
            table='Income',
            fields=['net_profit_excl_min_int_inc'],  # 归母净利
            report_type='report_time',   # 按报告期
            start_time='20230101',
            end_time='20251231'
        )
        
        print(f"[OK] 读取成功！数据形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")
        print("前5行数据:")
        print(df.head())
        return True
        
    except Exception as e:
        print(f"[ERROR] 读取失败: {e}")
        print("可能原因: 本地没有数据，需要先下载")
        return False

def test_download():
    """
    如果读取失败，则下载数据
    """
    print("\n" + "=" * 50)
    print("步骤2: 本地数据不存在，开始下载")
    print("=" * 50)
    
    try:
        print("正在下载财务数据...")
        print("股票: ['600519.SH']")
        print("报表: ['Income']")
        
        result = download_financial_data(
            stock_list=['600519.SH'],
            table_list=['Income']
        )
        
        print(f"[OK] 下载完成！结果: {result}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        return False

def main():
    """
    主函数
    """
    print("迅投（QMT）财务数据测试程序")
    print("逻辑：先读取，再下载")
    print("=" * 50)
    
    # 先尝试读取
    if test_read_first():
        print("\n[OK] 程序完成：本地数据读取成功！")
    else:
        # 读取失败，尝试下载
        if test_download():
            print("\n等待3秒后重新尝试读取...")
            import time
            time.sleep(3)
            
            # 重新尝试读取
            if test_read_first():
                print("\n[OK] 程序完成：下载并读取成功！")
            else:
                print("\n[ERROR] 程序失败：下载后仍无法读取数据")
        else:
            print("\n[ERROR] 程序失败：下载失败")

if __name__ == "__main__":
    main()


