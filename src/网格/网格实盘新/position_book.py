from __future__ import annotations

import csv
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
from threading import RLock

def generate_local_order_id() -> str:
    """
    生成本地订单号：格式为 LOC_{时间戳}_{随机4位}
    例如: LOC_20260331141500_A3F2
    """
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand_part = uuid.uuid4().hex[:4].upper()
    return f"LOC_{ts}_{rand_part}"


@dataclass
class PositionEntry:
    """单条仓位记录 - 不合并同价仓位，用于与卖出配对"""
    # 基础信息
    entry_id: str  # 本地订单号（唯一标识，下单前生成）
    level_index: int  # 网格层级
    buy_price: float  # 买入价格
    qty: int  # 买入数量
    buy_time: str  # 买入时间（完整时间戳）
    buy_date: str  # 买入日期（YYYY-MM-DD）
    buy_order_id: Optional[str] = None  # 券商委托单号（下单后回填）
    buy_trade_id: Optional[str] = None  # 券商成交单号（成交后回填）
    
    # 卖单状态
    sell_order_id: Optional[str] = None  # 卖单券商单号
    sell_status: str = "pending"  # pending/hanging/filled
    sell_price: Optional[float] = None  # 卖出挂单价格
    sell_level: Optional[int] = None  # 卖出目标层级
    sell_local_id: Optional[str] = None  # 卖单本地订单号（对应买单的entry_id）
    
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
            'sell_local_id': self.sell_local_id or '',
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
            sell_local_id=data.get('sell_local_id') or None,
        )


