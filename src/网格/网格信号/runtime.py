from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, time as dtime
from typing import Callable, Optional

import pandas as pd

from .grid_engine import GridEngine, GridSpec
from .order_sim import OrderSimulator, Trade
from .position_book import PositionBook
from .reporter import Reporter


def within_trading_window(now: datetime) -> bool:
    t = now.time()
    morning_start = dtime(9, 30)
    morning_end = dtime(11, 30)
    afternoon_start = dtime(13, 0)
    afternoon_end = dtime(15, 1)
    return (morning_start <= t <= morning_end) or (afternoon_start <= t <= afternoon_end)


def wait_until_open(get_quote: Callable[[], pd.DataFrame], symbol: str, poll_interval: float = 1.9) -> float:
    """
    等到 >= 09:30，获取当日open作为baseline。若已过开盘，直接取快照open。
    """
    while True:
        now = datetime.now()
        if now.time() >= dtime(9, 30):
            df = get_quote()
            row = df.loc[symbol]
            open_px = row.get("open")
            if pd.notna(open_px) and float(open_px) > 0:
                return float(open_px)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now_str}] 休息 {poll_interval:.1f} 秒 (等待9:30开盘)")
        time.sleep(poll_interval)


@dataclass
class RuntimeConfig:
    symbol: str = "512710.SH"
    step: float = 0.001
    up_grids: int = 10
    down_grids: int = 20
    lot_per_grid: int = 10
    hand_size: int = 100
    out_dir: str = "data/grid"
    tick_interval: float = 1.9
    baseline: Optional[float] = None  # 若提供则直接使用该基准价；否则使用9:30开盘价

    @property
    def qty_per_fill(self) -> int:
        return self.lot_per_grid * self.hand_size


