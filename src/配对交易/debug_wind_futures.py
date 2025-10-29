#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Wind API期货数据获取
"""

from WindPy import w
import pandas as pd
from datetime import datetime

def debug_wind_futures():
    """调试Wind API期货数据获取"""
    print("=== 调试Wind API期货数据获取 ===")
    
    try:
        w.start()
        print("✅ Wind连接成功")
        
        # 测试期货数据获取
        code = "AU2412.SHF"
        print(f"\n测试期货代码: {code}")
        
        data = w.wsd(
            codes=code,
            fields="close",
            beginTime="2024-01-01",
            endTime="2024-12-31",
            options="Days=Trading"
        )
        
        print(f"错误代码: {data.ErrorCode}")
        print(f"数据长度: {len(data.Data)}")
        print(f"字段: {data.Fields}")
        print(f"时间长度: {len(data.Times)}")
        
        if data.ErrorCode == 0 and len(data.Data) > 0:
            print("原始数据结构:")
            print(f"Data: {data.Data}")
            print(f"Fields: {data.Fields}")
            print(f"Times: {data.Times[:5]}...")  # 只显示前5个时间
            
            # 尝试转换为DataFrame
            try:
                df = pd.DataFrame(data.Data).T
                df.columns = data.Fields
                df.index = data.Times
                df.index.name = 'Date'
                
                print(f"\n转换后的DataFrame:")
                print(f"形状: {df.shape}")
                print(f"列名: {df.columns.tolist()}")
                print(f"前5行:")
                print(df.head())
                
                # 检查close列
                if 'close' in df.columns:
                    close_data = df['close'].dropna()
                    print(f"\nclose列数据:")
                    print(f"有效数据点数: {len(close_data)}")
                    print(f"前5个值: {close_data.head().tolist()}")
                else:
                    print("❌ 没有close列")
                    
            except Exception as e:
                print(f"❌ DataFrame转换失败: {e}")
        else:
            print("❌ 数据获取失败")
            
    except Exception as e:
        print(f"❌ 异常: {e}")
    finally:
        try:
            w.stop()
            print("\n✅ Wind连接已关闭")
        except:
            pass

if __name__ == "__main__":
    debug_wind_futures()
