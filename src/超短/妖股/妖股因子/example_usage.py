"""
妖股因子量化系统使用示例
========================

展示如何使用妖股因子量化系统进行完整的分析流程。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 导入系统模块
from .main import MonsterStockQuantSystem
from .factor_calculator import MonsterStockFactorCalculator
from .data_processor import DataProcessor
from .probability_synthesizer import MonsterStockProbabilitySynthesizer
from .data_fetcher import MonsterStockDataFetcher
from .backtester import MonsterStockBacktester


def example_1_basic_usage():
    """示例1：基本使用流程"""
    print("=" * 60)
    print("示例1：基本使用流程")
    print("=" * 60)
    
    # 创建系统实例（使用模拟数据）
    system = MonsterStockQuantSystem(use_mock_data=True)
    
    # 运行分析
    results = system.run_analysis(
        stock_code='000001.SZ',
        start_date='20240101',
        end_date='20241231',
        probability_threshold=0.6
    )
    
    # 查看结果
    print("\n分析完成！")
    print(f"最终因子数据形状: {results['final_factors'].shape}")
    print(f"妖股概率分范围: {results['final_factors']['monster_probability'].min():.3f} - {results['final_factors']['monster_probability'].max():.3f}")
    
    return results


def example_2_step_by_step():
    """示例2：分步骤使用"""
    print("=" * 60)
    print("示例2：分步骤使用")
    print("=" * 60)
    
    # 1. 数据获取
    print("步骤1：数据获取")
    data_fetcher = MonsterStockDataFetcher(use_mock_data=True)
    
    stock_data = data_fetcher.fetch_stock_data(
        stock_code='000002.SZ',
        start_date='20240101',
        end_date='20241231',
        fields=['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover']
    )
    
    financial_data = data_fetcher.fetch_financial_data(
        stock_codes=['000002.SZ'],
        fields=['market_cap', 'pe_ttm', 'pb_mrq', 'industry', 'beta'],
        trade_date='20241201'
    )
    
    print(f"✓ 股票数据: {stock_data.shape}")
    print(f"✓ 财务数据: {financial_data.shape}")
    
    # 2. 因子计算
    print("\n步骤2：因子计算")
    calculator = MonsterStockFactorCalculator()
    raw_factors = calculator.calculate_all_factors(stock_data)
    print(f"✓ 原始因子: {raw_factors.shape}")
    print(f"因子列表: {list(raw_factors.columns)}")
    
    # 3. 数据预处理
    print("\n步骤3：数据预处理")
    processor = DataProcessor()
    processed_factors = processor.process_factors(
        raw_factors,
        market_cap=financial_data['market_cap'].iloc[0] if 'market_cap' in financial_data.columns else None,
        industry=financial_data['industry'].iloc[0] if 'industry' in financial_data.columns else None,
        beta=financial_data['beta'].iloc[0] if 'beta' in financial_data.columns else None
    )
    print(f"✓ 预处理因子: {processed_factors.shape}")
    
    # 4. 概率分合成
    print("\n步骤4：概率分合成")
    synthesizer = MonsterStockProbabilitySynthesizer()
    final_factors = synthesizer.calculate_monster_probability(processed_factors)
    print(f"✓ 最终因子: {final_factors.shape}")
    print(f"妖股概率分统计:")
    print(final_factors[['monster_probability', 'monster_score']].describe())
    
    # 5. 回测验证
    print("\n步骤5：回测验证")
    backtester = MonsterStockBacktester()
    backtest_results = backtester.run_backtest(final_factors, stock_data)
    print("✓ 回测完成")
    
    # 打印回测摘要
    backtester.print_summary()
    
    return {
        'stock_data': stock_data,
        'financial_data': financial_data,
        'raw_factors': raw_factors,
        'processed_factors': processed_factors,
        'final_factors': final_factors,
        'backtest_results': backtest_results
    }


def example_3_multiple_stocks():
    """示例3：多股票分析"""
    print("=" * 60)
    print("示例3：多股票分析")
    print("=" * 60)
    
    stock_codes = ['000001.SZ', '000002.SZ', '600000.SH']
    results = {}
    
    system = MonsterStockQuantSystem(use_mock_data=True)
    
    for stock_code in stock_codes:
        print(f"\n分析股票: {stock_code}")
        try:
            result = system.run_analysis(
                stock_code=stock_code,
                start_date='20240101',
                end_date='20241231',
                probability_threshold=0.5,
                save_results=False
            )
            results[stock_code] = result
            
            # 打印该股票的关键指标
            final_factors = result['final_factors']
            if 'monster_probability' in final_factors.columns:
                avg_prob = final_factors['monster_probability'].mean()
                max_prob = final_factors['monster_probability'].max()
                high_prob_count = (final_factors['monster_probability'] > 0.7).sum()
                
                print(f"  平均妖股概率: {avg_prob:.3f}")
                print(f"  最高妖股概率: {max_prob:.3f}")
                print(f"  高概率样本数: {high_prob_count}")
            
        except Exception as e:
            print(f"  ❌ 分析失败: {e}")
            continue
    
    # 汇总结果
    print(f"\n多股票分析完成！")
    print(f"成功分析股票数: {len(results)}")
    
    # 比较各股票的妖股概率
    if results:
        print("\n各股票妖股概率对比:")
        for stock_code, result in results.items():
            final_factors = result['final_factors']
            if 'monster_probability' in final_factors.columns:
                avg_prob = final_factors['monster_probability'].mean()
                print(f"  {stock_code}: {avg_prob:.3f}")
    
    return results


def example_4_parameter_tuning():
    """示例4：参数调优"""
    print("=" * 60)
    print("示例4：参数调优")
    print("=" * 60)
    
    # 测试不同的概率阈值
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    results = {}
    
    system = MonsterStockQuantSystem(use_mock_data=True)
    
    for threshold in thresholds:
        print(f"\n测试概率阈值: {threshold}")
        try:
            result = system.run_analysis(
                stock_code='000001.SZ',
                start_date='20240101',
                end_date='20241231',
                probability_threshold=threshold,
                save_results=False
            )
            
            # 提取关键指标
            backtest = result['backtest_results']
            perf_metrics = backtest['performance_metrics']
            
            results[threshold] = {
                'annual_return': perf_metrics['strategy_annual_return'],
                'sharpe_ratio': perf_metrics['strategy_sharpe'],
                'max_drawdown': perf_metrics['strategy_max_drawdown'],
                'excess_return': perf_metrics['excess_return']
            }
            
            print(f"  年化收益率: {perf_metrics['strategy_annual_return']:.2%}")
            print(f"  夏普比率: {perf_metrics['strategy_sharpe']:.4f}")
            print(f"  最大回撤: {perf_metrics['strategy_max_drawdown']:.2%}")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            continue
    
    # 找到最佳参数
    if results:
        print(f"\n参数调优结果:")
        print(f"{'阈值':<8} {'年化收益率':<12} {'夏普比率':<10} {'最大回撤':<12} {'超额收益':<12}")
        print("-" * 60)
        
        best_sharpe = 0
        best_threshold = None
        
        for threshold, metrics in results.items():
            print(f"{threshold:<8} {metrics['annual_return']:<12.2%} {metrics['sharpe_ratio']:<10.4f} {metrics['max_drawdown']:<12.2%} {metrics['excess_return']:<12.2%}")
            
            if metrics['sharpe_ratio'] > best_sharpe:
                best_sharpe = metrics['sharpe_ratio']
                best_threshold = threshold
        
        print(f"\n最佳概率阈值: {best_threshold} (夏普比率: {best_sharpe:.4f})")
    
    return results


def example_5_custom_factors():
    """示例5：自定义因子"""
    print("=" * 60)
    print("示例5：自定义因子")
    print("=" * 60)
    
    # 创建示例数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    stock_data = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(100) * 0.5),
        'high': 100 + np.cumsum(np.random.randn(100) * 0.5) + np.random.uniform(0, 2, 100),
        'low': 100 + np.cumsum(np.random.randn(100) * 0.5) - np.random.uniform(0, 2, 100),
        'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
        'volume': np.random.uniform(1000000, 10000000, 100),
        'turnover': np.random.uniform(1, 10, 100)
    }, index=dates)
    
    # 确保价格数据合理性
    stock_data['high'] = np.maximum(stock_data['high'], np.maximum(stock_data['open'], stock_data['close']))
    stock_data['low'] = np.minimum(stock_data['low'], np.minimum(stock_data['open'], stock_data['close']))
    
    # 计算自定义因子
    calculator = MonsterStockFactorCalculator()
    
    # 计算各阶段因子
    latent_factors = calculator.calculate_latent_factors(stock_data)
    startup_factors = calculator.calculate_startup_factors(stock_data)
    acceleration_factors = calculator.calculate_acceleration_factors(stock_data)
    divergence_factors = calculator.calculate_divergence_factors(stock_data)
    
    print(f"潜伏期因子: {latent_factors.shape}")
    print(f"启动期因子: {startup_factors.shape}")
    print(f"加速期因子: {acceleration_factors.shape}")
    print(f"分歧期因子: {divergence_factors.shape}")
    
    # 合并所有因子
    all_factors = pd.concat([
        latent_factors,
        startup_factors,
        acceleration_factors,
        divergence_factors
    ], axis=1)
    
    print(f"\n所有因子: {all_factors.shape}")
    print("因子列表:")
    for i, col in enumerate(all_factors.columns, 1):
        print(f"  {i:2d}. {col}")
    
    # 数据预处理
    processor = DataProcessor()
    processed_factors = processor.process_factors(all_factors)
    
    # 概率分合成
    synthesizer = MonsterStockProbabilitySynthesizer()
    final_factors = synthesizer.calculate_monster_probability(processed_factors)
    
    print(f"\n最终结果: {final_factors.shape}")
    print(f"妖股概率分统计:")
    print(final_factors[['monster_probability', 'monster_score']].describe())
    
    return {
        'stock_data': stock_data,
        'all_factors': all_factors,
        'processed_factors': processed_factors,
        'final_factors': final_factors
    }


def run_all_examples():
    """运行所有示例"""
    print("妖股因子量化系统 - 完整示例演示")
    print("=" * 80)
    
    examples = [
        ("基本使用流程", example_1_basic_usage),
        ("分步骤使用", example_2_step_by_step),
        ("多股票分析", example_3_multiple_stocks),
        ("参数调优", example_4_parameter_tuning),
        ("自定义因子", example_5_custom_factors)
    ]
    
    for name, func in examples:
        try:
            print(f"\n{'='*20} {name} {'='*20}")
            result = func()
            print(f"✓ {name} 完成")
        except Exception as e:
            print(f"❌ {name} 失败: {e}")
            continue
    
    print(f"\n{'='*80}")
    print("所有示例演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    # 运行所有示例
    run_all_examples()
    
    # 或者运行单个示例
    # example_1_basic_usage()
    # example_2_step_by_step()
    # example_3_multiple_stocks()
    # example_4_parameter_tuning()
    # example_5_custom_factors()
