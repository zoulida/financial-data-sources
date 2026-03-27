"""
数据预处理模块
==============

实现因子预处理的三步法：
1. 去极值：Winsorize双侧2.5%
2. 中性化：对市值、行业、β做回归取残差
3. 标准化：横截面z-score
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class DataProcessor:
    """数据预处理器"""
    
    def __init__(self, 
                 winsorize_limits: Tuple[float, float] = (0.025, 0.975),
                 neutralize_factors: List[str] = None,
                 standardize_method: str = 'zscore'):
        """
        初始化数据预处理器
        
        Parameters:
        -----------
        winsorize_limits : tuple
            去极值的分位数限制，默认(0.025, 0.975)即2.5%双侧去极值
        neutralize_factors : list
            需要中性化的因子列表，默认['market_cap', 'industry', 'beta']
        standardize_method : str
            标准化方法，'zscore'或'minmax'
        """
        self.winsorize_limits = winsorize_limits
        self.neutralize_factors = neutralize_factors or ['market_cap', 'industry', 'beta']
        self.standardize_method = standardize_method
        
        # 存储预处理参数
        self.winsorize_bounds = {}
        self.neutralize_models = {}
        self.standardize_scalers = {}
        
    def process_factors(self, 
                       factors_df: pd.DataFrame,
                       market_cap: Optional[pd.Series] = None,
                       industry: Optional[pd.Series] = None,
                       beta: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        完整的因子预处理流程
        
        Parameters:
        -----------
        factors_df : pd.DataFrame
            原始因子数据，行为日期，列为因子
        market_cap : pd.Series, optional
            市值数据，用于中性化
        industry : pd.Series, optional
            行业数据，用于中性化
        beta : pd.Series, optional
            Beta数据，用于中性化
            
        Returns:
        --------
        pd.DataFrame : 预处理后的因子数据
        """
        print("开始因子预处理...")
        
        # 1. 去极值
        print("1. 去极值处理...")
        factors_winsorized = self.winsorize_factors(factors_df)
        
        # 2. 中性化
        print("2. 中性化处理...")
        factors_neutralized = self.neutralize_factors_data(
            factors_winsorized, market_cap, industry, beta
        )
        
        # 3. 标准化
        print("3. 标准化处理...")
        factors_standardized = self.standardize_factors(factors_neutralized)
        
        print("因子预处理完成！")
        return factors_standardized
    
    def winsorize_factors(self, factors_df: pd.DataFrame) -> pd.DataFrame:
        """
        去极值处理：Winsorize双侧2.5%
        
        Parameters:
        -----------
        factors_df : pd.DataFrame
            原始因子数据
            
        Returns:
        --------
        pd.DataFrame : 去极值后的因子数据
        """
        result = factors_df.copy()
        
        for col in factors_df.columns:
            if factors_df[col].dtype in ['float64', 'int64']:
                # 计算分位数
                lower_bound = factors_df[col].quantile(self.winsorize_limits[0])
                upper_bound = factors_df[col].quantile(self.winsorize_limits[1])
                
                # 存储边界值
                self.winsorize_bounds[col] = (lower_bound, upper_bound)
                
                # 去极值
                result[col] = np.clip(factors_df[col], lower_bound, upper_bound)
        
        return result
    
    def neutralize_factors_data(self, 
                               factors_df: pd.DataFrame,
                               market_cap: Optional[pd.Series] = None,
                               industry: Optional[pd.Series] = None,
                               beta: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        中性化处理：对市值、行业、β做回归取残差
        
        Parameters:
        -----------
        factors_df : pd.DataFrame
            去极值后的因子数据
        market_cap : pd.Series, optional
            市值数据
        industry : pd.Series, optional
            行业数据
        beta : pd.Series, optional
            Beta数据
            
        Returns:
        --------
        pd.DataFrame : 中性化后的因子数据
        """
        result = factors_df.copy()
        
        # 准备控制变量
        control_vars = self._prepare_control_variables(
            factors_df.index, market_cap, industry, beta
        )
        
        if control_vars is None or len(control_vars.columns) == 0:
            print("警告：无控制变量，跳过中性化处理")
            return result
        
        # 对每个因子进行中性化
        for col in factors_df.columns:
            if factors_df[col].dtype in ['float64', 'int64']:
                try:
                    # 获取有效数据
                    valid_mask = ~(factors_df[col].isna() | control_vars.isna().any(axis=1))
                    
                    if valid_mask.sum() < 10:  # 至少需要10个样本
                        print(f"警告：{col} 有效样本不足，跳过中性化")
                        continue
                    
                    y = factors_df[col][valid_mask]
                    X = control_vars[valid_mask]
                    
                    # 线性回归
                    model = LinearRegression()
                    model.fit(X, y)
                    
                    # 存储模型
                    self.neutralize_models[col] = model
                    
                    # 计算残差
                    y_pred = model.predict(X)
                    residuals = y - y_pred
                    
                    # 更新结果
                    result.loc[valid_mask, col] = residuals
                    
                except Exception as e:
                    print(f"警告：{col} 中性化失败: {e}")
                    continue
        
        return result
    
    def standardize_factors(self, factors_df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化处理：横截面z-score
        
        Parameters:
        -----------
        factors_df : pd.DataFrame
            中性化后的因子数据
            
        Returns:
        --------
        pd.DataFrame : 标准化后的因子数据
        """
        result = factors_df.copy()
        
        for col in factors_df.columns:
            if factors_df[col].dtype in ['float64', 'int64']:
                try:
                    if self.standardize_method == 'zscore':
                        # Z-score标准化
                        mean_val = factors_df[col].mean()
                        std_val = factors_df[col].std()
                        
                        if std_val > 0:
                            result[col] = (factors_df[col] - mean_val) / std_val
                        else:
                            result[col] = 0
                            
                    elif self.standardize_method == 'minmax':
                        # Min-Max标准化
                        min_val = factors_df[col].min()
                        max_val = factors_df[col].max()
                        
                        if max_val > min_val:
                            result[col] = (factors_df[col] - min_val) / (max_val - min_val)
                        else:
                            result[col] = 0
                    
                    # 存储标准化参数
                    self.standardize_scalers[col] = {
                        'method': self.standardize_method,
                        'mean': factors_df[col].mean(),
                        'std': factors_df[col].std(),
                        'min': factors_df[col].min(),
                        'max': factors_df[col].max()
                    }
                    
                except Exception as e:
                    print(f"警告：{col} 标准化失败: {e}")
                    continue
        
        return result
    
    def _prepare_control_variables(self, 
                                  index: pd.Index,
                                  market_cap: Optional[pd.Series] = None,
                                  industry: Optional[pd.Series] = None,
                                  beta: Optional[pd.Series] = None) -> Optional[pd.DataFrame]:
        """
        准备控制变量
        
        Parameters:
        -----------
        index : pd.Index
            数据索引
        market_cap : pd.Series, optional
            市值数据
        industry : pd.Series, optional
            行业数据
        beta : pd.Series, optional
            Beta数据
            
        Returns:
        --------
        pd.DataFrame : 控制变量DataFrame
        """
        control_vars = {}
        
        # 添加市值
        if market_cap is not None:
            if isinstance(market_cap, pd.Series) and len(market_cap) > 0:
                # 对齐索引
                aligned_market_cap = market_cap.reindex(index).fillna(market_cap.median())
                control_vars['market_cap'] = aligned_market_cap
            else:
                # 生成模拟市值数据
                control_vars['market_cap'] = self._generate_mock_market_cap(index)
        
        # 添加行业（转换为数值）
        if industry is not None:
            if isinstance(industry, pd.Series) and len(industry) > 0:
                # 对齐索引并转换为数值
                aligned_industry = industry.reindex(index).fillna('Unknown')
                industry_dummies = pd.get_dummies(aligned_industry, prefix='industry')
                control_vars.update(industry_dummies.to_dict('series'))
            else:
                # 生成模拟行业数据
                control_vars['industry'] = self._generate_mock_industry(index)
        
        # 添加Beta
        if beta is not None:
            if isinstance(beta, pd.Series) and len(beta) > 0:
                # 对齐索引
                aligned_beta = beta.reindex(index).fillna(1.0)
                control_vars['beta'] = aligned_beta
            else:
                # 生成模拟Beta数据
                control_vars['beta'] = self._generate_mock_beta(index)
        
        if not control_vars:
            return None
        
        return pd.DataFrame(control_vars, index=index)
    
    def _generate_mock_market_cap(self, index: pd.Index) -> pd.Series:
        """生成模拟市值数据"""
        np.random.seed(42)
        # 对数正态分布，均值10亿，标准差1
        log_market_cap = np.random.normal(9, 1, len(index))
        market_cap = np.exp(log_market_cap) * 1e8  # 转换为实际市值
        return pd.Series(market_cap, index=index)
    
    def _generate_mock_industry(self, index: pd.Index) -> pd.Series:
        """生成模拟行业数据"""
        np.random.seed(42)
        industries = ['银行', '地产', '科技', '医药', '消费', '制造', '能源', '金融']
        industry_codes = np.random.choice(industries, len(index))
        return pd.Series(industry_codes, index=index)
    
    def _generate_mock_beta(self, index: pd.Index) -> pd.Series:
        """生成模拟Beta数据"""
        np.random.seed(42)
        # Beta通常在0.5-2.0之间
        beta = np.random.normal(1.0, 0.3, len(index))
        beta = np.clip(beta, 0.3, 2.5)
        return pd.Series(beta, index=index)
    
    def inverse_transform(self, factors_df: pd.DataFrame) -> pd.DataFrame:
        """
        逆变换：将标准化后的数据还原
        
        Parameters:
        -----------
        factors_df : pd.DataFrame
            标准化后的因子数据
            
        Returns:
        --------
        pd.DataFrame : 还原后的因子数据
        """
        result = factors_df.copy()
        
        for col in factors_df.columns:
            if col in self.standardize_scalers:
                scaler_params = self.standardize_scalers[col]
                
                if scaler_params['method'] == 'zscore':
                    # 逆Z-score变换
                    result[col] = factors_df[col] * scaler_params['std'] + scaler_params['mean']
                elif scaler_params['method'] == 'minmax':
                    # 逆Min-Max变换
                    result[col] = factors_df[col] * (scaler_params['max'] - scaler_params['min']) + scaler_params['min']
        
        return result
    
    def get_preprocessing_summary(self) -> Dict:
        """
        获取预处理摘要信息
        
        Returns:
        --------
        Dict : 预处理摘要
        """
        summary = {
            'winsorize_limits': self.winsorize_limits,
            'winsorize_bounds_count': len(self.winsorize_bounds),
            'neutralize_models_count': len(self.neutralize_models),
            'standardize_scalers_count': len(self.standardize_scalers),
            'standardize_method': self.standardize_method
        }
        
        return summary


# 使用示例
if __name__ == "__main__":
    # 创建示例数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    # 创建因子数据
    factors_df = pd.DataFrame({
        'factor1': np.random.normal(0, 1, 100),
        'factor2': np.random.normal(0, 2, 100),
        'factor3': np.random.normal(0, 0.5, 100),
        'factor4': np.random.normal(0, 1.5, 100)
    }, index=dates)
    
    # 添加一些极值
    factors_df.loc[dates[10], 'factor1'] = 10  # 极值
    factors_df.loc[dates[20], 'factor2'] = -15  # 极值
    
    # 创建控制变量
    market_cap = pd.Series(np.random.lognormal(9, 1, 100) * 1e8, index=dates)
    industry = pd.Series(np.random.choice(['银行', '科技', '医药'], 100), index=dates)
    beta = pd.Series(np.random.normal(1.0, 0.3, 100), index=dates)
    
    print("原始因子数据统计:")
    print(factors_df.describe())
    
    # 创建预处理器
    processor = DataProcessor()
    
    # 预处理
    processed_factors = processor.process_factors(
        factors_df, market_cap, industry, beta
    )
    
    print("\n预处理后因子数据统计:")
    print(processed_factors.describe())
    
    print("\n预处理摘要:")
    summary = processor.get_preprocessing_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
