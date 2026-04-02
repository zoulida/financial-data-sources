"""
网格交易策略 —— 主类

本文件只保留：初始化、生命周期、on_tick 主循环、网格初始化、辅助方法。
买卖决策、卖单执行、回调处理、模拟撮合等逻辑通过 Mixin 引入：

    - DecisionMixin  (strategy_decision.py)  : 核心决策 + 买单逻辑
    - ExecutionMixin  (strategy_execution.py) : 卖单 + 成交回调 + 仓位同步
    - AuxiliaryMixin  (strategy_auxiliary.py) : 应急卖单 + 模拟撮合 + 日终报告
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

from .strategy_decision import DecisionMixin
from .strategy_execution import ExecutionMixin
from .strategy_auxiliary import AuxiliaryMixin


class GridStrategy(DecisionMixin, ExecutionMixin, AuxiliaryMixin, CtaTemplate):
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

    Mixin 拆分：
        - DecisionMixin  : 核心决策 + 买单逻辑  (strategy_decision.py)
        - ExecutionMixin  : 卖单 + 成交回调 + 仓位同步  (strategy_execution.py)
        - AuxiliaryMixin  : 应急卖单 + 模拟撮合 + 日终报告  (strategy_auxiliary.py)
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
            8. 保存仓位到 CSV
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
