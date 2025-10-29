#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流程：从指数列表到完整分析结果
"""

import pandas as pd
from WindPy import w
from datetime import datetime
import time

def main():
    """
    主流程
    """
    print("=" * 80)
    print("完整分析流程")
    print("=" * 80)
    
    # 1. 初始化Wind API
    print("\n1. 初始化Wind API...")
    w.start()
    
    # 2. 读取目标指数列表
    print("\n2. 读取目标指数列表...")
    indices_df = pd.read_csv('top_indices_list.csv')
    print(f"共 {len(indices_df)} 个指数待分析")
    
    # 3. 下载变动数据
    print("\n3. 开始下载变动数据...")
    start_date = "2023-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    completed = []
    failed = []
    
    for idx, row in indices_df.iterrows():
        wind_code = row['跟踪指数代码']
        index_name = row['跟踪指数名称']
        
        print(f"\n[{idx+1}/{len(indices_df)}] 正在下载: {index_name} ({wind_code})")
        
        try:
            # 检查是否已经下载
            filename = f"{index_name}_{wind_code}_changes.csv"
            try:
                pd.read_csv(filename)
                print(f"  数据已存在，跳过")
                completed.append(index_name)
                continue
            except:
                pass
            
            # 下载数据
            data = w.wset("indexhistory", 
                         f"startdate={start_date};enddate={end_date};windcode={wind_code}")
            
            if data.ErrorCode != 0:
                print(f"  下载失败，错误代码: {data.ErrorCode}")
                failed.append((index_name, wind_code))
                continue
            
            # 保存数据
            df = pd.DataFrame(data.Data).T
            df.columns = data.Fields
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            print(f"  成功下载 {len(df)} 条记录")
            completed.append(index_name)
            
            # 延迟以避免API限制
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  处理失败: {e}")
            failed.append((index_name, wind_code))
    
    # 4. 显示结果
    print("\n" + "=" * 80)
    print("下载完成")
    print("=" * 80)
    print(f"成功: {len(completed)} 个指数")
    print(f"失败: {len(failed)} 个指数")
    
    if completed:
        print("\n成功的指数:")
        for name in completed:
            print(f"  - {name}")
    
    if failed:
        print("\n失败的指数:")
        for name, code in failed:
            print(f"  - {name} ({code})")
    
    # 清理
    w.stop()
    print("\n分析流程完成！")

if __name__ == "__main__":
    main()
