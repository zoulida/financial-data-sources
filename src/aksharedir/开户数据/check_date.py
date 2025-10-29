"""检查开户数据的日期范围"""
import akshare as ak
import pandas as pd
from datetime import datetime

print("=" * 60)
print("检查开户数据日期范围")
print("=" * 60)

try:
    # 获取数据
    print("\n正在获取数据...")
    df = ak.stock_account_statistics_em()
    
    print(f"✓ 数据获取成功")
    print(f"  总行数: {len(df)}")
    
    # 转换日期
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 日期范围
    print(f"\n日期范围:")
    print(f"  最早: {df['数据日期'].min().strftime('%Y-%m-%d')}")
    print(f"  最新: {df['数据日期'].max().strftime('%Y-%m-%d')}")
    
    # 检查是否是最新数据
    latest_date = df['数据日期'].max()
    current_date = datetime.now()
    
    # 计算应该有的最新月份（上个月）
    if current_date.day < 15:  # 如果当前是本月15号之前，最新数据应该是前两个月
        expected_latest = pd.Timestamp(current_date.year, current_date.month, 1) - pd.DateOffset(months=2)
    else:  # 如果是15号之后，最新数据应该是上个月
        expected_latest = pd.Timestamp(current_date.year, current_date.month, 1) - pd.DateOffset(months=1)
    
    print(f"\n数据时效性:")
    print(f"  当前时间: {current_date.strftime('%Y-%m-%d')}")
    print(f"  预期最新: {expected_latest.strftime('%Y-%m')}")
    print(f"  实际最新: {latest_date.strftime('%Y-%m')}")
    
    if latest_date >= expected_latest:
        print(f"  状态: ✓ 数据是最新的")
    else:
        months_behind = (expected_latest.year - latest_date.year) * 12 + (expected_latest.month - latest_date.month)
        print(f"  状态: ⚠ 数据落后 {months_behind} 个月")
        print(f"  说明: 可能是数据源未更新或AKShare需要升级")
    
    # 显示最近的数据
    print(f"\n最近 10 条数据:")
    print(df[['数据日期', '新增投资者-总量', '期末投资者-总量', '上证指数-月末收盘价']].tail(10).to_string())
    
    # 保存到文件方便查看
    with open('src/aksharedir/开户数据/date_check_result.txt', 'w', encoding='utf-8') as f:
        f.write(f"检查时间: {current_date.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"数据行数: {len(df)}\n")
        f.write(f"最早日期: {df['数据日期'].min().strftime('%Y-%m-%d')}\n")
        f.write(f"最新日期: {df['数据日期'].max().strftime('%Y-%m-%d')}\n\n")
        f.write("最近10条数据:\n")
        f.write(df[['数据日期', '新增投资者-总量', '期末投资者-总量', '上证指数-月末收盘价']].tail(10).to_string())
    
    print(f"\n✓ 结果已保存到: src/aksharedir/开户数据/date_check_result.txt")
    
except Exception as e:
    print(f"\n✗ 错误: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

