"""
调试脚本 - 测试单只基金的数据获取和处理
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from data_fetcher import DataFetcher

# 测试单只基金
fetcher = DataFetcher(start_date="20241101", end_date="20251102")

test_codes = ["159001.SZ", "510300.SH", "512880.SH"]

for code in test_codes:
    print("\n" + "="*80)
    print(f"测试标的: {code}")
    print("="*80)
    
    df = fetcher.get_single_stock_data(code, min_days=252)
    
    if df is not None:
        print(f"[OK] 成功获取数据")
        print(f"  数据量: {len(df)} 行")
        print(f"  数据列: {list(df.columns)}")
        print(f"\n前3行数据:")
        print(df.head(3))
        print(f"\n数据类型:")
        print(df.dtypes)
    else:
        print(f"[ERROR] 数据获取失败")

