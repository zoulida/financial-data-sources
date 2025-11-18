"""
网格策略 - vnpy 框架版本
使用 xtquant 订阅实时行情数据

参考 golden_cross_demo.py 的实现方式

使用说明：
1. 设置 xtdata token（在代码中取消注释并填入你的token）
2. 运行脚本：python run_grid_512710_vnpy.py --symbol 512710.SH
3. 策略会自动订阅行情并执行网格交易逻辑

主要改动：
- 将原有的 GridRuntime 改为基于 vnpy CtaTemplate 的 GridStrategy
- 使用 xtdata.subscribe_whole_quote 订阅实时行情
- 保持原有的网格引擎、仓位管理、订单模拟和报告功能
- 支持命令行参数配置策略参数
"""
from __future__ import annotations

import argparse
import time
import traceback
from datetime import datetime, time as dtime
from typing import Any, Dict, Optional

from pathlib import Path
import sys

from xtquant import xtdata
from vnpy_ctastrategy import CtaTemplate, BarGenerator, ArrayManager
from vnpy.trader.constant import Direction, Interval, Offset, Exchange
from vnpy_ctastrategy import BarData, TickData, TradeData, OrderData

if __package__ in {None, ""}:
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent  # path to src/网格
    root_str = str(project_root.parent)  # project root (contains src package)
    if root_str not in sys.path:
        sys.path.append(root_str)
    from src.网格.网格信号实盘.grid_engine import GridEngine, GridSpec
    from src.网格.网格信号实盘.order_sim import OrderSimulator, Trade
    from src.网格.网格信号实盘.position_book import PositionBook
    from src.网格.网格信号实盘.reporter import Reporter
else:
    from .grid_engine import GridEngine, GridSpec
    from .order_sim import OrderSimulator, Trade
    from .position_book import PositionBook
    from .reporter import Reporter


def get_exchange_from_code(stock_code: str) -> Exchange:
    """
    根据股票代码判断交易所
    
    Args:
        stock_code: 股票代码，如 "000001.SZ" 或 "600000.SH"
        
    Returns:
        Exchange 枚举值
    """
    code_upper = stock_code.upper()
    if code_upper.endswith('.SZ'):
        return Exchange.SZSE
    elif code_upper.endswith('.SH'):
        return Exchange.SSE
    elif code_upper.startswith(('0', '3')):
        # 深圳股票：0开头或3开头
        return Exchange.SZSE
    elif code_upper.startswith('6'):
        # 上海股票：6开头
        return Exchange.SSE
    else:
        # 默认返回深圳交易所
        return Exchange.SZSE


def within_trading_window(now: datetime) -> bool:
    """判断是否在交易时段内"""
    t = now.time()
    morning_start = dtime(9, 30)
    morning_end = dtime(11, 30)
    afternoon_start = dtime(13, 0)
    afternoon_end = dtime(15, 1)
    return (morning_start <= t <= morning_end) or (afternoon_start <= t <= afternoon_end)