class GridRuntime:
    def __init__(self, cfg: RuntimeConfig, get_quote: Callable[[], pd.DataFrame]):
        self.cfg = cfg
        self.get_quote = get_quote
        self._debug_mode = getattr(get_quote, "_is_debug_source", False)
        self.spec: Optional[GridSpec] = None
        self.engine: Optional[GridEngine] = None
        self.pos_book = PositionBook()
        self.ord_sim = OrderSimulator()
        self.reporter = Reporter(out_dir=cfg.out_dir, symbol=cfg.symbol)
        self._last_px: Optional[float] = None

    def _current_price_from_df(self, df: pd.DataFrame) -> Optional[float]:
        row = df.loc[self.cfg.symbol]
        px = row.get("price")
        if pd.notna(px) and float(px) > 0:
            return float(px)
        bid1 = row.get("bid1")
        ask1 = row.get("ask1")
        if pd.notna(bid1) and pd.notna(ask1):
            mid = (float(bid1) + float(ask1)) / 2.0
            if mid > 0:
                return mid
        # 回退使用上一次价格
        return self._last_px

    def _ts(self) -> str:
        """返回当前时间的字符串表示，用于记录成交/日志时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _sleep_with_log(self, duration: float, reason: str = "") -> None:
        """打印当前时间和休息时长，然后sleep"""
        now_str = self._ts()
        reason_str = f" ({reason})" if reason else ""
        print(f"[{now_str}] 休息 {duration:.1f} 秒{reason_str}")
        # 调试模式下直接跳过等待，加快历史数据回放
        if not self._debug_mode:
            time.sleep(duration)

    def _init_grid(self) -> None:
        if self.cfg.baseline is not None:
            baseline = float(self.cfg.baseline)
            source = "Manual"
        else:
            baseline = wait_until_open(self.get_quote, self.cfg.symbol, self.cfg.tick_interval)
            source = "Open9:30"
        self.spec = GridSpec(baseline=baseline, step=self.cfg.step, up_grids=self.cfg.up_grids, down_grids=self.cfg.down_grids)
        self.engine = GridEngine(self.spec)
        min_px, max_px = self.engine.bounds()
        print(f"[{self._ts()}] Baseline({source})={baseline:.6f}, Grid [{min_px:.6f}, {max_px:.6f}]")
        try:
            levels_str = ", ".join(f"{px:.6f}" for px in self.engine.levels)
            print(f"[{self._ts()}] Levels: {levels_str}")
        except Exception:
            pass
        
        # 初始化：默认所有上网格都有仓位
        qty = self.cfg.qty_per_fill
        for level_idx in range(1, self.spec.max_level_index + 1):
            # 使用baseline价格作为初始成本价
            self.pos_book.set_holding(level_idx, baseline, qty)
        print(f"[{self._ts()}] 初始化完成：所有上网格(1到{self.spec.max_level_index})已设置仓位，每格{qty}股")

    def _handle_level_event(self, level_index: int, price: float) -> None:
        """
        新的买卖逻辑：
        1. 若该网格已经发出订单且没有成交，则等待下一个价格
        2. 若没有发出订单：
           - 若当前价格网格或以下网格有仓位：卖出这些仓位总和；同时确保当前价格以下5个网格都有买入订单（买入成功时仓位挂在上一个网格）
           - 否则：确保当前价格以下4个网格有买入订单，判断上一网格是否有仓位，若无且当前网格还没买入订单的，下买入订单
        3. debug模式：价格到达网格时，订单都假设成功成交
        """
        assert self.engine and self.spec
        qty = self.cfg.qty_per_fill
        ts = self._ts()

        # 1) 若该网格已经发出订单且没有成交，则等待下一个价格
        if self.ord_sim.has_order(level_index):
            print(f"[{ts}] 层级 {level_index} 已有订单未成交，等待下一个价格")
            return

        # 2) 检查当前价格网格或以下网格是否有仓位
        total_qty_below = 0
        levels_with_pos = []
        for idx in range(self.spec.min_level_index, level_index + 1):
            pos = self.pos_book.get(idx)
            if pos.qty > 0:
                total_qty_below += pos.qty
                levels_with_pos.append(idx)

        if total_qty_below > 0:
            # 有仓位：挂卖单卖出这些仓位
            for idx in levels_with_pos:
                pos = self.pos_book.get(idx)
                sell_qty = pos.qty
                if sell_qty > 0 and not self.ord_sim.has_order(idx, "SELL"):
                    self.ord_sim.place(idx, "SELL", sell_qty)
                    print(f"[{ts}] 挂单: SELL | 层级: {idx} | 数量: {sell_qty}")
        else:
            # 无仓位：判断上一网格是否已经有仓位，若无且当前网格还没买入订单的，下买入订单
            up_idx = level_index + 1
            if up_idx <= self.spec.max_level_index:
                up_pos = self.pos_book.get(up_idx)
                if up_pos.qty <= 0 and not self.ord_sim.has_order(level_index, "BUY"):
                    self.ord_sim.place(level_index, "BUY", qty)
                    print(f"[{ts}] 挂单: BUY | 层级: {level_index} | 数量: {qty}")
        
        # 每个价格时刻都确保挂单（不依赖是否有仓位）
        # 确保当前价格及以上5个网格（共5个网格：level_index 到 level_index+4）都有卖出订单
        for idx in range(level_index, min(self.spec.max_level_index + 1, level_index + 5)):
            pos = self.pos_book.get(idx)
            if pos.qty > 0 and not self.ord_sim.has_order(idx, "SELL"):
                self.ord_sim.place(idx, "SELL", pos.qty)
                print(f"[{ts}] 挂单: SELL | 层级: {idx} | 数量: {pos.qty}")
        
        # 确保当前价格以下5个网格都有买入订单（买入成功时仓位挂在上一个网格）
        for idx in range(max(self.spec.min_level_index, level_index - 5), level_index):
            if not self.ord_sim.has_order(idx, "BUY"):
                self.ord_sim.place(idx, "BUY", qty)
                print(f"[{ts}] 挂单: BUY | 层级: {idx} | 数量: {qty} (买入成功时仓位挂在上一个网格)")

        # 3) 处理买入订单成交（当价格到达该网格时）
        # 当价格到达某个网格时，检查该网格是否有买入订单需要成交
        if self.ord_sim.has_order(level_index, "BUY"):
            matched = self.ord_sim.match_if_any(level_index, ts, price)
            if matched:
                mode_str = "调试模式" if self._debug_mode else "实时模式"
                print(f"[{matched.ts}] {matched.side} 成交({mode_str}) | 价格: {matched.price:.6f} | 数量: {matched.qty} | 层级: {level_index}")
                self.reporter.log_trade(matched)
                # 买入成功时仓位挂在上一个网格
                target_level = level_index + 1
                if target_level <= self.spec.max_level_index:
                    self.pos_book.buy_at_level(target_level, matched.price, matched.qty)
                    print(f"[{ts}] 买入成功，仓位挂在层级: {target_level}")
                else:
                    # 如果上一个网格越界，则挂在当前网格
                    self.pos_book.buy_at_level(level_index, matched.price, matched.qty)
                    print(f"[{ts}] 买入成功，仓位挂在层级: {level_index} (上一网格越界)")
        
        # 4) 处理卖出订单成交（当价格到达该网格时）
        if self.ord_sim.has_order(level_index, "SELL"):
            matched = self.ord_sim.match_if_any(level_index, ts, price)
            if matched:
                mode_str = "调试模式" if self._debug_mode else "实时模式"
                print(f"[{matched.ts}] {matched.side} 成交({mode_str}) | 价格: {matched.price:.6f} | 数量: {matched.qty} | 层级: {level_index}")
                self.reporter.log_trade(matched)
                # 卖出成功，减少对应网格的仓位
                realized_qty = self.pos_book.sell_at_level(level_index, matched.qty)
                if realized_qty < matched.qty:
                    print(f"[{ts}] 警告: 卖出数量 {matched.qty} 超过可用仓位 {realized_qty}")

    def run(self) -> None:
        # 初始化网格（等待并获取9:30 open）
        self._init_grid()
        assert self.engine and self.spec

        try:
            while True:
                now = datetime.now()
                # 收盘后统一输出报表并退出循环
                if not self._debug_mode and now.time() > dtime(15, 1):
                    self.reporter.flush_end_of_day(now, self.pos_book.snapshot(), self.spec.level_price)
                    print(f"[{self._ts()}] EOD reports written.")
                    break

                try:
                    df = self.get_quote()
                except StopIteration:
                    if self._debug_mode:
                        self.reporter.flush_end_of_day(now, self.pos_book.snapshot(), self.spec.level_price)
                        print(f"[{self._ts()}] Debug tick playback completed. Reports written.")
                    break

                if self.cfg.symbol not in df.index:
                    self._sleep_with_log(self.cfg.tick_interval, "标的不在行情中")
                    continue

                current_px = self._current_price_from_df(df)
                if current_px is None:
                    self._sleep_with_log(self.cfg.tick_interval, "无法获取价格")
                    continue

                # 打印当前价格
                if self._debug_mode:
                    # Debug模式：从DataFrame中获取时间戳
                    row = df.loc[self.cfg.symbol]
                    timestamp = row.get("servertime", self._ts())
                    print(f"[{timestamp}] 当前价格: {current_px:.6f}")
                else:
                    print(f"[{self._ts()}] 当前价格: {current_px:.6f}")

                # 越界处理/恢复
                crossed = self.engine.update_and_get_crossed_levels(current_px)
                self._last_px = current_px

                if not self._debug_mode and not within_trading_window(now):
                    self._sleep_with_log(self.cfg.tick_interval, "非交易时段")
                    continue

                if self.engine.halted:
                    self._sleep_with_log(self.cfg.tick_interval, "价格越界暂停")
                    continue

                # 逐个触发处理
                for lvl_idx in crossed:
                    self._handle_level_event(lvl_idx, self.spec.level_price(lvl_idx))

                # debug模式：价格到达网格时，检查所有订单，自动成交符合条件的订单
                if self._debug_mode and current_px is not None:
                    for idx in range(self.spec.min_level_index, self.spec.max_level_index + 1):
                        # 处理买入订单：只有当当前价格 <= 订单价格时才能成交
                        if self.ord_sim.has_order(idx, "BUY"):
                            order_price = self.spec.level_price(idx)
                            if current_px <= order_price:
                                matched = self.ord_sim.match_if_any(idx, self._ts(), order_price)  # 尝试在该层级以给定价格生成成交记录（若有挂单）
                                if matched:
                                    print(f"[{matched.ts}] {matched.side} 成交(调试模式) | 价格: {matched.price:.6f} | 数量: {matched.qty} | 层级: {idx} | 当前价格: {current_px:.6f}")
                                    self.reporter.log_trade(matched)
                                    # 买入成功时仓位挂在上一个网格
                                    target_level = idx + 1
                                    if target_level <= self.spec.max_level_index:
                                        self.pos_book.buy_at_level(target_level, matched.price, matched.qty)
                                        print(f"[{matched.ts}] 买入成功，仓位挂在层级: {target_level}")
                                    else:
                                        # 如果上一个网格越界，则挂在当前网格
                                        self.pos_book.buy_at_level(idx, matched.price, matched.qty)
                                        print(f"[{matched.ts}] 买入成功，仓位挂在层级: {idx} (上一网格越界)")
                        
                        # 处理卖出订单：只有当当前价格 >= 订单价格时才能成交
                        if self.ord_sim.has_order(idx, "SELL"):
                            order_price = self.spec.level_price(idx)
                            if current_px >= order_price:
                                matched = self.ord_sim.match_if_any(idx, self._ts(), order_price)
                                if matched:
                                    print(f"[{matched.ts}] {matched.side} 成交(调试模式) | 价格: {matched.price:.6f} | 数量: {matched.qty} | 层级: {idx} | 当前价格: {current_px:.6f}")
                                    self.reporter.log_trade(matched)
                                    # 卖出成功，减少对应网格的仓位
                                    realized_qty = self.pos_book.sell_at_level(idx, matched.qty)
                                    if realized_qty < matched.qty:
                                        print(f"[{matched.ts}] 警告: 卖出数量 {matched.qty} 超过可用仓位 {realized_qty}")

                self._sleep_with_log(self.cfg.tick_interval, "正常轮询" if not self._debug_mode else "正常轮询(调试)")
        except KeyboardInterrupt:
            now = datetime.now()
            self.reporter.flush_end_of_day(now, self.pos_book.snapshot(), self.spec.level_price)
            print(f"[{self._ts()}] Interrupted. EOD reports written.")


