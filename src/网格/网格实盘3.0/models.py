"""
数据模型模块

集中定义所有数据结构，包括：
- GridSpec    : 网格规格参数
- PositionEntry : 单条仓位记录
- Trade       : 成交记录
- Order       : 订单模拟记录
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ============================================================
#  网格规格
# ============================================================
@dataclass
class GridSpec:
    """
    网格参数规格

    Attributes:
        baseline  : 基准价格（网格中心）
        step      : 网格步长（价格间距）
        up_grids  : 向上网格数量（layer_index 为负）
        down_grids: 向下网格数量（layer_index 为正）

    层级索引约定：
        - 0 = baseline 所在层级
        - 负数 = 价格高于 baseline
        - 正数 = 价格低于 baseline
        - min_level_index = -up_grids
        - max_level_index = +down_grids
    """
    baseline: float
    step: float
    up_grids: int
    down_grids: int

    @property
    def min_level_index(self) -> int:
        """最小层级索引（价格最高端）"""
        return -self.up_grids

    @property
    def max_level_index(self) -> int:
        """最大层级索引（价格最低端）"""
        return self.down_grids

    def level_price(self, level_index: int) -> float:
        """
        根据层级索引计算对应价格

        价格公式: baseline - level_index * step
        即 level_index=0 → baseline, level_index>0 → 更低价格
        """
        return round(self.baseline - level_index * self.step, 6)

    def is_in_range(self, level_index: int) -> bool:
        """判断层级索引是否在网格范围内"""
        return self.min_level_index <= level_index <= self.max_level_index


# ============================================================
#  仓位记录
# ============================================================
def generate_local_order_id() -> str:
    """
    生成本地订单号：格式为 LOC_{时间戳}_{随机4位}
    例如: LOC_20260331141500_A3F2
    """
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand_part = uuid.uuid4().hex[:4].upper()
    return f"LOC_{ts}_{rand_part}"


@dataclass
class PositionEntry:
    """
    单条仓位记录 —— 不合并同价仓位，用于与卖出配对

    字段说明：
        entry_id      : 本地唯一标识（下单前生成）
        level_index   : 网格层级
        buy_price     : 买入价格
        qty           : 买入数量
        buy_time      : 买入时间（YYYY-MM-DD HH:MM:SS）
        buy_date      : 买入日期（YYYY-MM-DD）
        buy_order_id  : 券商委托单号（下单成功后回填）
        buy_trade_id  : 券商成交单号（成交后回填）
        sell_order_id : 卖单券商单号
        sell_status   : 仓位状态 (pending/BuyFilled/hanging/filled/cancelled)
        sell_price    : 卖出挂单价格
        sell_level    : 卖出目标层级
        sell_local_id : 卖单本地订单号
    """
    # —— 基础信息 ——
    entry_id: str
    level_index: int
    buy_price: float
    qty: int
    buy_time: str
    buy_date: str
    buy_order_id: Optional[str] = None
    buy_trade_id: Optional[str] = None

    # —— 卖单状态 ——
    sell_order_id: Optional[str] = None
    sell_status: str = "pending"
    sell_price: Optional[float] = None
    sell_level: Optional[int] = None
    sell_local_id: Optional[str] = None

    # ------------------------------------------------------------------
    #  序列化 / 反序列化
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """转换为字典，用于 CSV 保存"""
        return {
            "entry_id": self.entry_id,
            "level_index": self.level_index,
            "buy_price": self.buy_price,
            "qty": self.qty,
            "buy_time": self.buy_time,
            "buy_date": self.buy_date,
            "buy_order_id": self.buy_order_id or "",
            "buy_trade_id": self.buy_trade_id or "",
            "sell_order_id": self.sell_order_id or "",
            "sell_status": self.sell_status,
            "sell_price": self.sell_price if self.sell_price is not None else "",
            "sell_level": self.sell_level if self.sell_level is not None else "",
            "sell_local_id": self.sell_local_id or "",
        }

    @classmethod
    def from_dict(cls, data: dict) -> PositionEntry:
        """从字典创建实例"""
        return cls(
            entry_id=data["entry_id"],
            level_index=int(data["level_index"]),
            buy_price=float(data["buy_price"]),
            qty=int(data["qty"]),
            buy_time=data["buy_time"],
            buy_date=data["buy_date"],
            buy_order_id=data.get("buy_order_id") or None,
            buy_trade_id=data.get("buy_trade_id") or None,
            sell_order_id=data.get("sell_order_id") or None,
            sell_status=data.get("sell_status", "pending"),
            sell_price=float(data["sell_price"]) if data.get("sell_price") else None,
            sell_level=int(data["sell_level"]) if data.get("sell_level") else None,
            sell_local_id=data.get("sell_local_id") or None,
        )


# ============================================================
#  成交记录（用于报告和模拟）
# ============================================================
@dataclass
class Trade:
    """一笔成交记录"""
    trade_id: int
    order_id: int
    ts: str            # 成交时间
    side: str          # "BUY" 或 "SELL"
    price: float
    qty: int
    level_index: int   # 所在网格层级


# ============================================================
#  模拟订单（仅用于 OrderSimulator）
# ============================================================
@dataclass
class SimOrder:
    """模拟订单（用于模拟撮合）"""
    order_id: int
    side: str          # "BUY" 或 "SELL"
    price: float
    qty: int
    level_index: int
    status: str = "pending"   # pending / filled / cancelled


# ============================================================
#  CSV 字段名常量
# ============================================================
POSITION_CSV_FIELDS = [
    "entry_id", "level_index", "buy_price", "qty",
    "buy_time", "buy_date", "buy_order_id", "buy_trade_id",
    "sell_order_id", "sell_status", "sell_price", "sell_level", "sell_local_id",
]
