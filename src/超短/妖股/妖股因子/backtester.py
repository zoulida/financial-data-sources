"""
回测框架
========

验证妖股因子的有效性，包括：
1. 因子有效性分析
2. 策略回测
3. 风险指标计算
4. 绩效评估
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class MonsterStockBacktester:
    """妖股因子回测器"""
    
    def __init__(self, 
                 min_boards: int = 4,
                 hold_days: int = 5,
                 transaction_cost: float = 0.001):
        """
        初始化回测器
        
        Parameters:
        -----------
        min_boards : int
            妖股定义：最少连板数
        hold_days : int
            持仓天数
        transaction_cost : float
            交易成本（单边）
        """
        self.min_boards = min_boards
        self.hold_days = hold_days
        self.transaction_cost = transaction_cost
        
        # 存储回测结果
        self.backtest_results = {}
        self.factor_analysis = {}
        
    def run_backtest(self, 
                    factors_df: pd.DataFrame,
                    price_data: pd.DataFrame,
                    probability_threshold: float = 0.5) -> Dict:
        """
        运行回测
        
        Parameters:
        -----------
        factors_df : pd.DataFrame
            包含妖股概率分的因子数据
        price_data : pd.DataFrame
            价格数据，包含close列
        probability_threshold : float
            买入概率阈值
            
        Returns:
        --------
        Dict : 回测结果
        """
        print("开始回测...")
        
        # 1. 因子有效性分析
        print("1. 分析因子有效性...")
        factor_analysis = self._analyze_factor_effectiveness(factors_df, price_data)
        
        # 2. 生成交易信号
        print("2. 生成交易信号...")
        signals = self._generate_trading_signals(factors_df, probability_threshold)
        
        # 3. 计算策略收益
        print("3. 计算策略收益...")
        strategy_returns = self._calculate_strategy_returns(signals, price_data)
        
        # 4. 计算基准收益
        print("4. 计算基准收益...")
        benchmark_returns = self._calculate_benchmark_returns(price_data)
        
        # 5. 计算绩效指标
        print("5. 计算绩效指标...")
        performance_metrics = self._calculate_performance_metrics(
            strategy_returns, benchmark_returns
        )
        
        # 6. 风险分析
        print("6. 风险分析...")
        risk_metrics = self._calculate_risk_metrics(strategy_returns)
        
        # 7. 整理结果
        results = {
            'factor_analysis': factor_analysis,
            'signals': signals,
            'strategy_returns': strategy_returns,
            'benchmark_returns': benchmark_returns,
            'performance_metrics': performance_metrics,
            'risk_metrics': risk_metrics,
            'trading_summary': self._generate_trading_summary(signals, strategy_returns)
        }
        
        self.backtest_results = results
        print("回测完成！")
        
        return results
    
    def _analyze_factor_effectiveness(self, 
                                    factors_df: pd.DataFrame, 
                                    price_data: pd.DataFrame) -> Dict:
        """分析因子有效性"""
        # 对齐数据
        common_index = factors_df.index.intersection(price_data.index)
        factors_aligned = factors_df.loc[common_index]
        price_aligned = price_data.loc[common_index]
        
        # 计算未来收益率
        future_returns = price_aligned['close'].pct_change(self.hold_days).shift(-self.hold_days)
        
        # 计算因子与未来收益率的相关性
        correlations = {}
        for col in factors_aligned.columns:
            if col not in ['monster_probability', 'monster_score']:
                corr = factors_aligned[col].corr(future_returns)
                correlations[col] = corr if not pd.isna(corr) else 0
        
        # 计算IC（信息系数）
        if correlations:
            ic_mean = np.mean(list(correlations.values()))
            ic_std = np.std(list(correlations.values()))
            ic_ir = ic_mean / ic_std if ic_std > 0 else 0
        else:
            ic_mean = ic_std = ic_ir = 0
        
        # 计算IC胜率
        ic_win_rate = sum(1 for corr in correlations.values() if corr > 0) / len(correlations) if correlations else 0
        
        return {
            'correlations': correlations,
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'ic_ir': ic_ir,
            'ic_win_rate': ic_win_rate
        }
    
    def _generate_trading_signals(self, 
                                 factors_df: pd.DataFrame, 
                                 probability_threshold: float) -> pd.DataFrame:
        """生成交易信号"""
        signals = pd.DataFrame(index=factors_df.index)
        
        # 买入信号：妖股概率分超过阈值
        signals['buy_signal'] = (factors_df['monster_probability'] > probability_threshold).astype(int)
        
        # 卖出信号：持仓期满或概率分下降
        signals['sell_signal'] = 0
        
        # 持仓状态
        signals['position'] = 0
        position = 0
        
        for i in range(len(signals)):
            if signals['buy_signal'].iloc[i] and position == 0:
                # 买入
                position = 1
                signals.iloc[i, signals.columns.get_loc('position')] = 1
            elif position == 1:
                # 检查是否卖出
                if i >= self.hold_days:
                    # 持仓期满
                    position = 0
                    signals.iloc[i, signals.columns.get_loc('sell_signal')] = 1
                elif i < len(signals) - 1 and factors_df['monster_probability'].iloc[i+1] < probability_threshold * 0.8:
                    # 概率分下降超过20%
                    position = 0
                    signals.iloc[i, signals.columns.get_loc('sell_signal')] = 1
                else:
                    # 继续持仓
                    signals.iloc[i, signals.columns.get_loc('position')] = 1
        
        return signals
    
    def _calculate_strategy_returns(self, 
                                   signals: pd.DataFrame, 
                                   price_data: pd.DataFrame) -> pd.Series:
        """计算策略收益"""
        # 对齐数据
        common_index = signals.index.intersection(price_data.index)
        signals_aligned = signals.loc[common_index]
        price_aligned = price_data.loc[common_index]
        
        # 计算日收益率
        daily_returns = price_aligned['close'].pct_change()
        
        # 计算策略收益率
        strategy_returns = daily_returns * signals_aligned['position']
        
        # 扣除交易成本
        trade_cost = 0
        for i in range(1, len(signals_aligned)):
            if signals_aligned['buy_signal'].iloc[i] and signals_aligned['position'].iloc[i-1] == 0:
                trade_cost += self.transaction_cost
            elif signals_aligned['sell_signal'].iloc[i] and signals_aligned['position'].iloc[i-1] == 1:
                trade_cost += self.transaction_cost
        
        # 平均分摊交易成本
        if len(strategy_returns) > 0:
            avg_trade_cost = trade_cost / len(strategy_returns)
            strategy_returns = strategy_returns - avg_trade_cost
        
        return strategy_returns.fillna(0)
    
    def _calculate_benchmark_returns(self, price_data: pd.DataFrame) -> pd.Series:
        """计算基准收益（买入持有）"""
        daily_returns = price_data['close'].pct_change()
        return daily_returns.fillna(0)
    
    def _calculate_performance_metrics(self, 
                                     strategy_returns: pd.Series, 
                                     benchmark_returns: pd.Series) -> Dict:
        """计算绩效指标"""
        # 对齐数据
        common_index = strategy_returns.index.intersection(benchmark_returns.index)
        strategy_aligned = strategy_returns.loc[common_index]
        benchmark_aligned = benchmark_returns.loc[common_index]
        
        # 累计收益
        strategy_cumret = (1 + strategy_aligned).cumprod() - 1
        benchmark_cumret = (1 + benchmark_aligned).cumprod() - 1
        
        # 年化收益率
        trading_days = 252
        strategy_annual_ret = (1 + strategy_cumret.iloc[-1]) ** (trading_days / len(strategy_aligned)) - 1
        benchmark_annual_ret = (1 + benchmark_cumret.iloc[-1]) ** (trading_days / len(benchmark_aligned)) - 1
        
        # 年化波动率
        strategy_vol = strategy_aligned.std() * np.sqrt(trading_days)
        benchmark_vol = benchmark_aligned.std() * np.sqrt(trading_days)
        
        # 夏普比率
        risk_free_rate = 0.03  # 假设无风险利率3%
        strategy_sharpe = (strategy_annual_ret - risk_free_rate) / strategy_vol if strategy_vol > 0 else 0
        benchmark_sharpe = (benchmark_annual_ret - risk_free_rate) / benchmark_vol if benchmark_vol > 0 else 0
        
        # 最大回撤
        strategy_dd = self._calculate_max_drawdown(strategy_cumret)
        benchmark_dd = self._calculate_max_drawdown(benchmark_cumret)
        
        # 超额收益
        excess_returns = strategy_aligned - benchmark_aligned
        excess_annual_ret = (1 + excess_returns).prod() ** (trading_days / len(excess_returns)) - 1
        
        # 信息比率
        excess_vol = excess_returns.std() * np.sqrt(trading_days)
        information_ratio = excess_annual_ret / excess_vol if excess_vol > 0 else 0
        
        return {
            'strategy_annual_return': strategy_annual_ret,
            'benchmark_annual_return': benchmark_annual_ret,
            'strategy_volatility': strategy_vol,
            'benchmark_volatility': benchmark_vol,
            'strategy_sharpe': strategy_sharpe,
            'benchmark_sharpe': benchmark_sharpe,
            'strategy_max_drawdown': strategy_dd,
            'benchmark_max_drawdown': benchmark_dd,
            'excess_return': excess_annual_ret,
            'information_ratio': information_ratio
        }
    
    def _calculate_risk_metrics(self, strategy_returns: pd.Series) -> Dict:
        """计算风险指标"""
        # VaR (Value at Risk)
        var_95 = np.percentile(strategy_returns, 5)
        var_99 = np.percentile(strategy_returns, 1)
        
        # CVaR (Conditional Value at Risk)
        cvar_95 = strategy_returns[strategy_returns <= var_95].mean()
        cvar_99 = strategy_returns[strategy_returns <= var_99].mean()
        
        # 偏度和峰度
        skewness = strategy_returns.skew()
        kurtosis = strategy_returns.kurtosis()
        
        # 胜率
        win_rate = (strategy_returns > 0).mean()
        
        # 平均盈利和平均亏损
        positive_returns = strategy_returns[strategy_returns > 0]
        negative_returns = strategy_returns[strategy_returns < 0]
        
        avg_win = positive_returns.mean() if len(positive_returns) > 0 else 0
        avg_loss = negative_returns.mean() if len(negative_returns) > 0 else 0
        
        # 盈亏比
        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        return {
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,
            'cvar_99': cvar_99,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_loss_ratio': profit_loss_ratio
        }
    
    def _calculate_max_drawdown(self, cumulative_returns: pd.Series) -> float:
        """计算最大回撤"""
        peak = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - peak) / (1 + peak)
        return drawdown.min()
    
    def _generate_trading_summary(self, 
                                 signals: pd.DataFrame, 
                                 strategy_returns: pd.Series) -> Dict:
        """生成交易摘要"""
        total_trades = signals['buy_signal'].sum()
        total_hold_days = signals['position'].sum()
        
        # 计算每笔交易的收益
        trade_returns = []
        in_trade = False
        trade_start = 0
        
        for i in range(len(signals)):
            if signals['buy_signal'].iloc[i] and not in_trade:
                # 开始交易
                in_trade = True
                trade_start = i
            elif signals['sell_signal'].iloc[i] and in_trade:
                # 结束交易
                trade_return = strategy_returns.iloc[trade_start:i+1].sum()
                trade_returns.append(trade_return)
                in_trade = False
        
        # 如果还有未结束的交易
        if in_trade:
            trade_return = strategy_returns.iloc[trade_start:].sum()
            trade_returns.append(trade_return)
        
        trade_returns = np.array(trade_returns)
        
        return {
            'total_trades': total_trades,
            'total_hold_days': total_hold_days,
            'avg_trade_return': trade_returns.mean() if len(trade_returns) > 0 else 0,
            'winning_trades': (trade_returns > 0).sum() if len(trade_returns) > 0 else 0,
            'losing_trades': (trade_returns < 0).sum() if len(trade_returns) > 0 else 0,
            'max_trade_return': trade_returns.max() if len(trade_returns) > 0 else 0,
            'min_trade_return': trade_returns.min() if len(trade_returns) > 0 else 0
        }
    
    def plot_results(self, save_path: Optional[str] = None):
        """绘制回测结果图表"""
        if not self.backtest_results:
            print("请先运行回测")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('妖股因子回测结果', fontsize=16)
        
        # 1. 累计收益曲线
        strategy_returns = self.backtest_results['strategy_returns']
        benchmark_returns = self.backtest_results['benchmark_returns']
        
        strategy_cumret = (1 + strategy_returns).cumprod() - 1
        benchmark_cumret = (1 + benchmark_returns).cumprod() - 1
        
        axes[0, 0].plot(strategy_cumret.index, strategy_cumret.values, label='策略', linewidth=2)
        axes[0, 0].plot(benchmark_cumret.index, benchmark_cumret.values, label='基准', linewidth=2)
        axes[0, 0].set_title('累计收益曲线')
        axes[0, 0].set_ylabel('累计收益率')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # 2. 因子相关性热力图
        factor_analysis = self.backtest_results['factor_analysis']
        correlations = factor_analysis['correlations']
        
        if correlations:
            corr_df = pd.DataFrame(list(correlations.items()), columns=['Factor', 'Correlation'])
            corr_df = corr_df.set_index('Factor')
            
            sns.heatmap(corr_df.values.reshape(-1, 1), 
                       annot=True, 
                       fmt='.3f',
                       yticklabels=corr_df.index,
                       xticklabels=['Correlation'],
                       ax=axes[0, 1])
            axes[0, 1].set_title('因子相关性')
        
        # 3. 收益率分布
        axes[1, 0].hist(strategy_returns, bins=50, alpha=0.7, label='策略', density=True)
        axes[1, 0].hist(benchmark_returns, bins=50, alpha=0.7, label='基准', density=True)
        axes[1, 0].set_title('收益率分布')
        axes[1, 0].set_xlabel('日收益率')
        axes[1, 0].set_ylabel('密度')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
        
        # 4. 绩效指标对比
        perf_metrics = self.backtest_results['performance_metrics']
        metrics_names = ['年化收益率', '年化波动率', '夏普比率', '最大回撤']
        strategy_values = [
            perf_metrics['strategy_annual_return'],
            perf_metrics['strategy_volatility'],
            perf_metrics['strategy_sharpe'],
            perf_metrics['strategy_max_drawdown']
        ]
        benchmark_values = [
            perf_metrics['benchmark_annual_return'],
            perf_metrics['benchmark_volatility'],
            perf_metrics['benchmark_sharpe'],
            perf_metrics['benchmark_max_drawdown']
        ]
        
        x = np.arange(len(metrics_names))
        width = 0.35
        
        axes[1, 1].bar(x - width/2, strategy_values, width, label='策略', alpha=0.8)
        axes[1, 1].bar(x + width/2, benchmark_values, width, label='基准', alpha=0.8)
        axes[1, 1].set_title('绩效指标对比')
        axes[1, 1].set_xticks(x)
        axes[1, 1].set_xticklabels(metrics_names, rotation=45)
        axes[1, 1].legend()
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        plt.show()
    
    def print_summary(self):
        """打印回测摘要"""
        if not self.backtest_results:
            print("请先运行回测")
            return
        
        print("=" * 60)
        print("妖股因子回测摘要")
        print("=" * 60)
        
        # 因子分析结果
        factor_analysis = self.backtest_results['factor_analysis']
        print(f"\n【因子有效性分析】")
        print(f"IC均值: {factor_analysis['ic_mean']:.4f}")
        print(f"IC标准差: {factor_analysis['ic_std']:.4f}")
        print(f"IC信息比率: {factor_analysis['ic_ir']:.4f}")
        print(f"IC胜率: {factor_analysis['ic_win_rate']:.2%}")
        
        # 绩效指标
        perf_metrics = self.backtest_results['performance_metrics']
        print(f"\n【绩效指标】")
        print(f"策略年化收益率: {perf_metrics['strategy_annual_return']:.2%}")
        print(f"基准年化收益率: {perf_metrics['benchmark_annual_return']:.2%}")
        print(f"策略年化波动率: {perf_metrics['strategy_volatility']:.2%}")
        print(f"基准年化波动率: {perf_metrics['benchmark_volatility']:.2%}")
        print(f"策略夏普比率: {perf_metrics['strategy_sharpe']:.4f}")
        print(f"基准夏普比率: {perf_metrics['benchmark_sharpe']:.4f}")
        print(f"策略最大回撤: {perf_metrics['strategy_max_drawdown']:.2%}")
        print(f"基准最大回撤: {perf_metrics['benchmark_max_drawdown']:.2%}")
        print(f"超额收益: {perf_metrics['excess_return']:.2%}")
        print(f"信息比率: {perf_metrics['information_ratio']:.4f}")
        
        # 风险指标
        risk_metrics = self.backtest_results['risk_metrics']
        print(f"\n【风险指标】")
        print(f"95% VaR: {risk_metrics['var_95']:.4f}")
        print(f"99% VaR: {risk_metrics['var_99']:.4f}")
        print(f"95% CVaR: {risk_metrics['cvar_95']:.4f}")
        print(f"99% CVaR: {risk_metrics['cvar_99']:.4f}")
        print(f"偏度: {risk_metrics['skewness']:.4f}")
        print(f"峰度: {risk_metrics['kurtosis']:.4f}")
        print(f"胜率: {risk_metrics['win_rate']:.2%}")
        print(f"平均盈利: {risk_metrics['avg_win']:.4f}")
        print(f"平均亏损: {risk_metrics['avg_loss']:.4f}")
        print(f"盈亏比: {risk_metrics['profit_loss_ratio']:.4f}")
        
        # 交易摘要
        trading_summary = self.backtest_results['trading_summary']
        print(f"\n【交易摘要】")
        print(f"总交易次数: {trading_summary['total_trades']}")
        print(f"总持仓天数: {trading_summary['total_hold_days']}")
        print(f"平均交易收益: {trading_summary['avg_trade_return']:.4f}")
        print(f"盈利交易次数: {trading_summary['winning_trades']}")
        print(f"亏损交易次数: {trading_summary['losing_trades']}")
        print(f"最大单笔收益: {trading_summary['max_trade_return']:.4f}")
        print(f"最大单笔亏损: {trading_summary['min_trade_return']:.4f}")


# 使用示例
if __name__ == "__main__":
    # 创建示例数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    # 创建因子数据
    factors_df = pd.DataFrame({
        'monster_probability': np.random.uniform(0, 1, 100),
        'monster_score': np.random.uniform(0, 100, 100),
        'factor1': np.random.normal(0, 1, 100),
        'factor2': np.random.normal(0, 1, 100),
        'factor3': np.random.normal(0, 1, 100)
    }, index=dates)
    
    # 创建价格数据
    price_data = pd.DataFrame({
        'close': 100 * np.cumprod(1 + np.random.normal(0.001, 0.02, 100))
    }, index=dates)
    
    # 创建回测器
    backtester = MonsterStockBacktester()
    
    # 运行回测
    results = backtester.run_backtest(factors_df, price_data)
    
    # 打印摘要
    backtester.print_summary()
    
    # 绘制结果
    backtester.plot_results()
