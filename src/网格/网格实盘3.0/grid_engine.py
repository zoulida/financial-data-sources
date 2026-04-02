"""
网格引擎模块

负责网格层级的管理，包括：
- 价格 ↔ 层级索引 的双向映射
- 价格跨越层级的检测
- 价格越界的检测与恢复
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .models import GridSpec


class GridEngine:
    """
    网格引擎 —— 管理网格层级、检测价格跨越和越界

    核心概念：
        - 每个层级 (level_index) 对应一个固定价格
        - 价格从低到高：level_index 从 min(-down_grids) 到 max(+up_grids)
        - 当价格跨越某个层级时，触发交易事件
        - 当价格超出网格范围时，进入 halted 状态
    """

    def __init__(self, spec: GridSpec) -> None:
        """
        初始化网格引擎

        Args:
            spec: 网格规格参数
        """
        self.spec = spec

        # 上一次记录的层级索引（用于检测跨越）
        self._last_level: Optional[int] = None

        # 越界暂停标志：True 表示价格已超出网格范围
        self.halted: bool = False

    # ------------------------------------------------------------------
    #  价格 ↔ 层级映射
    # ------------------------------------------------------------------
    def price_to_level_index(self, price: float) -> Optional[int]:
        """
        将价格映射到最近的网格层级索引

        计算方式: level_index = round((price - baseline) / step)
        然后限制在 [min_level_index, max_level_index] 范围内

        Args:
            price: 当前价格

        Returns:
            层级索引，如果价格无效则返回 None
        """
        if price <= 0 or self.spec.step <= 0:
            return None

        raw = (price - self.spec.baseline) / self.spec.step
        level = round(raw)

        # 限制在网格范围内
        level = max(self.spec.min_level_index, min(level, self.spec.max_level_index))
        return level

    def bounds(self) -> Tuple[float, float]:
        """
        获取网格价格边界

        Returns:
            (最低价格, 最高价格) 元组
        """
        low_price = self.spec.level_price(self.spec.min_level_index)
        high_price = self.spec.level_price(self.spec.max_level_index)
        return low_price, high_price

    # ------------------------------------------------------------------
    #  跨越 & 越界检测
    # ------------------------------------------------------------------
    def update_and_get_crossed_levels(self, price: float) -> List[int]:
        """
        更新价格并返回被跨越的层级列表

        如果价格从一个层级移动到另一个层级，返回中间所有被跨越的层级。
        同时处理越界检测：
            - 价格超出网格范围 → halted = True
            - 价格回到网格范围 → halted = False

        Args:
            price: 当前最新价格

        Returns:
            被跨越的层级索引列表（按时间顺序）
        """
        current_level = self.price_to_level_index(price)
        if current_level is None:
            return []

        # 越界检测
        low_px, high_px = self.bounds()
        if price < low_px or price > high_px:
            if not self.halted:
                self.halted = True
            return []
        else:
            if self.halted:
                # 价格回到范围内，恢复运行
                self.halted = False

        # 首次调用，记录初始层级
        if self._last_level is None:
            self._last_level = current_level
            return []

        # 无跨越
        if current_level == self._last_level:
            return []

        # 计算跨越的层级列表
        prev = self._last_level
        crossed: List[int] = []

        if current_level > prev:
            # 价格上涨：层级索引增大
            crossed = list(range(prev + 1, current_level + 1))
        else:
            # 价格下跌：层级索引减小
            crossed = list(range(prev - 1, current_level - 1, -1))

        self._last_level = current_level
        return crossed
