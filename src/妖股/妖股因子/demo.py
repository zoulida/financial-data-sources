"""
妖股因子量化系统演示
====================

展示完整的妖股因子量化分析流程
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 导入系统模块
from factor_calculator import MonsterStockFactorCalculator
from data_processor import DataProcessor
from probability_synthesizer import MonsterStockProbabilitySynthesizer
from data_fetcher import MonsterStockDataFetcher
from backtester import MonsterStockBacktester


def demo_complete_analysis():
    """完整分析演示"""
    print("=" * 80)
    print("妖股因子量化系统 - 完整分析演示")
    print("=" * 80)
    
    # 1. 数据获取
    print("\n【步骤1】数据获取")
    print("-" * 40)
    
    data_fetcher = MonsterStockDataFetcher(use_mock_data=True)
    
    # 获取股票数据
    stock_data = data_fetcher.fetch_stock_data(
        stock_code='000001.SZ',
        start_date='20240101',
        end_date='20241231',
        fields=['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover', 'pct_chg']
    )
    
    # 获取财务数据
    financial_data = data_fetcher.fetch_financial_data(
        stock_codes=['000001.SZ'],
        fields=['market_cap', 'pe_ttm', 'pb_mrq', 'industry', 'beta'],
        trade_date='20241201'
    )
    
    print(f"✓ 股票数据: {stock_data.shape}")
    print(f"✓ 财务数据: {financial_data.shape}")
    print(f"✓ 数据时间范围: {stock_data.index[0].strftime('%Y-%m-%d')} 到 {stock_data.index[-1].strftime('%Y-%m-%d')}")
    
    # 2. 因子计算
    print("\n【步骤2】因子计算")
    print("-" * 40)
    
    calculator = MonsterStockFactorCalculator()
    
    # 计算各阶段因子
    print("计算潜伏期因子...")
    latent_factors = calculator.calculate_latent_factors(stock_data)
    print(f"  潜伏期因子: {latent_factors.shape[1]} 个")
    
    print("计算启动期因子...")
    startup_factors = calculator.calculate_startup_factors(stock_data)
    print(f"  启动期因子: {startup_factors.shape[1]} 个")
    
    print("计算加速期因子...")
    acceleration_factors = calculator.calculate_acceleration_factors(stock_data)
    print(f"  加速期因子: {acceleration_factors.shape[1]} 个")
    
    print("计算分歧期因子...")
    divergence_factors = calculator.calculate_divergence_factors(stock_data)
    print(f"  分歧期因子: {divergence_factors.shape[1]} 个")
    
    # 合并所有因子
    all_factors = pd.concat([
        latent_factors, startup_factors, 
        acceleration_factors, divergence_factors
    ], axis=1)
    
    print(f"✓ 总因子数: {all_factors.shape[1]} 个")
    print(f"✓ 数据长度: {all_factors.shape[0]} 天")
    
    # 显示因子列表
    print("\n因子列表:")
    for i, col in enumerate(all_factors.columns, 1):
        print(f"  {i:2d}. {col}")
    
    # 3. 数据预处理
    print("\n【步骤3】数据预处理")
    print("-" * 40)
    
    processor = DataProcessor()
    processed_factors = processor.process_factors(
        all_factors,
        market_cap=financial_data['market_cap'].iloc[0] if 'market_cap' in financial_data.columns else None,
        industry=financial_data['industry'].iloc[0] if 'industry' in financial_data.columns else None,
        beta=financial_data['beta'].iloc[0] if 'beta' in financial_data.columns else None
    )
    
    print(f"✓ 预处理完成: {processed_factors.shape}")
    
    # 显示预处理前后的对比
    print("\n预处理前后对比 (前5个因子):")
    print("原始因子统计:")
    print(all_factors.iloc[:, :5].describe().round(4))
    print("\n预处理后因子统计:")
    print(processed_factors.iloc[:, :5].describe().round(4))
    
    # 4. 概率分合成
    print("\n【步骤4】概率分合成")
    print("-" * 40)
    
    synthesizer = MonsterStockProbabilitySynthesizer()
    final_factors = synthesizer.calculate_monster_probability(processed_factors)
    
    print(f"✓ 概率分合成完成: {final_factors.shape}")
    
    # 显示妖股概率分统计
    if 'monster_probability' in final_factors.columns:
        prob_stats = final_factors['monster_probability'].describe()
        print(f"\n妖股概率分统计:")
        print(f"  均值: {prob_stats['mean']:.4f}")
        print(f"  标准差: {prob_stats['std']:.4f}")
        print(f"  最小值: {prob_stats['min']:.4f}")
        print(f"  最大值: {prob_stats['max']:.4f}")
        print(f"  75%分位数: {prob_stats['75%']:.4f}")
        
        # 高概率样本统计
        high_prob_count = (final_factors['monster_probability'] > 0.7).sum()
        print(f"  高概率样本(>0.7): {high_prob_count} ({high_prob_count/len(final_factors):.1%})")
    
    # 显示特征重要性
    importance = synthesizer.get_feature_importance()
    if not importance.empty:
        print(f"\n特征重要性 (前10个):")
        for i, (factor, imp) in enumerate(importance.head(10).items(), 1):
            print(f"  {i:2d}. {factor}: {imp:.4f}")
    
    # 5. 回测验证
    print("\n【步骤5】回测验证")
    print("-" * 40)
    
    backtester = MonsterStockBacktester()
    backtest_results = backtester.run_backtest(final_factors, stock_data)
    
    print("✓ 回测完成")
    
    # 显示回测摘要
    print("\n回测结果摘要:")
    perf_metrics = backtest_results['performance_metrics']
    print(f"  策略年化收益率: {perf_metrics['strategy_annual_return']:.2%}")
    print(f"  基准年化收益率: {perf_metrics['benchmark_annual_return']:.2%}")
    print(f"  策略夏普比率: {perf_metrics['strategy_sharpe']:.4f}")
    print(f"  策略最大回撤: {perf_metrics['strategy_max_drawdown']:.2%}")
    print(f"  超额收益: {perf_metrics['excess_return']:.2%}")
    print(f"  信息比率: {perf_metrics['information_ratio']:.4f}")
    
    # 因子有效性
    factor_analysis = backtest_results['factor_analysis']
    print(f"\n因子有效性:")
    print(f"  IC均值: {factor_analysis['ic_mean']:.4f}")
    print(f"  IC信息比率: {factor_analysis['ic_ir']:.4f}")
    print(f"  IC胜率: {factor_analysis['ic_win_rate']:.2%}")
    
    # 交易摘要
    trading_summary = backtest_results['trading_summary']
    print(f"\n交易摘要:")
    print(f"  总交易次数: {trading_summary['total_trades']}")
    print(f"  总持仓天数: {trading_summary['total_hold_days']}")
    print(f"  平均交易收益: {trading_summary['avg_trade_return']:.4f}")
    print(f"  盈利交易次数: {trading_summary['winning_trades']}")
    print(f"  亏损交易次数: {trading_summary['losing_trades']}")
    
    # 6. 结果保存
    print("\n【步骤6】结果保存")
    print("-" * 40)
    
    # 保存因子数据
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    factor_file = f"monster_factors_demo_{timestamp}.csv"
    final_factors.to_csv(factor_file)
    print(f"✓ 因子数据已保存: {factor_file}")
    
    # 保存回测结果
    backtest_file = f"monster_backtest_demo_{timestamp}.csv"
    backtest_df = pd.DataFrame({
        'strategy_return': backtest_results['strategy_returns'],
        'benchmark_return': backtest_results['benchmark_returns']
    })
    backtest_df.to_csv(backtest_file)
    print(f"✓ 回测数据已保存: {backtest_file}")
    
    print("\n" + "=" * 80)
    print("🎉 完整分析演示完成！")
    print("=" * 80)
    
    return {
        'stock_data': stock_data,
        'financial_data': financial_data,
        'all_factors': all_factors,
        'processed_factors': processed_factors,
        'final_factors': final_factors,
        'backtest_results': backtest_results
    }


def demo_parameter_sensitivity():
    """参数敏感性演示"""
    print("\n" + "=" * 80)
    print("参数敏感性分析演示")
    print("=" * 80)
    
    # 创建测试数据
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
    
    # 计算因子
    calculator = MonsterStockFactorCalculator()
    all_factors = calculator.calculate_all_factors(stock_data)
    
    # 预处理
    processor = DataProcessor()
    processed_factors = processor.process_factors(all_factors)
    
    # 测试不同概率阈值
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    results = {}
    
    print("测试不同概率阈值的影响:")
    print(f"{'阈值':<8} {'年化收益率':<12} {'夏普比率':<10} {'最大回撤':<12} {'超额收益':<12}")
    print("-" * 60)
    
    for threshold in thresholds:
        try:
            # 概率分合成
            synthesizer = MonsterStockProbabilitySynthesizer()
            final_factors = synthesizer.calculate_monster_probability(processed_factors)
            
            # 回测
            backtester = MonsterStockBacktester()
            backtest_results = backtester.run_backtest(final_factors, stock_data, threshold)
            
            # 提取关键指标
            perf_metrics = backtest_results['performance_metrics']
            results[threshold] = {
                'annual_return': perf_metrics['strategy_annual_return'],
                'sharpe_ratio': perf_metrics['strategy_sharpe'],
                'max_drawdown': perf_metrics['strategy_max_drawdown'],
                'excess_return': perf_metrics['excess_return']
            }
            
            print(f"{threshold:<8} {perf_metrics['strategy_annual_return']:<12.2%} {perf_metrics['strategy_sharpe']:<10.4f} {perf_metrics['strategy_max_drawdown']:<12.2%} {perf_metrics['excess_return']:<12.2%}")
            
        except Exception as e:
            print(f"{threshold:<8} 测试失败: {e}")
            continue
    
    # 找到最佳参数
    if results:
        best_sharpe = max(results.values(), key=lambda x: x['sharpe_ratio'])
        best_threshold = [k for k, v in results.items() if v == best_sharpe][0]
        print(f"\n最佳概率阈值: {best_threshold} (夏普比率: {best_sharpe['sharpe_ratio']:.4f})")
    
    return results


if __name__ == "__main__":
    # 运行完整分析演示
    results = demo_complete_analysis()
    
    # 运行参数敏感性演示
    sensitivity_results = demo_parameter_sensitivity()
    
    print("\n" + "=" * 80)
    print("所有演示完成！")
    print("=" * 80)