class GridStrategy(CtaTemplate):
    """
    网格交易策略 - 基于 vnpy 框架
    
    策略逻辑：
    - 在基准价上下建立网格
    - 价格触及网格时自动买卖
    - 买入时仓位挂在上一个网格
    - 卖出时减少对应网格的仓位
    """
    
    author = "网格交易策略"
    
    # 策略参数
    step: float = 0.001
    up_grids: int = 10
    down_grids: int = 20
    lot_per_grid: int = 10
    hand_size: int = 100
    baseline: Optional[float] = None  # 若提供则直接使用该基准价；否则使用9:30开盘价
    
    parameters = ["step", "up_grids", "down_grids", "lot_per_grid", "hand_size", "baseline"]
    variables = ["spec", "engine", "pos_book", "ord_sim", "reporter", "initialized", "last_price"]
    
    def __init__(
        self,
        cta_engine,
        strategy_name: str,
        vt_symbol: str,
        setting: Dict[str, Any],
    ) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # 网格相关组件
        self.spec: Optional[GridSpec] = None
        self.engine: Optional[GridEngine] = None
        self.pos_book = PositionBook()
        self.ord_sim = OrderSimulator()
        
        # 报告器（需要从 setting 中获取 out_dir）
        out_dir = setting.get("out_dir", "data/grid")
        self.reporter = Reporter(out_dir=out_dir, symbol=vt_symbol)
        
        # 状态变量
        self.initialized = False
        self.last_price: Optional[float] = None
        self._baseline_set = False
        
    @property
    def qty_per_fill(self) -> int:
        """每格数量"""
        return self.lot_per_grid * self.hand_size
    
    def on_init(self) -> None:
        """策略初始化时的回调函数"""
        self.write_log("网格策略已初始化")
        # 注意：网格策略不需要加载历史K线，因为它是基于实时价格触发的
    
    def on_start(self) -> None:
        """策略启动时的回调函数"""
        self.write_log("网格策略已启动，等待开盘价确定基准价...")
    
    def on_stop(self) -> None:
        """策略停止时的回调函数"""
        self.write_log("网格策略已停止")
        # 输出日终报告
        if self.spec and self.engine:
            now = datetime.now()
            self.reporter.flush_end_of_day(
                now,
                self.pos_book.snapshot(),
                self.spec.level_price
            )
            self.write_log("日终报告已输出")
    
    def _init_grid(self, baseline: float) -> None:
        """初始化网格"""
        self.spec = GridSpec(
            baseline=baseline,
            step=self.step,
            up_grids=self.up_grids,
            down_grids=self.down_grids
        )
        self.engine = GridEngine(self.spec)
        min_px, max_px = self.engine.bounds()
        
        self.write_log(f"Baseline={baseline:.6f}, Grid [{min_px:.6f}, {max_px:.6f}]")
        
        # 初始化：默认所有上网格都有仓位
        qty = self.qty_per_fill
        for level_idx in range(1, self.spec.max_level_index + 1):
            # 使用baseline价格作为初始成本价
            self.pos_book.set_holding(level_idx, baseline, qty)
        
        self.write_log(f"初始化完成：所有上网格(1到{self.spec.max_level_index})已设置仓位，每格{qty}股")
        self.initialized = True
    
    def _get_baseline_from_open(self, tick: TickData) -> Optional[float]:
        """从tick数据获取开盘价作为基准价"""
        if tick.open_price and tick.open_price > 0:
            return float(tick.open_price)
        return None
    
    def _handle_level_event(self, level_index: int, price: float, current_price: float) -> None:
        """
        处理网格层级事件
        
        新的买卖逻辑：
        1. 若该网格已经发出订单且没有成交，则等待下一个价格
        2. 若没有发出订单：
           - 若当前价格网格或以下网格有仓位：卖出这些仓位总和；同时确保当前价格以下5个网格都有买入订单（买入成功时仓位挂在上一个网格）
           - 否则：确保当前价格以下4个网格有买入订单，判断上一网格是否有仓位，若无且当前网格还没买入订单的，下买入订单
        """
        assert self.engine and self.spec
        qty = self.qty_per_fill
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1) 若该网格已经发出订单且没有成交，则等待下一个价格
        if self.ord_sim.has_order(level_index):
            self.write_log(f"层级 {level_index} 已有订单未成交，等待下一个价格")
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
                    self.write_log(f"挂单: SELL | 层级: {idx} | 数量: {sell_qty}")
        else:
            # 无仓位：判断上一网格是否已经有仓位，若无且当前网格还没买入订单的，下买入订单
            up_idx = level_index + 1
            if up_idx <= self.spec.max_level_index:
                up_pos = self.pos_book.get(up_idx)
                if up_pos.qty <= 0 and not self.ord_sim.has_order(level_index, "BUY"):
                    self.ord_sim.place(level_index, "BUY", qty)
                    self.write_log(f"挂单: BUY | 层级: {level_index} | 数量: {qty}")
        
        # 每个价格时刻都确保挂单（不依赖是否有仓位）
        # 确保当前价格及以上5个网格（共5个网格：level_index 到 level_index+4）都有卖出订单
        for idx in range(level_index, min(self.spec.max_level_index + 1, level_index + 5)):
            pos = self.pos_book.get(idx)
            if pos.qty > 0 and not self.ord_sim.has_order(idx, "SELL"):
                self.ord_sim.place(idx, "SELL", pos.qty)
                self.write_log(f"挂单: SELL | 层级: {idx} | 数量: {pos.qty}")
        
        # 确保当前价格以下5个网格都有买入订单（买入成功时仓位挂在上一个网格）
        for idx in range(max(self.spec.min_level_index, level_index - 5), level_index):
            if not self.ord_sim.has_order(idx, "BUY"):
                self.ord_sim.place(idx, "BUY", qty)
                self.write_log(f"挂单: BUY | 层级: {idx} | 数量: {qty} (买入成功时仓位挂在上一个网格)")
        
        # 3) 处理买入订单成交（当价格到达该网格时）
        if self.ord_sim.has_order(level_index, "BUY"):
            matched = self.ord_sim.match_if_any(level_index, ts, price)
            if matched:
                self.write_log(f"{matched.side} 成交 | 价格: {matched.price:.6f} | 数量: {matched.qty} | 层级: {level_index}")
                self.reporter.log_trade(matched)
                # 买入成功时仓位挂在上一个网格
                target_level = level_index + 1
                if target_level <= self.spec.max_level_index:
                    self.pos_book.buy_at_level(target_level, matched.price, matched.qty)
                    self.write_log(f"买入成功，仓位挂在层级: {target_level}")
                else:
                    # 如果上一个网格越界，则挂在当前网格
                    self.pos_book.buy_at_level(level_index, matched.price, matched.qty)
                    self.write_log(f"买入成功，仓位挂在层级: {level_index} (上一网格越界)")
        
        # 4) 处理卖出订单成交（当价格到达该网格时）
        if self.ord_sim.has_order(level_index, "SELL"):
            matched = self.ord_sim.match_if_any(level_index, ts, price)
            if matched:
                self.write_log(f"{matched.side} 成交 | 价格: {matched.price:.6f} | 数量: {matched.qty} | 层级: {level_index}")
                self.reporter.log_trade(matched)
                # 卖出成功，减少对应网格的仓位
                realized_qty = self.pos_book.sell_at_level(level_index, matched.qty)
                if realized_qty < matched.qty:
                    self.write_log(f"警告: 卖出数量 {matched.qty} 超过可用仓位 {realized_qty}")
    
    def on_tick(self, tick: TickData) -> None:
        """Tick数据更新时的回调函数（推送模式）"""
        try:
            now = datetime.now()
            
            # 检查是否在交易时段
            if not within_trading_window(now):
                return
            
            # 获取当前价格
            current_price = tick.last_price
            if current_price <= 0:
                # 尝试使用买卖价中间价
                if tick.bid_price_1 > 0 and tick.ask_price_1 > 0:
                    current_price = (tick.bid_price_1 + tick.ask_price_1) / 2.0
                else:
                    return
            
            # 初始化网格（如果还未初始化）
            if not self.initialized:
                # 如果提供了baseline，直接使用
                if self.baseline is not None and not self._baseline_set:
                    baseline = float(self.baseline)
                    self._baseline_set = True
                    self._init_grid(baseline)
                # 否则等待9:30开盘价
                elif now.time() >= dtime(9, 30):
                    baseline = self._get_baseline_from_open(tick)
                    if baseline is not None:
                        self._init_grid(baseline)
                    else:
                        return
                else:
                    return
            
            if not self.initialized or self.engine is None or self.spec is None:
                return
            
            # 打印当前价格
            self.write_log(f"当前价格: {current_price:.6f}")
            
            # 越界处理/恢复
            crossed = self.engine.update_and_get_crossed_levels(current_price)
            self.last_price = current_price
            
            if self.engine.halted:
                self.write_log("价格越界暂停")
                return
            
            # 逐个触发处理
            for lvl_idx in crossed:
                grid_price = self.spec.level_price(lvl_idx)
                self._handle_level_event(lvl_idx, grid_price, current_price)
            
            # 处理所有订单的自动成交（当价格满足条件时）
            for idx in range(self.spec.min_level_index, self.spec.max_level_index + 1):
                order_price = self.spec.level_price(idx)
                
                # 处理买入订单：只有当当前价格 <= 订单价格时才能成交
                if self.ord_sim.has_order(idx, "BUY"):
                    if current_price <= order_price:
                        matched = self.ord_sim.match_if_any(idx, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_price)
                        if matched:
                            self.write_log(f"{matched.side} 成交 | 价格: {matched.price:.6f} | 数量: {matched.qty} | 层级: {idx} | 当前价格: {current_price:.6f}")
                            self.reporter.log_trade(matched)
                            # 买入成功时仓位挂在上一个网格
                            target_level = idx + 1
                            if target_level <= self.spec.max_level_index:
                                self.pos_book.buy_at_level(target_level, matched.price, matched.qty)
                                self.write_log(f"买入成功，仓位挂在层级: {target_level}")
                            else:
                                self.pos_book.buy_at_level(idx, matched.price, matched.qty)
                                self.write_log(f"买入成功，仓位挂在层级: {idx} (上一网格越界)")
                
                # 处理卖出订单：只有当当前价格 >= 订单价格时才能成交
                if self.ord_sim.has_order(idx, "SELL"):
                    if current_price >= order_price:
                        matched = self.ord_sim.match_if_any(idx, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_price)
                        if matched:
                            self.write_log(f"{matched.side} 成交 | 价格: {matched.price:.6f} | 数量: {matched.qty} | 层级: {idx} | 当前价格: {current_price:.6f}")
                            self.reporter.log_trade(matched)
                            # 卖出成功，减少对应网格的仓位
                            realized_qty = self.pos_book.sell_at_level(idx, matched.qty)
                            if realized_qty < matched.qty:
                                self.write_log(f"警告: 卖出数量 {matched.qty} 超过可用仓位 {realized_qty}")
            
            self.put_event()
            
        except Exception as e:
            self.write_log(f"处理tick数据失败: {e}")
            traceback.print_exc()
    
    def on_bar(self, bar: BarData) -> None:
        """K线数据更新时的回调函数（网格策略主要使用tick数据）"""
        pass
    
    def on_order(self, order: OrderData) -> None:
        """订单状态变化时的回调函数"""
        pass
    
    def on_trade(self, trade: TradeData) -> None:
        """成交时的回调函数"""
        self.put_event()


