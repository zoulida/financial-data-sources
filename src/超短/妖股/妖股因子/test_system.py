"""
妖股因子量化系统测试脚本
========================

快速测试系统各个模块是否正常工作
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    try:
        from src.妖股.妖股因子 import (
            MonsterStockFactorCalculator,
            DataProcessor,
            MonsterStockProbabilitySynthesizer,
            MonsterStockDataFetcher,
            MonsterStockBacktester,
            MonsterStockQuantSystem
        )
        print("✓ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def test_factor_calculator():
    """测试因子计算器"""
    print("\n测试因子计算器...")
    try:
        from src.妖股.妖股因子 import MonsterStockFactorCalculator
        
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
        return True
    except Exception as e:
        print(f"❌ 因子计算失败: {e}")
        return False

def test_data_processor():
    """测试数据预处理器"""
    print("\n测试数据预处理器...")
    try:
        from src.妖股.妖股因子 import DataProcessor
        
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
        return True
    except Exception as e:
        print(f"❌ 数据预处理失败: {e}")
        return False

def test_probability_synthesizer():
    """测试概率分合成器"""
    print("\n测试概率分合成器...")
    try:
        from src.妖股.妖股因子 import MonsterStockProbabilitySynthesizer
        
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
        return True
    except Exception as e:
        print(f"❌ 概率分合成失败: {e}")
        return False

def test_data_fetcher():
    """测试数据获取器"""
    print("\n测试数据获取器...")
    try:
        from src.妖股.妖股因子 import MonsterStockDataFetcher
        
        # 测试数据获取
        fetcher = MonsterStockDataFetcher(use_mock_data=True)
        stock_data = fetcher.fetch_stock_data('000001.SZ', '20240101', '20241231')
        
        print(f"✓ 数据获取成功，获取 {stock_data.shape[0]} 行数据")
        print(f"  数据列: {list(stock_data.columns)}")
        return True
    except Exception as e:
        print(f"❌ 数据获取失败: {e}")
        return False

def test_backtester():
    """测试回测框架"""
    print("\n测试回测框架...")
    try:
        from src.妖股.妖股因子 import MonsterStockBacktester
        
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
        return True
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        return False

def test_full_system():
    """测试完整系统"""
    print("\n测试完整系统...")
    try:
        from src.妖股.妖股因子 import MonsterStockQuantSystem
        
        # 创建系统
        system = MonsterStockQuantSystem(use_mock_data=True)
        
        # 运行分析
        results = system.run_analysis(
            stock_code='000001.SZ',
            start_date='20240101',
            end_date='20241231',
            probability_threshold=0.5,
            save_results=False
        )
        
        print(f"✓ 完整系统测试成功")
        print(f"  最终因子数据形状: {results['final_factors'].shape}")
        print(f"  回测结果项数: {len(results['backtest_results'])}")
        return True
    except Exception as e:
        print(f"❌ 完整系统测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("妖股因子量化系统 - 系统测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("因子计算器", test_factor_calculator),
        ("数据预处理器", test_data_processor),
        ("概率分合成器", test_probability_synthesizer),
        ("数据获取器", test_data_fetcher),
        ("回测框架", test_backtester),
        ("完整系统", test_full_system)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统运行正常")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查相关模块")
        return 1

if __name__ == "__main__":
    exit(main())
