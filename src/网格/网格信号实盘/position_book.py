from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
from threading import RLock

@dataclass
class PositionEntry:
    """单条仓位记录 - 不合并同价仓位，用于与卖出配对"""
    # 基础信息
    entry_id: str  # 唯一标识（时间戳）
    level_index: int  # 网格层级
    buy_price: float  # 买入价格
    qty: int  # 买入数量
    buy_time: str  # 买入时间（完整时间戳）
    buy_date: str  # 买入日期（YYYY-MM-DD）
    buy_order_id: Optional[str] = None  # 委托单号
    buy_trade_id: Optional[str] = None  # 成交单号
    
    # 卖单状态
    sell_order_id: Optional[str] = None  # 卖单单号
    sell_status: str = "pending"  # pending/hanging/filled
    sell_price: Optional[float] = None  # 卖出挂单价格
    sell_level: Optional[int] = None  # 卖出目标层级
    
    def to_dict(self) -> dict:
        """转换为字典，用于CSV保存"""
        return {
            'entry_id': self.entry_id,
            'level_index': self.level_index,
            'buy_price': self.buy_price,
            'qty': self.qty,
            'buy_time': self.buy_time,
            'buy_date': self.buy_date,
            'buy_order_id': self.buy_order_id or '',
            'buy_trade_id': self.buy_trade_id or '',
            'sell_order_id': self.sell_order_id or '',
            'sell_status': self.sell_status,
            'sell_price': self.sell_price or '',
            'sell_level': self.sell_level or '',
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PositionEntry':
        """从字典创建"""
        return cls(
            entry_id=data['entry_id'],
            level_index=int(data['level_index']),
            buy_price=float(data['buy_price']),
            qty=int(data['qty']),
            buy_time=data['buy_time'],
            buy_date=data['buy_date'],
            buy_order_id=data.get('buy_order_id') or None,
            buy_trade_id=data.get('buy_trade_id') or None,
            sell_order_id=data.get('sell_order_id') or None,
            sell_status=data.get('sell_status', 'pending'),
            sell_price=float(data['sell_price']) if data.get('sell_price') else None,
            sell_level=int(data['sell_level']) if data.get('sell_level') else None,
        )


class PositionBook:
    """
    仓位管理 - 支持多条仓位记录，不合并同价仓位
    """
    def __init__(self, csv_path: str = None) -> None:
        self.entries: List[PositionEntry] = []
        self.csv_path: Optional[str] = csv_path
        self._lock = RLock()
    
    def add_buy(self, level_index: int, price: float, qty: int, buy_time: str = None, buy_order_id: str = None, buy_trade_id: str = None) -> PositionEntry:
        """添加买入仓位记录（不合并）"""
        with self._lock:
            if buy_time is None:
                buy_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            buy_date = buy_time[:10]  # YYYY-MM-DD
            
            entry = PositionEntry(
                entry_id=f"{datetime.now().timestamp():.0f}",
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
    
    def remove_entry(self, entry_id: str) -> bool:
        """删除指定仓位记录"""
        with self._lock:
            for i, e in enumerate(self.entries):
                if e.entry_id == entry_id:
                    self.entries.pop(i)
                    return True
            return False
    
    def get_entries_by_level(self, level_index: int) -> List[PositionEntry]:
        """获取指定层级的所有仓位"""
        with self._lock:
            return [e for e in self.entries if e.level_index == level_index]
    
    def get_pending_sell_entries(self) -> List[PositionEntry]:
        """获取还未挂卖单的仓位（sell_status == pending）"""
        with self._lock:
            return [e for e in self.entries if e.sell_status == 'pending']
    
    def get_hanging_sell_entries(self) -> List[PositionEntry]:
        """获取已挂卖单但未成交的仓位"""
        with self._lock:
            return [e for e in self.entries if e.sell_status == 'hanging' and e.sell_order_id]
    
    def get_old_entries(self, today: str = None) -> List[PositionEntry]:
        """获取买入日期不是今天的仓位"""
        with self._lock:
            if today is None:
                today = date.today().strftime("%Y-%m-%d")
            return [e for e in self.entries if e.buy_date != today]
    
    def set_sell_order(self, entry_id: str, sell_order_id: str, sell_price: float, sell_level: int) -> bool:
        """设置卖单信息"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    e.sell_order_id = sell_order_id
                    e.sell_status = 'hanging'
                    e.sell_price = sell_price
                    e.sell_level = sell_level
                    return True
            return False
    
    def mark_sell_filled(self, entry_id: str) -> bool:
        """标记卖单已成交"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    e.sell_status = 'filled'
                    return True
            return False
    
    def get_total_qty_by_level(self, level_index: int) -> int:
        """获取指定层级的总数量"""
        with self._lock:
            return sum(e.qty for e in self.entries if e.level_index == level_index and e.sell_status != 'filled')
    
    def snapshot(self) -> List[Tuple[int, int, float]]:
        """返回 (level_index, qty, avg_cost) 列表，按level排序（兼容旧接口）"""
        with self._lock:
            level_dict: Dict[int, Tuple[int, float, int]] = {}
            for e in self.entries:
                if e.sell_status != 'filled':
                    if e.level_index not in level_dict:
                        level_dict[e.level_index] = [0, 0.0, 0]  # qty, total_cost, count
                    level_dict[e.level_index][0] += e.qty
                    level_dict[e.level_index][1] += e.buy_price * e.qty
                    level_dict[e.level_index][2] += 1
            
            result = []
            for level, (qty, total_cost, _) in sorted(level_dict.items()):
                avg_cost = total_cost / qty if qty > 0 else 0.0
                result.append((level, qty, avg_cost))
            return result
    
    def save_to_csv(self, path: str = None) -> None:
        """保存仓位到CSV"""
        with self._lock:
            if path is None:
                path = self.csv_path
            if path is None:
                return
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'entry_id', 'level_index', 'buy_price', 'qty', 'buy_time', 'buy_date',
                    'buy_order_id', 'buy_trade_id', 'sell_order_id', 'sell_status', 'sell_price', 'sell_level'
                ])
                writer.writeheader()
                for e in self.entries:
                    writer.writerow(e.to_dict())
    
    def load_from_csv(self, path: str = None) -> None:
        """从CSV加载仓位 - 支持按 entry_id 去重加载"""
        with self._lock:
            if path is None:
                path = self.csv_path
            if path is None or not os.path.exists(path):
                return
            
            # 使用字典按 entry_id 存储，实现去重（以文件中的最新记录为准）
            existing_entries = {e.entry_id: e for e in self.entries}
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        new_entry = PositionEntry.from_dict(row)
                        # 如果内存中已存在且状态已更新（例如已挂单），则保留内存中的，否则以文件为准
                        if new_entry.entry_id in existing_entries:
                            # 简单的合并逻辑：如果文件中的记录 sell_status 更有意义（比如 filled），则覆盖
                            # 这里暂定以文件为准，因为 _sync_positions_with_broker 的本意就是以文件为准
                            existing_entries[new_entry.entry_id] = new_entry
                        else:
                            existing_entries[new_entry.entry_id] = new_entry
                
                # 重新转换为列表并按 entry_id 排序（可选）
                self.entries = list(existing_entries.values())
            except Exception as e:
                print(f"加载CSV失败: {e}")
    
    def get_level_summary(self) -> Dict[int, dict]:
        """获取每个层级的汇总信息"""
        with self._lock:
            summary = {}
            for e in self.entries:
                if e.sell_status != 'filled':
                    if e.level_index not in summary:
                        summary[e.level_index] = {'qty': 0, 'avg_cost': 0.0, 'count': 0}
                    summary[e.level_index]['qty'] += e.qty
                    summary[e.level_index]['avg_cost'] += e.buy_price * e.qty
                    summary[e.level_index]['count'] += 1
            
            for level in summary:
                if summary[level]['qty'] > 0:
                    summary[level]['avg_cost'] /= summary[level]['qty']
            
            return summary


