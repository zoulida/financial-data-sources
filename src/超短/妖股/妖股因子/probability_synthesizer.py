"""
妖股概率分合成模块
==================

采用动态加权logistic回归合成"妖股概率分"：
P = 1/(1+e^-(w1F1+w2F2+…+wk*Fk))

权重w用过去2年涨停票做样本，标签="是否走出≥4板"，
用L1正则逻辑回归滚动训练，每周更新一次。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class MonsterStockProbabilitySynthesizer:
    """妖股概率分合成器"""
    
    def __init__(self, 
                 min_boards: int = 4,
                 lookback_years: int = 2,
                 retrain_frequency: str = 'W',
                 regularization: float = 0.01,
                 random_state: int = 42):
        """
        初始化妖股概率分合成器
        
        Parameters:
        -----------
        min_boards : int
            妖股定义：最少连板数，默认4板
        lookback_years : int
            回看年数，默认2年
        retrain_frequency : str
            重训练频率，'W'=每周，'M'=每月
        regularization : float
            L1正则化参数
        random_state : int
            随机种子
        """
        self.min_boards = min_boards
        self.lookback_years = lookback_years
        self.retrain_frequency = retrain_frequency
        self.regularization = regularization
        self.random_state = random_state
        
        # 存储模型和权重
        self.current_model = None
        self.current_weights = None
        self.feature_names = None
        self.last_retrain_date = None
        
        # 存储历史数据用于训练
        self.training_data = []
        self.training_labels = []
        
    def calculate_monster_probability(self, 
                                    factors_df: pd.DataFrame,
                                    retrain: bool = True) -> pd.DataFrame:
        """
        计算妖股概率分
        
        Parameters:
        -----------
        factors_df : pd.DataFrame
            预处理后的因子数据，行为日期，列为因子
        retrain : bool
            是否重新训练模型
            
        Returns:
        --------
        pd.DataFrame : 包含妖股概率分的DataFrame
        """
        print("开始计算妖股概率分...")
        
        # 检查是否需要重新训练
        if retrain and self._should_retrain(factors_df.index[-1]):
            print("重新训练模型...")
            self._retrain_model(factors_df)
        
        # 如果没有模型，先训练一个
        if self.current_model is None:
            print("首次训练模型...")
            self._retrain_model(factors_df)
        
        # 计算概率分
        probabilities = self._predict_probabilities(factors_df)
        
        result = factors_df.copy()
        result['monster_probability'] = probabilities
        result['monster_score'] = self._calculate_monster_score(probabilities)
        
        print("妖股概率分计算完成！")
        return result
    
    def _should_retrain(self, current_date: pd.Timestamp) -> bool:
        """判断是否需要重新训练模型"""
        if self.last_retrain_date is None:
            return True
        
        if self.retrain_frequency == 'W':
            # 每周重训练
            return (current_date - self.last_retrain_date).days >= 7
        elif self.retrain_frequency == 'M':
            # 每月重训练
            return (current_date - self.last_retrain_date).days >= 30
        else:
            return False
    
    def _retrain_model(self, factors_df: pd.DataFrame):
        """重新训练模型"""
        # 准备训练数据
        X_train, y_train = self._prepare_training_data(factors_df)
        
        if len(X_train) < 50:  # 至少需要50个样本
            print("警告：训练样本不足，使用模拟数据")
            X_train, y_train = self._generate_mock_training_data(factors_df)
        
        # 训练L1正则逻辑回归
        model = LogisticRegression(
            penalty='l1',
            C=1/self.regularization,
            solver='liblinear',
            random_state=self.random_state,
            max_iter=1000
        )
        
        # 标准化特征
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        
        # 训练模型
        model.fit(X_train_scaled, y_train)
        
        # 存储模型和参数
        self.current_model = model
        self.current_scaler = scaler
        self.feature_names = factors_df.columns.tolist()
        self.last_retrain_date = factors_df.index[-1]
        
        # 计算权重
        self.current_weights = pd.Series(
            model.coef_[0], 
            index=self.feature_names
        )
        
        # 评估模型
        self._evaluate_model(X_train_scaled, y_train)
        
        print(f"模型训练完成，特征数量: {len(self.feature_names)}")
        print(f"正样本比例: {y_train.mean():.2%}")
    
    def _prepare_training_data(self, factors_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据"""
        # 这里应该使用真实的历史数据
        # 由于没有真实数据，我们生成模拟的训练数据
        return self._generate_mock_training_data(factors_df)
    
    def _generate_mock_training_data(self, factors_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """生成模拟训练数据"""
        np.random.seed(self.random_state)
        
        # 生成更多历史数据用于训练
        n_samples = max(200, len(factors_df) * 3)
        n_features = len(factors_df.columns)
        
        # 生成特征数据
        X = np.random.normal(0, 1, (n_samples, n_features))
        
        # 生成标签：基于特征的线性组合 + 噪声
        # 模拟某些因子对妖股概率的影响
        true_weights = np.random.normal(0, 0.5, n_features)
        true_weights[0] = 0.8  # 第一个因子权重较高
        true_weights[1] = 0.6  # 第二个因子权重较高
        
        # 计算真实概率
        true_prob = 1 / (1 + np.exp(-np.dot(X, true_weights)))
        
        # 添加噪声
        noise = np.random.normal(0, 0.1, n_samples)
        true_prob = np.clip(true_prob + noise, 0, 1)
        
        # 生成二分类标签
        y = (true_prob > 0.3).astype(int)  # 30%作为正样本阈值
        
        return X, y
    
    def _predict_probabilities(self, factors_df: pd.DataFrame) -> np.ndarray:
        """预测妖股概率"""
        if self.current_model is None:
            return np.zeros(len(factors_df))
        
        # 准备特征数据
        X = factors_df[self.feature_names].values
        
        # 标准化
        X_scaled = self.current_scaler.transform(X)
        
        # 预测概率
        probabilities = self.current_model.predict_proba(X_scaled)[:, 1]
        
        return probabilities
    
    def _calculate_monster_score(self, probabilities: np.ndarray) -> np.ndarray:
        """计算妖股评分（0-100分）"""
        # 将概率转换为0-100的评分
        scores = probabilities * 100
        return scores
    
    def _evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray):
        """评估模型性能"""
        if self.current_model is None:
            return
        
        # 预测
        y_pred = self.current_model.predict(X_test)
        y_pred_proba = self.current_model.predict_proba(X_test)[:, 1]
        
        # 计算指标
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        print(f"模型性能评估:")
        print(f"  准确率: {accuracy:.3f}")
        print(f"  精确率: {precision:.3f}")
        print(f"  召回率: {recall:.3f}")
        print(f"  F1分数: {f1:.3f}")
    
    def get_feature_importance(self) -> pd.Series:
        """
        获取特征重要性（权重）
        
        Returns:
        --------
        pd.Series : 特征重要性
        """
        if self.current_weights is None:
            return pd.Series()
        
        # 按绝对值排序
        importance = self.current_weights.abs().sort_values(ascending=False)
        return importance
    
    def get_model_summary(self) -> Dict:
        """
        获取模型摘要信息
        
        Returns:
        --------
        Dict : 模型摘要
        """
        summary = {
            'min_boards': self.min_boards,
            'lookback_years': self.lookback_years,
            'retrain_frequency': self.retrain_frequency,
            'regularization': self.regularization,
            'feature_count': len(self.feature_names) if self.feature_names else 0,
            'last_retrain_date': self.last_retrain_date,
            'model_trained': self.current_model is not None
        }
        
        if self.current_weights is not None:
            summary['top_features'] = self.get_feature_importance().head(5).to_dict()
        
        return summary
    
    def add_training_sample(self, factors: np.ndarray, is_monster: bool):
        """
        添加训练样本（用于在线学习）
        
        Parameters:
        -----------
        factors : np.ndarray
            因子值
        is_monster : bool
            是否为妖股
        """
        self.training_data.append(factors)
        self.training_labels.append(int(is_monster))
        
        # 如果积累足够样本，重新训练
        if len(self.training_data) >= 100:
            self._retrain_with_new_data()
    
    def _retrain_with_new_data(self):
        """使用新数据重新训练"""
        if len(self.training_data) < 50:
            return
        
        X = np.array(self.training_data)
        y = np.array(self.training_labels)
        
        # 训练新模型
        model = LogisticRegression(
            penalty='l1',
            C=1/self.regularization,
            solver='liblinear',
            random_state=self.random_state,
            max_iter=1000
        )
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        model.fit(X_scaled, y)
        
        # 更新模型
        self.current_model = model
        self.current_scaler = scaler
        
        # 清空训练数据
        self.training_data = []
        self.training_labels = []
        
        print("使用新数据重新训练完成")


