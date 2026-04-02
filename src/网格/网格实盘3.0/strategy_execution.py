"""
网格策略 —— 卖单逻辑 + 成交回调 + 仓位同步 Mixin

职责：
- 卖单下单与挂卖单管理
- 券商成交回调处理（买/卖）
- 每 Tick 仓位状态同步
"""
from __future__ import annotations

import traceback
from datetime import datetime
from typing import List, Optional

from .config import DefaultParams, OrderConst, PositionStatus


class ExecutionMixin:
    """
    卖单逻辑 + 成交回调 + 仓位同步

    依赖主类提供：
        self.engine, self.spec, self.manager, self.pos_book,
        self.order_mgr, self.write_log, self._order_placer,
        self._simulate_mode, self._get_broker_data,
        self.hand_size, self._log_removed_positions
    """

    # ==============================================================
    #  卖单逻辑
    # ==============================================================
    def place_sell_order(self, level_index: int, qty: int, price: float) -> None:
        """卖出下单"""
        if self._simulate_mode:
            self.order_mgr.mark_pending(level_index, "SELL", qty, price)
            return

        if not self.order_mgr.check_price_limit(price, "SELL", level_index):
            return

        self.order_mgr.mark_pending(level_index, "SELL", qty, price)
        self.order_mgr.record_order_history("SELL", price)

        if self._order_placer is not None:
            self._order_placer(level_index, "SELL", qty, price)

    def _place_sell_for_pending_positions(self) -> None:
        """
        为买单已成交的仓位挂卖单

        处理 BuyFilled + cancelled 状态的仓位，
        按买入价从高到低排序（优先挂高价卖单），
        检查券商可用仓位后下单。
        """
        entries_to_sell = self.pos_book.get_entries_needing_sell()
        if not entries_to_sell:
            return

        # 按买入价从高到低排序
        entries_to_sell.sort(key=lambda e: e.buy_price, reverse=True)

        # 获取券商可用仓位
        broker_available = 0
        if self.manager and hasattr(self.manager, "broker") and self.manager.broker.is_connected:
            broker_available = self.manager.broker.get_available_qty()

        for entry in entries_to_sell:
            if not self.spec:
                continue

            # 计算卖出价格和层级
            is_emergency = entry.sell_order_id and str(entry.sell_order_id).startswith("EMERGENCY_")
            if is_emergency and entry.sell_price is not None:
                sell_price = entry.sell_price
                sell_level = entry.sell_level or int(round((sell_price - self.spec.baseline) / self.spec.step))
            else:
                sell_price = round(entry.buy_price + self.spec.step, DefaultParams.PRICE_DECIMALS)
                sell_level = int(round((sell_price - self.spec.baseline) / self.spec.step))

            # ── 检查券商可用仓位 ──
            if broker_available < self.hand_size:
                self.write_log(f"跳过挂卖单: 券商可用仓位不足 | 仓位ID={entry.entry_id} | 可用{broker_available}")
                continue

            # ── 检查网格范围 ──
            if not self.spec.is_in_range(sell_level):
                self.write_log(f"跳过挂卖单: 层级{sell_level}超出范围 | 仓位ID={entry.entry_id}")
                continue

            # ── 计算实际可挂数量 ──
            actual_qty = min(entry.qty, broker_available)
            actual_qty = (actual_qty // self.hand_size) * self.hand_size
            if actual_qty < self.hand_size:
                continue

            # ── 挂卖单 ──
            order_id = self._execute_sell_for_entry(entry, sell_price, actual_qty)
            if order_id:
                self.pos_book.set_sell_order(entry.entry_id, order_id, sell_price, sell_level)
                if actual_qty < entry.qty:
                    entry.qty -= actual_qty
                    self.write_log(f"部分挂单: 仓位ID={entry.entry_id} | 挂单{actual_qty} | 剩余{entry.qty}")
                self.write_log(
                    f"挂卖单: 仓位ID={entry.entry_id} | 买入价={entry.buy_price:.6f} | "
                    f"卖出价={sell_price:.6f} | 数量={actual_qty} | 订单号={order_id}"
                )
                broker_available -= actual_qty

    def _execute_sell_for_entry(self, entry, sell_price: float, qty: int) -> Optional[str]:
        """为指定仓位执行卖单下单"""
        try:
            if self._simulate_mode:
                order_id = f"SIM_{int(datetime.now().timestamp() * 1_000_000) % 1_000_000_000}"
                sell_level = int(round((sell_price - self.spec.baseline) / self.spec.step)) if self.spec else 0
                self.order_mgr.mark_pending(sell_level, "SELL", qty, sell_price, order_id)
                return order_id

            if self.manager and hasattr(self.manager, "broker") and self.manager.broker.is_connected:
                remark = f"SELL_{entry.entry_id}" if entry.entry_id else ""
                order_id = self.manager.broker.sell_direct(qty, sell_price, remark)
                if order_id:
                    sell_level = int(round((sell_price - self.spec.baseline) / self.spec.step)) if self.spec else 0
                    self.order_mgr.mark_pending(sell_level, "SELL", qty, sell_price, order_id)
                return order_id
        except Exception as e:
            self.write_log(f"挂卖单失败: {e}")
        return None

    # ==============================================================
    #  成交回调
    # ==============================================================
    def on_order_placed(self, level_index: int, side: str, qty: int, price: float, order_id) -> None:
        """券商确认挂单成功回调"""
        self.order_mgr.update_pending_order_id(level_index, side, order_id)
        grid_px = self.spec.level_price(level_index) if self.spec else price
        self.write_log(
            f"挂单成功: {side} | 层级{level_index} | 网格价{grid_px:.6f} | "
            f"挂单价{price:.6f} | 数量{qty} | 订单{order_id}"
        )

    def on_order_filled(self, level_index: int, side: str, fill_price: float, qty: int,
                        trade_id: str = None, entry_id: str = None) -> None:
        """
        订单成交回调

        买入成交 → 更新仓位状态为 BuyFilled
        卖出成交 → 标记仓位为 filled
        """
        try:
            # 清除本地挂单状态
            detail = self.order_mgr.get_pending_detail(level_index, side)
            order_id = detail.get("order_id") if detail else None
            self.order_mgr.clear_pending(level_index, side)

            if side == "BUY":
                self._handle_buy_filled(level_index, fill_price, qty, order_id, trade_id, entry_id)
            else:
                self._handle_sell_filled(level_index, fill_price, qty, order_id, trade_id)

        except Exception as e:
            self.write_log(f"订单成交处理失败: {e}")
            traceback.print_exc()
            raise

    def _handle_buy_filled(self, level_index, fill_price, qty, order_id, trade_id, entry_id):
        """处理买单成交"""
        order_id_str = str(order_id) if order_id else None
        trade_id_str = str(trade_id) if trade_id else None

        entry = self.pos_book.get_entry_by_id(entry_id) if entry_id else None
        if entry:
            entry.buy_order_id = order_id_str
            entry.buy_trade_id = trade_id_str
            entry.sell_status = PositionStatus.BUY_FILLED
            self.write_log(f"买单成交: 层级{level_index} | 价格{fill_price:.6f} | 数量{qty} | 仓位ID:{entry.entry_id}")
        else:
            buy_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = self.pos_book.add_buy(level_index, fill_price, qty, buy_time, order_id_str, trade_id_str)
            entry.sell_status = PositionStatus.BUY_FILLED
            self.write_log(f"买单成交(新建): 层级{level_index} | 价格{fill_price:.6f} | 仓位ID:{entry.entry_id}")

        self.pos_book.save_to_csv()

    def _handle_sell_filled(self, level_index, fill_price, qty, order_id, trade_id):
        """处理卖单成交"""
        self._mark_position_sell_filled(level_index, qty)
        self.write_log(f"卖单成交: 层级{level_index} | 价格{fill_price:.6f} | 数量{qty}")
        self.pos_book.save_to_csv()

    def _mark_position_sell_filled(self, level_index: int, qty: int) -> None:
        """标记对应仓位的卖单已成交"""
        entries = [
            e for e in self.pos_book.entries
            if e.level_index == level_index and e.sell_status == PositionStatus.HANGING
        ]
        remaining = qty
        for entry in entries:
            if remaining <= 0:
                break
            if entry.qty <= remaining:
                self.pos_book.mark_sell_filled(entry.entry_id)
                remaining -= entry.qty
            else:
                entry.qty -= remaining
                remaining = 0

    # ==============================================================
    #  每 Tick 仓位检查
    # ==============================================================
    def _check_positions_on_tick(self, all_orders: List[dict]) -> None:
        """
        同步仓位状态并处理挂卖单

        由 _handle_level_event 调用，券商数据由调用方传入（避免重复查询）。

        步骤：
            1. 同步买单状态 (BuySubmit→pending→BuyFilled / 删除)
            2. 同步卖单状态 (hanging → filled / cancelled)
            3. 清理已成交仓位
            4. 检查非今日仓位
            5. 为 BuyFilled/cancelled 仓位挂卖单
        """
        try:
            # 1. 同步买单状态
            if all_orders:
                updated = self.order_mgr.sync_buy_order_status(all_orders)
                if updated:
                    self.pos_book.save_to_csv()

            # 2. 同步卖单状态
            if all_orders:
                updated = self.order_mgr.sync_sell_order_status(all_orders)
                if updated:
                    self.pos_book.save_to_csv()

            # 3. 清理已成交仓位
            removed = self.pos_book.remove_filled_entries()
            if removed:
                self._log_removed_positions(removed, "filled状态清理")
                self.pos_book.save_to_csv()

            # 4. 检查非今日仓位
            self._check_old_positions()

            # 5. 挂卖单
            self._place_sell_for_pending_positions()

        except Exception as e:
            self.write_log(f"tick仓位检查失败: {e}")

    def _check_old_positions(self) -> None:
        """检查非今日仓位，打印提示"""
        today = datetime.now().strftime("%Y-%m-%d")
        old_entries = self.pos_book.get_old_entries(today)
        for entry in old_entries:
            if entry.sell_status in (PositionStatus.BUY_SUBMIT, PositionStatus.PENDING, PositionStatus.BUY_FILLED):
                self.write_log(
                    f"发现非今日仓位: 仓位ID={entry.entry_id} | "
                    f"买入日期={entry.buy_date} | 状态={entry.sell_status}"
                )
