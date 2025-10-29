#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载窄基前60名指数的成分股变动数据
"""

import pandas as pd
from WindPy import w
from datetime import datetime
import time
import os

def main():
    """
    主流程：下载所有指数变动数据
    """
    print("=" * 80)
    print("下载窄基前60名指数成分股变动数据")
    print("=" * 80)
    
    # 1. 初始化Wind API
    print("\n1. 初始化Wind API...")
    try:
        w.start()
        print("✓ Wind API 初始化成功")
    except Exception as e:
        print(f"✗ Wind API 初始化失败: {e}")
        return
    
    # 2. 读取目标指数列表
    print("\n2. 读取指数列表...")
    indices_file = 'zhaiji_top_indices_list.csv'
    
    if not os.path.exists(indices_file):
        print(f"✗ 文件不存在: {indices_file}")
        return
    
    indices_df = pd.read_csv(indices_file)
    print(f"✓ 共 {len(indices_df)} 个指数待下载")
    
    # 显示指数列表
    print("\n待下载指数列表:")
    for idx, row in indices_df.iterrows():
        print(f"  {idx+1:2d}. {row['跟踪指数代码']:15s} - {row['跟踪指数名称']}")
    
    # 3. 下载变动数据
    print("\n3. 开始下载变动数据...")
    start_date = "2023-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    completed = []
    failed = []
    skipped = []
    
    total = len(indices_df)
    
    for idx, row in indices_df.iterrows():
        wind_code = row['跟踪指数代码']
        index_name = row['跟踪指数名称']
        
        print(f"\n[{idx+1}/{total}] {index_name} ({wind_code})")
        
        try:
            # 检查是否已经下载
            filename = f"{index_name}_{wind_code}_changes.csv"
            
            if os.path.exists(filename):
                try:
                    df_existing = pd.read_csv(filename)
                    print(f"  ✓ 数据已存在，共 {len(df_existing)} 条记录，跳过")
                    skipped.append((index_name, wind_code, len(df_existing)))
                    completed.append(index_name)
                    continue
                except:
                    print(f"  ⚠ 文件存在但无法读取，重新下载...")
            
            # 下载数据
            print(f"  正在下载...")
            data = w.wset("indexhistory", 
                         f"startdate={start_date};enddate={end_date};windcode={wind_code}")
            
            if data.ErrorCode != 0:
                print(f"  ✗ 下载失败，错误代码: {data.ErrorCode}")
                failed.append((index_name, wind_code, data.ErrorCode))
                continue
            
            # 检查数据是否为空
            if not data.Data or len(data.Data) == 0:
                print(f"  ⚠ 未获取到数据")
                failed.append((index_name, wind_code, "无数据"))
                continue
            
            # 保存数据
            df = pd.DataFrame(data.Data).T
            df.columns = data.Fields
            
            # 统计纳入和剔除数量
            newly_included = df[df['tradestatus'] == '纳入'] if 'tradestatus' in df.columns else pd.DataFrame()
            excluded = df[df['tradestatus'] == '剔除'] if 'tradestatus' in df.columns else pd.DataFrame()
            
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            print(f"  ✓ 成功下载 {len(df)} 条记录 (纳入: {len(newly_included)}, 剔除: {len(excluded)})")
            completed.append(index_name)
            
            # 延迟以避免API限制
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            failed.append((index_name, wind_code, str(e)))
    
    # 4. 显示结果统计
    print("\n" + "=" * 80)
    print("下载完成统计")
    print("=" * 80)
    print(f"总计:     {total} 个指数")
    print(f"已存在:   {len(skipped)} 个指数")
    print(f"成功下载: {len(completed) - len(skipped)} 个指数")
    print(f"失败:     {len(failed)} 个指数")
    
    if skipped:
        print("\n已存在的指数:")
        for name, code, count in skipped:
            print(f"  ✓ {name} ({code}) - {count} 条记录")
    
    if completed and len(completed) > len(skipped):
        print("\n新下载的指数:")
        for name in completed:
            if name not in [s[0] for s in skipped]:
                print(f"  ✓ {name}")
    
    if failed:
        print("\n失败的指数:")
        for name, code, error in failed:
            print(f"  ✗ {name} ({code}) - {error}")
    
    # 5. 生成汇总报告
    if completed:
        print("\n" + "=" * 80)
        print("生成汇总报告...")
        print("=" * 80)
        
        all_data = []
        for name in completed:
            for row in indices_df.itertuples():
                if row.跟踪指数名称 == name:
                    wind_code = row.跟踪指数代码
                    filename = f"{name}_{wind_code}_changes.csv"
                    
                    try:
                        df = pd.read_csv(filename)
                        newly_included = df[df['tradestatus'] == '纳入'] if 'tradestatus' in df.columns else pd.DataFrame()
                        
                        all_data.append({
                            '跟踪指数代码': wind_code,
                            '跟踪指数名称': name,
                            '基金规模(亿元)': row.基金规模亿元,
                            '变动记录数': len(df),
                            '新纳入数': len(newly_included),
                            '剔除数': len(df) - len(newly_included)
                        })
                    except:
                        pass
                    break
        
        if all_data:
            summary_df = pd.DataFrame(all_data)
            summary_df = summary_df.sort_values('基金规模亿元', ascending=False)
            
            summary_file = 'download_summary.csv'
            summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
            print(f"✓ 汇总报告已保存到: {summary_file}")
            print(f"\n前10名指数:")
            for idx, row in summary_df.head(10).iterrows():
                print(f"  {idx+1:2d}. {row['跟踪指数名称']:20s} - 纳入: {row['新纳入数']:3d} / 剔除: {row['剔除数']:3d}")
    
    print("\n下载流程完成！")
    
    # 清理
    try:
        w.stop()
    except:
        pass

if __name__ == "__main__":
    main()