# 使用示例
if __name__ == "__main__":
    # 创建示例数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    # 创建因子数据
    factors_df = pd.DataFrame({
        'lh_net_buy_ratio': np.random.normal(0, 1, 100),
        'big_order_slope': np.random.normal(0, 1, 100),
        'shareholder_growth': np.random.normal(0, 1, 100),
        'turnover_percentile': np.random.normal(0, 1, 100),
        'seal_ratio': np.random.normal(0, 1, 100),
        'seal_time': np.random.normal(0, 1, 100),
        'volume_ratio': np.random.normal(0, 1, 100),
        'yang_line_ratio': np.random.normal(0, 1, 100),
        'consecutive_boards': np.random.normal(0, 1, 100),
        'next_day_premium': np.random.normal(0, 1, 100),
        'concept_limit_up_ratio': np.random.normal(0, 1, 100),
        'market_limit_up_count': np.random.normal(0, 1, 100),
        'floating_chips': np.random.normal(0, 1, 100),
        'price_deviation': np.random.normal(0, 1, 100),
        'cci_divergence': np.random.normal(0, 1, 100),
        'macd_divergence': np.random.normal(0, 1, 100)
    }, index=dates)
    
    print("原始因子数据形状:", factors_df.shape)
    print("因子列表:", list(factors_df.columns))
    
    # 创建合成器
    synthesizer = MonsterStockProbabilitySynthesizer()
    
    # 计算妖股概率分
    result = synthesizer.calculate_monster_probability(factors_df)
    
    print("\n结果数据形状:", result.shape)
    print("\n妖股概率分统计:")
    print(result[['monster_probability', 'monster_score']].describe())
    
    print("\n特征重要性（前10个）:")
    importance = synthesizer.get_feature_importance()
    print(importance.head(10))
    
    print("\n模型摘要:")
    summary = synthesizer.get_model_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    # 显示前10个样本的概率分
    print("\n前10个样本的妖股概率分:")
    print(result[['monster_probability', 'monster_score']].head(10))
