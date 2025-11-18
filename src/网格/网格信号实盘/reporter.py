from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

from .order_sim import Trade


@dataclass
class TradeRemainder:
    """包装Trade，跟踪剩余未配对数量"""
    trade: Trade
    remaining_qty: int


@dataclass
class Pair:
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
        return (self.sell_px - self.buy_px) * self.qty


@dataclass
class Reporter:
    out_dir: str
    symbol: str
    realized_pairs: List[Pair] = field(default_factory=list)
    trade_log: List[Trade] = field(default_factory=list)
    _buy_queue: List[TradeRemainder] = field(default_factory=list)  # 买入队列，按价格从低到高排序
    _sell_queue: List[TradeRemainder] = field(default_factory=list)  # 卖出队列，按价格从高到低排序

    def log_trade(self, tr: Trade) -> None:
        self.trade_log.append(tr)
        self._try_pair_low_buy_high_sell(tr)

    def _try_pair_low_buy_high_sell(self, tr: Trade) -> None:
        """
        低买高卖配对逻辑：
        - 买入时，尝试匹配价格最高的卖出（如果有）
        - 卖出时，尝试匹配价格最低的买入（如果有）
        """
        if tr.side == "BUY":
            # 买入：尝试匹配价格最高的卖出
            self._buy_queue.append(TradeRemainder(trade=tr, remaining_qty=tr.qty))
            # 按价格从低到高排序（优先匹配价格低的买入）
            self._buy_queue.sort(key=lambda x: (x.trade.price, x.trade.trade_id))
            
            # 尝试配对：卖出队列按价格从高到低排序
            self._sell_queue.sort(key=lambda x: (-x.trade.price, x.trade.trade_id))
            
            while self._buy_queue and self._sell_queue:
                buy_rem = self._buy_queue[0]
                sell_rem = self._sell_queue[0]
                buy = buy_rem.trade
                sell = sell_rem.trade
                
                # 只有买入价格 < 卖出价格时才配对（低买高卖）
                if buy.price < sell.price:
                    qty = min(buy_rem.remaining_qty, sell_rem.remaining_qty)
                    self.realized_pairs.append(Pair(
                        buy_trade_id=buy.trade_id,
                        buy_order_id=buy.order_id,
                        buy_ts=buy.ts,
                        buy_px=buy.price,
                        sell_trade_id=sell.trade_id,
                        sell_order_id=sell.order_id,
                        sell_ts=sell.ts,
                        sell_px=sell.price,
                        qty=qty
                    ))
                    
                    # 减少数量
                    buy_rem.remaining_qty -= qty
                    sell_rem.remaining_qty -= qty
                    
                    # 移除已完全配对的交易
                    if buy_rem.remaining_qty <= 0:
                        self._buy_queue.pop(0)
                    if sell_rem.remaining_qty <= 0:
                        self._sell_queue.pop(0)
                else:
                    # 买入价格 >= 卖出价格，无法配对
                    break
        else:  # SELL
            # 卖出：尝试匹配价格最低的买入
            self._sell_queue.append(TradeRemainder(trade=tr, remaining_qty=tr.qty))
            # 按价格从高到低排序（优先匹配价格高的卖出）
            self._sell_queue.sort(key=lambda x: (-x.trade.price, x.trade.trade_id))
            
            # 尝试配对：买入队列按价格从低到高排序
            self._buy_queue.sort(key=lambda x: (x.trade.price, x.trade.trade_id))
            
            while self._buy_queue and self._sell_queue:
                buy_rem = self._buy_queue[0]
                sell_rem = self._sell_queue[0]
                buy = buy_rem.trade
                sell = sell_rem.trade
                
                # 只有买入价格 < 卖出价格时才配对（低买高卖）
                if buy.price < sell.price:
                    qty = min(buy_rem.remaining_qty, sell_rem.remaining_qty)
                    self.realized_pairs.append(Pair(
                        buy_trade_id=buy.trade_id,
                        buy_order_id=buy.order_id,
                        buy_ts=buy.ts,
                        buy_px=buy.price,
                        sell_trade_id=sell.trade_id,
                        sell_order_id=sell.order_id,
                        sell_ts=sell.ts,
                        sell_px=sell.price,
                        qty=qty
                    ))
                    
                    # 减少数量
                    buy_rem.remaining_qty -= qty
                    sell_rem.remaining_qty -= qty
                    
                    # 移除已完全配对的交易
                    if buy_rem.remaining_qty <= 0:
                        self._buy_queue.pop(0)
                    if sell_rem.remaining_qty <= 0:
                        self._sell_queue.pop(0)
                else:
                    # 买入价格 >= 卖出价格，无法配对
                    break

    def try_pair(self, last_side_state: Dict[int, Trade], tr: Trade) -> None:
        """
        保留此方法以兼容旧代码，但实际配对逻辑在 _try_pair_low_buy_high_sell 中
        """
        pass

    def _ensure_dir(self, day_dir: str) -> None:
        os.makedirs(day_dir, exist_ok=True)

    def _day_dir(self, trading_day: datetime) -> str:
        return os.path.join(self.out_dir, self.symbol.replace(".", ""), trading_day.strftime("%Y%m%d"))

    def flush_end_of_day(self, trading_day: datetime, positions_snapshot: List[Tuple[int, int, float]], level_price_func) -> None:
        day_dir = self._day_dir(trading_day)
        self._ensure_dir(day_dir)

        # trades.csv
        trades_path = os.path.join(day_dir, "trades.csv")
        with open(trades_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["trade_id", "order_id", "ts", "side", "price", "qty", "level_idx"])
            for tr in self.trade_log:
                w.writerow([tr.trade_id, tr.order_id, tr.ts, tr.side, f"{tr.price:.6f}", tr.qty, tr.level_index])

        # pairs.csv
        pairs_path = os.path.join(day_dir, "pairs.csv")
        with open(pairs_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["buy_trade_id", "buy_order_id", "buy_ts", "buy_px", "sell_trade_id", "sell_order_id", "sell_ts", "sell_px", "qty", "pnl"])
            for p in self.realized_pairs:
                w.writerow([
                    p.buy_trade_id, p.buy_order_id, p.buy_ts, f"{p.buy_px:.6f}",
                    p.sell_trade_id, p.sell_order_id, p.sell_ts, f"{p.sell_px:.6f}",
                    p.qty, f"{p.pnl:.6f}"
                ])

        # positions.csv
        pos_path = os.path.join(day_dir, "positions.csv")
        with open(pos_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["level_idx", "level_px", "qty", "avg_cost", "unrealized_pnl"])
            total_unreal = 0.0
            for idx, qty, avg_cost in positions_snapshot:
                lp = level_price_func(idx)
                unreal = (lp - avg_cost) * qty if qty > 0 else 0.0
                total_unreal += unreal
                w.writerow([idx, f"{lp:.6f}", qty, f"{avg_cost:.6f}", f"{unreal:.6f}"])

        # pnl.csv
        realized_total = sum(p.pnl for p in self.realized_pairs)
        pnl_path = os.path.join(day_dir, "pnl.csv")
        with open(pnl_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["total_realized", "total_unrealized", "net"])
            net = realized_total + total_unreal
            w.writerow([f"{realized_total:.6f}", f"{total_unreal:.6f}", f"{net:.6f}"])