class GridStrategyManager:
    """网格策略管理器 - 使用推送模式"""
    
    def __init__(
        self,
        stock_code: str,
        strategy_params: Optional[Dict[str, Any]] = None,
        cta_engine=None
    ):
        """
        初始化策略管理器
        
        Args:
            stock_code: 股票代码，如 "512710.SH"
            strategy_params: 策略参数字典
            cta_engine: vnpy的CTA引擎（可选，如果为None则创建简化版本）
        """
        self.stock_code = stock_code
        self.strategy_params = strategy_params or {}
        self.cta_engine = cta_engine
        self.strategy: Optional[GridStrategy] = None
        self.subscription_id: Optional[int] = None
        
        print(f"初始化网格策略管理器，监控股票: {stock_code}")
    
    def _convert_xtdata_to_tick(self, stock_code: str, tick_data: Dict) -> Optional[TickData]:
        """
        将 xtdata 推送的数据转换为 vn.py 的 TickData 格式
        
        Args:
            stock_code: 股票代码
            tick_data: xtdata 推送的行情数据字典
            
        Returns:
            TickData 对象，如果转换失败返回 None
        """
        try:
            # 获取当前时间
            now = datetime.now()
            
            # 从 tick_data 中提取字段
            last_price = tick_data.get('lastPrice', 0.0)
            last_close = tick_data.get('lastClose', 0.0)
            volume = tick_data.get('volume', 0)
            amount = tick_data.get('amount', 0.0)
            bid_price_1 = tick_data.get('bidPrice1', 0.0)
            ask_price_1 = tick_data.get('askPrice1', 0.0)
            bid_volume_1 = tick_data.get('bidVol1', 0)
            ask_volume_1 = tick_data.get('askVol1', 0)
            open_price = tick_data.get('open', last_close)
            high_price = tick_data.get('high', last_price)
            low_price = tick_data.get('low', last_price)
            
            # 根据股票代码判断交易所
            exchange = get_exchange_from_code(stock_code)
            
            # 创建 TickData 对象
            tick = TickData(
                symbol=stock_code.split('.')[0],
                exchange=exchange,
                datetime=now,
                name=stock_code,
                volume=volume,
                open_interest=0.0,
                last_price=last_price,
                last_volume=0,
                limit_up=0.0,
                limit_down=0.0,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                pre_close=last_close,
                bid_price_1=bid_price_1,
                bid_price_2=0.0,
                bid_price_3=0.0,
                bid_price_4=0.0,
                bid_price_5=0.0,
                ask_price_1=ask_price_1,
                ask_price_2=0.0,
                ask_price_3=0.0,
                ask_price_4=0.0,
                ask_price_5=0.0,
                bid_volume_1=bid_volume_1,
                bid_volume_2=0,
                bid_volume_3=0,
                bid_volume_4=0,
                bid_volume_5=0,
                ask_volume_1=ask_volume_1,
                ask_volume_2=0,
                ask_volume_3=0,
                ask_volume_4=0,
                ask_volume_5=0,
                gateway_name="xtdata"
            )
            
            return tick
        except Exception as e:
            print(f"转换 tick 数据失败 {stock_code}: {e}")
            traceback.print_exc()
            return None
    
    def on_tick_data(self, datas: Dict[str, Dict]):
        """
        行情数据回调函数 - 处理推送的 tick 数据
        
        Args:
            datas: 字典，key 为股票代码，value 为行情数据字典
        """
        try:
            if self.stock_code not in datas:
                return
            
            tick_data = datas[self.stock_code]
            
            # 转换为 TickData
            tick = self._convert_xtdata_to_tick(self.stock_code, tick_data)
            if tick is None:
                return
            
            # 如果有策略实例，将tick传递给策略
            if self.strategy is not None:
                self.strategy.on_tick(tick)
            else:
                # 如果没有策略实例，只打印数据
                print(f"[{self.stock_code}] 收到 tick 数据: 价格={tick.last_price:.2f}, "
                      f"成交量={tick.volume}, 涨跌={(tick.last_price - tick.pre_close) / tick.pre_close * 100:.2f}%")
                    
        except Exception as e:
            print(f"处理 tick 数据失败: {e}")
            traceback.print_exc()
    
    def create_strategy(self, strategy_name: str = "GridStrategy") -> bool:
        """
        创建策略实例
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            bool: 是否成功创建
        """
        try:
            # 如果没有提供 cta_engine，创建一个简化版本
            if self.cta_engine is None:
                # 创建一个简化的 cta_engine 对象（仅用于策略初始化）
                class SimpleCtaEngine:
                    def __init__(self):
                        self.strategies = {}
                    
                    def add_strategy(self, *args, **kwargs):
                        pass
                    
                    def write_log(self, msg: str, strategy=None):
                        prefix = f"[{strategy.strategy_name}]" if strategy else "[SimpleCtaEngine]"
                        print(f"{prefix} {msg}")
                    
                    def put_strategy_event(self, strategy):
                        pass
                
                self.cta_engine = SimpleCtaEngine()
                print("警告: 未提供 cta_engine，使用简化模式（仅模拟交易）")
            
            # 准备策略设置
            setting = {
                "out_dir": self.strategy_params.get("out_dir", "data/grid"),
            }
            
            # 创建策略实例
            self.strategy = GridStrategy(
                cta_engine=self.cta_engine,
                strategy_name=strategy_name,
                vt_symbol=self.stock_code,
                setting=setting
            )
            
            # 设置策略参数
            for key, value in self.strategy_params.items():
                if hasattr(self.strategy, key):
                    setattr(self.strategy, key, value)
            
            # 初始化策略
            self.strategy.on_init()
            self.strategy.on_start()
            
            print(f"策略实例创建成功: {strategy_name}")
            return True
            
        except Exception as e:
            print(f"创建策略实例失败: {e}")
            traceback.print_exc()
            return False
    
    def subscribe_stock_quotes(self) -> bool:
        """
        订阅股票行情
        
        Returns:
            bool: 是否成功订阅
        """
        try:
            # 取消当前订阅
            if self.subscription_id is not None:
                xtdata.unsubscribe_quote(self.subscription_id)
                print(f"取消旧订阅 ID: {self.subscription_id}")
            
            # 创建新的订阅
            self.subscription_id = xtdata.subscribe_whole_quote(
                code_list=[self.stock_code],
                callback=self.on_tick_data
            )
            
            print(f"订阅成功，ID: {self.subscription_id}，订阅股票: {self.stock_code}")
            return True
            
        except Exception as e:
            print(f"订阅股票行情失败: {e}")
            traceback.print_exc()
            return False
    
    def unsubscribe_stock_quotes(self):
        """取消订阅股票行情"""
        try:
            if self.subscription_id is not None:
                xtdata.unsubscribe_quote(self.subscription_id)
                print(f"取消订阅 ID: {self.subscription_id}")
                self.subscription_id = None
        except Exception as e:
            print(f"取消订阅股票行情失败: {e}")
            traceback.print_exc()


