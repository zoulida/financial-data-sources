"""
仓位簿模块

负责仓位记录的增删改查和 CSV 持久化，包括：
- 线程安全的仓位 CRUD 操作
- CSV 文件的读写
- 删除仓位的审计日志
- 按层级/状态的聚合查询
"""
from __future__ import annotations

import csv
import os
import traceback
from datetime import datetime, date
from threading import RLock
from typing import Dict, List, Optional, Tuple

from .config import PositionStatus
from .models import PositionEntry, generate_local_order_id, POSITION_CSV_FIELDS


class PositionBook:
    """
    仓位簿 —— 管理所有仓位记录

    设计要点：
        - 每条仓位独立记录，不合并同价仓位
        - 所有公开方法均通过 RLock 保证线程安全
        - 保存前自动检测被删除的记录并写入审计日志
        - 加载时以内存为准，CSV 只补充新条目
    """

    def __init__(self, csv_path: Optional[str] = None) -> None:
        self.entries: List[PositionEntry] = []
        self.csv_path: Optional[str] = csv_path
        self._lock = RLock()

    # ==============================================================
    #  创建 & 更新
    # ==============================================================
    def create_pending_buy(self, level_index: int, price: float, qty: int) -> PositionEntry:
        """
        下单前创建待买入仓位（生成本地订单号，buy_order_id 暂空）

        Returns:
            新建的 PositionEntry，后续可回填 buy_order_id
        """
        with self._lock:
            entry_id = generate_local_order_id()
            buy_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            buy_date = buy_time[:10]
            entry = PositionEntry(
                entry_id=entry_id,
                level_index=level_index,
                buy_price=price,
                qty=qty,
                buy_time=buy_time,
                buy_date=buy_date,
            )
            self.entries.append(entry)
            return entry

    def add_buy(
        self,
        level_index: int,
        price: float,
        qty: int,
        buy_time: Optional[str] = None,
        buy_order_id: Optional[str] = None,
        buy_trade_id: Optional[str] = None,
    ) -> PositionEntry:
        """
        添加一条买入仓位记录（兼容旧接口，自动生成 entry_id）
        """
        with self._lock:
            if buy_time is None:
                buy_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            buy_date = buy_time[:10]
            entry = PositionEntry(
                entry_id=generate_local_order_id(),
                level_index=level_index,
                buy_price=price,
                qty=qty,
                buy_time=buy_time,
                buy_date=buy_date,
                buy_order_id=buy_order_id,
                buy_trade_id=buy_trade_id,
            )
            self.entries.append(entry)
            return entry

    def update_buy_order_id(self, entry_id: str, buy_order_id: str) -> bool:
        """下单成功后回填券商委托单号"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    e.buy_order_id = buy_order_id
                    return True
            return False

    def update_buy_trade_id(self, entry_id: str, buy_trade_id: str) -> bool:
        """成交后回填券商成交单号"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    e.buy_trade_id = buy_trade_id
                    return True
            return False

    def set_sell_order(
        self,
        entry_id: str,
        sell_order_id: str,
        sell_price: float,
        sell_level: int,
        sell_local_id: Optional[str] = None,
    ) -> bool:
        """为指定仓位设置卖单信息，状态改为 hanging"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    e.sell_order_id = sell_order_id
                    e.sell_status = PositionStatus.HANGING
                    e.sell_price = sell_price
                    e.sell_level = sell_level
                    e.sell_local_id = sell_local_id or entry_id
                    return True
            return False

    def mark_sell_filled(self, entry_id: str) -> bool:
        """标记卖单已成交"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    e.sell_status = PositionStatus.FILLED
                    return True
            return False

    # ==============================================================
    #  删除
    # ==============================================================
    def remove_entry(self, entry_id: str) -> bool:
        """根据 entry_id 删除仓位记录"""
        with self._lock:
            for i, e in enumerate(self.entries):
                if e.entry_id == entry_id:
                    self.entries.pop(i)
                    return True
            return False

    # ==============================================================
    #  查询
    # ==============================================================
    def get_entry_by_id(self, entry_id: str) -> Optional[PositionEntry]:
        """根据 entry_id 获取仓位"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    return e
            return None

    def get_entries_by_level(self, level_index: int) -> List[PositionEntry]:
        """获取指定层级的所有仓位"""
        with self._lock:
            return [e for e in self.entries if e.level_index == level_index]

    def get_total_qty_by_level(self, level_index: int) -> int:
        """获取指定层级的未成交总数量"""
        with self._lock:
            return sum(
                e.qty for e in self.entries
                if e.level_index == level_index and e.sell_status != PositionStatus.FILLED
            )

    def get_pending_entries(self) -> List[PositionEntry]:
        """获取买单未成交的仓位（BuySubmit + pending）"""
        with self._lock:
            return [e for e in self.entries if e.sell_status in (
                PositionStatus.BUY_SUBMIT, PositionStatus.PENDING
            )]

    def get_buy_submit_entries(self) -> List[PositionEntry]:
        """获取本地已发出但尚未确认券商挂单的仓位（BuySubmit）"""
        with self._lock:
            return [e for e in self.entries if e.sell_status == PositionStatus.BUY_SUBMIT]

    def get_buy_filled_entries(self) -> List[PositionEntry]:
        """获取买单已成交、等待挂卖单的仓位（BuyFilled）"""
        with self._lock:
            return [e for e in self.entries if e.sell_status == PositionStatus.BUY_FILLED]

    def get_hanging_sell_entries(self) -> List[PositionEntry]:
        """获取已挂卖单但未成交的仓位（hanging）"""
        with self._lock:
            return [e for e in self.entries if e.sell_status == PositionStatus.HANGING and e.sell_order_id]

    def get_cancelled_entries(self) -> List[PositionEntry]:
        """获取卖单已撤销的仓位（cancelled）"""
        with self._lock:
            return [e for e in self.entries if e.sell_status == PositionStatus.CANCELLED]

    def get_old_entries(self, today: Optional[str] = None) -> List[PositionEntry]:
        """获取买入日期不是今天的仓位"""
        with self._lock:
            if today is None:
                today = date.today().strftime("%Y-%m-%d")
            return [e for e in self.entries if e.buy_date != today]

    def get_entries_needing_sell(self) -> List[PositionEntry]:
        """获取需要挂卖单的仓位（BuyFilled + cancelled）"""
        with self._lock:
            return [
                e for e in self.entries
                if e.sell_status in (PositionStatus.BUY_FILLED, PositionStatus.CANCELLED)
            ]

    def get_pending_with_order_id(self) -> List[PositionEntry]:
        """获取 pending 状态且有 buy_order_id 的仓位（券商已确认挂单，需要查成交状态）"""
        with self._lock:
            return [
                e for e in self.entries
                if e.sell_status == PositionStatus.PENDING and e.buy_order_id
            ]

    def get_pending_without_order_id(self) -> List[PositionEntry]:
        """获取买单未成交且无 buy_order_id 的仓位（BuySubmit 或 pending 但无单号）"""
        with self._lock:
            return [
                e for e in self.entries
                if e.sell_status in (PositionStatus.BUY_SUBMIT, PositionStatus.PENDING)
                and not e.buy_order_id and e.buy_time
            ]

    # ==============================================================
    #  聚合
    # ==============================================================
    def snapshot(self) -> List[Tuple[int, int, float]]:
        """
        返回 (level_index, qty, avg_cost) 列表，按层级排序

        仅统计未成交的仓位，用于日终报告等场景
        """
        with self._lock:
            level_dict: Dict[int, List] = {}
            for e in self.entries:
                if e.sell_status != PositionStatus.FILLED:
                    if e.level_index not in level_dict:
                        level_dict[e.level_index] = [0, 0.0]
                    level_dict[e.level_index][0] += e.qty
                    level_dict[e.level_index][1] += e.buy_price * e.qty

            result = []
            for level in sorted(level_dict):
                qty, total_cost = level_dict[level]
                avg_cost = total_cost / qty if qty > 0 else 0.0
                result.append((level, qty, avg_cost))
            return result

    def total_unfilled_qty(self) -> int:
        """计算所有未成交仓位的总数量"""
        with self._lock:
            return sum(e.qty for e in self.entries if e.sell_status != PositionStatus.FILLED)

    def get_level_summary(self) -> Dict[int, dict]:
        """获取每个层级的汇总信息"""
        with self._lock:
            summary: Dict[int, dict] = {}
            for e in self.entries:
                if e.sell_status != PositionStatus.FILLED:
                    if e.level_index not in summary:
                        summary[e.level_index] = {"qty": 0, "avg_cost": 0.0, "count": 0}
                    summary[e.level_index]["qty"] += e.qty
                    summary[e.level_index]["avg_cost"] += e.buy_price * e.qty
                    summary[e.level_index]["count"] += 1

            for level in summary:
                if summary[level]["qty"] > 0:
                    summary[level]["avg_cost"] /= summary[level]["qty"]
            return summary

    # ==============================================================
    #  清理已成交仓位
    # ==============================================================
    def remove_filled_entries(self) -> List[PositionEntry]:
        """
        移除所有 filled 状态的仓位，返回被移除的列表

        调用方可将返回值传给审计日志
        """
        with self._lock:
            removed = [e for e in self.entries if e.sell_status == PositionStatus.FILLED]
            if removed:
                self.entries = [e for e in self.entries if e.sell_status != PositionStatus.FILLED]
            return removed

    # ==============================================================
    #  CSV 持久化
    # ==============================================================
    def save_to_csv(self, path: Optional[str] = None) -> None:
        """保存仓位到 CSV 文件（保存前记录被删除条目的审计日志）"""
        with self._lock:
            if path is None:
                path = self.csv_path
            if path is None:
                return

            # 保存前对比磁盘，记录消失的条目
            self._check_and_log_removals(path)

            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=POSITION_CSV_FIELDS)
                writer.writeheader()
                for e in self.entries:
                    writer.writerow(e.to_dict())

    def load_from_csv(self, path: Optional[str] = None) -> None:
        """
        从 CSV 加载仓位（内存优先策略）

        加载规则：
            - 内存中已有的条目保留（状态可能已更新）
            - CSV 中新增的条目追加到内存
        """
        with self._lock:
            if path is None:
                path = self.csv_path
            if path is None or not os.path.exists(path):
                return

            existing_ids = {e.entry_id for e in self.entries}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        new_entry = PositionEntry.from_dict(row)
                        if new_entry.entry_id not in existing_ids:
                            self.entries.append(new_entry)
                            existing_ids.add(new_entry.entry_id)
            except Exception as e:
                print(f"加载CSV失败: {e}")

    # ==============================================================
    #  审计日志（内部方法）
    # ==============================================================
    def _check_and_log_removals(self, csv_path: str) -> None:
        """保存前对比磁盘上的 CSV，记录消失的条目到 removed_positions.csv"""
        try:
            if not os.path.exists(csv_path):
                return

            # 读取磁盘上的条目
            disk_entries: Dict[str, dict] = {}
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("entry_id"):
                        disk_entries[row["entry_id"]] = row

            # 找出被删除的条目（磁盘有但内存没有）
            mem_ids = {e.entry_id for e in self.entries}
            removed_ids = set(disk_entries.keys()) - mem_ids
            if not removed_ids:
                return

            # 写入审计日志
            stack_info = "".join(traceback.format_stack()[-5:-1]).replace("\n", " | ")
            log_dir = os.path.dirname(csv_path)
            log_file = os.path.join(log_dir, "removed_positions.csv")
            file_exists = os.path.exists(log_file)

            with open(log_file, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        "remove_time", "entry_id", "level_index", "buy_price", "qty",
                        "sell_order_id", "sell_status", "sell_price", "sell_level", "call_stack",
                    ])

                remove_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for eid in removed_ids:
                    row = disk_entries[eid]
                    writer.writerow([
                        remove_time, row.get("entry_id", ""), row.get("level_index", ""),
                        row.get("buy_price", ""), row.get("qty", ""),
                        row.get("sell_order_id", ""), row.get("sell_status", ""),
                        row.get("sell_price", ""), row.get("sell_level", ""),
                        stack_info,
                    ])

            print(f"[删除日志] {len(removed_ids)}条仓位被移除: {removed_ids}")
        except Exception as e:
            print(f"[删除日志] 记录失败: {e}")
