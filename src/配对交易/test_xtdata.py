#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XtQuant xtdata 接口测试脚本
用于测试数据获取功能和验证接口可用性
"""

from xtquant import xtdata
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_xtdata_connection():
    """测试 xtdata 连接"""
    try:
        print("🔍 测试 XtQuant xtdata 连接...")
        
        # 注意：需要先设置 Token
        # xtdata.set_token('your_token_here')
        
        print("✅ xtdata 模块导入成功")
        return True
    except Exception as e:
        print(f"❌ xtdata 连接失败: {str(e)}")
        return False

def test_stock_data():
    """测试股票数据获取"""
    try:
        print("\n📈 测试股票数据获取...")
        
        # 测试获取平安银行数据
        data = xtdata.get_market_data_ex(
            field_list=['close'],
            stock_list=['000001.SZ'],
            period='1d',
            count=10
        )
        
        if data and 'close' in data:
            print(f"✅ 股票数据获取成功，数据点: {len(data['close'])}")
            print(f"最新收盘价: {data['close']['000001.SZ'].iloc[-1]:.2f}")
            return True
        else:
            print("❌ 股票数据获取失败")
            return False
            
    except Exception as e:
        print(f"❌ 股票数据获取失败: {str(e)}")
        return False

def test_index_data():
    """测试指数数据获取"""
    try:
        print("\n📊 测试指数数据获取...")
        
        # 测试获取沪深300指数数据
        data = xtdata.get_market_data_ex(
            field_list=['close'],
            stock_list=['000300.SH'],
            period='1d',
            count=10
        )
        
        if data and 'close' in data:
            print(f"✅ 指数数据获取成功，数据点: {len(data['close'])}")
            print(f"最新收盘价: {data['close']['000300.SH'].iloc[-1]:.2f}")
            return True
        else:
            print("❌ 指数数据获取失败")
            return False
            
    except Exception as e:
        print(f"❌ 指数数据获取失败: {str(e)}")
        return False

def test_etf_data():
    """测试ETF数据获取"""
    try:
        print("\n💰 测试ETF数据获取...")
        
        # 测试获取中证500ETF数据
        data = xtdata.get_market_data_ex(
            field_list=['close'],
            stock_list=['510500.SH'],
            period='1d',
            count=10
        )
        
        if data and 'close' in data:
            print(f"✅ ETF数据获取成功，数据点: {len(data['close'])}")
            print(f"最新收盘价: {data['close']['510500.SH'].iloc[-1]:.2f}")
            return True
        else:
            print("❌ ETF数据获取失败")
            return False
            
    except Exception as e:
        print(f"❌ ETF数据获取失败: {str(e)}")
        return False

def test_futures_data():
    """测试期货数据获取"""
    try:
        print("\n⚡ 测试期货数据获取...")
        
        # 测试获取铜期货主力合约数据
        data = xtdata.get_market_data_ex(
            field_list=['close'],
            stock_list=['CU0'],
            period='1d',
            count=10
        )
        
        if data and 'close' in data:
            print(f"✅ 期货数据获取成功，数据点: {len(data['close'])}")
            print(f"最新收盘价: {data['close']['CU0'].iloc[-1]:.2f}")
            return True
        else:
            print("❌ 期货数据获取失败")
            return False
            
    except Exception as e:
        print(f"❌ 期货数据获取失败: {str(e)}")
        return False

def test_financial_data():
    """测试财务数据获取"""
    try:
        print("\n📋 测试财务数据获取...")
        
        # 测试获取财务数据
        data = xtdata.get_financial_data(
            stock_list=['000001.SZ'],
            report_type='Income',
            field_list=['totalRevenue', 'netProfit'],
            start_time='20230101',
            end_time='20231231'
        )
        
        if data:
            print(f"✅ 财务数据获取成功")
            print(f"数据字段: {list(data.keys())}")
            return True
        else:
            print("❌ 财务数据获取失败")
            return False
            
    except Exception as e:
        print(f"❌ 财务数据获取失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始 XtQuant xtdata 接口测试")
    print("=" * 50)
    
    # 测试连接
    if not test_xtdata_connection():
        print("\n❌ 无法连接到 xtdata，请检查 Token 设置")
        return
    
    # 测试各种数据获取
    tests = [
        test_stock_data,
        test_index_data,
        test_etf_data,
        test_futures_data,
        test_financial_data
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
            results.append(False)
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    test_names = [
        "股票数据",
        "指数数据", 
        "ETF数据",
        "期货数据",
        "财务数据"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{i+1}. {name}: {status}")
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n🎯 总体结果: {success_count}/{total_count} 项测试通过")
    
    if success_count == total_count:
        print("🎉 所有测试通过！可以开始使用比价监控脚本")
    else:
        print("⚠️  部分测试失败，请检查相关接口和权限")

if __name__ == "__main__":
    main()
