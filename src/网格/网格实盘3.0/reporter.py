"""
交易报告模块

负责交易记录的配对和日终报告生成，包括：
- 低买高卖配对逻辑
- trades.csv   : 成交记录
- pairs.csv    : 配对交易
- positions.csv: 当日仓位快照
- pnl.csv      : 盈亏汇总
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Tuple

from .models import Trade


# ============================================================
#  配对辅助数据结构
# ============================================================
@dataclass
class TradeRemainder:
    """包装 Trade，跟踪剩余未配对数量"""
    trade: Trade
    remaining_qty: int


@dataclass
class Pair:
    """一对已配对的买卖交易"""
    buy_trade_id: int
    buy_order_id: int
    buy_ts: str
    buy_px: float
    sell_trade_id: int
    sell_order_id: int
    sell_ts: str
    sell_px: float
    qty: int

    @property
    def pnl(self) -> float:
        """该配对的盈亏"""
        return (self.sell_px - self.buy_px) * self.qty


# ============================================================
#  报告器
# ============================================================
@dataclass
class Reporter:
    """
    交易报告器

    功能：
        - 记录每笔成交
        - 自动进行低买高卖配对
        - 生成日终报告文件
    """
    out_dir: str
    symbol: str
    realized_pairs: List[Pair] = field(default_factory=list)
    trade_log: List[Trade] = field(default_factory=list)
    _buy_queue: List[TradeRemainder] = field(default_factory=list)
    _sell_queue: List[TradeRemainder] = field(default_factory=list)

    def log_trade(self, tr: Trade) -> None:
        """
        记录一笔成交并尝试配对

        Args:
            tr: 成交记录
        """
        self.trade_log.append(tr)
        self._try_pair(tr)

    # ------------------------------------------------------------------
    #  配对逻辑（内部）
    # ------------------------------------------------------------------
    def _try_pair(self, tr: Trade) -> None:
        """
        低买高卖配对

        规则：
        - 买入时入队，按价格从低到高排序
        - 卖出时入队，按价格从高到低排序
        - 尝试匹配：最低买入 vs 最高卖出，价差为正则配对
        """
        if tr.side == "BUY":
            self._buy_queue.append(TradeRemainder(trade=tr, remaining_qty=tr.qty))
            self._buy_queue.sort(key=lambda x: (x.trade.price, x.trade.trade_id))
        else:
            self._sell_queue.append(TradeRemainder(trade=tr, remaining_qty=tr.qty))

        # 对两个队列排序后尝试匹配
        self._buy_queue.sort(key=lambda x: (x.trade.price, x.trade.trade_id))
        self._sell_queue.sort(key=lambda x: (-x.trade.price, x.trade.trade_id))

        while self._buy_queue and self._sell_queue:
            buy_rem = self._buy_queue[0]
            sell_rem = self._sell_queue[0]

            if buy_rem.trade.price < sell_rem.trade.price:
                qty = min(buy_rem.remaining_qty, sell_rem.remaining_qty)
                self.realized_pairs.append(Pair(
                    buy_trade_id=buy_rem.trade.trade_id,
                    buy_order_id=buy_rem.trade.order_id,
                    buy_ts=buy_rem.trade.ts,
                    buy_px=buy_rem.trade.price,
                    sell_trade_id=sell_rem.trade.trade_id,
                    sell_order_id=sell_rem.trade.order_id,
                    sell_ts=sell_rem.trade.ts,
                    sell_px=sell_rem.trade.price,
                    qty=qty,
                ))
                buy_rem.remaining_qty -= qty
                sell_rem.remaining_qty -= qty
                if buy_rem.remaining_qty <= 0:
                    self._buy_queue.pop(0)
                if sell_rem.remaining_qty <= 0:
                    self._sell_queue.pop(0)
            else:
                break

    # ------------------------------------------------------------------
    #  日终报告
    # ------------------------------------------------------------------
    def flush_end_of_day(
        self,
        trading_day: datetime,
        positions_snapshot: List[Tuple[int, int, float]],
        level_price_func: Callable[[int], float],
    ) -> None:
        """
        生成日终报告文件

        Args:
            trading_day      : 交易日
            positions_snapshot: [(level_index, qty, avg_cost), ...]
            level_price_func : 层级索引 → 价格 的函数
        """
        day_dir = self._day_dir(trading_day)
        os.makedirs(day_dir, exist_ok=True)

        # ── trades.csv ──
        trades_path = os.path.join(day_dir, "trades.csv")
        with open(trades_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["trade_id", "order_id", "ts", "side", "price", "qty", "level_idx"])
            for tr in self.trade_log:
                w.writerow([tr.trade_id, tr.order_id, tr.ts, tr.side, f"{tr.price:.6f}", tr.qty, tr.level_index])

        # ── pairs.csv ──
        pairs_path = os.path.join(day_dir, "pairs.csv")
        with open(pairs_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["buy_trade_id", "buy_order_id", "buy_ts", "buy_px",
                         "sell_trade_id", "sell_order_id", "sell_ts", "sell_px", "qty", "pnl"])
            for p in self.realized_pairs:
                w.writerow([
                    p.buy_trade_id, p.buy_order_id, p.buy_ts, f"{p.buy_px:.6f}",
                    p.sell_trade_id, p.sell_order_id, p.sell_ts, f"{p.sell_px:.6f}",
                    p.qty, f"{p.pnl:.6f}",
                ])

        # ── positions.csv ──
        pos_path = os.path.join(day_dir, "positions.csv")
        total_unreal = 0.0
        with open(pos_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["level_idx", "level_px", "qty", "avg_cost", "unrealized_pnl"])
            for idx, qty, avg_cost in positions_snapshot:
                lp = level_price_func(idx)
                unreal = (lp - avg_cost) * qty if qty > 0 else 0.0
                total_unreal += unreal
                w.writerow([idx, f"{lp:.6f}", qty, f"{avg_cost:.6f}", f"{unreal:.6f}"])

        # ── pnl.csv ──
        realized_total = sum(p.pnl for p in self.realized_pairs)
        pnl_path = os.path.join(day_dir, "pnl.csv")
        with open(pnl_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["total_realized", "total_unrealized", "net"])
            net = realized_total + total_unreal
            w.writerow([f"{realized_total:.6f}", f"{total_unreal:.6f}", f"{net:.6f}"])

    # ------------------------------------------------------------------
    #  内部辅助
    # ------------------------------------------------------------------
    def _day_dir(self, trading_day: datetime) -> str:
        """构建日期目录路径"""
        symbol_clean = self.symbol.replace(".", "")
        return os.path.join(self.out_dir, symbol_clean, trading_day.strftime("%Y%m%d"))
