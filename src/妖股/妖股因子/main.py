"""
妖股因子量化主程序
==================

完整的妖股因子量化系统，包含：
1. 数据获取
2. 因子计算
3. 数据预处理
4. 概率分合成
5. 回测验证

使用示例：
python main.py --stock 000001.SZ --start 20240101 --end 20241231
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from .factor_calculator import MonsterStockFactorCalculator
from .data_processor import DataProcessor
from .probability_synthesizer import MonsterStockProbabilitySynthesizer
from .data_fetcher import MonsterStockDataFetcher
from .backtester import MonsterStockBacktester


class MonsterStockQuantSystem:
    """妖股因子量化系统主类"""
    
    def __init__(self, 
                 wind_token: str = None,
                 xtquant_token: str = None,
                 use_mock_data: bool = False):
        """
        初始化妖股因子量化系统
        
        Parameters:
        -----------
        wind_token : str, optional
            Wind API token
        xtquant_token : str, optional
            XtQuant API token
        use_mock_data : bool
            是否使用模拟数据
        """
        # 初始化各个模块
        self.data_fetcher = MonsterStockDataFetcher(
            wind_token=wind_token,
            xtquant_token=xtquant_token,
            use_mock_data=use_mock_data
        )
        
        self.factor_calculator = MonsterStockFactorCalculator()
        self.data_processor = DataProcessor()
        self.probability_synthesizer = MonsterStockProbabilitySynthesizer()
        self.backtester = MonsterStockBacktester()
        
        # 存储结果
        self.results = {}
        
    def run_analysis(self, 
                    stock_code: str,
                    start_date: str,
                    end_date: str,
                    probability_threshold: float = 0.5,
                    save_results: bool = True) -> Dict:
        """
        运行完整的妖股因子分析
        
        Parameters:
        -----------
        stock_code : str
            股票代码，如'000001.SZ'
        start_date : str
            开始日期，格式'YYYYMMDD'
        end_date : str
            结束日期，格式'YYYYMMDD'
        probability_threshold : float
            妖股概率阈值
        save_results : bool
            是否保存结果
            
        Returns:
        --------
        Dict : 分析结果
        """
        print("=" * 80)
        print("妖股因子量化分析系统")
        print("=" * 80)
        print(f"股票代码: {stock_code}")
        print(f"分析期间: {start_date} - {end_date}")
        print(f"概率阈值: {probability_threshold}")
        print("=" * 80)
        
        try:
            # 1. 数据获取
            print("\n【步骤1】数据获取...")
            stock_data = self._fetch_stock_data(stock_code, start_date, end_date)
            financial_data = self._fetch_financial_data(stock_code, end_date)
            market_data = self._fetch_market_data(start_date, end_date)
            
            print(f"✓ 股票数据: {stock_data.shape}")
            print(f"✓ 财务数据: {financial_data.shape}")
            print(f"✓ 市场数据: {market_data.shape}")
            
            # 2. 因子计算
            print("\n【步骤2】因子计算...")
            raw_factors = self.factor_calculator.calculate_all_factors(stock_data)
            print(f"✓ 原始因子: {raw_factors.shape}")
            
            # 3. 数据预处理
            print("\n【步骤3】数据预处理...")
            processed_factors = self.data_processor.process_factors(
                raw_factors, 
                market_cap=financial_data.get('market_cap'),
                industry=financial_data.get('industry'),
                beta=financial_data.get('beta')
            )
            print(f"✓ 预处理因子: {processed_factors.shape}")
            
            # 4. 概率分合成
            print("\n【步骤4】概率分合成...")
            final_factors = self.probability_synthesizer.calculate_monster_probability(
                processed_factors
            )
            print(f"✓ 最终因子: {final_factors.shape}")
            
            # 5. 回测验证
            print("\n【步骤5】回测验证...")
            backtest_results = self.backtester.run_backtest(
                final_factors, 
                stock_data, 
                probability_threshold
            )
            print("✓ 回测完成")
            
            # 6. 整理结果
            results = {
                'stock_code': stock_code,
                'start_date': start_date,
                'end_date': end_date,
                'probability_threshold': probability_threshold,
                'stock_data': stock_data,
                'financial_data': financial_data,
                'market_data': market_data,
                'raw_factors': raw_factors,
                'processed_factors': processed_factors,
                'final_factors': final_factors,
                'backtest_results': backtest_results,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.results = results
            
            # 7. 输出结果
            self._print_analysis_summary(results)
            
            # 8. 保存结果
            if save_results:
                self._save_results(results, stock_code)
            
            print("\n" + "=" * 80)
            print("分析完成！")
            print("=" * 80)
            
            return results
            
        except Exception as e:
            print(f"\n❌ 分析过程中出现错误: {e}")
            raise
    
    def _fetch_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票数据"""
        fields = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover', 'pct_chg']
        return self.data_fetcher.fetch_stock_data(stock_code, start_date, end_date, fields)
    
    def _fetch_financial_data(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """获取财务数据"""
        fields = ['market_cap', 'pe_ttm', 'pb_mrq', 'ps_ttm', 'industry', 'beta']
        return self.data_fetcher.fetch_financial_data([stock_code], fields, trade_date)
    
    def _fetch_market_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取市场数据"""
        return self.data_fetcher.fetch_market_data(start_date, end_date)
    
    def _print_analysis_summary(self, results: Dict):
        """打印分析摘要"""
        print("\n" + "=" * 60)
        print("分析结果摘要")
        print("=" * 60)
        
        # 因子统计
        final_factors = results['final_factors']
        print(f"\n【因子统计】")
        print(f"总因子数量: {len(final_factors.columns)}")
        print(f"数据长度: {len(final_factors)}")
        
        # 妖股概率分统计
        if 'monster_probability' in final_factors.columns:
            prob_stats = final_factors['monster_probability'].describe()
            print(f"\n【妖股概率分统计】")
            print(f"均值: {prob_stats['mean']:.4f}")
            print(f"标准差: {prob_stats['std']:.4f}")
            print(f"最小值: {prob_stats['min']:.4f}")
            print(f"最大值: {prob_stats['max']:.4f}")
            print(f"75%分位数: {prob_stats['75%']:.4f}")
            
            # 高概率样本
            high_prob_count = (final_factors['monster_probability'] > 0.7).sum()
            print(f"高概率样本(>0.7): {high_prob_count} ({high_prob_count/len(final_factors):.1%})")
        
        # 回测结果
        if 'backtest_results' in results:
            backtest = results['backtest_results']
            perf_metrics = backtest['performance_metrics']
            
            print(f"\n【回测结果】")
            print(f"策略年化收益率: {perf_metrics['strategy_annual_return']:.2%}")
            print(f"基准年化收益率: {perf_metrics['benchmark_annual_return']:.2%}")
            print(f"策略夏普比率: {perf_metrics['strategy_sharpe']:.4f}")
            print(f"策略最大回撤: {perf_metrics['strategy_max_drawdown']:.2%}")
            print(f"超额收益: {perf_metrics['excess_return']:.2%}")
            print(f"信息比率: {perf_metrics['information_ratio']:.4f}")
            
            # 因子有效性
            factor_analysis = backtest['factor_analysis']
            print(f"\n【因子有效性】")
            print(f"IC均值: {factor_analysis['ic_mean']:.4f}")
            print(f"IC信息比率: {factor_analysis['ic_ir']:.4f}")
            print(f"IC胜率: {factor_analysis['ic_win_rate']:.2%}")
    
    def _save_results(self, results: Dict, stock_code: str):
        """保存结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存因子数据
        factor_file = f"monster_factors_{stock_code}_{timestamp}.csv"
        results['final_factors'].to_csv(factor_file)
        print(f"✓ 因子数据已保存: {factor_file}")
        
        # 保存回测结果
        if 'backtest_results' in results:
            backtest_file = f"monster_backtest_{stock_code}_{timestamp}.csv"
            backtest_df = pd.DataFrame({
                'strategy_return': results['backtest_results']['strategy_returns'],
                'benchmark_return': results['backtest_results']['benchmark_returns']
            })
            backtest_df.to_csv(backtest_file)
            print(f"✓ 回测数据已保存: {backtest_file}")
        
        # 保存摘要报告
        summary_file = f"monster_summary_{stock_code}_{timestamp}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"妖股因子量化分析报告\n")
            f.write(f"股票代码: {stock_code}\n")
            f.write(f"分析时间: {results['analysis_time']}\n")
            f.write(f"分析期间: {results['start_date']} - {results['end_date']}\n")
            f.write(f"概率阈值: {results['probability_threshold']}\n\n")
            
            # 因子统计
            final_factors = results['final_factors']
            f.write(f"因子统计:\n")
            f.write(f"  总因子数量: {len(final_factors.columns)}\n")
            f.write(f"  数据长度: {len(final_factors)}\n\n")
            
            # 回测结果
            if 'backtest_results' in results:
                backtest = results['backtest_results']
                perf_metrics = backtest['performance_metrics']
                f.write(f"回测结果:\n")
                f.write(f"  策略年化收益率: {perf_metrics['strategy_annual_return']:.2%}\n")
                f.write(f"  基准年化收益率: {perf_metrics['benchmark_annual_return']:.2%}\n")
                f.write(f"  策略夏普比率: {perf_metrics['strategy_sharpe']:.4f}\n")
                f.write(f"  策略最大回撤: {perf_metrics['strategy_max_drawdown']:.2%}\n")
                f.write(f"  超额收益: {perf_metrics['excess_return']:.2%}\n")
                f.write(f"  信息比率: {perf_metrics['information_ratio']:.4f}\n")
        
        print(f"✓ 摘要报告已保存: {summary_file}")
    
    def plot_results(self, save_path: str = None):
        """绘制分析结果图表"""
        if not self.results:
            print("请先运行分析")
            return
        
        # 绘制回测结果
        if 'backtest_results' in self.results:
            self.backtester.plot_results(save_path)
        
        # 绘制因子分布
        self._plot_factor_distribution()
    
    def _plot_factor_distribution(self):
        """绘制因子分布图"""
        if not self.results or 'final_factors' not in self.results:
            return
        
        import matplotlib.pyplot as plt
        
        final_factors = self.results['final_factors']
        
        # 选择数值型因子
        numeric_factors = final_factors.select_dtypes(include=[np.number])
        
        if len(numeric_factors.columns) == 0:
            return
        
        # 绘制因子分布
        n_factors = min(6, len(numeric_factors.columns))
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        for i, col in enumerate(numeric_factors.columns[:n_factors]):
            if i < len(axes):
                axes[i].hist(numeric_factors[col].dropna(), bins=30, alpha=0.7)
                axes[i].set_title(f'{col} 分布')
                axes[i].grid(True)
        
        # 隐藏多余的子图
        for i in range(n_factors, len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        plt.show()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='妖股因子量化分析系统')
    parser.add_argument('--stock', type=str, default='000001.SZ', help='股票代码')
    parser.add_argument('--start', type=str, default='20240101', help='开始日期')
    parser.add_argument('--end', type=str, default='20241231', help='结束日期')
    parser.add_argument('--threshold', type=float, default=0.5, help='概率阈值')
    parser.add_argument('--wind-token', type=str, help='Wind API token')
    parser.add_argument('--xtquant-token', type=str, help='XtQuant API token')
    parser.add_argument('--mock-data', action='store_true', help='使用模拟数据')
    parser.add_argument('--plot', action='store_true', help='绘制结果图表')
    
    args = parser.parse_args()
    
    # 创建系统实例
    system = MonsterStockQuantSystem(
        wind_token=args.wind_token,
        xtquant_token=args.xtquant_token,
        use_mock_data=args.mock_data
    )
    
    try:
        # 运行分析
        results = system.run_analysis(
            stock_code=args.stock,
            start_date=args.start,
            end_date=args.end,
            probability_threshold=args.threshold
        )
        
        # 绘制图表
        if args.plot:
            system.plot_results()
        
    except Exception as e:
        print(f"分析失败: {e}")
        return 1
    
    finally:
        # 关闭数据源
        system.data_fetcher.close_apis()
    
    return 0


if __name__ == "__main__":
    exit(main())
