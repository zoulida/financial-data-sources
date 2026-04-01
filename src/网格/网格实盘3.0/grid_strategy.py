"""
网格交易策略核心模块

职责：
- 网格初始化（基准价 → 网格层级）
- Tick 数据处理与事件路由
- 买卖决策逻辑（层级事件处理）
- 仓位检查与卖单管理
- 模拟撮合（模拟模式）
- 应急卖单
- 日终报告输出

注意：本模块仅负责交易决策，
      订单同步由 OrderManager 负责，
      券商交互由 BrokerGateway 负责。
"""
from __future__ import annotations

import csv
import os
import traceback
from datetime import datetime, time as dtime
from typing import Any, Callable, Dict, List, Optional

from vnpy_ctastrategy import CtaTemplate, BarData, TickData, TradeData, OrderData

from .config import DefaultParams, OrderConst, PositionStatus
from .models import GridSpec, Trade
from .grid_engine import GridEngine
from .position_book import PositionBook
from .order_manager import OrderManager
from .reporter import Reporter
from .utils import within_trading_window


class GridStrategy(CtaTemplate):
    """
    网格交易策略

    核心逻辑：
        1. 在基准价上下建立等距网格
        2. 价格触及网格时触发买卖事件
        3. 买入后在高一格处挂卖单
        4. 卖出后释放仓位，等待下次买入

    模块协作：
        - GridEngine    : 价格 ↔ 层级映射
        - PositionBook  : 仓位记录 CRUD
        - OrderManager  : 订单状态管理与同步
        - BrokerGateway : 券商下单（通过 _order_placer 回调注入）
        - Reporter      : 交易配对与日终报告
    """

    author = "网格交易策略 v3.0"

    # ── 策略参数（可通过 setting 覆盖） ──
    step: float = DefaultParams.STEP
    up_grids: int = DefaultParams.UP_GRIDS
    down_grids: int = DefaultParams.DOWN_GRIDS
    lot_per_grid: int = DefaultParams.LOT_PER_GRID
    hand_size: int = DefaultParams.HAND_SIZE
    baseline: Optional[float] = None  # 若提供则直接使用；否则使用开盘价

    parameters = ["step", "up_grids", "down_grids", "lot_per_grid", "hand_size", "baseline"]
    variables = ["spec", "engine", "pos_book", "initialized", "last_price"]

    # ==============================================================
    #  初始化
    # ==============================================================
    def __init__(
        self,
        cta_engine,
        strategy_name: str,
        vt_symbol: str,
        setting: Dict[str, Any],
        manager=None,
    ) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 策略管理器引用（用于访问 broker）
        self.manager = manager

        # ── 网格组件 ──
        self.spec: Optional[GridSpec] = None
        self.engine: Optional[GridEngine] = None

        # ── 仓位簿 ──
        self.pos_book = PositionBook()
        self._setup_position_csv_path(vt_symbol)

        # ── 订单管理器 ──
        self.order_mgr = OrderManager(self.pos_book, log_fn=self.write_log)

        # ── 交易报告器 ──
        strategy_dir = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(strategy_dir, "trading_records")
        self.reporter = Reporter(out_dir=out_dir, symbol=vt_symbol)

        # ── 状态变量 ──
        self.initialized = False
        self.last_price: Optional[float] = None
        self._baseline_set = False
        self._simulate_mode = setting.get("simulate_mode", False)
        self._order_placer: Optional[Callable] = None
        self._pos_loaded_from_text = False
        self.trades: List[Trade] = []

        # ── 应急卖单 ──
        self._max_position_trigger_count = 0
        self._setup_emergency_log(vt_symbol)

    def _setup_position_csv_path(self, vt_symbol: str) -> None:
        """设置仓位 CSV 文件路径"""
        strategy_dir = os.path.dirname(os.path.abspath(__file__))
        pos_dir = os.path.join(strategy_dir, "positionsRecord")
        os.makedirs(pos_dir, exist_ok=True)
        symbol_clean = vt_symbol.replace(".", "")
        self.pos_book.csv_path = os.path.join(pos_dir, f"grid_positions_{symbol_clean}.csv")

    def _setup_emergency_log(self, vt_symbol: str) -> None:
        """初始化应急卖单触发记录文件"""
        strategy_dir = os.path.dirname(os.path.abspath(__file__))
        symbol_clean = vt_symbol.replace(".", "")
        today = datetime.now().strftime("%Y%m%d")
        emergency_dir = os.path.join(strategy_dir, "trading_records", symbol_clean, today)
        os.makedirs(emergency_dir, exist_ok=True)
        self._emergency_log_path = os.path.join(emergency_dir, "emergency_sell_triggers.csv")
        try:
            with open(self._emergency_log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "current_price", "sell_price", "sell_level", "trigger_count"])
        except Exception as e:
            self.write_log(f"初始化应急卖单日志失败: {e}")

    # ==============================================================
    #  重写基类方法（兼容 cta_engine=None 的独立运行模式）
    # ==============================================================
    def write_log(self, msg: str) -> None:
        """日志输出：有 cta_engine 则走框架日志，否则直接 print"""
        if self.cta_engine is not None:
            self.cta_engine.write_log(msg, self)
        else:
            print(f"[GridStrategy] {msg}")

    def put_event(self) -> None:
        """UI 事件推送：有 cta_engine 则推送，否则忽略"""
        if self.cta_engine is not None:
            self.cta_engine.put_strategy_event(self)

    # ==============================================================
    #  属性
    # ==============================================================
    @property
    def qty_per_fill(self) -> int:
        """每格成交数量"""
        return self.lot_per_grid * self.hand_size

    # ==============================================================
    #  生命周期回调
    # ==============================================================
    def on_init(self) -> None:
        """策略初始化"""
        self.write_log("网格策略已初始化")

    def on_start(self) -> None:
        """策略启动"""
        self.write_log("网格策略已启动，等待开盘价确定基准价...")
        # 加载已有仓位
        if self.pos_book.csv_path and os.path.exists(self.pos_book.csv_path):
            self.pos_book.load_from_csv()
            self.write_log(f"已加载仓位记录: {len(self.pos_book.entries)}条")

    def on_stop(self) -> None:
        """策略停止"""
        self.write_log("网格策略已停止")
        # 保存仓位
        if self.pos_book.csv_path:
            self.pos_book.save_to_csv()
            self.write_log(f"仓位已保存到: {self.pos_book.csv_path}")
        # 日终报告
        if self.spec and self.engine:
            self._flush_end_of_day_report()

    def on_bar(self, bar: BarData) -> None:
        """K线回调（网格策略主要使用 tick 数据，此处留空）"""
        pass

    def on_order(self, order: OrderData) -> None:
        """订单状态变化回调"""
        pass

    def on_trade(self, trade: TradeData) -> None:
        """成交回调"""
        self.put_event()

    def set_order_placer(self, placer: Callable) -> None:
        """注入真实下单函数（由 strategy_manager 调用）"""
        self._order_placer = placer

    # ==============================================================
    #  Tick 处理（主入口）
    # ==============================================================
    def on_tick(self, tick: TickData) -> None:
        """
        Tick 数据更新回调 —— 策略主循环

        处理流程：
            1. 交易时段检查
            2. 获取当前价格
            3. 更新涨跌停价格
            4. 网格初始化（首次）
            5. 越界检测
            6. 层级事件处理（买卖决策）
            7. 模拟撮合（模拟模式）
            8. 仓位检查（订单同步、挂卖单）
            9. 保存仓位到 CSV
        """
        try:
            now = datetime.now()

            # 定期清理过期挂单（每5分钟）
            if now.minute % 5 == 0 and now.second < 5:
                self.order_mgr.cleanup_old_pending()

            # 交易时段检查（模拟模式跳过）
            if not self._simulate_mode and not within_trading_window(now):
                return

            # ── 获取当前价格 ──
            current_price = self._extract_price(tick)
            if current_price is None:
                return

            # ── 更新涨跌停价格 ──
            if hasattr(tick, "limit_up") and tick.limit_up > 0:
                self.order_mgr.update_price_limits(tick.limit_up, tick.limit_down)

            # ── 网格初始化 ──
            if not self.initialized:
                if not self._try_init_grid(tick, current_price, now):
                    return

            if not self.initialized or self.engine is None or self.spec is None:
                return

            # ── 打印当前价格 ──
            self.write_log(f"当前价格: {current_price:.6f}{'—' * 80}")

            # ── 越界处理 ──
            crossed = self.engine.update_and_get_crossed_levels(current_price)
            self.last_price = current_price

            if self.engine.halted:
                self._log_out_of_bounds(current_price)
                return

            # ── 层级事件处理（核心决策逻辑） ──
            current_level = self.engine.price_to_level_index(current_price)
            if current_level is not None:
                self._handle_level_event(current_level, current_price)
            elif crossed:
                last_crossed = crossed[-1]
                self._handle_level_event(last_crossed, current_price)

            # ── 模拟撮合 ──
            if self._simulate_mode:
                tick_time = tick.datetime.strftime("%Y-%m-%d %H:%M:%S") if tick.datetime else now.strftime("%Y-%m-%d %H:%M:%S")
                self._simulate_matching(current_price, tick_time)

            # ── 仓位检查（同步 + 挂卖单） ──
            self._check_positions_on_tick(current_price)

            # ── 保存仓位 ──
            if self.pos_book.csv_path:
                self.pos_book.save_to_csv()

            self.put_event()

        except Exception as e:
            self.write_log(f"处理tick数据失败: {e}")
            traceback.print_exc()

    # ==============================================================
    #  网格初始化
    # ==============================================================
    def _try_init_grid(self, tick: TickData, current_price: float, now: datetime) -> bool:
        """
        尝试初始化网格

        Returns:
            True = 已初始化（或本次成功初始化），False = 尚未初始化
        """
        if self.baseline is not None and not self._baseline_set:
            # 使用手动指定的 baseline
            self._init_grid(float(self.baseline))
            self._baseline_set = True
            return True

        if self._simulate_mode:
            # 模拟模式：直接使用开盘价或当前价
            bl = self._get_baseline_from_open(tick)
            if bl is None or bl <= 0:
                bl = current_price if current_price > 0 else tick.pre_close
            if bl and bl > 0:
                self._init_grid(bl)
                return True
            return False

        # 实盘模式：等待 9:30 开盘价
        if now.time() >= dtime(9, 30):
            bl = self._get_baseline_from_open(tick)
            if bl is not None:
                self._init_grid(bl)
                return True
        return False

    def _init_grid(self, baseline: float) -> None:
        """初始化网格引擎"""
        self.spec = GridSpec(
            baseline=baseline,
            step=self.step,
            up_grids=self.up_grids,
            down_grids=self.down_grids,
        )
        self.engine = GridEngine(self.spec)
        low_px, high_px = self.engine.bounds()
        self.write_log(f"Baseline={baseline:.6f}, Grid [{low_px:.6f}, {high_px:.6f}]")

        if self._pos_loaded_from_text:
            self.write_log("网格初始化完成：已从历史文件加载仓位")
        else:
            self.write_log("网格初始化完成：等待价格触发交易")
        self.initialized = True

    def _get_baseline_from_open(self, tick: TickData) -> Optional[float]:
        """从 tick 数据获取开盘价作为基准价"""
        if tick.open_price and tick.open_price > 0:
            return float(tick.open_price)
        return None

    # ==============================================================
    #  辅助方法
    # ==============================================================
    def _extract_price(self, tick: TickData) -> Optional[float]:
        """从 tick 中提取有效价格"""
        price = tick.last_price
        if price <= 0:
            if tick.bid_price_1 > 0 and tick.ask_price_1 > 0:
                price = (tick.bid_price_1 + tick.ask_price_1) / 2.0
            else:
                return None
        return price

    def _log_out_of_bounds(self, current_price: float) -> None:
        """打印价格越界的详细信息"""
        self.write_log(
            f"⚠️ 价格越界暂停 | 当前价:{current_price:.6f} | "
            f"涨停:{self.order_mgr._limit_up:.6f} | 跌停:{self.order_mgr._limit_down:.6f} | "
            f"网格范围:[{self.spec.min_level_index}~{self.spec.max_level_index}]"
        )

    def _get_current_price_grid(self, current_price: float) -> Optional[int]:
        """
        获取当前价格网格（小于等于当前价格的第一个网格）
        """
        if not self.spec or not self.engine:
            return None
        level = self.engine.price_to_level_index(current_price)
        if level is None:
            return None
        grid_price = self.spec.level_price(level)
        if grid_price > current_price and level > self.spec.min_level_index:
            level -= 1
        return level

    def _get_broker_data(self):
        """获取券商相关数据（统一入口，减少重复代码）"""
        if not self.manager or not hasattr(self.manager, "broker") or not self.manager.broker.is_connected:
            return None, [], []
        broker = self.manager.broker
        unfilled = broker.get_my_unfilled_orders()
        all_orders = broker.get_my_all_orders()
        return broker, unfilled, all_orders

    # ==============================================================
    #  层级事件处理（核心决策）
    # ==============================================================
    def _handle_level_event(self, level_index: int, current_price: float) -> None:
        """
        处理网格层级事件 —— 核心买卖决策

        步骤：
            0.5 补全缺失的 buy_order_id
            0.6 同步本地挂单状态
            1.  确保当前价格以下 4 个网格有买单
            2.  若当前网格已有未成交订单 → 等待
            3.  若当前网格和上一网格无仓位 → 挂买单
        """
        assert self.engine and self.spec

        broker, unfilled_orders, all_orders = self._get_broker_data()

        # ── 0.5 补全缺失的 buy_order_id ──
        if unfilled_orders:
            self.order_mgr.fill_missing_buy_order_ids(unfilled_orders, self.manager.stock_code if self.manager else "")

        # ── 0.6 同步本地挂单与券商订单 ──
        self.order_mgr.sync_local_pending_with_broker(
            unfilled_orders, self.manager.stock_code if self.manager else ""
        )

        # ── 0. 获取当前价格网格 ──
        current_level = self._get_current_price_grid(current_price)
        if current_level is None:
            return

        stock_code = self.manager.stock_code if self.manager else ""

        # ── 1. 确保当前价格以下 4 个网格有买单 ──
        self._ensure_buy_orders_below(current_level, unfilled_orders, stock_code)

        # ── 2. 当前网格有未成交订单 → 等待 ──
        if self.order_mgr.has_pending(current_level, "BUY") or self.order_mgr.has_pending(current_level, "SELL"):
            self.write_log(f"当前价格网格 {current_level} 已有未成交订单，等待")
            return

        # ── 3. 当前网格无仓位且上一网格无仓位 → 挂买单 ──
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

        # ── 同一层级已有 pending 记录 → 跳过 ──
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

            # ── 检查是否已有该价格卖单 ──
            broker, unfilled, _ = self._get_broker_data()
            stock_code = self.manager.stock_code if self.manager else ""
            if unfilled and self.order_mgr.has_real_sell_order_at_level(sell_level, self.spec, unfilled, stock_code):
                self.write_log(f"跳过挂卖单: 层级{sell_level}已有在途卖单 | 仓位ID={entry.entry_id}")
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
    def _check_positions_on_tick(self, current_price: float) -> None:
        """
        每个 tick 检查仓位状态

        步骤：
            0. 同步买单状态 (pending → BuyFilled / 删除)
            1. 同步卖单状态 (hanging → filled / cancelled)
            2. 检查非今日仓位
            3. 为 BuyFilled/cancelled 仓位挂卖单
        """
        try:
            broker, unfilled, all_orders = self._get_broker_data()

            # 0. 同步买单状态
            if all_orders:
                updated = self.order_mgr.sync_buy_order_status(all_orders)
                if updated:
                    self.pos_book.save_to_csv()

            # 1. 同步卖单状态
            if all_orders:
                updated = self.order_mgr.sync_sell_order_status(all_orders)
                if updated:
                    self.pos_book.save_to_csv()

            # 1.5 清理已成交仓位
            removed = self.pos_book.remove_filled_entries()
            if removed:
                self._log_removed_positions(removed, "filled状态清理")
                self.pos_book.save_to_csv()

            # 2. 检查非今日仓位
            self._check_old_positions()

            # 3. 挂卖单
            self._place_sell_for_pending_positions()

        except Exception as e:
            self.write_log(f"tick仓位检查失败: {e}")

    def _check_old_positions(self) -> None:
        """检查非今日仓位，打印提示"""
        today = datetime.now().strftime("%Y-%m-%d")
        old_entries = self.pos_book.get_old_entries(today)
        for entry in old_entries:
            if entry.sell_status in (PositionStatus.PENDING, PositionStatus.BUY_FILLED):
                self.write_log(
                    f"发现非今日仓位: 仓位ID={entry.entry_id} | "
                    f"买入日期={entry.buy_date} | 状态={entry.sell_status}"
                )

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
