"""
简单的系统测试脚本
==================

直接测试各个模块的功能
"""

import pandas as pd
import numpy as np
from datetime import datetime

def test_basic_functionality():
    """测试基本功能"""
    print("妖股因子量化系统 - 基本功能测试")
    print("=" * 50)
    
    # 1. 测试因子计算器
    print("\n1. 测试因子计算器...")
    try:
        from factor_calculator import MonsterStockFactorCalculator
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        np.random.seed(42)
        
        df = pd.DataFrame({
            'open': 100 + np.cumsum(np.random.randn(50) * 0.5),
            'high': 100 + np.cumsum(np.random.randn(50) * 0.5) + np.random.uniform(0, 2, 50),
            'low': 100 + np.cumsum(np.random.randn(50) * 0.5) - np.random.uniform(0, 2, 50),
            'close': 100 + np.cumsum(np.random.randn(50) * 0.5),
            'volume': np.random.uniform(1000000, 10000000, 50),
            'turnover': np.random.uniform(1, 10, 50)
        }, index=dates)
        
        # 确保价格数据合理性
        df['high'] = np.maximum(df['high'], np.maximum(df['open'], df['close']))
        df['low'] = np.minimum(df['low'], np.minimum(df['open'], df['close']))
        
        # 测试因子计算
        calculator = MonsterStockFactorCalculator()
        factors = calculator.calculate_all_factors(df)
        
        print(f"✓ 因子计算成功，生成 {factors.shape[1]} 个因子")
        print(f"  因子列表: {list(factors.columns)[:5]}...")  # 显示前5个因子
        
    except Exception as e:
        print(f"❌ 因子计算失败: {e}")
        return False
    
    # 2. 测试数据预处理器
    print("\n2. 测试数据预处理器...")
    try:
        from data_processor import DataProcessor
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        np.random.seed(42)
        
        factors_df = pd.DataFrame({
            'factor1': np.random.normal(0, 1, 50),
            'factor2': np.random.normal(0, 2, 50),
            'factor3': np.random.normal(0, 0.5, 50)
        }, index=dates)
        
        # 测试预处理
        processor = DataProcessor()
        processed_factors = processor.process_factors(factors_df)
        
        print(f"✓ 数据预处理成功，处理 {processed_factors.shape[1]} 个因子")
        
    except Exception as e:
        print(f"❌ 数据预处理失败: {e}")
        return False
    
    # 3. 测试概率分合成器
    print("\n3. 测试概率分合成器...")
    try:
        from probability_synthesizer import MonsterStockProbabilitySynthesizer
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        np.random.seed(42)
        
        factors_df = pd.DataFrame({
            'factor1': np.random.normal(0, 1, 50),
            'factor2': np.random.normal(0, 1, 50),
            'factor3': np.random.normal(0, 1, 50)
        }, index=dates)
        
        # 测试概率分合成
        synthesizer = MonsterStockProbabilitySynthesizer()
        result = synthesizer.calculate_monster_probability(factors_df)
        
        print(f"✓ 概率分合成成功，生成 {result.shape[1]} 列数据")
        if 'monster_probability' in result.columns:
            print(f"  妖股概率分范围: {result['monster_probability'].min():.3f} - {result['monster_probability'].max():.3f}")
        
    except Exception as e:
        print(f"❌ 概率分合成失败: {e}")
        return False
    
    # 4. 测试数据获取器
    print("\n4. 测试数据获取器...")
    try:
        from data_fetcher import MonsterStockDataFetcher
        
        # 测试数据获取
        fetcher = MonsterStockDataFetcher(use_mock_data=True)
        stock_data = fetcher.fetch_stock_data('000001.SZ', '20240101', '20241231', ['open', 'high', 'low', 'close', 'volume'])
        
        print(f"✓ 数据获取成功，获取 {stock_data.shape[0]} 行数据")
        print(f"  数据列: {list(stock_data.columns)}")
        
    except Exception as e:
        print(f"❌ 数据获取失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 测试回测框架
    print("\n5. 测试回测框架...")
    try:
        from backtester import MonsterStockBacktester
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        np.random.seed(42)
        
        factors_df = pd.DataFrame({
            'monster_probability': np.random.uniform(0, 1, 50),
            'monster_score': np.random.uniform(0, 100, 50)
        }, index=dates)
        
        price_data = pd.DataFrame({
            'close': 100 * np.cumprod(1 + np.random.normal(0.001, 0.02, 50))
        }, index=dates)
        
        # 测试回测
        backtester = MonsterStockBacktester()
        results = backtester.run_backtest(factors_df, price_data)
        
        print(f"✓ 回测成功，生成 {len(results)} 个结果项")
        
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 所有基本功能测试通过！")
    return True

if __name__ == "__main__":
    test_basic_functionality()
