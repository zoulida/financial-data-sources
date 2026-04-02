"""
网格策略 —— 核心决策 + 买单逻辑 Mixin

职责：
- _handle_level_event：核心决策主流程
- 买单相关：确保下方网格有买单、当前网格挂买单、执行买单
"""
from __future__ import annotations

import traceback
from datetime import datetime
from typing import List, Optional

from .config import DefaultParams, OrderConst, PositionStatus


class DecisionMixin:
    """
    核心决策 + 买单逻辑

    依赖主类提供：
        self.engine, self.spec, self.manager, self.pos_book,
        self.order_mgr, self.write_log, self._order_placer,
        self._simulate_mode, self._get_broker_data,
        self._get_current_price_grid, self._check_positions_on_tick,
        self._create_emergency_sell_order, self.hand_size
    """

    # ==============================================================
    #  层级事件处理（核心决策）
    # ==============================================================
    def _handle_level_event(self, level_index: int, current_price: float) -> None:
        """
        处理网格层级事件 —— 核心买卖决策

        步骤：
            1. 获取券商数据（统一查询一次）
            2. 补全缺失的 buy_order_id（为后续状态同步做准备）
            3. 同步仓位状态（买单/卖单成交确认 + 挂卖单）
            4. 同步本地挂单标记（清理过时的防重复标记）
            5. 获取当前价格网格
            6. 确保当前价格以下 4 个网格有买单
            7. 当前网格有未成交订单 → 等待
            8. 当前网格无仓位且上一网格无仓位 → 挂买单
        """
        assert self.engine and self.spec
        stock_code = self.manager.stock_code if self.manager else ""

        # ── 1. 获取券商数据（全函数只查一次） ──
        broker, unfilled_orders, all_orders = self._get_broker_data()

        # ── 2. 补全缺失的 buy_order_id ──
        # 买单下了但本地没记住券商订单号，从未成交列表按价格匹配回填
        # 必须在步骤3之前执行，否则 sync_buy_order_status 无法匹配订单
        if unfilled_orders:
            self.order_mgr.fill_missing_buy_order_ids(unfilled_orders, stock_code)

        # ── 3. 同步仓位状态（买单/卖单成交确认 + 挂卖单） ──
        self._check_positions_on_tick(all_orders)

        # ── 4. 同步本地挂单标记（清理过时的防重复标记） ──
        self.order_mgr.sync_local_pending_with_broker(unfilled_orders, stock_code)

        # ── 5. 获取当前价格网格 ──
        current_level = self._get_current_price_grid(current_price)
        if current_level is None:
            return

        # ── 6. 确保当前价格以下 4 个网格有买单 ──
        self._ensure_buy_orders_below(current_level, unfilled_orders, stock_code)

        # ── 7. 当前网格有未成交订单 → 等待 ──
        if self.order_mgr.has_pending(current_level, "BUY") or self.order_mgr.has_pending(current_level, "SELL"):
            self.write_log(f"当前价格网格 {current_level} 已有未成交订单，等待")
            return

        # ── 8. 当前网格无仓位且上一网格无仓位 → 挂买单 ──
        self._place_buy_order_if_empty(current_level, unfilled_orders, stock_code)

    # ==============================================================
    #  买单逻辑
    # ==============================================================
    def _ensure_buy_orders_below(self, current_level: int, unfilled_orders: List[dict], stock_code: str) -> None:
        """
        确保当前价格以下 N 个网格有买单（不含当前网格）

        对空网格挂买单，已有订单则跳过。
        """
        if not self.spec:
            return
        qty = self.qty_per_fill
        low = max(self.spec.min_level_index, current_level - OrderConst.BUY_GRIDS_BELOW)

        for i in range(low, current_level):
            # ── 仓位簿去重：该层级已有未完成仓位（pending/BuyFilled/hanging/cancelled）→ 跳过 ──
            if self.pos_book.get_total_qty_by_level(i) > 0:
                continue

            has_local = self.order_mgr.has_pending(i, "BUY")
            has_real_buy = self.order_mgr.has_real_buy_order_at_level(i, self.spec, unfilled_orders, stock_code)
            has_real_sell_above = self.order_mgr.has_real_sell_order_at_level(i + 1, self.spec, unfilled_orders, stock_code)

            if not has_local and not has_real_buy and not has_real_sell_above:
                if self._can_place_buy_order(qty):
                    grid_price = self.spec.level_price(i)
                    self._place_buy(i, qty, grid_price)
                    self.write_log(f"低4格挂买单: 层级{i} | 价格{grid_price:.6f} | 数量{qty}")

    def _place_buy_order_if_empty(self, current_level: int, unfilled_orders: List[dict], stock_code: str) -> None:
        """
        若当前网格和上一网格均无仓位/挂单/卖单 → 挂买单
        """
        if not self.spec:
            return
        qty = self.qty_per_fill

        current_qty = self.pos_book.get_total_qty_by_level(current_level)
        higher_qty = self.pos_book.get_total_qty_by_level(current_level + 1)

        if current_qty > 0 or higher_qty > 0:
            return

        if self.order_mgr.has_pending(current_level, "BUY"):
            return
        if self.order_mgr.has_real_buy_order_at_level(current_level, self.spec, unfilled_orders, stock_code):
            return
        if self.order_mgr.has_real_sell_order_at_level(current_level + 1, self.spec, unfilled_orders, stock_code):
            return

        grid_price = self.spec.level_price(current_level)
        if self._can_place_buy_order(qty):
            self._place_buy(current_level, qty, grid_price)
            self.write_log(f"当前网格挂买单: 层级{current_level} | 价格{grid_price:.6f} | 数量{qty}")

    def _can_place_buy_order(self, qty: int) -> bool:
        """
        检查是否可以下买单（最大持仓 + 资金检查）
        """
        total_position = self.pos_book.total_unfilled_qty()
        if total_position + qty > DefaultParams.MAX_POSITION:
            print(f"[错误] 超过最大持仓: 当前{total_position}股, 欲买{qty}股, 最大{DefaultParams.MAX_POSITION}股")
            return False
        return True

    def place_buy_order(self, level_index: int, qty: int, price: float, max_position: int = 0) -> bool:
        """
        买入下单（带券商可用仓位检查 + 应急卖单触发）

        Args:
            max_position: 当券商可用仓位超过此值时停止买入（0=不限制）
        """
        # 检查券商真实仓位
        if max_position > 0 and self.manager and hasattr(self.manager, "broker") and self.manager.broker.is_connected:
            real_qty = self.manager.broker.get_available_qty()
            if real_qty > max_position:
                self._max_position_trigger_count += 1
                print(f"[错误] 券商可用仓位{real_qty}超过阈值{max_position}，停止买入 (触发{self._max_position_trigger_count}/50)")
                if self._max_position_trigger_count >= OrderConst.EMERGENCY_TRIGGER_COUNT:
                    self._create_emergency_sell_order()
                    self._max_position_trigger_count = 0
                return False
            else:
                if self._max_position_trigger_count > 0:
                    self._max_position_trigger_count = 0

        self._place_buy(level_index, qty, price)
        return True

    def _place_buy(self, level_index: int, qty: int, price: float) -> None:
        """
        执行买单下单

        流程：
            1. 涨跌停检查
            2. 去重检查
            3. pending 记录去重
            4. 生成 entry_id 并预写入仓位
            5. 标记本地挂单
            6. 调用 order_placer（实盘）
        """
        if self._simulate_mode:
            # 模拟模式：仅标记本地挂单
            self.order_mgr.mark_pending(level_index, "BUY", qty, price)
            return

        # ── 涨跌停检查 ──
        if not self.order_mgr.check_price_limit(price, "BUY", level_index):
            return

        # ── 去重 ──
        if self.order_mgr.is_duplicate_order("BUY", price):
            return

        # ── 同一层级已有未完成仓位（pending/BuyFilled/hanging/cancelled）→ 跳过 ──
        if self.pos_book.get_total_qty_by_level(level_index) > 0:
            self.write_log(f"[去重] 层级{level_index}已有仓位，跳过")
            return
        if self.order_mgr.has_pending_buy_at_level(level_index):
            self.write_log(f"[去重] 层级{level_index}已有pending记录，跳过")
            return

        # ── 生成 entry_id，预写入仓位 ──
        entry_id = self.order_mgr.generate_entry_id()
        buy_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = self.pos_book.add_buy(level_index, price, qty, buy_time, None, None)
        entry.entry_id = entry_id
        self.pos_book.save_to_csv()
        self.write_log(f"[预下单] 买单已写入position: entry_id={entry_id} | 层级={level_index} | 价格={price:.6f}")

        # ── 标记本地挂单 ──
        self.order_mgr.mark_pending(level_index, "BUY", qty, price)
        self.order_mgr.record_order_history("BUY", price)

        # ── 调用真实下单 ──
        if self._order_placer is not None:
            self._order_placer(level_index, "BUY", qty, price, entry_id)
