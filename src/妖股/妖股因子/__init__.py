"""
妖股因子量化系统
================

将"妖股"拆解为可计算、可回测、可落地的数字指标。
通过四个生命周期阶段的核心因子，合成"妖股概率分"。

生命周期阶段：
1. 潜伏期（T-20～T-2）：资金潜伏、筹码松动
2. 启动期（T-1～T+0）：涨停强度、量价爆破  
3. 加速期（T+1～T+N）：连板强度、情绪共振
4. 分歧期（高位巨量断板）：筹码博弈、技术背离

作者：AI Assistant
版本：1.0.0
"""

from .factor_calculator import MonsterStockFactorCalculator
from .data_processor import DataProcessor
from .probability_synthesizer import MonsterStockProbabilitySynthesizer
from .data_fetcher import MonsterStockDataFetcher
from .backtester import MonsterStockBacktester

__version__ = "1.0.0"
__all__ = [
    "MonsterStockFactorCalculator",
    "DataProcessor", 
    "MonsterStockProbabilitySynthesizer",
    "MonsterStockDataFetcher",
    "MonsterStockBacktester"
]
