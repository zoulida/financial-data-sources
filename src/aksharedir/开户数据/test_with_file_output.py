"""测试脚本 - 结果输出到文件"""
import sys
import akshare as ak
import pandas as pd
from datetime import datetime

# 输出到文件和控制台
output_file = 'src/aksharedir/开户数据/test_result.txt'

def log(msg):
    """同时输出到控制台和文件"""
    print(msg)
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

# 清空文件
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('')

log("=" * 60)
log("AKShare 开户数据获取测试")
log("=" * 60)
log(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log(f"Python版本: {sys.version}")

try:
    log("\n1. 正在获取数据...")
    df = ak.stock_account_statistics_em()
    
    log(f"✓ 数据获取成功！")
    log(f"  数据行数: {len(df)}")
    log(f"  数据列数: {len(df.columns)}")
    
    log(f"\n2. 字段列表:")
    for i, col in enumerate(df.columns, 1):
        log(f"  {i}. {col}")
    
    # 转换日期
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    log(f"\n3. 数据范围:")
    log(f"  最早: {df['数据日期'].min().strftime('%Y-%m')}")
    log(f"  最新: {df['数据日期'].max().strftime('%Y-%m')}")
    
    log(f"\n4. 最近 5 条数据:")
    for idx, row in df.tail(5).iterrows():
        log(f"  {row['数据日期'].strftime('%Y-%m')} | "
            f"新增: {row['新增投资者-数量']:>7.2f}万户 | "
            f"总量: {row['期末投资者-总量']:>9.2f}万户 | "
            f"指数: {row['上证指数-收盘']:>7.2f}")
    
    log(f"\n5. 最新一条记录:")
    latest = df.iloc[-1]
    log(f"  数据日期: {latest['数据日期'].strftime('%Y-%m')}")
    log(f"  新增开户: {latest['新增投资者-数量']:.2f} 万户")
    log(f"  期末总量: {latest['期末投资者-总量']:.2f} 万户")
    log(f"  上证指数: {latest['上证指数-收盘']:.2f} 点")
    
    log(f"\n6. 基础统计:")
    log(f"  新增开户平均值: {df['新增投资者-数量'].mean():.2f} 万户")
    log(f"  新增开户中位数: {df['新增投资者-数量'].median():.2f} 万户")
    log(f"  新增开户最大值: {df['新增投资者-数量'].max():.2f} 万户")
    log(f"  新增开户最小值: {df['新增投资者-数量'].min():.2f} 万户")
    
    # 检查数据时效性
    latest_date = df['数据日期'].max()
    current_date = datetime.now()
    months_behind = (current_date.year - latest_date.year) * 12 + (current_date.month - latest_date.month)
    
    log(f"\n7. 数据时效性:")
    log(f"  当前时间: {current_date.strftime('%Y-%m')}")
    log(f"  数据最新: {latest_date.strftime('%Y-%m')}")
    log(f"  落后月数: {months_behind} 个月")
    
    if months_behind > 2:
        log(f"  ⚠️  提示: 数据已落后 {months_behind} 个月，可能需要使用其他数据源")
    
    log("\n" + "=" * 60)
    log("✓ 测试通过！所有功能正常")
    log("=" * 60)
    log(f"\n结果已保存到: {output_file}")
    
except Exception as e:
    log(f"\n✗ 测试失败: {str(e)}")
    import traceback
    log("\n详细错误信息:")
    log(traceback.format_exc())

print(f"\n\n完整结果请查看: {output_file}")

