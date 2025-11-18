"""
配置文件示例
============

复制此文件为 config.py 并修改为实际配置。
"""

# 交易账号配置
ACCOUNT_ID = "8886063599"  # 您的账号
ACCOUNT_TYPE = "STOCK"  # 账号类型：STOCK/CREDIT/FUTURES
QMT_PATH = r"D:\国金证券QMT交易端\userdata_mini"  # QMT 客户端路径

# 策略参数
STOCK_CODE = "159100.SZ"  # 目标股票代码
BUY_VOLUME = 100  # 买入数量（1手=100股）

# Broker 参数
COMMISSION = 0.0003  # 佣金费率（0.03%）
SLIPPAGE = 0.0  # 滑点

# 数据参数
DATA_COUNT = 100  # 获取历史数据的数量（天数）

