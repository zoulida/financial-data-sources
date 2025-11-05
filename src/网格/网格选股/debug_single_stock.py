"""
调试脚本 - 测试单只基金的处理过程
找出为什么所有基金处理都失败
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import traceback

# 添加项目路径
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from data_fetcher import DataFetcher
from md.获取enddate.get_date_range import get_date_range

print("="*80)
print("调试脚本 - 测试单只基金处理")
print("="*80)

# 获取日期范围
start_date, end_date, reason = get_date_range()
print(f"\n日期范围: {start_date} ~ {end_date} ({reason})")

# 初始化数据获取器
print("\n初始化数据获取器...")
fetcher = DataFetcher(start_date=start_date, end_date=end_date)

# 测试基金列表
test_codes = ["159001.SZ", "510300.SH", "512880.SH"]

for code in test_codes:
    print("\n" + "="*80)
    print(f"测试基金: {code}")
    print("="*80)
    
    try:
        # 1. 获取数据
        print(f"\n[步骤1] 获取数据...")
        df = fetcher.get_single_stock_data(code)
        
        if df is None:
            print(f"[ERROR] 数据获取失败 - df 为 None")
            continue
        
        print(f"[OK] 数据获取成功")
        print(f"  数据量: {len(df)} 行")
        print(f"  数据列: {list(df.columns)}")
        print(f"  数据类型: {df.dtypes.to_dict()}")
        
        # 显示前几行
        print(f"\n前5行数据:")
        print(df.head())
        
        # 2. 检查数据是否足够252天
        print(f"\n[步骤2] 检查数据量...")
        if len(df) < 252:
            print(f"[ERROR] 数据不足 - 需要252天，实际{len(df)}天")
            continue
        else:
            print(f"[OK] 数据量充足 - {len(df)}天")
        
        # 3. 检查必需列
        print(f"\n[步骤3] 检查必需列...")
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"[ERROR] 缺少列: {missing_cols}")
            continue
        else:
            print(f"[OK] 所有必需列存在")
        
        # 4. 测试计算VolScore
        print(f"\n[步骤4] 计算VolScore...")
        try:
            close = df['close'].values
            open_price = df['open'].values
            high = df['high'].values
            low = df['low'].values
            
            # 计算30日收盘-收盘年化波动率
            returns_30 = np.log(close[-30:] / close[-31:-1])
            hist_vol_30 = np.std(returns_30) * np.sqrt(252) * 100
            
            print(f"[OK] VolScore 计算成功")
            print(f"  30日年化波动率: {hist_vol_30:.2f}%")
            
        except Exception as e:
            print(f"[ERROR] VolScore 计算失败: {e}")
            traceback.print_exc()
            continue
        
        # 5. 测试计算HLScore
        print(f"\n[步骤5] 计算HLScore...")
        try:
            import statsmodels.api as sm
            
            # 取最近252个交易日
            close_252 = close[-252:]
            log_prices = np.log(close_252)
            
            # 测试单次HL计算
            y_t = log_prices[1:]
            y_t_1 = log_prices[:-1]
            delta_y = y_t - y_t_1
            
            X = sm.add_constant(y_t_1)
            model = sm.OLS(delta_y, X)
            results = model.fit()
            beta = results.params[1]
            
            if beta < 0:
                theta = -np.log(1 + beta)
                hl = np.log(2) / theta
                print(f"[OK] HLScore 计算成功")
                print(f"  半衰期: {hl:.2f} 天")
                print(f"  beta: {beta:.6f}")
            else:
                print(f"[WARNING] beta >= 0，不均值回归")
                print(f"  beta: {beta:.6f}")
            
        except Exception as e:
            print(f"[ERROR] HLScore 计算失败: {e}")
            traceback.print_exc()
            continue
        
        print(f"\n[SUCCESS] {code} 所有测试通过！")
        
    except Exception as e:
        print(f"\n[ERROR] 处理 {code} 时发生异常:")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {str(e)}")
        traceback.print_exc()

print("\n" + "="*80)
print("调试完成")
print("="*80)