def run_realtime_strategy() -> None:
    """
    运行实时网格策略 - 使用推送模式获取数据
    """
    # 设置 xtdata token（需要根据实际情况设置）
    # xtdata.set_token('your_token_here')
    
    # 配置股票代码
    stock_code = "512710.SH"  # 可以根据需要修改
    
    # 策略参数
    strategy_params = {
        "step": 0.001,
        "up_grids": 10,
        "down_grids": 20,
        "lot_per_grid": 10,
        "hand_size": 100,
        "baseline": None,  # 如果提供则使用该值，否则使用9:30开盘价
        "out_dir": "data/grid",
    }
    
    # 创建策略管理器
    manager = GridStrategyManager(stock_code, strategy_params)
    
    # 创建策略实例（简化模式，不需要完整的 cta_engine）
    if not manager.create_strategy():
        print("创建策略失败，退出程序")
        return
    
    # 订阅行情
    if not manager.subscribe_stock_quotes():
        print("订阅失败，退出程序")
        return
    
    print("\n策略已启动，等待行情数据推送...")
    print("按 Ctrl+C 停止策略\n")
    
    try:
        # 保持运行，等待数据推送
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n收到停止信号，正在取消订阅...")
        if manager.strategy:
            manager.strategy.on_stop()
        manager.unsubscribe_stock_quotes()
        print("策略已停止")


