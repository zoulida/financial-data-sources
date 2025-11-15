from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Position:
    qty: int = 0
    avg_cost: float = 0.0

    def add(self, price: float, qty: int) -> None:
        if qty <= 0:
            return
        new_total_qty = self.qty + qty
        if new_total_qty <= 0:
            self.qty = 0
            self.avg_cost = 0.0
            return
        self.avg_cost = (self.avg_cost * self.qty + price * qty) / new_total_qty if self.qty > 0 else price
        self.qty = new_total_qty

    def reduce(self, qty: int) -> None:
        self.qty = max(0, self.qty - qty)
        if self.qty == 0:
            self.avg_cost = 0.0


@dataclass
class PositionBook:
    """
    按网格价位维护仓位（每格仅0或固定手数）。
    """
    level_index_to_pos: Dict[int, Position] = field(default_factory=dict)

    def get(self, level_index: int) -> Position:
        if level_index not in self.level_index_to_pos:
            self.level_index_to_pos[level_index] = Position()
        return self.level_index_to_pos[level_index]

    def set_holding(self, level_index: int, price: float, qty: int) -> None:
        pos = self.get(level_index)
        if qty > 0:
            pos.add(price, qty)
        elif qty == 0:
            pos.qty = 0
            pos.avg_cost = 0.0

    def buy_at_level(self, level_index: int, price: float, qty: int) -> None:
        self.get(level_index).add(price, qty)

    def sell_at_level(self, level_index: int, qty: int) -> float:
        pos = self.get(level_index)
        realized_qty = min(qty, pos.qty)
        pos.reduce(realized_qty)
        return float(realized_qty)

    def snapshot(self) -> List[Tuple[int, int, float]]:
        """
        返回 (level_index, qty, avg_cost) 列表，按level排序。
        """
        items = [(idx, p.qty, p.avg_cost) for idx, p in self.level_index_to_pos.items()]
        items.sort(key=lambda x: x[0])
        return items


