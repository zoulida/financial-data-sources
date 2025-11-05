#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Wind API获取历史期货数据
"""

from WindPy import w
import pandas as pd
from datetime import datetime, timedelta

def test_historical_futures():
    """测试历史期货数据"""
    print("=== 测试Wind历史期货数据获取 ===")
    
    # 尝试不同年份的期货合约
    futures_codes = [
        # 2023年合约
        "AU2306.SHFE", "AG2306.SHFE", "CU2306.SHFE", "AL2306.SHFE",
        "AU2312.SHFE", "AG2312.SHFE", "CU2312.SHFE", "AL2312.SHFE",
        # 2022年合约
        "AU2206.SHFE", "AG2206.SHFE", "CU2206.SHFE", "AL2206.SHFE",
        "AU2212.SHFE", "AG2212.SHFE", "CU2212.SHFE", "AL2212.SHFE",
        # 主力合约（通用代码）
        "AU0.SHFE", "AG0.SHFE", "CU0.SHFE", "AL0.SHFE",
    ]
    
    successful_codes = []
    
    for code in futures_codes:
        try:
            print(f"\n尝试获取期货数据: {code}")
            
            # 使用WSD获取历史数据
            data = w.wsd(
                codes=code,
                fields="close,open,high,low,volume,amt",
                beginTime="2023-01-01",
                endTime="2023-12-31",
                options="Days=Trading"
            )
            
            if data.ErrorCode != 0:
                print(f"❌ {code}: 错误代码 {data.ErrorCode}")
                continue
            
            # 转换为DataFrame
            if len(data.Data) > 0:
                df = pd.DataFrame(data.Data).T
                df.columns = data.Fields
                df.index = data.Times
                df.index.name = 'Date'
                
                # 检查是否有有效数据
                valid_data = df.dropna()
                if not valid_data.empty:
                    print(f"✅ {code}: 数据形状 {df.shape}, 有效数据 {len(valid_data)}")
                    print(f"   最新数据: {valid_data.tail(3)}")
                    successful_codes.append(code)
                else:
                    print(f"❌ {code}: 数据为空")
            else:
                print(f"❌ {code}: 无数据")
                
        except Exception as e:
            print(f"❌ {code}: 异常 {e}")
    
    return successful_codes

def test_futures_list():
    """测试获取期货列表"""
    print("\n=== 测试获取期货列表 ===")
    
    try:
        # 尝试获取期货列表
        data = w.wset("sectorconstituent", "sectorid=1000000000000000", "field=wind_code,sec_name")
        
        if data.ErrorCode != 0:
            print(f"❌ 获取期货列表失败: 错误代码 {data.ErrorCode}")
            return []
        
        # 转换为DataFrame
        df = pd.DataFrame(data.Data, columns=data.Fields, index=data.Codes)
        print(f"✅ 获取到期货列表，共{len(df)}个")
        
        # 筛选SHFE期货
        shfe_futures = df[df['WIND_CODE'].str.contains('SHFE', na=False)]
        print(f"SHFE期货数量: {len(shfe_futures)}")
        
        if len(shfe_futures) > 0:
            print("前10个SHFE期货:")
            print(shfe_futures.head(10))
            
            # 尝试获取前几个期货的数据
            test_codes = shfe_futures['WIND_CODE'].head(3).tolist()
            print(f"\n测试前3个期货: {test_codes}")
            
            for code in test_codes:
                try:
                    data = w.wsd(
                        codes=code,
                        fields="close",
                        beginTime="2024-01-01",
                        endTime="2024-12-31",
                        options="Days=Trading"
                    )
                    
                    if data.ErrorCode == 0 and len(data.Data) > 0:
                        df_test = pd.DataFrame(data.Data).T
                        df_test.columns = data.Fields
                        df_test.index = data.Times
                        valid_data = df_test.dropna()
                        
                        if not valid_data.empty:
                            print(f"✅ {code}: 有效数据 {len(valid_data)} 条")
                        else:
                            print(f"❌ {code}: 数据为空")
                    else:
                        print(f"❌ {code}: 获取失败")
                        
                except Exception as e:
                    print(f"❌ {code}: 异常 {e}")
        
        return shfe_futures['WIND_CODE'].tolist()
        
    except Exception as e:
        print(f"❌ 获取期货列表异常: {e}")
        return []

if __name__ == "__main__":
    print("开始测试Wind历史期货数据...")
    
    # 测试Wind连接
    try:
        w.start()
        print("✅ Wind连接成功")
    except Exception as e:
        print(f"❌ Wind连接失败: {e}")
        exit(1)
    
    try:
        # 测试期货列表
        futures_list = test_futures_list()
        
        # 测试历史期货数据
        successful_codes = test_historical_futures()
        
        if successful_codes:
            print(f"\n🎉 成功获取期货数据的代码: {successful_codes}")
        else:
            print("\n❌ 未获取到任何期货数据")
            
    finally:
        # 关闭Wind连接
        try:
            w.stop()
            print("\n✅ Wind连接已关闭")
        except:
            pass
    
    print("\n测试完成！")
