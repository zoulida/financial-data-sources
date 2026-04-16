"""
订单管理模块

负责订单生命周期的管理，包括：
- 本地挂单状态维护 (pending_orders)
- 买单/卖单状态与券商的同步
- 涨跌停价格检查
- 订单去重
- 废单清理
- 过期挂单清理
- 补全缺失的 buy_order_id
"""
from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .config import (
    DefaultParams,
    OrderConst,
    OrderStatus,
    OrderType,
    PositionStatus,
)
from .models import GridSpec, PositionEntry
from .position_book import PositionBook
from .utils import match_stock_code


class OrderManager:
    """
    订单管理器

    管理本地挂单状态，并与券商订单保持同步。
    不直接调用券商接口，而是通过注入的回调/引用来操作。

    Attributes:
        pos_book      : 仓位簿引用
        _pending_orders: 本地挂单集合 {(level_index, side)}
        _pending_details: 挂单详细信息 {(level_index, side): {qty, price, order_id, timestamp}}
        _limit_up     : 当前涨停价
        _limit_down   : 当前跌停价
    """

    def __init__(self, pos_book: PositionBook, log_fn: Optional[Callable] = None) -> None:
        """
        Args:
            pos_book: 仓位簿实例
            log_fn  : 日志输出函数（默认 print）
        """
        self.pos_book = pos_book
        self._log = log_fn or print

        # ── 本地挂单状态 ──
        self._pending_orders: Set[Tuple[int, str]] = set()
        self._pending_details: Dict[Tuple[int, str], Dict[str, Any]] = {}

        # ── 涨跌停价格（由外部 tick 更新） ──
        self._limit_up: float = 0.0
        self._limit_down: float = 0.0

        # ── 下单历史（用于去重） ──
        self._order_history: List[str] = []

        # ── entry_id 生成计数器 ──
        self._entry_id_counter: int = 0

    # ==============================================================
    #  涨跌停价格
    # ==============================================================
    def update_price_limits(self, limit_up: float, limit_down: float) -> None:
        """更新涨跌停价格（每个 tick 调用一次）"""
        if limit_up > 0:
            self._limit_up = limit_up
        if limit_down > 0:
            self._limit_down = limit_down

    def check_price_limit(self, price: float, side: str, level_index: int, silent: bool = False) -> bool:
        """
        检查下单价格是否在涨跌停范围内

        Args:
            silent: 为 True 时不打印拦截日志（用于批量检查后统一汇总）

        Returns:
            True = 价格合法可下单, False = 超出范围被拦截
        """
        if self._limit_up > 0 and price > self._limit_up:
            if not silent:
                self._log(f"[拦截] 下单价格{price:.6f}超过涨停价{self._limit_up:.6f}，不下单 | {side} 层级{level_index}")
            return False
        if self._limit_down > 0 and price < self._limit_down:
            if not silent:
                self._log(f"[拦截] 下单价格{price:.6f}低于跌停价{self._limit_down:.6f}，不下单 | {side} 层级{level_index}")
            return False
        return True

    # ==============================================================
    #  entry_id 生成
    # ==============================================================
    def generate_entry_id(self) -> str:
        """生成唯一的本地订单号（微秒时间戳 + 自增计数器）"""
        self._entry_id_counter += 1
        ts = int(datetime.now().timestamp() * 1_000_000)
        return f"{ts}_{self._entry_id_counter}"

    # ==============================================================
    #  本地挂单状态管理
    # ==============================================================
    def mark_pending(
        self,
        level_index: int,
        side: str,
        qty: int,
        price: float,
        order_id: Optional[Any] = None,
    ) -> None:
        """标记本地挂单状态"""
        key = (level_index, side)
        self._pending_orders.add(key)
        self._pending_details[key] = {
            "qty": qty,
            "price": price,
            "order_id": order_id,
            "timestamp": datetime.now(),
        }

    def has_pending(self, level_index: int, side: Optional[str] = None) -> bool:
        """检查指定层级是否有本地挂单"""
        if side is None:
            return (level_index, "BUY") in self._pending_orders or (level_index, "SELL") in self._pending_orders
        return (level_index, side) in self._pending_orders

    def clear_pending(self, level_index: int, side: Optional[str] = None) -> None:
        """清除指定层级的本地挂单状态"""
        if side is None:
            for s in ("BUY", "SELL"):
                key = (level_index, s)
                self._pending_orders.discard(key)
                self._pending_details.pop(key, None)
        else:
            key = (level_index, side)
            self._pending_orders.discard(key)
            self._pending_details.pop(key, None)

    def clear_all_pending(self) -> None:
        """清除所有本地挂单状态"""
        self._pending_orders.clear()
        self._pending_details.clear()

    def get_pending_detail(self, level_index: int, side: str) -> Optional[Dict[str, Any]]:
        """获取指定挂单的详细信息"""
        return self._pending_details.get((level_index, side))

    def update_pending_order_id(self, level_index: int, side: str, order_id: Any) -> None:
        """更新挂单的券商订单号"""
        key = (level_index, side)
        if key in self._pending_details:
            self._pending_details[key]["order_id"] = order_id

    # ==============================================================
    #  去重检查
    # ==============================================================
    def is_duplicate_order(self, side: str, price: float) -> bool:
        """
        检查是否为重复挂单（与上一个挂单相同方向和价格）

        Returns:
            True = 重复，应跳过
        """
        key = f"{side}_{price:.6f}"
        if self._order_history and self._order_history[-1] == key:
            return True
        return False

    def record_order_history(self, side: str, price: float) -> None:
        """记录下单历史（用于去重）"""
        key = f"{side}_{price:.6f}"
        self._order_history.append(key)

    def has_pending_buy_at_level(self, level_index: int) -> bool:
        """检查指定层级是否已有买单记录（BuySubmit 或 pending，避免重复创建）"""
        entries = [
            e for e in self.pos_book.entries
            if e.level_index == level_index
            and e.sell_status in (PositionStatus.BUY_SUBMIT, PositionStatus.PENDING)
        ]
        return len(entries) > 0

    # ==============================================================
    #  券商订单查询（通过注入的 broker 引用）
    # ==============================================================
    def has_real_buy_order_at_level(
        self, level_index: int, spec: GridSpec, unfilled_orders: List[dict], stock_code: str
    ) -> bool:
        """
        检查券商是否有指定层级价格的买单

        Args:
            level_index    : 目标层级
            spec           : 网格规格（用于计算目标价格）
            unfilled_orders: 券商未成交订单列表
            stock_code     : 股票代码
        """
        target_price = spec.level_price(level_index)
        for order in unfilled_orders:
            if not match_stock_code(order.get("stock_code", ""), stock_code):
                continue
            order_type = order.get("order_type")
            order_side = order.get("order_side", 0)
            is_buy = (order_type in [OrderType.BUY, OrderType.BUY_OPEN]) or (order_side == 48)
            if is_buy and abs(round(order.get("price", 0), 3) - target_price) < DefaultParams.PRICE_TOLERANCE:
                return True
        return False

    def has_real_sell_order_at_level(
        self, level_index: int, spec: GridSpec, unfilled_orders: List[dict], stock_code: str
    ) -> bool:
        """检查券商是否有指定层级价格的卖单"""
        target_price = round(spec.level_price(level_index), 3)
        for order in unfilled_orders:
            if not match_stock_code(order.get("stock_code", ""), stock_code):
                continue
            order_type = order.get("order_type")
            order_side = order.get("order_side", 0)
            is_sell = (order_type in [OrderType.SELL, OrderType.SELL_CLOSE]) or (order_side == 49)
            if is_sell and abs(round(order.get("price", 0), 3) - target_price) < DefaultParams.PRICE_TOLERANCE:
                return True
        return False

    # ==============================================================
    #  订单状态同步
    # ==============================================================
    def sync_local_pending_with_broker(
        self, unfilled_orders: List[dict], stock_code: str
    ) -> None:
        """
        将本地挂单标记与券商未成交订单同步

        背景：
            本地 _pending_orders 是"防重复下单"的标记集合，
            记录"哪个层级已经有挂单了，不要再下"。
            但券商侧订单可能已成交/撤销/废单，标记就过时了。

        规则：
            - 本地有标记但券商未成交列表没有 → 订单已离开（成交/撤销/废单），
              清除过时标记，让后续决策逻辑可以重新挂单
            - 本地有标记且券商有，但剩余数量变化 → 更新本地数量
            - 本地有标记但无 order_id，券商有匹配订单 → 补全 order_id

        注意：
            这里只负责"数据清理"，不负责重新下单。
            重新下单由 _handle_level_event 中的 _ensure_buy_orders_below
            和 _place_buy_order_if_empty 在下一轮自动完成。
        """
        # 券商无任何未成交订单 → 本地所有挂单标记都是过时的，全部清除
        if not unfilled_orders:
            self.clear_all_pending()
            return

        # ── 第一步：构建券商真实未成交订单字典 ──
        # key=order_id, value={side, price, qty(剩余), status}
        real_orders: Dict[Any, Dict] = {}
        for order in unfilled_orders:
            # 只处理当前股票的订单
            if not match_stock_code(order.get("stock_code", ""), stock_code):
                continue
            order_id = order.get("order_id")
            order_volume = order.get("order_volume", 0)
            traded_volume = order.get("traded_volume", 0)
            remaining = order_volume - traded_volume  # 尚未成交的剩余数量
            if remaining <= 0:
                continue  # 已全部成交，不算未成交

            # 判断买卖方向
            order_type = order.get("order_type")
            order_remark = order.get("order_remark", "").lower()
            if order_type == OrderType.BUY:
                side = "BUY"
            elif order_type == OrderType.SELL:
                side = "SELL"
            elif "buy" in order_remark:
                side = "BUY"
            elif "sell" in order_remark:
                side = "SELL"
            else:
                continue  # 无法判断方向，跳过

            real_orders[order_id] = {
                "side": side,
                "price": order.get("price", 0),
                "qty": remaining,
                "status": order.get("order_status"),
            }

        # ── 第二步：逐个检查本地挂单标记，与券商订单对比 ──
        to_remove = []  # 需要清除的过时标记
        for (level_idx, side) in list(self._pending_orders):
            detail = self._pending_details.get((level_idx, side))
            if not detail:
                # 有标记但无详情，数据不一致，清除
                to_remove.append((level_idx, side))
                continue

            local_price = round(detail.get("price", 0), 6)

            # 在券商订单中查找匹配项（按方向 + 价格匹配）
            matched = None
            for oid, info in real_orders.items():
                if info["side"] == side and abs(info["price"] - local_price) < 0.001:
                    matched = (oid, info)
                    break

            if matched:
                # 找到匹配：券商确实有这笔未成交订单
                oid, info = matched
                if info["qty"] != detail.get("qty"):
                    detail["qty"] = info["qty"]  # 部分成交，更新剩余数量
                if detail.get("order_id") is None:
                    detail["order_id"] = oid  # 补全缺失的 order_id
            else:
                # 未找到匹配：订单已不在券商未成交列表中
                # 可能已成交、已撤销或废单，清除过时标记
                to_remove.append((level_idx, side))

        # ── 第三步：执行清除 ──
        for key in to_remove:
            self._pending_orders.discard(key)
            self._pending_details.pop(key, None)

    def sync_buy_order_status(self, all_orders: List[dict]) -> bool:
        """
        同步买单状态

        处理两类仓位：
        1. BuySubmit（本地已发出，尚未确认）：
           - 在券商未成交列表中找到 → pending（确认挂单成功）
           - 在券商全部订单中找到已成交(56) → BuyFilled
           - 超时无 buy_order_id → 删除（发单失败）
        2. pending（券商已确认挂单）：
           - 已成交(56) → BuyFilled
           - 已撤销(54) → 删除
           - 废单(57)   → 删除
           - 无 buy_order_id 且超时 → 删除

        Returns:
            是否有更新（需要保存 CSV）
        """
        updated = False

        # ── 1. 处理 BuySubmit 状态：确认券商是否已接受挂单 ──
        submit_entries = self.pos_book.get_buy_submit_entries()
        for entry in submit_entries:
            if not entry.buy_order_id:
                # 无 buy_order_id，检查是否超时
                try:
                    entry_time = datetime.strptime(entry.buy_time, "%Y-%m-%d %H:%M:%S")
                    age = (datetime.now() - entry_time).total_seconds()
                    if age > OrderConst.STALE_PENDING_TIMEOUT:
                        self._log(
                            f"[清理] BuySubmit无单号超时: 仓位ID={entry.entry_id} | "
                            f"层级={entry.level_index} | 已过{int(age)}秒 | 发单可能失败"
                        )
                        self.pos_book.remove_entry(entry.entry_id)
                        updated = True
                except Exception:
                    pass
                continue

            # 有 buy_order_id，查券商订单状态
            for order in all_orders:
                if str(order.get("order_id", "")) != str(entry.buy_order_id):
                    continue
                status = order.get("order_status", 0)
                if status == OrderStatus.FILLED:
                    # 已成交 → 直接跳到 BuyFilled
                    entry.sell_status = PositionStatus.BUY_FILLED
                    self._log(
                        f"BuySubmit→BuyFilled: 仓位ID={entry.entry_id} | "
                        f"层级={entry.level_index} | 买单号={entry.buy_order_id}"
                    )
                elif status in (OrderStatus.CANCELLED, OrderStatus.REJECTED):
                    # 撤销/废单 → 删除
                    self._log(
                        f"BuySubmit撤销/废单: 仓位ID={entry.entry_id} | "
                        f"层级={entry.level_index} | 买单号={entry.buy_order_id} | 将删除"
                    )
                    self.pos_book.remove_entry(entry.entry_id)
                else:
                    # 其他状态（如已报/部成）→ 确认券商已接受，转为 pending
                    entry.sell_status = PositionStatus.PENDING
                    self._log(
                        f"BuySubmit→pending: 仓位ID={entry.entry_id} | "
                        f"层级={entry.level_index} | 券商状态={status} | 确认挂单成功"
                    )
                updated = True
                break

        # ── 2. 清理无 buy_order_id 且超时的 pending 条目 ──
        stale_entries = [
            e for e in self.pos_book.entries
            if e.sell_status == PositionStatus.PENDING and not e.buy_order_id and e.buy_time
        ]
        for entry in stale_entries:
            try:
                entry_time = datetime.strptime(entry.buy_time, "%Y-%m-%d %H:%M:%S")
                age = (datetime.now() - entry_time).total_seconds()
                if age > OrderConst.STALE_PENDING_TIMEOUT:
                    self._log(
                        f"[清理] pending无买单号过期: 仓位ID={entry.entry_id} | "
                        f"层级={entry.level_index} | 已过{int(age)}秒"
                    )
                    self.pos_book.remove_entry(entry.entry_id)
                    updated = True
            except Exception:
                pass

        # ── 3. 查询有 buy_order_id 的 pending 条目，确认成交状态 ──
        pending_entries = self.pos_book.get_pending_with_order_id()
        if not pending_entries or not all_orders:
            return updated

        for entry in pending_entries:
            for order in all_orders:
                if str(order.get("order_id", "")) != str(entry.buy_order_id):
                    continue
                status = order.get("order_status", 0)

                if status == OrderStatus.FILLED:
                    # 已成交 → BuyFilled
                    entry.sell_status = PositionStatus.BUY_FILLED
                    self._log(
                        f"买单已成交(同步): 仓位ID={entry.entry_id} | "
                        f"层级={entry.level_index} | 买单号={entry.buy_order_id} | 状态→BuyFilled"
                    )
                    updated = True

                elif status == OrderStatus.CANCELLED:
                    # 已撤销 → 删除
                    self._log(
                        f"买单已撤销(同步): 仓位ID={entry.entry_id} | "
                        f"层级={entry.level_index} | 买单号={entry.buy_order_id} | 将删除"
                    )
                    self.pos_book.remove_entry(entry.entry_id)
                    updated = True

                elif status == OrderStatus.REJECTED:
                    # 废单 → 删除
                    self._log(
                        f"买单废单(同步): 仓位ID={entry.entry_id} | "
                        f"层级={entry.level_index} | 买单号={entry.buy_order_id} | 将删除"
                    )
                    self.pos_book.remove_entry(entry.entry_id)
                    updated = True

                break  # 找到匹配订单后跳出内层循环

        return updated

    def sync_sell_order_status(self, all_orders: List[dict]) -> bool:
        """
        同步卖单状态：hanging → filled / cancelled

        检查 hanging 状态的仓位，查券商确认：
        - 已成交(56) → filled
        - 已撤销(54) → cancelled
        - 已报/部成(50/55) → 保持 hanging

        Returns:
            是否有更新
        """
        updated = False
        hanging_entries = self.pos_book.get_hanging_sell_entries()

        for entry in hanging_entries:
            if not entry.sell_order_id:
                continue

            for order in all_orders:
                if str(order.get("order_id", "")) != str(entry.sell_order_id):
                    continue

                status = order.get("order_status", 0)
                if status == OrderStatus.FILLED:
                    self.pos_book.mark_sell_filled(entry.entry_id)
                    self._log(f"卖单已成交(同步): 仓位ID={entry.entry_id} | 卖单号={entry.sell_order_id}")
                    updated = True
                elif status == OrderStatus.CANCELLED:
                    entry.sell_status = PositionStatus.CANCELLED
                    self._log(f"卖单已撤销: 仓位ID={entry.entry_id} | 状态→cancelled")
                    updated = True
                break

        return updated

    def fill_missing_buy_order_ids(
        self, unfilled_orders: List[dict], stock_code: str,
        all_orders: Optional[List[dict]] = None,
    ) -> bool:
        """
        补全缺失的 buy_order_id

        检查无 buy_order_id 的仓位，通过券商 order_remark 匹配 entry_id
        先从未成交订单匹配，未匹配到的再从全量订单（含已成交）中查找

        Returns:
            是否有更新
        """
        entries = [
            e for e in self.pos_book.entries
            if e.entry_id and not e.buy_order_id and e.sell_status != PositionStatus.FILLED
        ]
        if not entries:
            return False

        self._log(f"[订单补全] 发现{len(entries)}条缺少buy_order_id的记录")

        # 从订单中构建 entry_id → order_id 映射的辅助函数
        def _build_mapping(orders: List[dict]) -> Dict[str, str]:
            mapping: Dict[str, str] = {}
            for order in orders:
                if not match_stock_code(order.get("stock_code", ""), stock_code):
                    continue
                if order.get("order_type") != OrderType.BUY:
                    continue
                remark = order.get("order_remark", "")
                if remark.startswith("BUY_"):
                    extracted_id = remark[4:]
                else:
                    extracted_id = remark
                if extracted_id:
                    mapping[extracted_id] = str(order.get("order_id"))
            return mapping

        # 先从未成交订单匹配
        entry_to_order = _build_mapping(unfilled_orders)

        # 未匹配到的，从全量订单（含已成交）中查找
        still_missing = [e for e in entries if e.entry_id not in entry_to_order]
        if still_missing and all_orders:
            all_mapping = _build_mapping(all_orders)
            for k, v in all_mapping.items():
                if k not in entry_to_order:
                    entry_to_order[k] = v

        # 更新
        count = 0
        for entry in entries:
            if entry.entry_id in entry_to_order:
                entry.buy_order_id = entry_to_order[entry.entry_id]
                count += 1
                self._log(
                    f"[订单补全] entry_id={entry.entry_id} → order_id={entry.buy_order_id}"
                )

        if count > 0:
            self._log(f"[订单补全] 已更新{count}条记录")
            self.pos_book.save_to_csv()
        return count > 0

    # ==============================================================
    #  过期挂单清理
    # ==============================================================
    def cleanup_old_pending(self, max_age_minutes: int = OrderConst.PENDING_CLEANUP_MINUTES) -> None:
        """清理过期的本地挂单状态"""
        now = datetime.now()
        to_remove = []
        for key, detail in self._pending_details.items():
            ts = detail.get("timestamp")
            if ts and (now - ts).total_seconds() > max_age_minutes * 60:
                to_remove.append(key)

        for key in to_remove:
            self._pending_orders.discard(key)
            self._pending_details.pop(key, None)
            self._log(f"清理过期挂单: 层级{key[0]} 方向{key[1]}")