def main(argv: list[str] | None = None) -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Run grid strategy with vnpy framework")
    parser.add_argument("--symbol", default="512710.SH", help="股票代码")
    parser.add_argument("--step", type=float, default=0.001, help="网格步长")
    parser.add_argument("--up_grids", type=int, default=10, help="向上网格数")
    parser.add_argument("--down_grids", type=int, default=20, help="向下网格数")
    parser.add_argument("--lot_per_grid", type=int, default=2, help="每格手数")
    parser.add_argument("--hand_size", type=int, default=100, help="每手股数")
    parser.add_argument("--out_dir", default="data/grid", help="输出目录")
    parser.add_argument(
        "--baseline",
        type=float,
        default=None,
        help="若提供则使用该基准价（例如 0.680）；否则用9:30开盘价",
    )
    
    args = parser.parse_args(argv)
    
    # 策略参数
    strategy_params = {
        "step": args.step,
        "up_grids": args.up_grids,
        "down_grids": args.down_grids,
        "lot_per_grid": args.lot_per_grid,
        "hand_size": args.hand_size,
        "baseline": args.baseline,
        "out_dir": args.out_dir,
    }
    
    # 创建策略管理器
    manager = GridStrategyManager(args.symbol, strategy_params)
    
    # 创建策略实例（简化模式，不需要完整的 cta_engine）
    if not manager.create_strategy():
        print("创建策略失败，退出程序")
        return 1
    
    # 订阅行情
    if not manager.subscribe_stock_quotes():
        print("订阅失败，退出程序")
        return 1
    
    print("\n策略已启动，等待行情数据推送...")
    print("按 Ctrl+C 停止策略\n")
    
    try:
        # 保持运行，等待数据推送
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n收到停止信号，正在取消订阅...")
        if manager.strategy:
            manager.strategy.on_stop()
        manager.unsubscribe_stock_quotes()
        print("策略已停止")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

