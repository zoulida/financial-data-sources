"""
OU半衰期估计模块

使用Kalman Filter平滑价差序列，然后通过OLS回归估计OU模型的参数，
计算半衰期（half-life）。
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, Optional
from pykalman import KalmanFilter

from config import Config

logger = logging.getLogger(__name__)


class OUEstimator:
    """OU（Ornstein-Uhlenbeck）模型参数估计器"""
    
    def __init__(self):
        """初始化OU估计器"""
        self.max_half_life = Config.OUModel.MAX_HALF_LIFE
        self.min_half_life = Config.OUModel.MIN_HALF_LIFE
        self.obs_cov = Config.OUModel.KF_OBSERVATION_COVARIANCE
        self.trans_cov = Config.OUModel.KF_TRANSITION_COVARIANCE
        
        logger.info(f"OU估计器初始化完成 (半衰期范围: {self.min_half_life}-{self.max_half_life}天)")
    
    def estimate_half_life(self, spread: pd.Series) -> Tuple[float, float]:
        """
        估计OU模型的半衰期
        
        Args:
            spread: 价差序列
            
        Returns:
            (半衰期, phi参数)
        """
        try:
            if spread is None or len(spread) < 10:
                logger.debug("价差数据不足，无法估计半衰期")
                return np.inf, np.nan
            
            # 去除均值
            spread_values = spread.values
            spread_centered = spread_values - np.mean(spread_values)
            
            # 使用Kalman Filter平滑
            kf = KalmanFilter(
                transition_matrices=[[1]],
                observation_matrices=[[1]],
                initial_state_mean=0,
                initial_state_covariance=1,
                observation_covariance=self.obs_cov,
                transition_covariance=self.trans_cov
            )
            
            # 过滤（平滑）
            state_means, _ = kf.filter(spread_centered)
            z_filtered = state_means.flatten()
            
            # 构建AR(1)模型: z_t = phi * z_{t-1} + epsilon
            # 使用OLS估计phi
            z_lag = z_filtered[:-1]
            z_current = z_filtered[1:]
            
            # phi = (Z_lag' * Z_current) / (Z_lag' * Z_lag)
            phi = np.dot(z_lag, z_current) / np.dot(z_lag, z_lag)
            
            # 计算半衰期
            # H = -ln(2) / ln|phi|
            if abs(phi) >= 1:
                # phi >= 1 意味着非均值回归，半衰期无穷大
                return np.inf, phi
            
            if phi <= 0:
                # phi <= 0 意味着震荡但非均值回归
                return np.inf, phi
            
            half_life = -np.log(2) / np.log(phi)
            
            logger.debug(f"半衰期估计: H={half_life:.2f}, phi={phi:.4f}")
            
            return half_life, phi
            
        except Exception as e:
            logger.warning(f"半衰期估计失败: {e}")
            return np.inf, np.nan
    
    def test_half_life(self, half_life: float) -> bool:
        """
        检验半衰期是否在合理范围内
        
        Args:
            half_life: 半衰期值
            
        Returns:
            是否通过检验
        """
        if np.isinf(half_life) or np.isnan(half_life):
            return False
        
        return self.min_half_life <= half_life <= self.max_half_life
    
    def estimate_batch_half_life(
        self,
        pairs_data: list
    ) -> pd.DataFrame:
        """
        批量估计半衰期
        
        Args:
            pairs_data: 配对数据列表，每个元素为字典，包含code1, code2, spread等
            
        Returns:
            估计结果DataFrame
        """
        logger.info(f"开始批量估计半衰期，共 {len(pairs_data)} 对")
        
        results = []
        
        for i, pair in enumerate(pairs_data):
            if (i + 1) % 100 == 0:
                logger.info(f"半衰期估计进度: {i+1}/{len(pairs_data)} ({(i+1)/len(pairs_data)*100:.1f}%)")
            
            code1 = pair.get('code1')
            code2 = pair.get('code2')
            spread = pair.get('spread')
            
            if spread is None:
                logger.warning(f"缺少价差数据: {code1} - {code2}")
                continue
            
            half_life, phi = self.estimate_half_life(spread)
            passed = self.test_half_life(half_life)
            
            results.append({
                'code1': code1,
                'code2': code2,
                'half_life': half_life,
                'phi': phi,
                'passed': passed
            })
        
        results_df = pd.DataFrame(results)
        
        passed_count = results_df['passed'].sum()
        pass_rate = passed_count / len(results_df) * 100 if len(results_df) > 0 else 0
        
        logger.info(f"半衰期估计完成: 总数 {len(results_df)}, 通过 {passed_count} ({pass_rate:.2f}%)")
        
        return results_df
    
    def get_half_life_stats(self, results_df: pd.DataFrame) -> dict:
        """
        获取半衰期统计信息
        
        Args:
            results_df: 估计结果DataFrame
            
        Returns:
            统计信息字典
        """
        # 过滤掉无穷大的值
        finite_results = results_df[np.isfinite(results_df['half_life'])]
        passed = results_df[results_df['passed']]
        failed = results_df[~results_df['passed']]
        
        stats = {
            'total_pairs': len(results_df),
            'passed_pairs': len(passed),
            'failed_pairs': len(failed),
            'pass_rate': len(passed) / len(results_df) * 100 if len(results_df) > 0 else 0,
            'avg_half_life_all': finite_results['half_life'].mean() if len(finite_results) > 0 else np.nan,
            'avg_half_life_passed': passed['half_life'].mean() if len(passed) > 0 else np.nan,
            'min_half_life': passed['half_life'].min() if len(passed) > 0 else np.nan,
            'max_half_life': passed['half_life'].max() if len(passed) > 0 else np.nan,
            'median_half_life': passed['half_life'].median() if len(passed) > 0 else np.nan,
            'half_life_threshold': (self.min_half_life, self.max_half_life)
        }
        
        return stats


if __name__ == '__main__':
    """OU估计器测试"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*80)
    print("OU半衰期估计器测试")
    print("="*80)
    
    estimator = OUEstimator()
    
    # 生成测试数据
    print("\n生成测试数据...")
    np.random.seed(42)
    
    # 测试1: 快速均值回归（小半衰期）
    print("\n测试1: 快速均值回归序列 (phi=0.95)")
    phi_true = 0.95
    n = 250
    spread = np.zeros(n)
    spread[0] = 0
    
    for t in range(1, n):
        spread[t] = phi_true * spread[t-1] + np.random.randn() * 0.5
    
    spread_series = pd.Series(spread)
    half_life, phi_est = estimator.estimate_half_life(spread_series)
    passed = estimator.test_half_life(half_life)
    
    print(f"真实phi={phi_true:.4f}, 估计phi={phi_est:.4f}")
    print(f"估计半衰期={half_life:.2f}天")
    print(f"通过检验={passed}")
    
    # 测试2: 慢速均值回归（大半衰期）
    print("\n测试2: 慢速均值回归序列 (phi=0.99)")
    phi_true = 0.99
    spread = np.zeros(n)
    spread[0] = 0
    
    for t in range(1, n):
        spread[t] = phi_true * spread[t-1] + np.random.randn() * 0.5
    
    spread_series = pd.Series(spread)
    half_life, phi_est = estimator.estimate_half_life(spread_series)
    passed = estimator.test_half_life(half_life)
    
    print(f"真实phi={phi_true:.4f}, 估计phi={phi_est:.4f}")
    print(f"估计半衰期={half_life:.2f}天")
    print(f"通过检验={passed}")
    
    # 测试3: 随机游走（phi=1）
    print("\n测试3: 随机游走序列 (phi≈1)")
    spread = np.cumsum(np.random.randn(n))
    spread_series = pd.Series(spread)
    half_life, phi_est = estimator.estimate_half_life(spread_series)
    passed = estimator.test_half_life(half_life)
    
    print(f"估计phi={phi_est:.4f}")
    print(f"估计半衰期={half_life:.2f}天")
    print(f"通过检验={passed}")
    
    # 测试4: 批量估计
    print("\n测试4: 批量半衰期估计")
    
    # 生成多个价差序列
    test_pairs = []
    
    # 3个快速回归序列
    for i in range(3):
        phi = 0.90 + i * 0.02  # 0.90, 0.92, 0.94
        spread = np.zeros(n)
        for t in range(1, n):
            spread[t] = phi * spread[t-1] + np.random.randn() * 0.5
        
        test_pairs.append({
            'code1': f'fast_{i}_1',
            'code2': f'fast_{i}_2',
            'spread': pd.Series(spread)
        })
    
    # 2个慢速回归序列
    for i in range(2):
        phi = 0.98 + i * 0.005  # 0.98, 0.985
        spread = np.zeros(n)
        for t in range(1, n):
            spread[t] = phi * spread[t-1] + np.random.randn() * 0.5
        
        test_pairs.append({
            'code1': f'slow_{i}_1',
            'code2': f'slow_{i}_2',
            'spread': pd.Series(spread)
        })
    
    results_df = estimator.estimate_batch_half_life(test_pairs)
    
    print("\n批量估计结果:")
    print(results_df[['code1', 'code2', 'half_life', 'phi', 'passed']].to_string(index=False))
    
    print("\n统计信息:")
    stats = estimator.get_half_life_stats(results_df)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*80)

