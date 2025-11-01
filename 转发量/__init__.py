"""
转发量统计模块
整合百度、搜狗、微博三大平台的数据获取功能
"""

from .baidu_search import BaiduSearchCounter, baidu_hour_cnt
from .sogou_search import SogouSearchCounter, sogou_hour_cnt
from .weibo_stats import WeiboStatsCounter, weibo_30min_stat, is_high_heat
from .main import RepostMonitor, quick_check, batch_check

__version__ = "1.0.0"
__author__ = "Data Source Team"

__all__ = [
    'BaiduSearchCounter',
    'baidu_hour_cnt',
    'SogouSearchCounter', 
    'sogou_hour_cnt',
    'WeiboStatsCounter',
    'weibo_30min_stat',
    'is_high_heat',
    'RepostMonitor',
    'quick_check',
    'batch_check'
]
