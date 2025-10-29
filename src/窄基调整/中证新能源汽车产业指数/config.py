#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 新纳入股票表现分析
"""

# XtQuant配置
XTQUANT_CONFIG = {
    'token': 'your_token_here',  # 请替换为你的XtQuant token
    'timeout': 30,  # 请求超时时间（秒）
}

# 分析参数配置
ANALYSIS_CONFIG = {
    'days_before': 5,  # 关键日期前观察天数
    'days_after': 5,   # 关键日期后观察天数
    'buffer_days': 10, # 数据获取的缓冲天数
}

# 输出文件配置
OUTPUT_CONFIG = {
    'detail_file': 'newly_included_performance_detail.csv',
    'cutoff_summary_file': 'newly_included_summary_cutoff_date.csv',
    'effective_summary_file': 'newly_included_summary_effective_date.csv',
    'overall_summary_file': 'newly_included_overall_summary.txt',
    'encoding': 'utf-8-sig',  # CSV文件编码
}

# 数据字段配置
DATA_FIELDS = {
    'market_data_fields': ['close', 'volume'],  # 需要获取的行情字段
    'analysis_fields': [  # 需要计算的指标
        'avg_daily_return',
        'cumulative_return', 
        'win_rate',
        'volume_change_rate',
        'max_daily_return',
        'min_daily_return',
        'volatility'
    ]
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',  # 日志级别：DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file': 'analysis.log',  # 日志文件名
}
