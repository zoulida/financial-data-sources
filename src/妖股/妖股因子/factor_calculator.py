"""
妖股因子计算器
==============

实现四个生命周期阶段的核心因子计算：
1. 潜伏期因子：资金潜伏、筹码松动
2. 启动期因子：涨停强度、量价爆破
3. 加速期因子：连板强度、情绪共振  
4. 分歧期因子：筹码博弈、技术背离
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class MonsterStockFactorCalculator:
    """妖股因子计算器"""
    
    def __init__(self):
        """初始化因子计算器"""
        self.factor_cache = {}
        
    def calculate_latent_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算潜伏期因子（T-20～T-2）
        
        Parameters:
        -----------
        df : pd.DataFrame
            包含OHLCV数据的DataFrame，索引为日期
            
        Returns:
        --------
        pd.DataFrame : 包含潜伏期因子的DataFrame
        """
        result = pd.DataFrame(index=df.index)
        
        # 1.1 资金潜伏因子
        # 龙虎榜净买占比（模拟数据）
        result['lh_net_buy_ratio'] = self._simulate_lh_net_buy_ratio(df)
        
        # 大单净流入5日斜率
        result['big_order_slope'] = self._calculate_big_order_slope(df)
        
        # 1.2 筹码松动因子
        # 股东户数环比增速（模拟数据）
        result['shareholder_growth'] = self._simulate_shareholder_growth(df)
        
        # 换手率20日移动均值分位
        result['turnover_percentile'] = self._calculate_turnover_percentile(df)
        
        return result
    
    def calculate_startup_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算启动期因子（T-1～T+0，首板）
        
        Parameters:
        -----------
        df : pd.DataFrame
            包含OHLCV数据的DataFrame，索引为日期
            
        Returns:
        --------
        pd.DataFrame : 包含启动期因子的DataFrame
        """
        result = pd.DataFrame(index=df.index)
        
        # 2.1 涨停强度因子
        # 封单额/流通市值（模拟数据）
        result['seal_ratio'] = self._simulate_seal_ratio(df)
        
        # 封板耗时
        result['seal_time'] = self._calculate_seal_time(df)
        
        # 2.2 量价爆破因子
        # 量比
        result['volume_ratio'] = self._calculate_volume_ratio(df)
        
        # 实体阳线占比
        result['yang_line_ratio'] = self._calculate_yang_line_ratio(df)
        
        return result
    
    def calculate_acceleration_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算加速期因子（T+1～T+N，连板）
        
        Parameters:
        -----------
        df : pd.DataFrame
            包含OHLCV数据的DataFrame，索引为日期
            
        Returns:
        --------
        pd.DataFrame : 包含加速期因子的DataFrame
        """
        result = pd.DataFrame(index=df.index)
        
        # 3.1 连板强度因子
        # 连板数
        result['consecutive_boards'] = self._calculate_consecutive_boards(df)
        
        # 隔日溢价
        result['next_day_premium'] = self._calculate_next_day_premium(df)
        
        # 3.2 情绪共振因子
        # 所属概念板块涨停数占比（模拟数据）
        result['concept_limit_up_ratio'] = self._simulate_concept_limit_up_ratio(df)
        
        # 全A涨停数（模拟数据）
        result['market_limit_up_count'] = self._simulate_market_limit_up_count(df)
        
        return result
    
    def calculate_divergence_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算分歧期因子（高位巨量断板）
        
        Parameters:
        -----------
        df : pd.DataFrame
            包含OHLCV数据的DataFrame，索引为日期
            
        Returns:
        --------
        pd.DataFrame : 包含分歧期因子的DataFrame
        """
        result = pd.DataFrame(index=df.index)
        
        # 4.1 筹码博弈因子
        # WINNER(C)浮动筹码（模拟数据）
        result['floating_chips'] = self._simulate_floating_chips(df)
        
        # 价格中枢偏离度
        result['price_deviation'] = self._calculate_price_deviation(df)
        
        # 4.2 技术背离因子
        # CCI突破+200后3日回落
        result['cci_divergence'] = self._calculate_cci_divergence(df)
        
        # MACD 15min顶背离信号
        result['macd_divergence'] = self._calculate_macd_divergence(df)
        
        return result
    
    def calculate_all_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有生命周期因子
        
        Parameters:
        -----------
        df : pd.DataFrame
            包含OHLCV数据的DataFrame，索引为日期
            
        Returns:
        --------
        pd.DataFrame : 包含所有因子的DataFrame
        """
        # 计算各阶段因子
        latent_factors = self.calculate_latent_factors(df)
        startup_factors = self.calculate_startup_factors(df)
        acceleration_factors = self.calculate_acceleration_factors(df)
        divergence_factors = self.calculate_divergence_factors(df)
        
        # 合并所有因子
        all_factors = pd.concat([
            latent_factors,
            startup_factors, 
            acceleration_factors,
            divergence_factors
        ], axis=1)
        
        return all_factors
    
    # ==================== 潜伏期因子实现 ====================
    
    def _simulate_lh_net_buy_ratio(self, df: pd.DataFrame) -> pd.Series:
        """模拟龙虎榜净买占比"""
        # 模拟数据：基于价格波动和成交量
        price_volatility = df['close'].pct_change().rolling(5).std()
        volume_ratio = df['volume'] / df['volume'].rolling(20).mean()
        
        # 生成模拟的龙虎榜净买占比（0-5%）
        base_ratio = np.random.normal(0.5, 0.3, len(df))
        volatility_factor = price_volatility.fillna(0) * 2
        volume_factor = np.clip(volume_ratio.fillna(1) - 1, 0, 2) * 0.5
        
        result = np.clip(base_ratio + volatility_factor + volume_factor, 0, 5) / 100
        return pd.Series(result, index=df.index)
    
    def _calculate_big_order_slope(self, df: pd.DataFrame) -> pd.Series:
        """计算大单净流入5日斜率"""
        # 模拟大单净流入数据
        big_order_flow = df['volume'] * df['close'] * np.random.normal(0.1, 0.05, len(df))
        
        slopes = []
        for i in range(len(df)):
            if i < 4:
                slopes.append(0)
            else:
                # 线性回归计算斜率
                x = np.arange(5)
                y = big_order_flow.iloc[i-4:i+1].values
                if len(y) == 5 and not np.isnan(y).any():
                    slope = np.polyfit(x, y, 1)[0]
                    slopes.append(slope)
                else:
                    slopes.append(0)
        
        return pd.Series(slopes, index=df.index)
    
    def _simulate_shareholder_growth(self, df: pd.DataFrame) -> pd.Series:
        """模拟股东户数环比增速"""
        # 基于价格和成交量变化模拟股东户数变化
        price_change = df['close'].pct_change().fillna(0)
        volume_change = df['volume'].pct_change().fillna(0)
        
        # 生成模拟的股东户数环比增速（-20%到30%）
        base_growth = np.random.normal(5, 8, len(df))
        price_factor = price_change * 10
        volume_factor = volume_change * 5
        
        result = np.clip(base_growth + price_factor + volume_factor, -20, 30)
        return pd.Series(result, index=df.index)
    
    def _calculate_turnover_percentile(self, df: pd.DataFrame) -> pd.Series:
        """计算换手率20日移动均值分位"""
        turnover_ma20 = df['turnover'].rolling(20).mean()
        
        percentiles = []
        for i in range(len(df)):
            if i < 250:
                percentiles.append(50)  # 默认中位数
            else:
                # 计算过去250日的分位数
                historical_data = turnover_ma20.iloc[i-250:i]
                current_value = turnover_ma20.iloc[i]
                
                if not pd.isna(current_value) and not historical_data.isna().all():
                    percentile = (historical_data <= current_value).sum() / len(historical_data) * 100
                    percentiles.append(percentile)
                else:
                    percentiles.append(50)
        
        return pd.Series(percentiles, index=df.index)
    
    # ==================== 启动期因子实现 ====================
    
    def _simulate_seal_ratio(self, df: pd.DataFrame) -> pd.Series:
        """模拟封单额/流通市值"""
        # 基于涨停概率和成交量模拟封单比例
        is_limit_up = (df['close'] >= df['close'].shift(1) * 1.1).astype(int)
        volume_factor = df['volume'] / df['volume'].rolling(20).mean()
        
        # 主板>5%，20cm板>3%
        base_ratio = np.where(is_limit_up, 
                             np.random.uniform(3, 8, len(df)),
                             np.random.uniform(0, 2, len(df)))
        
        volume_boost = np.clip(volume_factor.fillna(1) - 1, 0, 3) * 2
        result = np.clip(base_ratio + volume_boost, 0, 10) / 100
        
        return pd.Series(result, index=df.index)
    
    def _calculate_seal_time(self, df: pd.DataFrame) -> pd.Series:
        """计算封板耗时（分钟）"""
        # 模拟封板时间，基于开盘强度和成交量
        open_strength = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        volume_ratio = df['volume'] / df['volume'].rolling(20).mean()
        
        # 开盘越强，封板越快
        base_time = 60 - open_strength.fillna(0) * 200  # 基础时间60分钟
        volume_factor = np.clip(volume_ratio.fillna(1) - 1, 0, 2) * -20  # 放量加速封板
        
        result = np.clip(base_time + volume_factor, 5, 120)  # 5-120分钟
        return pd.Series(result, index=df.index)
    
    def _calculate_volume_ratio(self, df: pd.DataFrame) -> pd.Series:
        """计算量比"""
        volume_ma60 = df['volume'].rolling(60).mean()
        volume_ratio = df['volume'] / volume_ma60
        return volume_ratio.fillna(1)
    
    def _calculate_yang_line_ratio(self, df: pd.DataFrame) -> pd.Series:
        """计算实体阳线占比（近5日）"""
        is_yang = (df['close'] > df['open']).astype(int)
        yang_ratio = is_yang.rolling(5).mean() * 100
        return yang_ratio.fillna(50)
    
    # ==================== 加速期因子实现 ====================
    
    def _calculate_consecutive_boards(self, df: pd.DataFrame) -> pd.Series:
        """计算连板数"""
        is_limit_up = (df['close'] >= df['close'].shift(1) * 1.1).astype(int)
        
        consecutive = []
        current_count = 0
        
        for i in range(len(df)):
            if is_limit_up.iloc[i]:
                current_count += 1
            else:
                current_count = 0
            consecutive.append(current_count)
        
        return pd.Series(consecutive, index=df.index)
    
    def _calculate_next_day_premium(self, df: pd.DataFrame) -> pd.Series:
        """计算隔日溢价"""
        # 计算高开幅度
        gap_up = (df['open'] - df['close'].shift(1)) / df['close'].shift(1) * 100
        
        # 计算30分钟内是否回封（模拟数据）
        is_limit_up = (df['close'] >= df['close'].shift(1) * 1.1).astype(int)
        next_day_limit_up = is_limit_up.shift(-1)
        
        # 隔日溢价 = 高开幅度 * 是否回封
        premium = gap_up * next_day_limit_up.fillna(0)
        
        return premium.fillna(0)
    
    def _simulate_concept_limit_up_ratio(self, df: pd.DataFrame) -> pd.Series:
        """模拟所属概念板块涨停数占比"""
        # 基于市场热度和个股表现模拟概念板块热度
        market_heat = df['close'].pct_change().rolling(5).mean().fillna(0)
        individual_performance = df['close'].pct_change().fillna(0)
        
        # 生成模拟的概念板块涨停占比（0-50%）
        base_ratio = np.random.uniform(5, 15, len(df))
        heat_factor = np.abs(market_heat) * 20
        performance_factor = np.abs(individual_performance) * 10
        
        result = np.clip(base_ratio + heat_factor + performance_factor, 0, 50)
        return pd.Series(result, index=df.index)
    
    def _simulate_market_limit_up_count(self, df: pd.DataFrame) -> pd.Series:
        """模拟全A涨停数"""
        # 基于市场整体表现模拟涨停数量
        market_volatility = df['close'].pct_change().rolling(10).std().fillna(0)
        market_trend = df['close'].pct_change().rolling(5).mean().fillna(0)
        
        # 生成模拟的全A涨停数（50-500只）
        base_count = np.random.uniform(100, 200, len(df))
        volatility_factor = market_volatility * 1000
        trend_factor = np.abs(market_trend) * 200
        
        result = np.clip(base_count + volatility_factor + trend_factor, 50, 500)
        return pd.Series(result, index=df.index)
    
    # ==================== 分歧期因子实现 ====================
    
    def _simulate_floating_chips(self, df: pd.DataFrame) -> pd.Series:
        """模拟WINNER(C)浮动筹码"""
        # 基于价格位置和换手率模拟浮动筹码比例
        price_position = (df['close'] - df['close'].rolling(20).min()) / \
                       (df['close'].rolling(20).max() - df['close'].rolling(20).min())
        turnover_factor = df['turnover'].rolling(5).mean() / df['turnover'].rolling(20).mean()
        
        # 价格位置越高，换手越大，浮动筹码越多
        base_chips = price_position.fillna(0.5) * 50
        turnover_boost = np.clip(turnover_factor.fillna(1) - 1, 0, 2) * 20
        
        result = np.clip(base_chips + turnover_boost, 20, 90)
        return pd.Series(result, index=df.index)
    
    def _calculate_price_deviation(self, df: pd.DataFrame) -> pd.Series:
        """计算价格中枢偏离度"""
        ma13 = df['close'].rolling(13).mean()
        deviation = (df['close'] - ma13) / ma13 * 100
        return deviation.fillna(0)
    
    def _calculate_cci_divergence(self, df: pd.DataFrame) -> pd.Series:
        """计算CCI突破+200后3日回落"""
        # 计算CCI指标
        cci = self._calculate_cci(df, period=14)
        
        # 检测突破+200后3日回落
        cci_above_200 = (cci > 200).astype(int)
        cci_divergence = cci_above_200.rolling(4).apply(
            lambda x: 1 if x.iloc[0] == 1 and x.iloc[-1] == 0 and x.iloc[1:3].sum() >= 2 else 0,
            raw=False
        )
        
        return cci_divergence.fillna(0)
    
    def _calculate_macd_divergence(self, df: pd.DataFrame) -> pd.Series:
        """计算MACD 15min顶背离信号"""
        # 计算MACD指标
        macd_line, signal_line, histogram = self._calculate_macd(df)
        
        # 检测顶背离：价格创新高但MACD不创新高
        price_high = df['close'].rolling(5).max() == df['close']
        macd_high = macd_line.rolling(5).max() == macd_line
        
        # 背离信号：价格创新高但MACD未创新高
        divergence = (price_high & ~macd_high).astype(int)
        
        return divergence.fillna(0)
    
    # ==================== 技术指标辅助函数 ====================
    
    def _calculate_cci(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算CCI指标"""
        high = df['high']
        low = df['low'] 
        close = df['close']
        
        tp = (high + low + close) / 3
        ma_tp = tp.rolling(period).mean()
        mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())))
        
        cci = (tp - ma_tp) / (0.015 * mad)
        return cci.fillna(0)
    
    def _calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD指标"""
        close = df['close']
        
        ema_fast = close.ewm(span=fast).mean()
        ema_slow = close.ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram


# 使用示例
if __name__ == "__main__":
    # 创建示例数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    df = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(100) * 0.5),
        'high': 100 + np.cumsum(np.random.randn(100) * 0.5) + np.random.uniform(0, 2, 100),
        'low': 100 + np.cumsum(np.random.randn(100) * 0.5) - np.random.uniform(0, 2, 100),
        'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
        'volume': np.random.uniform(1000000, 10000000, 100),
        'turnover': np.random.uniform(1, 10, 100)
    }, index=dates)
    
    # 确保high >= low, high >= close, low <= close
    df['high'] = np.maximum(df['high'], np.maximum(df['open'], df['close']))
    df['low'] = np.minimum(df['low'], np.minimum(df['open'], df['close']))
    
    # 计算因子
    calculator = MonsterStockFactorCalculator()
    factors = calculator.calculate_all_factors(df)
    
    print("妖股因子计算完成！")
    print(f"因子数量: {len(factors.columns)}")
    print(f"数据长度: {len(factors)}")
    print("\n因子列表:")
    for i, col in enumerate(factors.columns, 1):
        print(f"{i:2d}. {col}")
    
    print("\n前5行数据:")
    print(factors.head())
