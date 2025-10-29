"""
简单测试脚本 - 测试开户数据获取基本功能
"""

import akshare as ak
import pandas as pd

print("=" * 60)
print("测试 AKShare 开户数据获取")
print("=" * 60)

try:
    print("\n1. 正在获取数据...")
    df = ak.stock_account_statistics_em()
    print(df)
    
    print(f"✓ 数据获取成功！")
    print(f"  数据行数: {len(df)}")
    print(f"  数据列数: {len(df.columns)}")
    
    print(f"\n2. 字段列表:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    
    print(f"\n3. 数据范围:")
    print(f"  最早: {df['数据日期'].min()}")
    print(f"  最新: {df['数据日期'].max()}")
    
    print(f"\n4. 最近 5 个月数据:")
    print(df.tail().to_string())
    
    print(f"\n5. 最新一条记录:")
    latest = df.sort_values('数据日期').iloc[-1]
    print(f"  数据日期: {latest['数据日期']}")
    print(f"  新增开户: {latest['新增投资者-数量']:.2f} 万户")
    print(f"  期末总量: {latest['期末投资者-总量']:.2f} 万户")
    print(f"  上证指数: {latest['上证指数-收盘']:.2f} 点")
    
    print(f"\n6. 基础统计:")
    print(f"  新增开户平均值: {df['新增投资者-数量'].mean():.2f} 万户")
    print(f"  新增开户中位数: {df['新增投资者-数量'].median():.2f} 万户")
    print(f"  新增开户最大值: {df['新增投资者-数量'].max():.2f} 万户")
    print(f"  新增开户最小值: {df['新增投资者-数量'].min():.2f} 万户")
    
    print("\n" + "=" * 60)
    print("✓ 测试通过！所有功能正常")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ 测试失败: {str(e)}")
    import traceback
    traceback.print_exc()

