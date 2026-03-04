"""
网格策略 - vnpy 框架版本
使用 xtquant 订阅实时行情数据

参考 golden_cross_demo.py 的实现方式

使用说明：

实盘模式（默认）：
1. 设置 xtdata token（在代码中取消注释并填入你的token）
2. 运行脚本：python run_grid_512710_vnpy.py --symbol 512710.SH
3. 策略会自动订阅行情并执行网格交易逻辑

模拟模式（用于非交易时间调试）：
1. 运行脚本：python run_grid_512710_vnpy.py --symbol 512710.SH --simulate
2. 可选参数：
   - --simulate-date 20251112  # 指定回放的日期
   - --speed-factor 2.0  # 回放速度（2.0表示2倍速）
3. 策略会使用历史tick数据回放进行调试

主要改动：
- 将原有的 GridRuntime 改为基于 vnpy CtaTemplate 的 GridStrategy
- 使用 xtdata.subscribe_whole_quote 订阅实时行情
- 保持原有的网格引擎、仓位管理、订单模拟和报告功能
- 支持命令行参数配置策略参数
- 支持模拟模式：使用历史tick数据回放进行调试（可在非交易时间使用）
"""
from __future__ import annotations

import argparse
import time
import traceback
import threading
from datetime import datetime, time as dtime, timedelta, timezone
from typing import Any, Dict, Optional

from pathlib import Path
import sys
import pandas as pd

from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
from vnpy_ctastrategy import CtaTemplate, BarGenerator, ArrayManager
from vnpy.trader.constant import Direction, Interval, Offset, Exchange
from vnpy_ctastrategy import BarData, TickData, TradeData, OrderData

if __package__ in {None, ""}:
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent  # path to src/网格
    root_str = str(project_root.parent)  # project root (contains src package)
    if root_str not in sys.path:
        sys.path.append(root_str)
    # easy_qmt_trader: 需要在将项目根目录加入 sys.path 之后再导入
    from md.xtdata.easy_qmt_trader示例.easy_qmt_trader import easy_qmt_trader
    from src.网格.网格信号实盘.grid_engine import GridEngine, GridSpec
    from src.网格.网格信号实盘.order_sim import Trade
    from src.网格.网格信号实盘.position_book import PositionBook
    from src.网格.网格信号实盘.reporter import Reporter
    # 导入模拟模式所需的函数
    from src.网格.网格信号实盘.run_grid_512710 import _load_tick_raw_dataframe, _prepare_tick_dataframe
else:
    from .grid_engine import GridEngine, GridSpec
    from .order_sim import Trade
    from .position_book import PositionBook
    from .reporter import Reporter
    from .run_grid_512710 import _load_tick_raw_dataframe, _prepare_tick_dataframe
    # 包导入场景：同样显式导入 easy_qmt_trader
    from md.xtdata.easy_qmt_trader示例.easy_qmt_trader import easy_qmt_trader


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


