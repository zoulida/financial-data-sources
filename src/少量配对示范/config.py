#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XtQuant 比价监控脚本配置文件
"""

# XtQuant Token 配置（不需要Token，设为None）
XTQUANT_TOKEN = None

# 监控对子配置
PAIRS_CONFIG = {
    # 指数对子
    "000300.SH/000852.SH": {"threshold": 2.0, "type": "index"},
    "000016.SH/399303.SZ": {"threshold": 2.0, "type": "index"},
    
    # ETF vs 指数
    "510500.SH/000905.SH": {"threshold": 2.0, "type": "etf_index"},
    "510300.SH/000300.SH": {"threshold": 2.0, "type": "etf_index"},
    
    # ETF vs 期货
    "518880.SH/AU0": {"threshold": 1.5, "type": "etf_futures"},
    "518800.SH/AG0": {"threshold": 1.5, "type": "etf_futures"},
    
    # 期货跨期
    "CU0/CU1": {"threshold": 2.0, "type": "futures_spread"},
    "AL0/AL1": {"threshold": 2.0, "type": "futures_spread"},
    
    # ETF vs 现货篮（需要持仓数据）
    "510300.SH/300现货篮": {"threshold": 1.5, "type": "etf_basket"},
    "159949.SZ/创50现货篮": {"threshold": 1.5, "type": "etf_basket"},
    "512880.SH/券商现货篮": {"threshold": 1.5, "type": "etf_basket"},
}

# 数据获取配置
DATA_CONFIG = {
    "start_date": "20150101",  # 数据开始日期
    "end_date": None,          # 数据结束日期，None表示获取到最新
    "min_data_points": 40,     # 最少数据点数
    "retry_times": 3,          # 重试次数
    "retry_delay": 2,          # 重试延迟（秒）
}

# 统计计算配置
STATS_CONFIG = {
    "z_score_window": 40,      # Z-score计算窗口
    "min_half_life_data": 10,  # 半衰期计算最少数据点
}

# 输出配置
OUTPUT_CONFIG = {
    "csv_filename": "ratio_monitor_xtdata.csv",
    "log_filename": "ratio_monitor_xtdata.log",
    "log_level": "INFO",       # 日志级别：DEBUG, INFO, WARNING, ERROR
}

# 警告配置
ALERT_CONFIG = {
    "enable_terminal_alert": True,    # 启用终端警告
    "enable_log_alert": True,         # 启用日志警告
    "alert_colors": True,             # 启用彩色输出
}

# 对子类型说明
PAIR_TYPES = {
    "index": "指数 vs 指数",
    "etf_index": "ETF vs 指数", 
    "etf_futures": "ETF vs 期货",
    "futures_spread": "期货主力 vs 次主力",
    "etf_basket": "ETF vs 现货篮"
}

