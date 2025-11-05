"""
配对初筛模块

通过相关性、波动率、成交额三个指标快速筛选候选配对，
减少90%的计算量，只对通过初筛的配对进行协整检验。
"""

import pandas as pd
import numpy as np
import logging
import random
from typing import List, Tuple, Dict
from itertools import combinations

from config import Config

logger = logging.getLogger(__name__)


class PairScreener:
    """配对初筛器"""
    
    def __init__(self):
        """初始化配对初筛器"""
        self.min_corr = Config.PairScreen.MIN_CORRELATION
        self.max_spread_vol = Config.PairScreen.MAX_SPREAD_VOLATILITY
        self.min_data_points = Config.PairScreen.MIN_DATA_POINTS
        
        logger.info(f"配对初筛器初始化完成 (相关系数>={self.min_corr}, 价差波动<={self.max_spread_vol*100}%)")
    
    def calculate_correlation(self, price1: pd.Series, price2: pd.Series) -> float:
        """
        计算两个价格序列的Pearson相关系数
        
        Args:
            price1: 价格序列1
            price2: 价格序列2
            
        Returns:
            相关系数
        """
        # 对齐日期
        aligned_data = pd.DataFrame({'p1': price1, 'p2': price2}).dropna()
        
        if len(aligned_data) < self.min_data_points:
            return -1.0
        
        return aligned_data['p1'].corr(aligned_data['p2'])
    
    def calculate_spread_volatility(self, price1: pd.Series, price2: pd.Series) -> float:
        """
        计算价差的年化波动率
        
        Args:
            price1: 价格序列1
            price2: 价格序列2
            
        Returns:
            年化波动率
        """
        # 对齐日期
        aligned_data = pd.DataFrame({'p1': price1, 'p2': price2}).dropna()
        
        if len(aligned_data) < self.min_data_points:
            return float('inf')
        
        # 计算对数价差
        log_spread = np.log(aligned_data['p1']) - np.log(aligned_data['p2'])
        
        # 计算日波动率
        daily_vol = log_spread.std()
        
        # 年化波动率（假设250个交易日）
        annual_vol = daily_vol * np.sqrt(250)
        
        return annual_vol
    
    def screen_single_pair(
        self, 
        code1: str, 
        code2: str,
        price1: pd.Series, 
        price2: pd.Series,
        info1: dict = None,
        info2: dict = None
    ) -> Tuple[bool, Dict]:
        """
        筛选单个配对
        
        Args:
            code1: 标的1代码
            code2: 标的2代码
            price1: 标的1价格序列
            price2: 标的2价格序列
            info1: 标的1的额外信息（如名称、成交额等）
            info2: 标的2的额外信息
            
        Returns:
            (是否通过, 筛选结果详情)
        """
        result = {
            'code1': code1,
            'code2': code2,
            'correlation': np.nan,
            'spread_volatility': np.nan,
            'data_points': 0,
            'passed': False,
            'fail_reason': ''
        }
        
        # 对齐数据
        aligned_data = pd.DataFrame({'p1': price1, 'p2': price2}).dropna()
        result['data_points'] = len(aligned_data)
        
        # 检查数据点数
        if result['data_points'] < self.min_data_points:
            result['fail_reason'] = f'数据点不足({result["data_points"]}<{self.min_data_points})'
            return False, result
        
        # 计算相关系数
        result['correlation'] = aligned_data['p1'].corr(aligned_data['p2'])
        
        if result['correlation'] < self.min_corr:
            result['fail_reason'] = f'相关系数过低({result["correlation"]:.3f}<{self.min_corr})'
            return False, result
        
        # 计算价差波动率
        log_spread = np.log(aligned_data['p1']) - np.log(aligned_data['p2'])
        daily_vol = log_spread.std()
        result['spread_volatility'] = daily_vol * np.sqrt(250)
        
        if result['spread_volatility'] > self.max_spread_vol:
            result['fail_reason'] = f'价差波动过高({result["spread_volatility"]:.3f}>{self.max_spread_vol})'
            return False, result
        
        # 添加额外信息
        if info1:
            result['name1'] = info1.get('name', '')
            result['avg_amount1'] = info1.get('avg_amount', np.nan)
        
        if info2:
            result['name2'] = info2.get('name', '')
            result['avg_amount2'] = info2.get('avg_amount', np.nan)
        
        result['passed'] = True
        return True, result
    
    def screen_all_pairs(
        self,
        price_data: Dict[str, pd.Series],
        info_data: Dict[str, dict] = None
    ) -> Tuple[List[Tuple[str, str]], pd.DataFrame]:
        """
        筛选所有配对
        
        Args:
            price_data: 代码到价格序列的字典
            info_data: 代码到信息字典的映射
            
        Returns:
            (通过的配对列表, 筛选结果DataFrame)
        """
        codes = list(price_data.keys())
        total_pairs = len(codes) * (len(codes) - 1) // 2
        
        # 调试模式：采样配对
        all_pairs_list = list(combinations(codes, 2))
        if Config.System.DEBUG_MODE and Config.System.DEBUG_SAMPLE_RATIO < 1.0:
            # 设置随机种子确保可重复
            random.seed(Config.System.DEBUG_SAMPLE_SEED)
            np.random.seed(Config.System.DEBUG_SAMPLE_SEED)
            
            # 采样配对
            sample_size = max(1, int(len(all_pairs_list) * Config.System.DEBUG_SAMPLE_RATIO))
            sampled_pairs = random.sample(all_pairs_list, sample_size)
            
            logger.info(f"调试模式：从 {total_pairs} 个候选配对中采样 {sample_size} 个 ({Config.System.DEBUG_SAMPLE_RATIO*100:.1f}%)")
            logger.info(f"随机种子: {Config.System.DEBUG_SAMPLE_SEED}")
        else:
            sampled_pairs = all_pairs_list
        
        actual_total_pairs = len(sampled_pairs)
        logger.info(f"开始配对初筛，共 {len(codes)} 个标的，实际处理 {actual_total_pairs} 个候选配对")
        
        passed_pairs = []
        all_results = []
        
        # 处理采样后的配对
        for i, (code1, code2) in enumerate(sampled_pairs):
            if (i + 1) % max(1, actual_total_pairs // 10) == 0 or (i + 1) == actual_total_pairs:
                logger.info(f"初筛进度: {i+1}/{actual_total_pairs} ({(i+1)/actual_total_pairs*100:.1f}%)")
            
            price1 = price_data[code1]
            price2 = price_data[code2]
            
            info1 = info_data.get(code1) if info_data else None
            info2 = info_data.get(code2) if info_data else None
            
            passed, result = self.screen_single_pair(
                code1, code2, price1, price2, info1, info2
            )
            
            if passed:
                passed_pairs.append((code1, code2))
            
            all_results.append(result)
        
        results_df = pd.DataFrame(all_results)
        
        pass_rate = len(passed_pairs) / actual_total_pairs * 100 if actual_total_pairs > 0 else 0
        logger.info(f"初筛完成: 处理配对 {actual_total_pairs}, 通过 {len(passed_pairs)} ({pass_rate:.2f}%)")
        if Config.System.DEBUG_MODE and Config.System.DEBUG_SAMPLE_RATIO < 1.0:
            logger.info(f"注：实际候选配对总数为 {total_pairs}，调试模式下仅处理了 {Config.System.DEBUG_SAMPLE_RATIO*100:.1f}%")
        
        # 统计失败原因
        if len(results_df[~results_df['passed']]) > 0:
            fail_reasons = results_df[~results_df['passed']]['fail_reason'].value_counts()
            logger.info("失败原因统计:")
            for reason, count in fail_reasons.items():
                logger.info(f"  {reason}: {count} 对")
        
        return passed_pairs, results_df
    
    def get_screening_stats(self, results_df: pd.DataFrame) -> Dict:
        """
        获取筛选统计信息
        
        Args:
            results_df: 筛选结果DataFrame
            
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
            'avg_correlation': passed['correlation'].mean() if len(passed) > 0 else np.nan,
            'avg_spread_volatility': passed['spread_volatility'].mean() if len(passed) > 0 else np.nan,
            'avg_data_points': passed['data_points'].mean() if len(passed) > 0 else 0
        }
        
        # 失败原因统计
        if len(failed) > 0:
            stats['fail_reasons'] = failed['fail_reason'].value_counts().to_dict()
        else:
            stats['fail_reasons'] = {}
        
        return stats


if __name__ == '__main__':
    """配对初筛器测试"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*80)
    print("配对初筛器测试")
    print("="*80)
    
    screener = PairScreener()
    
    # 生成测试数据
    print("\n生成测试数据...")
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=250, freq='D')
    
    # 生成5只高度相关的模拟股票
    test_data = {}
    base_series = np.cumsum(np.random.randn(250)) + 100
    
    for i in range(5):
        noise = np.random.randn(250) * 2
        price_series = pd.Series(base_series + noise, index=dates, name=f'stock_{i}')
        test_data[f'stock_{i}'] = price_series
    
    # 添加几只低相关的股票
    for i in range(5, 8):
        random_series = np.cumsum(np.random.randn(250)) + 100
        price_series = pd.Series(random_series, index=dates, name=f'stock_{i}')
        test_data[f'stock_{i}'] = price_series
    
    print(f"生成了 {len(test_data)} 只测试股票")
    
    # 测试筛选
    print("\n开始配对筛选...")
    passed_pairs, results_df = screener.screen_all_pairs(test_data)
    
    print(f"\n筛选结果:")
    print(f"总配对数: {len(results_df)}")
    print(f"通过数量: {len(passed_pairs)}")
    print(f"通过率: {len(passed_pairs)/len(results_df)*100:.2f}%")
    
    # 显示通过的配对
    if len(passed_pairs) > 0:
        print(f"\n通过的配对:")
        passed_results = results_df[results_df['passed']]
        print(passed_results[['code1', 'code2', 'correlation', 'spread_volatility', 'data_points']].to_string(index=False))
    
    # 显示统计信息
    print("\n统计信息:")
    stats = screener.get_screening_stats(results_df)
    for key, value in stats.items():
        if key != 'fail_reasons':
            print(f"  {key}: {value}")
    
    if stats['fail_reasons']:
        print("\n失败原因:")
        for reason, count in stats['fail_reasons'].items():
            print(f"  {reason}: {count}")
    
    print("\n" + "="*80)

