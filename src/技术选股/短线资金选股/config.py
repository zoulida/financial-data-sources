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
    "mfd_netbuyamt",           # 主力净流入额
    "mfd_inflowproportion_a",  # 净流入额占成交额比
    "mfd_inflowrate_close_m",  # 尾盘净流入率（金额）
    "mfd_inflow_m",            # 主力净流入额
]
WIND_MFD_LOOKBACK_DAYS = 20   # Wind 资金流向回看天数（用于下载缓存，覆盖14日打分窗口）
WIND_BATCH_SIZE = 25          # 每批Wind查询股票数
WIND_TIMEOUT = 60             # Wind Excel轮询超时（秒）

# ── 14日波段资金维度阈值 ──
FLOW_LOOKBACK_DAYS = 14              # 波段资金主观察窗口
FLOW_RECENT_WINDOW = 5               # 最近加速窗口
FLOW_BAD_DAY_THRESHOLD = -0.02       # 单日净流入 / 成交额 低于该值视为坏流出日
FLOW_PREBREAK_RET_LOW = -0.02        # 14日涨幅低于该值，视为仍偏弱
FLOW_PREBREAK_RET_HIGH = 0.08        # 14日涨幅高于该值，视为已开始明显拉升
SCORE_FLOW_14D_MAX = 12              # 14日累计净流入强度
SCORE_FLOW_ACCEL_MAX = 8             # 近5日相对前9日改善
SCORE_FLOW_STABILITY_MAX = 5         # 坏流出天数控制
SCORE_FLOW_PREBREAK_MAX = 5          # 资金介入但仍处预启动区

# ── 维度权重（总分90） ──
WEIGHT_CAPITAL_FLOW = 30      # 资金流向
WEIGHT_VOLUME_PRICE = 25      # 量价异动
WEIGHT_TECHNICAL = 20         # 技术形态
WEIGHT_CHIP = 15              # 筹码结构

# ── 量价异动维度阈值 ──
VOL_SURGE_LOW = 1.05                # 近5日均量相对前20日均量的加分起点
VOL_SURGE_BEST = 1.45               # 最佳温和放量区
VOL_SURGE_HIGH = 2.20               # 过热量能上限
SCORE_VOL_SURGE_MAX = 10

AMOUNT_STABILITY_LOW = 1.00         # 近10日成交额相对前20日开始抬升
AMOUNT_STABILITY_HIGH = 1.60        # 成交额稳定放大的上限
SCORE_AMOUNT_STABILITY_MAX = 8

SCORE_PULLBACK_VOLUME_MAX = 6       # 回踩缩量

# ── 技术形态维度阈值 ──
MA_DISTANCE_LOW = 0.00              # 10日线略强于20日线即可
MA_DISTANCE_HIGH = 0.06             # 过度乖离不追
SCORE_MA_TREND_MAX = 8
SCORE_MACD_MAX = 6
SCORE_PLATFORM_MAX = 6

# ── 筹码结构维度阈值 ──
SHRINK_RATIO_THRESHOLD = 0.75       # 近5日均量 / 前20日均量，越低越好
SCORE_SHRINK_EXPAND_MAX = 5

AMP_NARROW_RATIO = 0.55             # 近10日振幅 / 前30日振幅，越低说明越收敛
SCORE_AMP_NARROW_MAX = 5

POS_BEST_LOW = 0.20                 # 最优位置区间下限
POS_BEST_HIGH = 0.55                # 最优位置区间上限
SCORE_POSITION_MAX = 5

# ── 基本面安全垫阈值 ──
MCAP_BEST_LOW = 30.0          # 最优市值下限（亿）
MCAP_BEST_HIGH = 70.0         # 最优市值上限（亿）
MCAP_OK_LOW = 20.0            # 可接受市值下限（亿）
SCORE_MCAP_MAX = 4

MIN_AVG_AMOUNT_20D = 2000e4   # 20日日均成交额下限（2000万）
SCORE_LIQUIDITY_MAX = 3

MIN_LIST_DAYS = 60            # 最少上市天数
SCORE_SAFETY_MAX = 3

# ── 输出 ──
TOP_N = 30                    # 输出前N只