class MockTickReplayer:
    """
    模拟tick数据回放器
    用于在非交易时间调试策略
    """
    
    def __init__(
        self,
        symbol: str,
        tick_df: pd.DataFrame,
        callback: callable,
        speed_factor: float = 1.0
    ):
        """
        初始化模拟回放器
        
        Args:
            symbol: 股票代码
            tick_df: 历史tick数据DataFrame
            callback: 回调函数，接收 {symbol: tick_dict} 格式的数据
            speed_factor: 回放速度因子，1.0表示按原始时间间隔，2.0表示2倍速
        """
        self.symbol = symbol
        self.callback = callback
        self.speed_factor = speed_factor
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # 准备tick数据
        if tick_df.empty:
            raise ValueError("tick数据为空，无法进行模拟回放")
        
        # 使用_prepare_tick_dataframe处理数据
        self.tick_df = _prepare_tick_dataframe(symbol, tick_df)
        
        # 解析时间列
        self._parse_time_column()
        
        print(f"模拟回放器初始化完成: {symbol}, 共 {len(self.tick_df)} 条tick数据")
    
    def _parse_time_column(self):
        """解析时间列，计算时间间隔"""
        # 查找时间列
        time_col = None
        for col in ("servertime", "time", "stime", "date"):
            if col in self.tick_df.columns:
                time_col = col
                break
        
        if time_col is None:
            # 如果没有时间列，使用固定间隔（假设1秒一条）
            self.tick_df["_parsed_time"] = pd.date_range(
                start=datetime.now(),
                periods=len(self.tick_df),
                freq="1S"
            )
        else:
            # 解析时间字符串
            try:
                self.tick_df["_parsed_time"] = pd.to_datetime(
                    self.tick_df[time_col],
                    errors='coerce'
                )
                # 如果解析失败，使用固定间隔
                if self.tick_df["_parsed_time"].isna().any():
                    start_time = datetime.now()
                    self.tick_df["_parsed_time"] = pd.date_range(
                        start=start_time,
                        periods=len(self.tick_df),
                        freq="1S"
                    )
            except Exception:
                # 解析失败，使用固定间隔
                start_time = datetime.now()
                self.tick_df["_parsed_time"] = pd.date_range(
                    start=start_time,
                    periods=len(self.tick_df),
                    freq="1S"
                )
        
        # 计算时间间隔（秒）
        if len(self.tick_df) > 1:
            time_diffs = self.tick_df["_parsed_time"].diff().dt.total_seconds()
            time_diffs = time_diffs.fillna(0.0)
            # 将间隔应用速度因子
            self.tick_df["_interval"] = time_diffs / self.speed_factor
        else:
            self.tick_df["_interval"] = 0.0
    
    def _convert_row_to_tick_dict(self, row: pd.Series) -> Dict[str, Any]:
        """将DataFrame行转换为tick字典格式"""
        tick_dict = {
            "lastPrice": float(row.get("price", 0.0)),
            "lastClose": float(row.get("last_close", 0.0)),
            "volume": int(row.get("vol", 0)),
            "amount": float(row.get("amount", 0.0)),
            "bidPrice1": float(row.get("bid1", 0.0)),
            "askPrice1": float(row.get("ask1", 0.0)),
            "bidVol1": int(row.get("bid1", 0) > 0) * 100,  # 模拟值
            "askVol1": int(row.get("ask1", 0) > 0) * 100,  # 模拟值
            "open": float(row.get("open", row.get("price", 0.0))),
            "high": float(row.get("high", row.get("price", 0.0))),
            "low": float(row.get("low", row.get("price", 0.0))),
            "servertime": row.get("servertime", ""),  # 添加原始时间字段
        }
        return tick_dict
    
    def _replay_loop(self):
        """回放循环"""
        try:
            for i, (idx, row) in enumerate(self.tick_df.iterrows()):
                if not self._running:
                    break
                
                # 转换为tick字典
                tick_dict = self._convert_row_to_tick_dict(row)
                
                # 调用回调函数
                self.callback({self.symbol: tick_dict})
                
                # 快速回放：不等待时间间隔
                # if i < len(self.tick_df) - 1:
                #     interval = row.get("_interval", 0.0)
                #     if interval > 0:
                #         time.sleep(interval)
            
            print(f"\n模拟回放完成: {self.symbol}, 共回放 {len(self.tick_df)} 条数据")
            
        except Exception as e:
            print(f"模拟回放出错: {e}")
            traceback.print_exc()
        finally:
            self._running = False
    
    def start(self):
        """开始回放"""
        if self._running:
            print("回放已在运行中")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._replay_loop, daemon=True)
        self._thread.start()
        print(f"开始模拟回放: {self.symbol}")
    
    def stop(self):
        """停止回放"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        print(f"停止模拟回放: {self.symbol}")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running


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
    variables = ["spec", "engine", "pos_book", "reporter", "initialized", "last_price"]
    
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
        
        # 报告器（保存到策略目录）
        import os
        strategy_dir = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(strategy_dir, "trading_records")
        self.reporter = Reporter(out_dir=out_dir, symbol=vt_symbol)
        
        # 状态变量
        self.initialized = False
        self.last_price: Optional[float] = None
        self._baseline_set = False
        self._simulate_mode = setting.get("simulate_mode", False)
        self._order_placer = None
        self._pending_orders = set()  # (level_index, side)
        self._pending_details: Dict[tuple, Dict[str, Any]] = {}
        self._pos_loaded_from_text = False
        
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
            self.write_log(f"开始输出日终报告到: {self.reporter.out_dir}")
            try:
                self.reporter.flush_end_of_day(
                    now,
                    self.pos_book.snapshot(),
                    self.spec.level_price
                )
                self.write_log("日终报告已输出")
            except Exception as e:
                self.write_log(f"输出日终报告失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 打印交易记录到控制台
            self._print_trading_records()
    
    def _print_trading_records(self) -> None:
        """打印交易记录到控制台"""
        try:
            import os
            strategy_dir = os.path.dirname(os.path.abspath(__file__))
            out_dir = os.path.join(strategy_dir, "trading_records")
            symbol_clean = self.vt_symbol.replace(".", "")
            today = datetime.now().strftime("%Y%m%d")
            day_dir = os.path.join(out_dir, symbol_clean, today)
            
            print("\n" + "="*60)
            print("📊 交易记录汇总")
            print("="*60)
            
            # 打印交易记录
            trades_path = os.path.join(day_dir, "trades.csv")
            if os.path.exists(trades_path):
                print("\n📋 交易记录:")
                with open(trades_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if len(lines) > 1:  # 有数据
                        for line in lines:
                            print(f"  {line.strip()}")
                    else:
                        print("  (无交易记录)")
            else:
                print("\n📋 交易记录: (文件不存在)")
            
            # 打印配对交易
            pairs_path = os.path.join(day_dir, "pairs.csv")
            if os.path.exists(pairs_path):
                print("\n🔄 配对交易:")
                with open(pairs_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if len(lines) > 1:  # 有数据
                        for line in lines:
                            print(f"  {line.strip()}")
                    else:
                        print("  (无配对交易)")
            else:
                print("\n🔄 配对交易: (文件不存在)")
            
            # 打印盈亏汇总
            pnl_path = os.path.join(day_dir, "pnl.csv")
            if os.path.exists(pnl_path):
                print("\n💰 盈亏汇总:")
                with open(pnl_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        print(f"  {line.strip()}")
            else:
                print("\n💰 盈亏汇总: (文件不存在)")
            
            # 打印当前仓位
            positions_path = os.path.join(day_dir, "positions.csv")
            if os.path.exists(positions_path):
                print("\n📈 当前仓位:")
                with open(positions_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        print(f"  {line.strip()}")
            else:
                print("\n📈 当前仓位: (文件不存在)")
            
            print("\n" + "="*60)
            print(f"📁 交易记录文件位置: {day_dir}")
            print("="*60)
            
        except Exception as e:
            print(f"打印交易记录失败: {e}")
    
    def _init_grid(self, baseline: float) -> None:
        """初始化网格 - 修复版本"""
        self.spec = GridSpec(
            baseline=baseline,
            step=self.step,
            up_grids=self.up_grids,
            down_grids=self.down_grids
        )
        self.engine = GridEngine(self.spec)
        min_px, max_px = self.engine.bounds()
        
        self.write_log(f"Baseline={baseline:.6f}, Grid [{min_px:.6f}, {max_px:.6f}]")
        
        if not self._pos_loaded_from_text:
            # 初始化：不预设任何仓位，等待价格触发
            self.write_log("网格初始化完成：等待价格触发交易")
        else:
            self.write_log("网格初始化完成：已从历史文件加载仓位")
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
        1、开盘之前有持仓，则在avg_cost位置挂卖出
        2、若当前网格价已经发出订单且没有成交（不管是买还是卖），则等待下一个价格
        3、若没有发出订单：
           - 若当前价格网格或以下网格有仓位：卖出这些仓位总和；同时确保当前价格以下5个网格都有买入订单；买单成交时，记录avg_cost为买入价格+一个网格，同时在挂卖单在avg_cost
           - 否则：确保当前价格以下4个网格有买入订单（没有要挂买单）；判断上一网格是否有仓位（在grid_positions判断），若无且当前网格还没挂买入订单的，挂买入订单
        """
        assert self.engine and self.spec
        qty = self.qty_per_fill
        
        # 1) 检查是否已有挂单，避免重复操作
        if self._has_pending(level_index):
            # 打印详细的未成交订单信息
            msgs = []
            for s in ("BUY", "SELL"):
                key = (level_index, s)
                if key in self._pending_orders:
                    det = self._pending_details.get(key, {})
                    qty0 = det.get("qty", 0)
                    px0 = det.get("price", self.spec.level_price(level_index))
                    oid0 = det.get("order_id")
                    if oid0 is not None:
                        msgs.append(f"{s} | 订单编号: {oid0} | 价格: {px0:.6f} | 数量: {qty0}")
                    else:
                        msgs.append(f"{s} | 价格: {px0:.6f} | 数量: {qty0}")
            detail = "；".join(msgs) if msgs else ""
            self.write_log(f"层级 {level_index} 已有订单未成交，等待下一个价格{(' ｜ ' + detail) if detail else ''}")
            
            # 打印当前所有挂单状态汇总
            self._print_pending_orders_summary()
            return
        
        # 2) 检查当前网格及以下网格的仓位情况
        total_position_below = 0
        has_position_at_or_below = False
        
        for i in range(self.spec.min_level_index, level_index + 1):
            pos = self.pos_book.get(i)
            if pos.qty > 0:
                has_position_at_or_below = True
                total_position_below += pos.qty
        
        # 3) 根据仓位情况决定操作
        if has_position_at_or_below:
            # 有仓位：卖出这些仓位总和
            if not self._has_pending(level_index, "SELL"):
                sell_qty = total_position_below
                grid_price = self.spec.level_price(level_index)
                # 卖出时挂高一点，避免主动成交
                sell_price = grid_price #+ 0.001  # 挂高0.001等待被动成交
                
                # 价格保护：检查是否超出合理范围
                if sell_price > grid_price * 1.1:  # 防止挂价过高
                    sell_price = grid_price + 0.0005  # 减小挂价幅度
                    
                self._place_order_real(level_index, "SELL", sell_qty, sell_price)
                self._mark_pending(level_index, "SELL", sell_qty, sell_price)
        else:
            # 无仓位：买入逻辑
            # 检查上一网格是否有仓位
            prev_level_pos = self.pos_book.get(level_index - 1)
            
            # 确保当前价格以下4个网格有买入订单
            for i in range(max(self.spec.min_level_index, level_index - 4), level_index):
                if not self._has_pending(i, "BUY"):
                    grid_price_i = self.spec.level_price(i)
                    buy_price_i = grid_price_i #- 0.001
                    if buy_price_i < grid_price_i * 0.9:
                        buy_price_i = grid_price_i - 0.0005
                    self._place_order_real(i, "BUY", qty, buy_price_i)
                    self._mark_pending(i, "BUY", qty, buy_price_i)
            
            # 判断上一网格是否有仓位，若无且当前网格还没挂买入订单的，挂买入订单
            if (prev_level_pos.qty <= 0 and not self._has_pending(level_index, "BUY")):
                grid_price = self.spec.level_price(level_index)
                buy_price = grid_price #- 0.001
                if buy_price < grid_price * 0.9:
                    buy_price = grid_price - 0.0005
                self._place_order_real(level_index, "BUY", qty, buy_price)
                self._mark_pending(level_index, "BUY", qty, buy_price)
        
        # 4) 成交由实盘回调驱动；不做本地撮合
    
    def on_tick(self, tick: TickData) -> None:
        """Tick数据更新时的回调函数（推送模式）"""
        try:
            now = datetime.now()
            
            # 定期清理过期挂单状态（每5分钟清理一次）
            if now.minute % 5 == 0 and now.second < 5:
                self._cleanup_old_pending_orders()
            
            # 检查是否在交易时段（模拟模式下跳过此检查）
            if not self._simulate_mode and not within_trading_window(now):
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
                # 模拟模式下：直接使用第一个tick的开盘价或当前价
                elif self._simulate_mode:
                    baseline = self._get_baseline_from_open(tick)
                    if baseline is None or baseline <= 0:
                        # 如果开盘价不可用，使用当前价
                        baseline = current_price if current_price > 0 else tick.pre_close
                    if baseline and baseline > 0:
                        self._init_grid(baseline)
                    else:
                        return
                # 实盘模式：等待9:30开盘价
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
            
            # 模拟模式下进行撮合，实盘模式等待回调
            if self._simulate_mode:
                # 获取tick时间 - 优先使用tick.datetime，否则使用当前时间
                if hasattr(tick, 'datetime') and tick.datetime:
                    tick_time = tick.datetime.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    tick_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._simulate_matching(current_price, tick_time)
            # 实盘模式不进行本地撮合，等待实盘回调
            
            self.put_event()
            
        except Exception as e:
            self.write_log(f"处理tick数据失败: {e}")
            traceback.print_exc()
    
    def _simulate_matching(self, current_price: float, tick_time: str) -> None:
        """模拟撮合 - 使用tick原始时间"""
        try:
            # 复制一份挂单详情，避免在迭代过程中修改
            pending_to_check = list(self._pending_orders.copy())
            
            for key in pending_to_check:
                level_index, side = key
                if key not in self._pending_details:
                    continue
                    
                detail = self._pending_details[key]
                order_price = detail.get("price", 0)
                order_qty = detail.get("qty", 0)
                
                if order_price <= 0 or order_qty <= 0:
                    continue
                
                # 检查是否应该成交
                should_fill = False
                
                if side == "BUY":
                    # 买单：当前价格 <= 订单价格时成交
                    if current_price <= order_price:
                        should_fill = True
                else:  # SELL
                    # 卖单：当前价格 >= 订单价格时成交
                    if current_price >= order_price:
                        should_fill = True
                
                if should_fill:
                    # 模拟成交 - 传递tick时间
                    self._simulate_order_fill(level_index, side, order_price, order_qty, current_price, tick_time)
                    
        except Exception as e:
            self.write_log(f"模拟撮合失败: {e}")
    
    def _simulate_order_fill(self, level_index: int, side: str, order_price: float, order_qty: int, fill_price: float, tick_time: str) -> None:
        """模拟订单成交"""
        try:
            # 生成模拟订单编号
            order_id = int(datetime.now().timestamp() * 1000000) % 1000000000
            
            # 清除挂单状态
            key = (level_index, side)
            if key in self._pending_orders:
                self._pending_orders.remove(key)
            if key in self._pending_details:
                del self._pending_details[key]
            
            # 更新仓位
            if side == "BUY":
                self.pos_book.buy_at_level(level_index, fill_price, order_qty)
                self.write_log(f"模拟成交: BUY | 层级: {level_index} | 价格: {fill_price:.6f} | 数量: {order_qty} | 订单编号: {order_id}")
            else:  # SELL
                realized_qty = self.pos_book.sell_at_level(level_index, order_qty)
                self.write_log(f"模拟成交: SELL | 层级: {level_index} | 价格: {fill_price:.6f} | 数量: {order_qty} | 订单编号: {order_id}")
            
            # 记录交易 - 使用tick原始时间
            tr = Trade(
                trade_id=self._next_trade_id(),
                order_id=order_id,
                ts=tick_time,  # 使用tick原始时间
                side=side,
                price=fill_price,
                qty=order_qty,
                level_index=level_index,
            )
            self.reporter.log_trade(tr)
            
            # 调用买入成交后的逻辑（如avg_cost挂卖单）
            self.on_order_filled(level_index, side)
            
        except Exception as e:
            self.write_log(f"模拟订单成交失败: {e}")
    
    def _next_trade_id(self) -> int:
        """生成下一个交易ID"""
        if not hasattr(self, '_trade_id_counter'):
            self._trade_id_counter = 1
        else:
            self._trade_id_counter += 1
        return self._trade_id_counter
    
    def on_bar(self, bar: BarData) -> None:
        """K线数据更新时的回调函数（网格策略主要使用tick数据）"""
        pass
    
    def on_order(self, order: OrderData) -> None:
        """订单状态变化时的回调函数"""
        pass
    
    def on_trade(self, trade: TradeData) -> None:
        """成交时的回调函数"""
        self.put_event()

    def set_order_placer(self, placer):
        self._order_placer = placer

    def _place_order_real(self, level_index: int, side: str, qty: int, price: float) -> None:
        """真实下单函数 - 模拟模式下不执行"""
        if self._simulate_mode:
            self.write_log(f"模拟模式: 跳过真实下单 {side} | 层级: {level_index} | 价格: {price:.6f} | 数量: {qty}")
            return
            
        if self._order_placer is not None:
            self._order_placer(level_index, side, qty, price)

    def _mark_pending(self, level_index: int, side: str, qty: int, price: float, order_id: Optional[int] = None) -> None:
        """标记挂单状态 - 增强版本"""
        key = (level_index, side)
        self._pending_orders.add(key)
        self._pending_details[key] = {
            "qty": qty,
            "price": price,
            "order_id": order_id,
            "timestamp": datetime.now(),  # 添加时间戳
        }
    
    def _print_pending_orders_summary(self) -> None:
        """打印当前挂单状态汇总"""
        if not self._pending_orders:
            self.write_log("当前无挂单")
            return
            
        summary_lines = []
        total_buy_qty = 0
        total_sell_qty = 0
        
        # 按价格排序显示
        pending_items = []
        for (level_idx, side), details in self._pending_details.items():
            if (level_idx, side) in self._pending_orders:
                pending_items.append((level_idx, side, details))
        
        pending_items.sort(key=lambda x: x[2]['price'])  # 按价格排序
        
        for level_idx, side, details in pending_items:
            price = details['price']
            qty = details['qty']
            order_id = details.get('order_id', 'N/A')
            
            if side == "BUY":
                total_buy_qty += qty
                summary_lines.append(f"  买入: 价格{price:.6f} 数量{qty} 层级{level_idx} 订单{order_id}")
            else:
                total_sell_qty += qty
                summary_lines.append(f"  卖出: 价格{price:.6f} 数量{qty} 层级{level_idx} 订单{order_id}")
        
        summary_lines.insert(0, f"=== 当前挂单状态 (买入{total_buy_qty}股, 卖出{total_sell_qty}股) ===")
        summary_lines.append("=== 挂单状态结束 ===")
        
        for line in summary_lines:
            self.write_log(line)
    
    def _has_pending(self, level_index: int, side: str | None = None) -> bool:
        """检查是否有挂单 - 增强版本"""
        if side is None:
            return (level_index, "BUY") in self._pending_orders or (level_index, "SELL") in self._pending_orders
        return (level_index, side) in self._pending_orders
    
    def _clear_pending(self, level_index: int, side: str | None = None) -> None:
        """清除挂单状态 - 新增方法"""
        if side is None:
            # 清除该网格的所有挂单
            keys_to_remove = [key for key in self._pending_orders if key[0] == level_index]
            for key in keys_to_remove:
                self._pending_orders.remove(key)
                if key in self._pending_details:
                    del self._pending_details[key]
        else:
            # 清除特定方向的挂单
            key = (level_index, side)
            if key in self._pending_orders:
                self._pending_orders.remove(key)
                if key in self._pending_details:
                    del self._pending_details[key]
    
    def _cleanup_old_pending_orders(self, max_age_minutes: int = 30) -> None:
        """清理过期的挂单状态 - 新增方法"""
        now = datetime.now()
        keys_to_remove = []
        
        for key, details in self._pending_details.items():
            timestamp = details.get("timestamp")
            if timestamp and (now - timestamp).total_seconds() > max_age_minutes * 60:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self._pending_orders.remove(key)
            del self._pending_details[key]
            self.write_log(f"清理过期挂单状态: 层级 {key[0]}, 方向 {key[1]}")

    def on_order_placed(self, level_index: int, side: str, qty: int, price: float, order_id: int) -> None:
        # 更新/补全订单编号，并打印挂单成功日志
        self._pending_details[(level_index, side)] = {
            "qty": qty,
            "price": price,
            "order_id": order_id,
        }
        # 获取网格价用于日志显示
        if self.strategy and self.strategy.spec:
            grid_price = self.strategy.spec.level_price(level_index)
            self.write_log(f"挂单成功: {side} | 层级: {level_index} | 网格价: {grid_price:.6f} | 挂单价: {price:.6f} | 数量: {qty} | 订单编号: {order_id}")
        else:
            self.write_log(f"挂单成功: {side} | 层级: {level_index} | 价格: {price:.6f} | 数量: {qty} | 订单编号: {order_id}")

    def on_order_filled(self, level_index: int, side: str) -> None:
        """订单成交回调 - 修复版本"""
        try:
            key = (level_index, side)
            # 清除挂单状态和详细信息
            if key in self._pending_orders:
                self._pending_orders.remove(key)
            if key in self._pending_details:
                del self._pending_details[key]
            
            # 买入成交时，记录avg_cost为买入价格+一个网格，同时在avg_cost挂卖单
            if side == "BUY":
                # 获取买入成交价格
                pos = self.pos_book.get(level_index)
                if pos and pos.avg_cost > 0:
                    # 计算新的avg_cost：买入价格+一个网格
                    buy_price = pos.avg_cost  # 这里应该是成交价格，但pos_book中存储的是avg_cost
                    new_avg_cost = buy_price + self.spec.step
                    
                    # 找到avg_cost对应的网格层级
                    avg_cost_level = int(round((new_avg_cost - self.spec.baseline) / self.spec.step))
                    
                    # 确保在网格范围内
                    if self.spec.min_level_index <= avg_cost_level <= self.spec.max_level_index:
                        # 在avg_cost位置挂卖单
                        if not self._has_pending(avg_cost_level, "SELL"):
                            sell_qty = pos.qty  # 卖出相同数量
                            sell_price = new_avg_cost  # 在avg_cost位置卖出
                            
                            self._place_order_real(avg_cost_level, "SELL", sell_qty, sell_price)
                            self._mark_pending(avg_cost_level, "SELL", sell_qty, sell_price)
                            
                            self.write_log(f"买入成交后在avg_cost挂卖单: 层级{avg_cost_level} | 价格{sell_price:.6f} | 数量{sell_qty}")
            
            self.write_log(f"订单成交: {side} | 层级: {level_index} | 挂单状态已清除")
        except Exception as e:
            self.write_log(f"清除挂单状态失败: {e}")


