"""
网格策略 —— 辅助功能 Mixin

职责：
- 应急卖单（超仓位阈值时自动创建虚拟卖单）
- 模拟撮合（回测模式下模拟订单成交）
- 日终报告输出
- 删除仓位审计日志
"""
from __future__ import annotations

import csv
import os
import traceback
from datetime import datetime
from typing import List, Optional

from .config import DefaultParams, PositionStatus
from .models import Trade


class AuxiliaryMixin:
    """
    辅助功能：应急卖单 + 模拟撮合 + 日终报告

    依赖主类提供：
        self.engine, self.spec, self.manager, self.pos_book,
        self.order_mgr, self.write_log, self.reporter,
        self._simulate_mode, self._get_broker_data,
        self.last_price, self.hand_size,
        self._emergency_log_path, self._max_position_trigger_count
    """

    # ==============================================================
    #  应急卖单
    # ==============================================================
    def _create_emergency_sell_order(self) -> None:
        """
        创建应急卖单

        当触发次数超过阈值时，在 CSV 中创建虚拟仓位记录，
        卖出价 = 当前价 + 一个网格步长，
        下个 tick 由 _place_sell_for_pending_positions 处理。
        """
        try:
            if not self.spec or not self.last_price or not self.engine:
                self.write_log("[应急卖单] 无法创建: 网格未初始化或无当前价格")
                return

            current_level = self.engine.price_to_level_index(self.last_price)
            if current_level is None:
                return

            sell_price = round(self.last_price + self.spec.step, DefaultParams.PRICE_DECIMALS)
            sell_level = current_level + 1
            if sell_level > self.spec.max_level_index:
                self.write_log(f"[应急卖单] 层级{sell_level}超出最大范围")
                return

            broker, unfilled, _ = self._get_broker_data()
            stock_code = self.manager.stock_code if self.manager else ""
            if unfilled and self.order_mgr.has_real_sell_order_at_level(sell_level, self.spec, unfilled, stock_code):
                self.write_log(f"[应急卖单] 层级{sell_level}已有卖单")
                return

            buy_price = round(sell_price - self.spec.step, DefaultParams.PRICE_DECIMALS)
            buy_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = self.pos_book.add_buy(current_level, buy_price, self.hand_size, buy_time, None, None)
            entry.sell_order_id = f"EMERGENCY_{int(datetime.now().timestamp())}"
            entry.sell_price = sell_price
            entry.sell_level = sell_level

            # 记录到应急日志
            self._append_emergency_log(self.last_price, sell_price, sell_level, self._max_position_trigger_count)
            self.write_log(f"[应急卖单] 已创建: 买价={buy_price:.6f}, 卖价={sell_price:.6f}, 层级={sell_level}")
            self.pos_book.save_to_csv()

        except Exception as e:
            self.write_log(f"[应急卖单] 创建失败: {e}")
            traceback.print_exc()

    def _append_emergency_log(self, current_price, sell_price, sell_level, trigger_count):
        """追加应急卖单触发记录"""
        try:
            with open(self._emergency_log_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([ts, f"{current_price:.6f}", f"{sell_price:.6f}", sell_level, trigger_count])
        except Exception:
            pass

    # ==============================================================
    #  模拟撮合
    # ==============================================================
    def _simulate_matching(self, current_price: float, tick_time: str) -> None:
        """模拟模式下的订单撮合"""
        try:
            pending_copy = list(self.order_mgr._pending_orders.copy())
            for key in pending_copy:
                level_index, side = key
                detail = self.order_mgr.get_pending_detail(level_index, side)
                if not detail:
                    continue

                order_price = detail.get("price", 0)
                order_qty = detail.get("qty", 0)
                if order_price <= 0 or order_qty <= 0:
                    continue

                should_fill = False
                if side == "BUY" and current_price <= order_price:
                    should_fill = True
                elif side == "SELL" and current_price >= order_price:
                    should_fill = True

                if should_fill:
                    self._simulate_fill(level_index, side, order_price, order_qty, current_price, tick_time)

        except Exception as e:
            self.write_log(f"模拟撮合失败: {e}")

    def _simulate_fill(self, level_index, side, order_price, order_qty, fill_price, tick_time):
        """模拟订单成交"""
        try:
            order_id = int(datetime.now().timestamp() * 1_000_000) % 1_000_000_000
            trade_id = order_id + 1

            self.order_mgr.clear_pending(level_index, side)

            if side == "BUY":
                entry = self.pos_book.add_buy(level_index, fill_price, order_qty, tick_time, str(order_id), str(trade_id))
                self.write_log(f"模拟成交: BUY | 层级{level_index} | 价格{fill_price:.6f} | 仓位ID:{entry.entry_id}")
            else:
                self._mark_position_sell_filled(level_index, order_qty)
                self.write_log(f"模拟成交: SELL | 层级{level_index} | 价格{fill_price:.6f}")

            tr = Trade(
                trade_id=self._next_trade_id(),
                order_id=order_id,
                ts=tick_time,
                side=side,
                price=fill_price,
                qty=order_qty,
                level_index=level_index,
            )
            self.reporter.log_trade(tr)
            self.on_order_filled(level_index, side, fill_price, order_qty, str(trade_id))

        except Exception as e:
            self.write_log(f"模拟成交失败: {e}")

    def _next_trade_id(self) -> int:
        if not hasattr(self, "_trade_id_counter"):
            self._trade_id_counter = 0
        self._trade_id_counter += 1
        return self._trade_id_counter

    # ==============================================================
    #  日终报告
    # ==============================================================
    def _flush_end_of_day_report(self) -> None:
        """输出日终报告"""
        now = datetime.now()
        self.write_log(f"开始输出日终报告到: {self.reporter.out_dir}")
        try:
            self.reporter.flush_end_of_day(now, self.pos_book.snapshot(), self.spec.level_price)
            self.write_log("日终报告已输出")
        except Exception as e:
            self.write_log(f"输出日终报告失败: {e}")
            traceback.print_exc()

    # ==============================================================
    #  删除仓位审计日志
    # ==============================================================
    def _log_removed_positions(self, entries: list, reason: str) -> None:
        """记录被删除的仓位到审计日志"""
        try:
            log_dir = os.path.dirname(self.pos_book.csv_path) if self.pos_book.csv_path else "."
            log_file = os.path.join(log_dir, "removed_positions.csv")
            file_exists = os.path.exists(log_file)

            with open(log_file, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        "remove_time", "reason", "entry_id", "level_index", "buy_price", "qty",
                        "buy_time", "buy_date", "buy_order_id", "buy_trade_id",
                        "sell_order_id", "sell_status", "sell_price", "sell_level",
                    ])

                remove_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for e in entries:
                    writer.writerow([
                        remove_time, reason, e.entry_id, e.level_index, e.buy_price, e.qty,
                        e.buy_time, e.buy_date, e.buy_order_id, e.buy_trade_id,
                        e.sell_order_id, e.sell_status, e.sell_price, e.sell_level,
                    ])
            self.write_log(f"[删除日志] 已记录{len(entries)}条被删除仓位")
        except Exception as e:
            self.write_log(f"[删除日志] 记录失败: {e}")
