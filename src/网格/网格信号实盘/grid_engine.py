from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class GridSpec:
    baseline: float
    step: float
    up_grids: int
    down_grids: int

    @property
    def min_level_index(self) -> int:
        return -self.down_grids

    @property
    def max_level_index(self) -> int:
        return self.up_grids

    def level_price(self, level_index: int) -> float:
        return round(self.baseline + level_index * self.step, 6)

    def levels(self) -> List[float]:
        return [self.level_price(i) for i in range(self.min_level_index, self.max_level_index + 1)]


class GridEngine:
    """
    网格引擎：负责网格生成、价位跨越检测、越界停止/恢复。
    """

    def __init__(self, spec: GridSpec):
        self.spec = spec
        self._levels: List[float] = spec.levels()
        self._min_price = self._levels[0]
        self._max_price = self._levels[-1]
        self.halted: bool = False
        self._last_price: Optional[float] = None

    @property
    def levels(self) -> List[float]:
        return self._levels

    def bounds(self) -> Tuple[float, float]:
        return self._min_price, self._max_price

    def price_to_level_index(self, price: float) -> Optional[int]:
        """
        将价格映射到最接近的网格索引（当价格恰好等于某网格价位时返回该索引；否则返回 None）。
        """
        if price is None:
            return None
        step = self.spec.step
        # 判断是否与某个网格价位几乎相等（浮点容差）
        nearest_idx_float = (price - self.spec.baseline) / step
        nearest_idx = int(round(nearest_idx_float))
        px_at_idx = self.spec.level_price(nearest_idx)
        if abs(px_at_idx - price) <= max(step, 1e-6) * 1e-6:
            if self.spec.min_level_index <= nearest_idx <= self.spec.max_level_index:
                return nearest_idx
        return None

    def update_and_get_crossed_levels(self, current_price: float) -> List[int]:
        """
        根据上一个价格与当前价格，返回“跨越或到达”的网格索引列表（按穿越方向排序）。
        仅当价格在网格区间内时产生事件；越界时会设置 halted 并返回空列表。
        """
        if current_price is None:
            return []
        # 越界检查
        if current_price < self._min_price or current_price > self._max_price:
            self.halted = True
            self._last_price = current_price
            return []

        # 若之前越界，现在回到区间内，则恢复
        if self.halted and (self._min_price <= current_price <= self._max_price):
            self.halted = False

        crossed: List[int] = []
        if self._last_price is None:
            # 首次价格设置，不触发事件
            self._last_price = current_price
            return crossed

        last_price = self._last_price
        self._last_price = current_price

        # 同价或未跨越
        if current_price == last_price:
            idx = self.price_to_level_index(current_price)
            if idx is not None:
                crossed.append(idx)
            return crossed

        # 计算跨越的网格索引
        step = self.spec.step
        # 找到两端对应的近似索引（可能不正好在网格上）
        start_float = (last_price - self.spec.baseline) / step
        end_float = (current_price - self.spec.baseline) / step
        start_idx = int(round(start_float))
        end_idx = int(round(end_float))

        # 为了保证完整跨越，按方向生成索引范围
        if current_price > last_price:
            # 上行，包含所有从较小到较大且在边界内的网格
            rng = range(max(self.spec.min_level_index, min(start_idx, end_idx)),
                        min(self.spec.max_level_index, max(start_idx, end_idx)) + 1)
        else:
            # 下行
            rng = range(min(self.spec.max_level_index, max(start_idx, end_idx)),
                        max(self.spec.min_level_index, min(start_idx, end_idx)) - 1, -1)

        # 仅保留确实被跨越或到达的网格：价格区间包含该网格价格
        lo, hi = (last_price, current_price) if last_price < current_price else (current_price, last_price)
        for idx in rng:
            px = self.spec.level_price(idx)
            if lo <= px <= hi:
                crossed.append(idx)

        return crossed


