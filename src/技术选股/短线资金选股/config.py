"""
短线资金进场选股 —— 参数配置
================================
所有阈值、权重、路径集中管理，便于调参。
"""

from pathlib import Path

# ── 项目路径 ──
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src 的上一级
OUTPUT_DIR = PROJECT_ROOT / "data" / "result"

# ── 股票池 ──
MAX_MARKET_CAP = 70.0   # 最大市值（亿元）
MIN_MARKET_CAP = 0.0    # 最小市值（亿元），0表示不限
MAX_PRICE = 50.0        # 最大股价（元）
MIN_PRICE = 2.0         # 最小股价（元）
KLINE_DAYS = 120        # 获取K线天数

# ── Wind 资金流向 ──
WIND_MFD_FIELDS = [
    "mfd_inflow_m",           # 主力净流入额
    "mfd_inflow_close_m",     # 尾盘主力净流入额
    "mfd_inflowrate_m",       # 主力净流入率（金额）
    "mfd_netbuyamt_a",        # 净主动买入额
]
WIND_MFD_LOOKBACK_DAYS = 5   # 资金流向回看天数
WIND_BATCH_SIZE = 50          # 每批Wind查询股票数
WIND_TIMEOUT = 60             # Wind Excel轮询超时（秒）

# ── 维度权重（总分100） ──
WEIGHT_CAPITAL_FLOW = 30      # 资金流向
WEIGHT_VOLUME_PRICE = 25      # 量价异动
WEIGHT_TECHNICAL = 20         # 技术形态
WEIGHT_CHIP = 15              # 筹码结构
WEIGHT_FUNDAMENTAL = 10       # 基本面安全垫

# ── 资金流向维度阈值 ──
# 近3日主力净流入累计（10分）—— 按排名分位打分
SCORE_MFD_3D_MAX = 10
# 今日尾盘主力净流入（8分）
SCORE_MFD_CLOSE_MAX = 8
# 主力净流入率（6分）
SCORE_MFD_RATE_MAX = 6
# 净主动买入额（6分）
SCORE_MFD_ACTIVE_MAX = 6

# ── 量价异动维度阈值 ──
# 量比
VOL_RATIO_LOW = 1.5           # 量比下限（加分起点）
VOL_RATIO_BEST = 2.5          # 量比最佳值
VOL_RATIO_HIGH = 4.0          # 量比过热阈值
SCORE_VOL_RATIO_MAX = 8

# 换手率加速
TURN_ACCEL_LOW = 1.2          # 换手率加速比下限
TURN_ACCEL_HIGH = 3.0         # 换手率加速比上限
SCORE_TURN_ACCEL_MAX = 6

# 成交额放大
AMT_RATIO_LOW = 1.5           # 成交额放大比下限
AMT_RATIO_HIGH = 5.0          # 成交额放大比上限
SCORE_AMT_RATIO_MAX = 5

# 量价配合
SCORE_VOL_PRICE_MAX = 6

# ── 技术形态维度阈值 ──
# 5日动量
MOMENTUM_5D_BEST_LOW = 0.0    # 最优动量区间下限
MOMENTUM_5D_BEST_HIGH = 0.10  # 最优动量区间上限
SCORE_MOMENTUM_MAX = 5

# 均线多头
SCORE_MA_MULTI_MAX = 5

# MACD状态
SCORE_MACD_MAX = 5

# 突破整理
SCORE_BREAKOUT_MAX = 5

# ── 筹码结构维度阈值 ──
# 缩量后放量
SCORE_SHRINK_EXPAND_MAX = 6

# 振幅收窄后突破
AMP_NARROW_RATIO = 0.5        # 近10日振幅 < 前30日振幅的50%
SCORE_AMP_BREAKOUT_MAX = 5

# 底部位置
POS_BEST_LOW = 0.2            # 最优底部位置区间下限
POS_BEST_HIGH = 0.5           # 最优底部位置区间上限
SCORE_POSITION_MAX = 4

# ── 基本面安全垫阈值 ──
# 市值区间
MCAP_BEST_LOW = 30.0          # 最优市值下限（亿）
MCAP_BEST_HIGH = 70.0         # 最优市值上限（亿）
MCAP_OK_LOW = 20.0            # 可接受市值下限（亿）
SCORE_MCAP_MAX = 4

# 流动性
MIN_AVG_AMOUNT_20D = 2000e4   # 20日日均成交额下限（2000万）
SCORE_LIQUIDITY_MAX = 3

# 非ST/非新股
MIN_LIST_DAYS = 60             # 最少上市天数
SCORE_SAFETY_MAX = 3

# ── 输出 ──
TOP_N = 30                     # 输出前N只