class PositionBook:
    """
    仓位管理 - 支持多条仓位记录，不合并同价仓位
    新增功能：
    - 下单前生成本地订单号(entry_id)
    - 支持检查有entry_id但无buy_order_id的条目
    """
    def __init__(self, csv_path: str = None) -> None:
        self.entries: List[PositionEntry] = []
        self.csv_path: Optional[str] = csv_path
        self._lock = RLock()
    
    def create_pending_buy(self, level_index: int, price: float, qty: int) -> PositionEntry:
        """
        下单前创建待买入仓位记录（生成本地订单号，但不填券商单号）
        返回entry供后续更新券商单号
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
                buy_order_id=None,  # 下单后回填
                buy_trade_id=None,
            )
            self.entries.append(entry)
            return entry
    
    def update_buy_order_id(self, entry_id: str, buy_order_id: str) -> bool:
        """下单成功后更新券商委托单号"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    e.buy_order_id = buy_order_id
                    return True
            return False
    
    def update_buy_trade_id(self, entry_id: str, buy_trade_id: str) -> bool:
        """成交后更新券商成交单号"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    e.buy_trade_id = buy_trade_id
                    return True
            return False
    
    def get_pending_buy_entries(self) -> List[PositionEntry]:
        """获取有entry_id但无buy_order_id的条目（需要检查券商挂单或补单）"""
        with self._lock:
            return [e for e in self.entries 
                    if e.entry_id and not e.buy_order_id and e.sell_status != 'filled']
    
    def get_entry_by_id(self, entry_id: str) -> Optional[PositionEntry]:
        """根据entry_id获取仓位记录"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    return e
            return None
    
    def remove_entry_by_id(self, entry_id: str) -> bool:
        """根据entry_id删除仓位记录"""
        with self._lock:
            for i, e in enumerate(self.entries):
                if e.entry_id == entry_id:
                    self.entries.pop(i)
                    return True
            return False
    
    def add_buy(self, level_index: int, price: float, qty: int, buy_time: str = None, buy_order_id: str = None, buy_trade_id: str = None) -> PositionEntry:
        """添加买入仓位记录（兼容旧接口，同时生成本地订单号）"""
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
        """获取还未挂卖单的仓位（sell_status == pending）- 旧方法，保留兼容"""
        with self._lock:
            return [e for e in self.entries if e.sell_status == 'pending']
    
    def get_buy_filled_entries(self) -> List[PositionEntry]:
        """获取买单已成交、等待挂卖单的仓位（sell_status == BuyFilled）"""
        with self._lock:
            return [e for e in self.entries if e.sell_status == 'BuyFilled']
    
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
    
    def set_sell_order(self, entry_id: str, sell_order_id: str, sell_price: float, sell_level: int, sell_local_id: str = None) -> bool:
        """设置卖单信息"""
        with self._lock:
            for e in self.entries:
                if e.entry_id == entry_id:
                    e.sell_order_id = sell_order_id
                    e.sell_status = 'hanging'
                    e.sell_price = sell_price
                    e.sell_level = sell_level
                    e.sell_local_id = sell_local_id or entry_id  # 卖单本地订单号默认使用买单的entry_id
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
                        level_dict[e.level_index] = [0, 0.0, 0]
                    level_dict[e.level_index][0] += e.qty
                    level_dict[e.level_index][1] += e.buy_price * e.qty
                    level_dict[e.level_index][2] += 1
            
            result = []
            for level, (qty, total_cost, _) in sorted(level_dict.items()):
                avg_cost = total_cost / qty if qty > 0 else 0.0
                result.append((level, qty, avg_cost))
            return result
    
    def save_to_csv(self, path: str = None) -> None:
        """保存仓位到CSV，并记录删除日志"""
        with self._lock:
            if path is None:
                path = self.csv_path
            if path is None:
                return
            
            # 【新增】保存前检查：对比磁盘上的条目，记录消失的条目
            self._check_and_log_removals(path)
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'entry_id', 'level_index', 'buy_price', 'qty', 'buy_time', 'buy_date',
                    'buy_order_id', 'buy_trade_id', 'sell_order_id', 'sell_status', 'sell_price', 'sell_level', 'sell_local_id'
                ])
                writer.writeheader()
                for e in self.entries:
                    writer.writerow(e.to_dict())
    
    def load_from_csv(self, path: str = None) -> None:
        """从CSV加载仓位 - 支持按 entry_id 去重加载
        
        合并策略：内存中已有的条目优先保留（状态可能更新），CSV中新增的条目追加
        """
        with self._lock:
            if path is None:
                path = self.csv_path
            if path is None or not os.path.exists(path):
                return
            
            # 【修改】内存中的条目优先，CSV只补充内存中没有的条目
            existing_ids = {e.entry_id for e in self.entries}
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        new_entry = PositionEntry.from_dict(row)
                        if new_entry.entry_id not in existing_ids:
                            # 只追加内存中不存在的条目
                            self.entries.append(new_entry)
                            existing_ids.add(new_entry.entry_id)
            except Exception as e:
                print(f"加载CSV失败: {e}")
    
    def _check_and_log_removals(self, csv_path: str) -> None:
        """保存前检查：对比磁盘上的CSV，记录消失的条目到removed_positions.csv"""
        try:
            if not os.path.exists(csv_path):
                return
            
            # 读取磁盘上的条目ID
            disk_entries = {}
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('entry_id'):
                        disk_entries[row['entry_id']] = row
            
            # 当前内存中的条目ID
            mem_ids = {e.entry_id for e in self.entries}
            
            # 找出被删除的条目（磁盘上有但内存中没有的）
            removed_ids = set(disk_entries.keys()) - mem_ids
            if not removed_ids:
                return
            
            # 记录到删除日志
            import traceback
            log_dir = os.path.dirname(csv_path)
            log_file = os.path.join(log_dir, 'removed_positions.csv')
            file_exists = os.path.exists(log_file)
            
            # 获取调用栈信息
            stack_info = ''.join(traceback.format_stack()[-5:-1]).replace('\n', ' | ')
            
            with open(log_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        'remove_time', 'entry_id', 'level_index', 'buy_price', 'qty',
                        'sell_order_id', 'sell_status', 'sell_price', 'sell_level', 'call_stack'
                    ])
                
                remove_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for eid in removed_ids:
                    row = disk_entries[eid]
                    writer.writerow([
                        remove_time, row.get('entry_id',''), row.get('level_index',''),
                        row.get('buy_price',''), row.get('qty',''),
                        row.get('sell_order_id',''), row.get('sell_status',''),
                        row.get('sell_price',''), row.get('sell_level',''),
                        stack_info
                    ])
            
            print(f"[删除日志] {len(removed_ids)}条仓位被移除: {removed_ids}")
        except Exception as e:
            print(f"[删除日志] 记录失败: {e}")
    
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

