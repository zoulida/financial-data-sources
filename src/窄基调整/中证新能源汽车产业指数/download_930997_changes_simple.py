#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载930997（中证1000）变动股数据 - 简化版
使用Wind API的wset函数获取指数变动股数据
"""

from WindPy import w
import pandas as pd
from datetime import datetime

def download_930997_changes():
    """
    下载930997（中证1000）变动股数据
    """
    try:
        # 初始化Wind API
        print("正在初始化Wind API...")
        w.start()
        
        # 设置日期范围
        start_date = "2024-01-01"
        end_date = "2025-10-24"
        
        print(f"正在下载930997（中证1000）{start_date}至{end_date}的变动股数据...")
        
        # 使用wset函数获取指数变动股数据
        data = w.wset("indexhistory", f"startdate={start_date};enddate={end_date};windcode=930997.CSI")
        
        # 检查数据是否获取成功
        if data.ErrorCode != 0:
            print(f"数据获取失败，错误代码: {data.ErrorCode}")
            print(f"错误信息: {data.Data}")
            return None
        
        # 将数据转换为DataFrame
        if data.Data and data.Fields:
            df = pd.DataFrame(data.Data).T
            df.columns = data.Fields
            df.index.name = 'Index'
        else:
            print("没有获取到数据")
            return None
        
        print(f"成功获取{len(df)}条变动股数据")
        print(f"数据字段: {data.Fields}")
        
        # 显示前几行数据
        print("\n前10行数据预览:")
        print(df.head(10))
        
        # 保存数据到CSV文件
        output_file = f"930997_changes_{start_date.replace('-', '')}_{end_date.replace('-', '')}.csv"
        df.to_csv(output_file, encoding='utf-8-sig')
        print(f"\n数据已保存到: {output_file}")
        
        # 显示统计信息
        print(f"\n统计信息:")
        print(f"总变动记录数: {len(df)}")
        print(f"数据字段数量: {len(data.Fields)}")
        
        # 显示变动类型统计
        if 'tradestatus' in df.columns:
            print(f"\n变动类型统计:")
            print(df['tradestatus'].value_counts())
        
        # 显示行业分布
        if 'windhy' in df.columns:
            print(f"\n行业分布:")
            print(df['windhy'].value_counts())
        
        return df
        
    except Exception as e:
        print(f"下载过程中发生错误: {str(e)}")
        return None
    
    finally:
        # 关闭Wind API连接
        try:
            w.stop()
            print("\nWind API连接已关闭")
        except:
            pass

if __name__ == "__main__":
    print("=" * 60)
    print("930997（中证1000）变动股数据下载工具")
    print("=" * 60)
    
    # 下载变动股数据
    result = download_930997_changes()
    
    if result is not None:
        print("\n下载完成！")
        print(f"共获取 {len(result)} 条变动记录")
        print("数据已保存为CSV文件")
    else:
        print("下载失败，请检查网络连接和Wind API配置")
