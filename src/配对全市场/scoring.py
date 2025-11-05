"""
评分排序模块

根据协整检验的p值和OU模型的半衰期计算配对得分，
并按得分降序排列，输出前N名配对。
"""

import pandas as pd
import numpy as np
import logging
from typing import List, Dict

from config import Config

logger = logging.getLogger(__name__)


class PairScorer:
    """配对评分器"""
    
    def __init__(self):
        """初始化评分器"""
        self.p_weight = Config.Scoring.P_VALUE_WEIGHT
        self.hl_weight = Config.Scoring.HALF_LIFE_WEIGHT
        self.max_half_life = Config.OUModel.MAX_HALF_LIFE
        self.top_n = Config.Scoring.TOP_N
        
        formula = f"{self.p_weight}×(1-p) + {self.hl_weight}×(1-H/{self.max_half_life})"
        logger.info(f"评分器初始化完成，评分公式: Score = {formula}")
    
    def calculate_score(self, p_value: float, half_life: float) -> float:
        """
        计算单个配对的得分
        
        Args:
            p_value: 协整检验p值
            half_life: OU半衰期
            
        Returns:
            得分
        """
        # p值部分: 越小越好，范围[0, 1]
        p_component = self.p_weight * max(0, 1 - p_value)
        
        # 半衰期部分: 越小越好，但有上限
        hl_ratio = min(1.0, half_life / self.max_half_life)
        hl_component = self.hl_weight * max(0, 1 - hl_ratio)
        
        score = p_component + hl_component
        
        return score
    
    def score_pairs(self, pairs_df: pd.DataFrame) -> pd.DataFrame:
        """
        为所有配对计算得分
        
        Args:
            pairs_df: 包含code1, code2, p_value, half_life等列的DataFrame
            
        Returns:
            添加了score列的DataFrame
        """
        if 'p_value' not in pairs_df.columns or 'half_life' not in pairs_df.columns:
            raise ValueError("DataFrame必须包含p_value和half_life列")
        
        logger.info(f"开始计算 {len(pairs_df)} 个配对的得分...")
        
        # 计算得分
        pairs_df['score'] = pairs_df.apply(
            lambda row: self.calculate_score(row['p_value'], row['half_life']),
            axis=1
        )
        
        # 按得分降序排序
        pairs_df = pairs_df.sort_values('score', ascending=False).reset_index(drop=True)
        
        logger.info(f"得分计算完成，最高分: {pairs_df['score'].max():.2f}, 最低分: {pairs_df['score'].min():.2f}")
        
        return pairs_df
    
    def get_top_pairs(self, pairs_df: pd.DataFrame, n: int = None) -> pd.DataFrame:
        """
        获取得分前N名的配对
        
        Args:
            pairs_df: 包含score列的DataFrame
            n: 返回前N名，默认使用配置中的值
            
        Returns:
            前N名配对的DataFrame
        """
        if n is None:
            n = self.top_n
        
        if 'score' not in pairs_df.columns:
            raise ValueError("DataFrame必须包含score列")
        
        # 确保按score降序排列
        pairs_df = pairs_df.sort_values('score', ascending=False)
        
        # 取前N名
        top_pairs = pairs_df.head(n).reset_index(drop=True)
        
        logger.info(f"获取前 {len(top_pairs)} 名配对")
        
        return top_pairs
    
    def get_scoring_stats(self, pairs_df: pd.DataFrame) -> Dict:
        """
        获取评分统计信息
        
        Args:
            pairs_df: 包含score列的DataFrame
            
        Returns:
            统计信息字典
        """
        if 'score' not in pairs_df.columns:
            return {}
        
        stats = {
            'total_pairs': len(pairs_df),
            'max_score': pairs_df['score'].max(),
            'min_score': pairs_df['score'].min(),
            'avg_score': pairs_df['score'].mean(),
            'median_score': pairs_df['score'].median(),
            'std_score': pairs_df['score'].std(),
            'top_10_avg_score': pairs_df.head(10)['score'].mean() if len(pairs_df) >= 10 else np.nan,
            'top_100_avg_score': pairs_df.head(100)['score'].mean() if len(pairs_df) >= 100 else np.nan
        }
        
        # 得分分布
        if len(pairs_df) > 0:
            stats['score_distribution'] = {
                '>90': len(pairs_df[pairs_df['score'] > 90]),
                '80-90': len(pairs_df[(pairs_df['score'] >= 80) & (pairs_df['score'] <= 90)]),
                '70-80': len(pairs_df[(pairs_df['score'] >= 70) & (pairs_df['score'] < 80)]),
                '60-70': len(pairs_df[(pairs_df['score'] >= 60) & (pairs_df['score'] < 70)]),
                '<60': len(pairs_df[pairs_df['score'] < 60])
            }
        
        return stats


if __name__ == '__main__':
    """评分器测试"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*80)
    print("配对评分器测试")
    print("="*80)
    
    scorer = PairScorer()
    
    # 生成测试数据
    print("\n生成测试数据...")
    np.random.seed(42)
    
    # 生成20个模拟配对
    test_data = []
    for i in range(20):
        # 模拟不同质量的配对
        p_value = np.random.uniform(0.001, 0.1)
        half_life = np.random.uniform(10, 80)
        
        test_data.append({
            'code1': f'stock_{i}_1',
            'code2': f'stock_{i}_2',
            'p_value': p_value,
            'half_life': half_life
        })
    
    pairs_df = pd.DataFrame(test_data)
    
    # 测试1: 计算得分
    print("\n测试1: 计算配对得分")
    scored_df = scorer.score_pairs(pairs_df)
    
    print("\n前10名配对:")
    print(scored_df[['code1', 'code2', 'p_value', 'half_life', 'score']].head(10).to_string(index=False))
    
    # 测试2: 获取前5名
    print("\n测试2: 获取前5名配对")
    top5 = scorer.get_top_pairs(scored_df, n=5)
    print(top5[['code1', 'code2', 'p_value', 'half_life', 'score']].to_string(index=False))
    
    # 测试3: 统计信息
    print("\n测试3: 评分统计信息")
    stats = scorer.get_scoring_stats(scored_df)
    
    print("\n基础统计:")
    for key in ['total_pairs', 'max_score', 'min_score', 'avg_score', 'median_score', 'std_score']:
        if key in stats:
            print(f"  {key}: {stats[key]:.2f}" if isinstance(stats[key], float) else f"  {key}: {stats[key]}")
    
    print("\n得分分布:")
    if 'score_distribution' in stats:
        for range_key, count in stats['score_distribution'].items():
            print(f"  {range_key}: {count} 对")
    
    # 测试4: 不同p值和半衰期的得分对比
    print("\n测试4: 得分对比分析")
    test_cases = [
        {'p_value': 0.001, 'half_life': 20, 'desc': '优质配对 (低p, 短半衰期)'},
        {'p_value': 0.01, 'half_life': 30, 'desc': '良好配对'},
        {'p_value': 0.03, 'half_life': 50, 'desc': '中等配对'},
        {'p_value': 0.05, 'half_life': 60, 'desc': '边缘配对 (临界p, 长半衰期)'},
    ]
    
    print("\n不同类型配对的得分:")
    print(f"{'描述':<30} {'p值':>8} {'半衰期':>8} {'得分':>8}")
    print("-" * 60)
    for case in test_cases:
        score = scorer.calculate_score(case['p_value'], case['half_life'])
        print(f"{case['desc']:<30} {case['p_value']:>8.3f} {case['half_life']:>8.1f} {score:>8.2f}")
    
    print("\n" + "="*80)

