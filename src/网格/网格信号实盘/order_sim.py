from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

Side = Literal["BUY", "SELL"]


_order_id_counter = 0
_trade_id_counter = 0


def _next_order_id() -> int:
    global _order_id_counter
    _order_id_counter += 1
    return _order_id_counter


def _next_trade_id() -> int:
    global _trade_id_counter
    _trade_id_counter += 1
    return _trade_id_counter


@dataclass
class Order:
    order_id: int
    level_index: int
    side: Side
    qty: int


@dataclass
class Trade:
    trade_id: int
    order_id: int
    ts: str
    side: Side
    price: float
    qty: int
    level_index: int


@dataclass
class OrderSimulator:
    """
    简单挂单簿：仅在指定level触发即成。
    用于覆盖"默认规则"优先级：若有挂单先成交挂单，否则按持仓规则执行。
    """
    pending: Dict[int, Order] = field(default_factory=dict)  # key: level_index
    trades: List[Trade] = field(default_factory=list)

    def place(self, level_index: int, side: Side, qty: int) -> None:
        if qty <= 0:
            return
        self.pending[level_index] = Order(order_id=_next_order_id(), level_index=level_index, side=side, qty=qty)

    def cancel(self, level_index: int) -> None:
        self.pending.pop(level_index, None)

    def has_order(self, level_index: int, side: Optional[Side] = None) -> bool:
        ord_obj = self.pending.get(level_index)
        if not ord_obj:
            return False
        return side is None or ord_obj.side == side

    def match_if_any(self, level_index: int, ts: str, price: float) -> Optional[Trade]:
        """若该层级存在挂单则立即生成成交记录并返回，否则返回None。
        不校验价格条件（由上层逻辑负责），成交后从pending移除并写入trades。"""
        ord_obj = self.pending.pop(level_index, None)
        if not ord_obj:
            return None
        tr = Trade(
            trade_id=_next_trade_id(),
            order_id=ord_obj.order_id,
            ts=ts,
            side=ord_obj.side,
            price=price,
            qty=ord_obj.qty,
            level_index=level_index
        )
        self.trades.append(tr)
        return tr


