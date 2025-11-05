"""
协整检验模块

使用Engle-Granger两步法检验两个价格序列的协整关系。
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, Optional
from statsmodels.tsa.stattools import coint

from config import Config

logger = logging.getLogger(__name__)


class CointegrationTester:
    """协整检验器"""
    
    def __init__(self):
        """初始化协整检验器"""
        self.max_p_value = Config.Cointegration.MAX_P_VALUE
        self.method = Config.Cointegration.METHOD
        
        logger.info(f"协整检验器初始化完成 (p值阈值<{self.max_p_value})")
    
    def test_cointegration(
        self,
        price1: pd.Series,
        price2: pd.Series
    ) -> Tuple[bool, float, float, pd.Series]:
        """
        使用Engle-Granger方法检验协整关系
        
        Args:
            price1: 价格序列1
            price2: 价格序列2
            
        Returns:
            (是否通过, p值, beta系数, 价差序列)
        """
        try:
            # 对齐数据
            aligned_data = pd.DataFrame({'p1': price1, 'p2': price2}).dropna()
            
            if len(aligned_data) < 20:
                logger.debug("数据点不足，无法进行协整检验")
                return False, 1.0, np.nan, None
            
            x = aligned_data['p1'].values
            y = aligned_data['p2'].values
            
            # 取对数
            log_x = np.log(x)
            log_y = np.log(y)
            
            # Engle-Granger协整检验
            # score是检验统计量，p_value是p值，crit_values是临界值
            score, p_value, crit_values = coint(log_y, log_x, autolag='AIC')
            
            # 计算beta系数（用于构造价差）
            # beta = (Y'X) / (X'X)
            beta = np.linalg.lstsq(log_x[:, None], log_y, rcond=None)[0][0]
            
            # 构造价差
            spread = log_y - beta * log_x
            spread_series = pd.Series(spread, index=aligned_data.index)
            
            # 判断是否通过
            passed = p_value < self.max_p_value
            
            logger.debug(f"协整检验: p_value={p_value:.4f}, beta={beta:.4f}, passed={passed}")
            
            return passed, p_value, beta, spread_series
            
        except Exception as e:
            logger.warning(f"协整检验失败: {e}")
            return False, 1.0, np.nan, None
    
    def test_batch_cointegration(
        self,
        pairs: list,
        price_data: dict
    ) -> pd.DataFrame:
        """
        批量检验协整关系
        
        Args:
            pairs: 配对列表，格式为 [(code1, code2), ...]
            price_data: 代码到价格序列的字典
            
        Returns:
            检验结果DataFrame
        """
        logger.info(f"开始批量协整检验，共 {len(pairs)} 对")
        
        results = []
        
        for i, (code1, code2) in enumerate(pairs):
            if (i + 1) % 100 == 0:
                logger.info(f"协整检验进度: {i+1}/{len(pairs)} ({(i+1)/len(pairs)*100:.1f}%)")
            
            price1 = price_data.get(code1)
            price2 = price_data.get(code2)
            
            if price1 is None or price2 is None:
                logger.warning(f"缺少价格数据: {code1} 或 {code2}")
                continue
            
            passed, p_value, beta, spread = self.test_cointegration(price1, price2)
            
            results.append({
                'code1': code1,
                'code2': code2,
                'p_value': p_value,
                'beta': beta,
                'passed': passed,
                'spread_mean': spread.mean() if spread is not None else np.nan,
                'spread_std': spread.std() if spread is not None else np.nan
            })
        
        results_df = pd.DataFrame(results)
        
        passed_count = results_df['passed'].sum()
        pass_rate = passed_count / len(results_df) * 100 if len(results_df) > 0 else 0
        
        logger.info(f"协整检验完成: 总数 {len(results_df)}, 通过 {passed_count} ({pass_rate:.2f}%)")
        
        return results_df
    
    def get_cointegration_stats(self, results_df: pd.DataFrame) -> dict:
        """
        获取协整检验统计信息
        
        Args:
            results_df: 检验结果DataFrame
            
        Returns:
            统计信息字典
        """
        passed = results_df[results_df['passed']]
        failed = results_df[~results_df['passed']]
        
        stats = {
            'total_pairs': len(results_df),
            'passed_pairs': len(passed),
            'failed_pairs': len(failed),
            'pass_rate': len(passed) / len(results_df) * 100 if len(results_df) > 0 else 0,
            'avg_p_value_passed': passed['p_value'].mean() if len(passed) > 0 else np.nan,
            'avg_p_value_failed': failed['p_value'].mean() if len(failed) > 0 else np.nan,
            'min_p_value': results_df['p_value'].min(),
            'max_p_value': results_df['p_value'].max(),
            'p_value_threshold': self.max_p_value
        }
        
        return stats


if __name__ == '__main__':
    """协整检验器测试"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*80)
    print("协整检验器测试")
    print("="*80)
    
    tester = CointegrationTester()
    
    # 生成测试数据
    print("\n生成测试数据...")
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=250, freq='D')
    
    # 生成协整的价格序列
    print("\n测试1: 协整的价格序列")
    x = np.cumsum(np.random.randn(250)) + 100
    y = 1.5 * x + np.random.randn(250) * 2  # y = 1.5x + noise
    
    price1 = pd.Series(x, index=dates, name='stock1')
    price2 = pd.Series(y, index=dates, name='stock2')
    
    passed, p_value, beta, spread = tester.test_cointegration(price1, price2)
    
    print(f"结果: 通过={passed}, p值={p_value:.4f}, beta={beta:.4f}")
    if spread is not None:
        print(f"价差统计: 均值={spread.mean():.4f}, 标准差={spread.std():.4f}")
    
    # 生成非协整的价格序列
    print("\n测试2: 非协整的价格序列")
    x = np.cumsum(np.random.randn(250)) + 100
    y = np.cumsum(np.random.randn(250)) + 150  # 独立的随机游走
    
    price1 = pd.Series(x, index=dates, name='stock3')
    price2 = pd.Series(y, index=dates, name='stock4')
    
    passed, p_value, beta, spread = tester.test_cointegration(price1, price2)
    
    print(f"结果: 通过={passed}, p值={p_value:.4f}, beta={beta:.4f}")
    if spread is not None:
        print(f"价差统计: 均值={spread.mean():.4f}, 标准差={spread.std():.4f}")
    
    # 测试批量检验
    print("\n测试3: 批量协整检验")
    test_data = {}
    test_pairs = []
    
    # 生成3对协整序列
    for i in range(3):
        x = np.cumsum(np.random.randn(250)) + 100
        y = 1.5 * x + np.random.randn(250) * 2
        test_data[f'stock_{i}_1'] = pd.Series(x, index=dates)
        test_data[f'stock_{i}_2'] = pd.Series(y, index=dates)
        test_pairs.append((f'stock_{i}_1', f'stock_{i}_2'))
    
    # 生成2对非协整序列
    for i in range(3, 5):
        x = np.cumsum(np.random.randn(250)) + 100
        y = np.cumsum(np.random.randn(250)) + 150
        test_data[f'stock_{i}_1'] = pd.Series(x, index=dates)
        test_data[f'stock_{i}_2'] = pd.Series(y, index=dates)
        test_pairs.append((f'stock_{i}_1', f'stock_{i}_2'))
    
    results_df = tester.test_batch_cointegration(test_pairs, test_data)
    
    print("\n批量检验结果:")
    print(results_df[['code1', 'code2', 'p_value', 'beta', 'passed']].to_string(index=False))
    
    print("\n统计信息:")
    stats = tester.get_cointegration_stats(results_df)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*80)