class GridStrategyManager:
    """网格策略管理器 - 使用推送模式，支持实盘和模拟模式"""
    
    def __init__(
        self,
        stock_code: str,
        strategy_params: Optional[Dict[str, Any]] = None,
        cta_engine=None,
        simulate: bool = False,
        simulate_date: Optional[str] = None,
        speed_factor: float = 1.0
    ):
        """
        初始化策略管理器
        
        Args:
            stock_code: 股票代码，如 "512710.SH"
            strategy_params: 策略参数字典
            cta_engine: vnpy的CTA引擎（可选，如果为None则创建简化版本）
            simulate: 是否使用模拟模式（回放历史数据）
            simulate_date: 模拟模式下的日期，格式如 "20251112"，如果为None则使用今天
            speed_factor: 模拟模式下的回放速度因子，1.0表示按原始时间间隔
        """
        self.stock_code = stock_code
        self.strategy_params = strategy_params or {}
        self.cta_engine = cta_engine
        self.strategy: Optional[GridStrategy] = None
        self.subscription_id: Optional[int] = None
        self.simulate = simulate
        self.simulate_date = simulate_date
        self.speed_factor = speed_factor
        self.mock_replayer: Optional[MockTickReplayer] = None
        self.trader: Optional[easy_qmt_trader] = None
        self._order_map: Dict[int, Dict[str, Any]] = {}
        self._trade_seq: int = 0
        
        mode_str = "模拟模式" if simulate else "实盘模式"
        print(f"初始化网格策略管理器 ({mode_str})，监控股票: {stock_code}")

        # 始终初始化交易通道：simulate 仅用于数据订阅/回放，不影响下单
        self._init_qmt_trader()

    def _next_trade_id(self) -> int:
        self._trade_seq += 1
        return self._trade_seq
    
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
            # 获取tick原始时间 - 优先使用servertime字段
            servertime = tick_data.get('servertime', '')
            if servertime:
                # 解析servertime为datetime
                if isinstance(servertime, str):
                    # 尝试解析时间格式
                    try:
                        tick_time = datetime.strptime(servertime, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            tick_time = datetime.strptime(servertime, '%Y%m%d %H:%M:%S')
                        except ValueError:
                            tick_time = datetime.now()
                else:
                    tick_time = datetime.now()
            else:
                tick_time = datetime.now()
            
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
            
            # 创建 TickData 对象 - 使用tick原始时间
            tick = TickData(
                symbol=stock_code.split('.')[0],
                exchange=exchange,
                datetime=tick_time,  # 使用tick原始时间
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
                "simulate_mode": self.simulate,  # 传递模拟模式标志
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

            # 只要交易通道存在，就注入真实下单函数（simulate 仅影响数据）
            if self.trader is not None:
                self.strategy.set_order_placer(self._place_real_order)
            
            if not self._init_positions_text_and_check():
                print("用户取消，停止策略创建")
                return False

            print(f"策略实例创建成功: {strategy_name}")
            return True
            
        except Exception as e:
            print(f"创建策略实例失败: {e}")
            traceback.print_exc()
            return False

    def _init_qmt_trader(self) -> None:
        def on_filled(event: Dict[str, Any]):
            try:
                order_id_raw = event.get("order_id", None)
                # 兼容字符串/整数订单编号
                order_id_str = str(order_id_raw) if order_id_raw is not None else None
                try:
                    order_id_int = int(order_id_raw) if order_id_raw is not None else None
                except Exception:
                    order_id_int = None
                
                traded_price = float(event.get("traded_price", 0))
                traded_volume = int(event.get("traded_volume", 0))
                meta = None
                if order_id_int is not None:
                    meta = self._order_map.pop(order_id_int, None)
                if meta is None and order_id_str is not None:
                    meta = self._order_map.pop(order_id_str, None)
                
                # 如果找不到订单元数据，跳过处理（可能是历史成交）
                if not meta or self.strategy is None or self.strategy.spec is None:
                    return
                level_index = meta["level_index"]
                side = meta["side"]
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if side == "BUY":
                    # 买入成交：仓位挂在当前网格（修复：原来错误地挂在上一个网格）
                    self.strategy.pos_book.buy_at_level(level_index, traded_price, traded_volume)
                    
                    tr = Trade(
                        trade_id=self._next_trade_id(),
                        order_id=int(order_id_int) if order_id_int is not None else int(order_id_str) if order_id_str and order_id_str.isdigit() else 0,
                        ts=ts,
                        side=side,
                        price=traded_price,
                        qty=traded_volume,
                        level_index=level_index,
                    )
                    self.strategy.reporter.log_trade(tr)
                else:
                    realized_qty = self.strategy.pos_book.sell_at_level(level_index, traded_volume)
                    tr = Trade(
                        trade_id=self._next_trade_id(),
                        order_id=int(order_id_int) if order_id_int is not None else int(order_id_str) if order_id_str and order_id_str.isdigit() else 0,
                        ts=ts,
                        side=side,
                        price=traded_price,
                        qty=traded_volume,
                        level_index=level_index,
                    )
                    self.strategy.reporter.log_trade(tr)
                # 成交日志（方向/层级/价格/数量/订单编号）
                try:
                    oid_log = order_id_str if order_id_str is not None else str(order_id_int)
                    self.strategy.write_log(f"成交: {side} | 层级: {level_index} | 价格: {traded_price:.6f} | 数量: {traded_volume} | 订单编号: {oid_log}")
                except Exception:
                    pass
                # 清除挂单状态
                try:
                    self.strategy.on_order_filled(level_index, side)
                except Exception:
                    pass
                self.strategy.put_event()
                self._save_positions_to_text()
            except Exception:
                traceback.print_exc()

        self.trader = build_qmt_trader_with_callback(
            on_filled=on_filled,
            path=self.strategy_params.get("qmt_path", r"D:/国金QMT交易端模拟/userdata_mini"),
            account=self.strategy_params.get("qmt_account", "55009640"),
            account_type=self.strategy_params.get("qmt_account_type", "STOCK"),
            session_id=self.strategy_params.get("qmt_session_id", 123456),
        )

    def _place_real_order(self, level_index: int, side: str, qty: int, price: float) -> None:
        if self.trader is None:
            return
        order_type = xtconstant.STOCK_BUY if side == "BUY" else xtconstant.STOCK_SELL
        oid = self.trader.order_stock(
            stock_code=self.stock_code,
            order_type=order_type,
            order_volume=qty,
            price_type=xtconstant.FIX_PRICE,
            price=price,
        )
        try:
            # 兼容字符串/整数订单编号，映射两份键
            oid_str = str(oid)
            self._order_map[oid_str] = {"level_index": level_index, "side": side, "qty": qty, "price": price}
            try:
                oid_int = int(oid)
                self._order_map[oid_int] = {"level_index": level_index, "side": side, "qty": qty, "price": price}
            except Exception:
                oid_int = None
            # 通知策略：挂单成功，带订单编号
            if self.strategy is not None:
                try:
                    self.strategy.on_order_placed(level_index, side, qty, price, oid_str if oid_int is None else oid_int)
                except Exception:
                    pass
        except Exception:
            pass
    
    def _positions_text_path(self) -> Path:
        base = Path(__file__).resolve().parent / "positionsRecord"
        base.mkdir(parents=True, exist_ok=True)
        code = self.stock_code
        return base / f"grid_positions_{code}.csv"

    def _save_positions_to_text(self) -> None:
        try:
            if self.strategy is None:
                return
            snap = self.strategy.pos_book.snapshot()
            path = self._positions_text_path()
            with open(path, "w", encoding="utf-8") as f:
                f.write("level_idx,qty,avg_cost\n")
                for idx, qty, avg_cost in snap:
                    if qty > 0:
                        f.write(f"{idx},{qty},{avg_cost:.6f}\n")
        except Exception:
            traceback.print_exc()

    def _load_positions_from_text(self) -> None:
        try:
            if self.strategy is None:
                return
            path = self._positions_text_path()
            if not path.exists():
                with open(path, "w", encoding="utf-8") as f:
                    f.write("level_idx,qty,avg_cost\n")
                return
            book = PositionBook()
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            if len(lines) <= 1:
                self.strategy.pos_book = book
                try:
                    self.strategy._pos_loaded_from_text = True
                except Exception:
                    pass
                return
            for line in lines[1:]:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 3:
                    continue
                try:
                    level_idx = int(float(parts[0]))
                    qty = int(float(parts[1]))
                    avg_cost = float(parts[2])
                except Exception:
                    continue
                if qty > 0:
                    book.set_holding(level_idx, avg_cost, qty)
            self.strategy.pos_book = book
            try:
                self.strategy._pos_loaded_from_text = True
            except Exception:
                pass
        except Exception:
            traceback.print_exc()

    def _xt_position_qty_for_symbol(self) -> int:
        try:
            if self.trader is None:
                return 0
            df = self.trader.query_stock_positions()
            if df is None or df.empty:
                return 0
            code6 = self.stock_code.split(".")[0]
            codes = df.get("证券代码")
            if codes is None:
                return 0
            mask = codes.astype(str) == code6
            if not mask.any():
                return 0
            qtys = df.loc[mask, "持仓数量"]
            total = int(float(qtys.fillna(0).sum()))
            return total
        except Exception:
            traceback.print_exc()
            return 0

    def _text_total_qty(self) -> int:
        try:
            if self.strategy is None:
                return 0
            snap = self.strategy.pos_book.snapshot()
            return int(sum(q for _, q, _ in snap))
        except Exception:
            return 0

    def _init_positions_text_and_check(self) -> bool:
        try:
            self._load_positions_from_text()
            txt_qty = self._text_total_qty()
            xt_qty = self._xt_position_qty_for_symbol()
            if xt_qty != txt_qty:
                print(f"检测到持仓不一致：xtquant={xt_qty}，文本={txt_qty}。按回车继续，输入 n 取消。")
                ans = input().strip().lower()
                if ans in ("n", "no", "q", "quit", "cancel", "c"):
                    return False
            return True
        except Exception:
            traceback.print_exc()
            return True

    def _load_simulate_data(self) -> Optional[pd.DataFrame]:
        """
        加载模拟模式所需的历史tick数据
        
        Returns:
            DataFrame: 历史tick数据，如果加载失败返回None
        """
        try:
            # 确定日期
            if self.simulate_date:
                date_str = self.simulate_date
            else:
                date_str = datetime.now().strftime("%Y%m%d")
            
            # 构建开始时间（9:30开盘）
            start_time = f"{date_str}093000"
            
            print(f"加载模拟数据: {self.stock_code}, 日期: {date_str}, 开始时间: {start_time}")
            
            # 加载历史tick数据
            raw_df = _load_tick_raw_dataframe(self.stock_code, start_time)
            
            if raw_df is None or len(raw_df) == 0:
                print(f"警告: 无法加载历史tick数据，日期: {date_str}")
                return None
            
            print(f"成功加载 {len(raw_df)} 条历史tick数据")
            return raw_df
            
        except Exception as e:
            print(f"加载模拟数据失败: {e}")
            traceback.print_exc()
            return None
    
    def subscribe_stock_quotes(self) -> bool:
        """
        订阅股票行情（实盘模式）或启动模拟回放（模拟模式）
        
        Returns:
            bool: 是否成功订阅/启动
        """
        if self.simulate:
            # 模拟模式：加载历史数据并启动回放
            try:
                tick_df = self._load_simulate_data()
                if tick_df is None or tick_df.empty:
                    print("无法加载模拟数据，退出")
                    return False
                
                # 创建模拟回放器
                self.mock_replayer = MockTickReplayer(
                    symbol=self.stock_code,
                    tick_df=tick_df,
                    callback=self.on_tick_data,
                    speed_factor=self.speed_factor
                )
                
                # 启动回放
                self.mock_replayer.start()
                
                print(f"模拟模式启动成功: {self.stock_code}")
                return True
                
            except Exception as e:
                print(f"启动模拟模式失败: {e}")
                traceback.print_exc()
                return False
        else:
            # 实盘模式：订阅实时行情
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
        """取消订阅股票行情（实盘模式）或停止模拟回放（模拟模式）"""
        try:
            if self.simulate:
                # 模拟模式：停止回放
                if self.mock_replayer is not None:
                    self.mock_replayer.stop()
                    self.mock_replayer = None
            else:
                # 实盘模式：取消订阅
                if self.subscription_id is not None:
                    xtdata.unsubscribe_quote(self.subscription_id)
                    print(f"取消订阅 ID: {self.subscription_id}")
                    self.subscription_id = None
        except Exception as e:
            print(f"取消订阅/停止回放失败: {e}")
            traceback.print_exc()


def build_qmt_trader_with_callback(on_filled, path: str, account: str, account_type: str, session_id: int = 123456) -> easy_qmt_trader:
    class MyXtQuantTraderCallbackNew(XtQuantTraderCallback):
        def on_stock_order(self, order):
            try:
                # 56: 已成（根据 easy_qmt_trader README 的对照），或成交数量达到委托数量
                if getattr(order, "order_status", None) == 56 or getattr(order, "traded_volume", 0) >= getattr(order, "order_volume", 0):
                    evt = {
                        "order_id": order.order_id,
                        "stock_code": order.stock_code,
                        "order_type": order.order_type,
                        "order_volume": order.order_volume,
                        "traded_volume": order.traded_volume,
                        "traded_price": order.traded_price,
                        "order_status": order.order_status,
                    }
                    on_filled(evt)
            except Exception:
                traceback.print_exc()

        def on_stock_trade(self, trade):
            # 仅在订单回报里处理“全部成交”，成交推送不直接触发
            pass

    #xt = XtQuantTrader(path, int(session_id))
    #acc = StockAccount(account_id=account, account_type=account_type)
    cb = MyXtQuantTraderCallbackNew()
    #xt.register_callback(cb)
    #xt.start()
    #ret = xt.connect()
    #if ret == 0:
    #    xt.subscribe(acc)
    trader = easy_qmt_trader()
    trader.connect(cb)
    print(trader.query_stock_positions())
    return trader

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
    parser.add_argument("--symbol", default="162411.SZ", help="股票代码")
    parser.add_argument("--step", type=float, default=0.001, help="网格步长")
    parser.add_argument("--up_grids", type=int, default=10, help="向上网格数")
    parser.add_argument("--down_grids", type=int, default=20, help="向下网格数")
    parser.add_argument("--lot_per_grid", type=int, default=1, help="每格手数")
    parser.add_argument("--hand_size", type=int, default=100, help="每手股数")
    parser.add_argument("--out_dir", default="data/grid", help="输出目录")
    parser.add_argument(
        "--baseline",
        type=float,
        default=0.818,
        help="若提供则使用该基准价（例如 0.680）；否则用9:30开盘价",
    )
    parser.add_argument(
        "--simulate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="启用模拟模式：使用历史tick数据回放进行调试（非交易时间可用）",
    )
    parser.add_argument(
        "--simulate-date",
        type=str,
        default='20260227',
        help="模拟模式下的日期，格式如 '20251112'，如果未指定则使用今天",
    )
    parser.add_argument(
        "--speed-factor",
        type=float,
        default=1.0,
        help="模拟模式下的回放速度因子，1.0表示按原始时间间隔，2.0表示2倍速",
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
    
    # 创建策略管理器（支持模拟模式和实盘模式）
    manager = GridStrategyManager(
        stock_code=args.symbol,
        strategy_params=strategy_params,
        simulate=args.simulate,
        simulate_date=args.simulate_date,
        speed_factor=args.speed_factor
    )
    
    # 创建策略实例（简化模式，不需要完整的 cta_engine）
    if not manager.create_strategy():
        print("创建策略失败，退出程序")
        return 1
    
    # 订阅行情（实盘模式）或启动模拟回放（模拟模式）
    if not manager.subscribe_stock_quotes():
        print("订阅/启动失败，退出程序")
        return 1
    
    mode_str = "模拟回放" if args.simulate else "实时行情"
    print(f"\n策略已启动 ({mode_str})，等待行情数据推送...")
    print("按 Ctrl+C 停止策略\n")
    
    try:
        # 保持运行，等待数据推送
        while True:
            time.sleep(0.1)  # 减少等待时间
            # 如果是模拟模式，检查回放是否完成
            if args.simulate and manager.mock_replayer and not manager.mock_replayer.is_running():
                print("\n模拟回放已完成，程序将退出")
                # 调用策略停止方法以输出交易记录
                if manager.strategy:
                    manager.strategy.on_stop()
                break
    except KeyboardInterrupt:
        print("\n\n收到停止信号，正在取消订阅/停止回放...")
        if manager.strategy:
            manager.strategy.on_stop()
        manager.unsubscribe_stock_quotes()
        print("策略已停止")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

