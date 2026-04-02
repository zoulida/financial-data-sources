"""
配置常量模块

集中管理所有配置参数、默认值和状态码映射，
避免魔法数字散落在各处，提升可维护性。
"""
from __future__ import annotations


# ============================================================
#  券商订单状态码 (QMT)
# ============================================================
class OrderStatus:
    """券商订单状态码常量"""
    NOT_REPORTED    = 48   # 未报
    PENDING_REPORT  = 49   # 待报
    REPORTED        = 50   # 已报
    REPORTED_CANCEL = 51   # 已报待撤
    PARTIAL_CANCEL  = 52   # 部成待撤
    PART_CANCELLED  = 53   # 部撤
    CANCELLED       = 54   # 已撤
    PARTIAL_FILLED  = 55   # 部成
    FILLED          = 56   # 已成
    REJECTED        = 57   # 废单
    UNKNOWN         = 255  # 未知

    # 状态码 → 中文描述
    DESC_MAP = {
        48: "未报", 49: "待报", 50: "已报", 51: "已报待撤",
        52: "部成待撤", 53: "部撤", 54: "已撤", 55: "部成",
        56: "已成", 57: "废单", 255: "未知",
    }

    @classmethod
    def describe(cls, code: int) -> str:
        """根据状态码获取中文描述"""
        return cls.DESC_MAP.get(code, f"未知状态({code})")


# ============================================================
#  券商订单类型码 (QMT)
# ============================================================
class OrderType:
    """券商订单类型码常量"""
    BUY       = 23   # 买入
    SELL      = 24   # 卖出
    BUY_OPEN  = 33   # 买入开仓
    SELL_CLOSE = 34  # 卖出平仓


# ============================================================
#  仓位状态 (sell_status 字段)
# ============================================================
class PositionStatus:
    """
    仓位状态流转:
        BuySubmit → pending → BuyFilled → hanging → filled
                                                  ↘ cancelled → hanging (重新挂)

        BuySubmit : 本地已发出买单请求，尚未确认券商是否接受
        pending   : 券商已确认挂单（在未成交列表中可查到）
        BuyFilled : 买单已成交，等待挂卖单
        hanging   : 卖单已挂出，等待成交
        filled    : 卖单已成交，一轮交易完成 → 随后清理删除
        cancelled : 卖单被撤销 → 重新挂卖单
    """
    BUY_SUBMIT  = "BuySubmit"    # 本地已发出买单，尚未确认券商挂单成功
    PENDING     = "pending"      # 券商已确认挂单，等待成交
    BUY_FILLED  = "BuyFilled"    # 买单已成交，等待挂卖单
    HANGING     = "hanging"      # 卖单已挂出
    FILLED      = "filled"       # 卖单已成交（完成一轮交易）
    CANCELLED   = "cancelled"    # 卖单已撤销，需重新挂


# ============================================================
#  默认策略参数
# ============================================================
class DefaultParams:
    """策略默认参数"""
    STEP           = 0.001    # 网格步长
    UP_GRIDS       = 10       # 向上网格数量
    DOWN_GRIDS     = 20       # 向下网格数量
    LOT_PER_GRID   = 1        # 每格手数
    HAND_SIZE      = 100      # 每手股数
    MAX_POSITION   = 10000    # 最大持仓股数
    PRICE_DECIMALS = 3        # 价格保留小数位数
    PRICE_TOLERANCE = 0.0001  # 价格匹配容差


# ============================================================
#  订单相关常量
# ============================================================
class OrderConst:
    """订单相关常量"""
    STALE_PENDING_TIMEOUT = 60     # pending 无买单号条目超时秒数
    PENDING_CLEANUP_MINUTES = 30   # 过期挂单清理时间（分钟）
    ORDER_TIMEOUT_SECONDS = 5      # 下单超时秒数
    BUY_GRIDS_BELOW = 4            # 当前价格网格以下挂买单的数量
    EMERGENCY_TRIGGER_COUNT = 50   # 应急卖单触发次数阈值


# ============================================================
#  QMT 交易器默认配置
# ============================================================
class BrokerConfig:
    """QMT 交易器默认配置"""
    DEFAULT_PATH = r"D:\国金证券QMT交易端\userdata_mini"
    DEFAULT_ACCOUNT = "8886063599"
    DEFAULT_ACCOUNT_TYPE = "STOCK"
