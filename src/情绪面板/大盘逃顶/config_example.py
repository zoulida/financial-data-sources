"""
配置文件示例
使用方法：
1. 复制此文件为 config.py
2. 填入你的实际配置信息
3. config.py 已在 .gitignore 中，不会被提交
"""

# XtQuant 配置
XTQUANT_CONFIG = {
    'token': 'your_xtquant_token_here',  # 在 http://dict.thinktrader.net 注册获取
    'use_xtquant': True  # 是否使用XtQuant，如果为False则使用备用数据源
}

# Wind API 配置
WIND_CONFIG = {
    'use_wind': True  # 是否使用Wind API，需要安装Wind终端
}

# 数据源优先级配置
DATA_SOURCE_PRIORITY = {
    'financing_balance': ['wind', 'eastmoney'],  # 融资余额: Wind → 东方财富
    'new_accounts': ['wind', 'akshare', 'chinaclear'],  # 开户数: Wind → akshare → 中国结算
    'volume_divergence': ['xtquant', 'akshare'],  # 量价背离: XtQuant → akshare
    'valuation': ['akshare']  # 估值百分位: akshare
}

# 评分规则配置（可调整）
SCORING_RULES = {
    'financing_balance': {
        'three_negative_days': 1.0,  # 3日全为负的得分
        'two_negative_days': 0.4     # 2日为负的得分
    },
    'new_accounts': {
        'threshold_decline': 30,  # 环比降幅阈值(%)
        'min_score': 0.0,
        'max_score': 1.0
    },
    'volume_divergence': {
        'lookback_days': 5,          # 回看天数
        'volume_shrink_threshold': 0.20,  # 成交量萎缩阈值(20%)
        'base_score': 1.0,           # 1日的基础分
        'additional_score': 0.5      # 每多1日的额外分
    },
    'valuation': {
        'lookback_years': 5,         # 估值百分位回看年数
        'high_threshold': 95,        # 高估值阈值(百分位)
        'low_threshold': 80,         # 低估值阈值(百分位)
        'max_score': 1.0
    }
}

# 逃顶信号阈值
ESCAPE_THRESHOLD = 2.2  # 总分超过此值发出强烈逃顶信号

# 图表配置
CHART_CONFIG = {
    'history_days': 90,  # 显示最近多少天的数据
    'figure_size': (14, 7),
    'dpi': 150,
    'warning_line_color': 'red',
    'score_line_color': '#1f77b4'
}

