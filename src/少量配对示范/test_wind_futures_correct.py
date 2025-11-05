#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Wind API获取期货数据 - 使用正确的代码格式
"""

from WindPy import w
import pandas as pd
from datetime import datetime

def test_wind_connection():
    """测试Wind连接"""
    print("=== 测试Wind连接 ===")
    try:
        w.start()
        print("✅ Wind连接成功")
        return True
    except Exception as e:
        print(f"❌ Wind连接失败: {e}")
        return False

def test_futures_data():
    """测试期货数据获取 - 使用正确的代码格式"""
    print("\n=== 测试Wind期货数据获取（正确代码格式） ===")
    
    # 使用正确的期货代码格式
    futures_codes = [
        # 上期所期货 - 使用.SHF后缀
        "AU2406.SHF", "AG2406.SHF", "CU2406.SHF", "AL2406.SHF",
        "AU2412.SHF", "AG2412.SHF", "CU2412.SHF", "AL2412.SHF",
        "AU2501.SHF", "AG2501.SHF", "CU2501.SHF", "AL2501.SHF",
        # 主力合约
        "AU0.SHF", "AG0.SHF", "CU0.SHF", "AL0.SHF",
        # 其他可能格式
        "AU2406.SHFE", "AG2406.SHFE", "CU2406.SHFE", "AL2406.SHFE",
    ]
    
    successful_codes = []
    
    for code in futures_codes:
        try:
            print(f"\n尝试获取期货数据: {code}")
            
            # 使用WSD获取历史数据
            data = w.wsd(
                codes=code,
                fields="close,open,high,low,volume,amt",
                beginTime="2024-01-01",
                endTime="2024-12-31",
                options="Days=Trading"
            )
            
            if data.ErrorCode != 0:
                print(f"❌ {code}: 错误代码 {data.ErrorCode}, 错误信息 {data.Data}")
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

def test_futures_snapshot():
    """测试期货截面数据"""
    print("\n=== 测试Wind期货截面数据 ===")
    
    futures_codes = ["AU2406.SHF", "AG2406.SHF", "CU2406.SHF", "AL2406.SHF"]
    
    try:
        # 使用WSS获取截面数据
        data = w.wss(
            codes=futures_codes,
            fields="sec_name,close,pre_close,chg,pct_chg,volume,amt",
            options="tradeDate=20241201"
        )
        
        if data.ErrorCode != 0:
            print(f"❌ 截面数据获取失败: 错误代码 {data.ErrorCode}")
            return False
        
        # 转换为DataFrame
        if len(data.Data) > 0:
            df = pd.DataFrame(data.Data).T
            df.columns = data.Fields
            df.index = data.Codes
            df.index.name = 'Code'
            
            print("✅ 期货截面数据获取成功:")
            print(df)
            return True
        else:
            print("❌ 截面数据为空")
            return False
        
    except Exception as e:
        print(f"❌ 截面数据获取异常: {e}")
        return False

def test_stock_data():
    """测试股票数据获取（对比）"""
    print("\n=== 测试Wind股票数据获取（对比） ===")
    
    try:
        # 获取股票数据作为对比
        data = w.wsd(
            codes="000001.SZ",
            fields="close,open,high,low,volume,amt",
            beginTime="2024-01-01",
            endTime="2024-12-31",
            options="Days=Trading"
        )
        
        if data.ErrorCode != 0:
            print(f"❌ 股票数据获取失败: 错误代码 {data.ErrorCode}")
            return False
        
        # 转换为DataFrame
        if len(data.Data) > 0:
            df = pd.DataFrame(data.Data).T
            df.columns = data.Fields
            df.index = data.Times
            df.index.name = 'Date'
            
            print("✅ 股票数据获取成功:")
            print(f"数据形状: {df.shape}")
            print(f"最新数据: {df.tail(3)}")
            return True
        else:
            print("❌ 股票数据为空")
            return False
        
    except Exception as e:
        print(f"❌ 股票数据获取异常: {e}")
        return False

if __name__ == "__main__":
    print("开始测试Wind API（正确代码格式）...")
    
    # 测试Wind连接
    if not test_wind_connection():
        print("Wind连接失败，退出测试")
        exit(1)
    
    try:
        # 测试股票数据（对比）
        test_stock_data()
        
        # 测试期货截面数据
        test_futures_snapshot()
        
        # 测试期货历史数据
        successful_codes = test_futures_data()
        
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
