"""
网格交易策略模块 - 基于 vnpy 框架
"""
import json
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Optional

from vnpy_ctastrategy import CtaTemplate
from vnpy_ctastrategy import BarData, TickData, TradeData, OrderData

# 导入网格相关组件
if __package__ in {None, ""}:
    from src.网格.网格信号实盘.grid_engine import GridEngine, GridSpec
    from src.网格.网格信号实盘.order_sim import Trade
    from src.网格.网格信号实盘.position_book import PositionBook
    from src.网格.网格信号实盘.reporter import Reporter
    from src.网格.网格信号实盘.utils import within_trading_window
else:
    from .grid_engine import GridEngine, GridSpec
    from .order_sim import Trade
    from .position_book import PositionBook
    from .reporter import Reporter
    from .utils import within_trading_window


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
        manager=None,  # 添加策略管理器引用
    ) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # 保存策略管理器引用
        self.manager = manager
        
        # 网格相关组件
        self.spec: Optional[GridSpec] = None
        self.engine: Optional[GridEngine] = None
        self.pos_book = PositionBook()
        
        # 报告器（保存到策略目录）
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
        self.trades = []  # 交易记录列表
        
                
    def _get_order_status_desc(self, status_code: int) -> str:
        """获取订单状态中文描述"""
        status_map = {
            48: "未报",
            49: "待报",
            50: "已报",
            51: "已报待撤", 
            52: "部成待撤",
            53: "部撤",
            54: "已撤",
            55: "部成",
            56: "已成",
            57: "废单",
            255: "未知"
        }
        return status_map.get(status_code, f"未知状态({status_code})")
    
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
                traceback.print_exc()
            
            # 打印交易记录到控制台
            self._print_trading_records()
    
    def _print_trading_records(self) -> None:
        """打印交易记录到控制台"""
        try:
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
        print(f"当前价格及毫秒时间: {current_price}, {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        assert self.engine and self.spec
        qty = self.qty_per_fill
        
        # 同步最新订单状态
        self._sync_order_status()
        
        # 同步完成后，立即打印真实订单状态
        self._print_local_order_status()
        
        # 2) 同步真实仓位与本地仓位
        self._sync_positions_with_broker()
        
        # 3) 检查是否已有挂单，避免重复操作
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
            pass  # 暂时注释掉重复的等待日志
            
            # 打印当前所有挂单状态汇总
            #self._print_pending_orders_summary()
            return
        
        # 3) 检查当前网格及以下网格的仓位情况
        total_position_below = 0
        has_position_at_or_below = False
        
        for i in range(self.spec.min_level_index, level_index + 1):
            pos = self.pos_book.get(i)
            if pos.qty > 0:
                has_position_at_or_below = True
                total_position_below += pos.qty
        
        # 4) 根据仓位情况决定操作
        if has_position_at_or_below:
            # 有仓位：立即在目标卖出价格挂卖单排队
            # 找到要卖出的仓位信息，确保在正确的价格卖出
            for i in range(self.spec.min_level_index, level_index + 1):
                pos = self.pos_book.get(i)
                if pos.qty > 0 and pos.avg_cost > 0:  # 确保有成本记录
                    # 计算该仓位应该卖出的价格：avg_cost + step
                    target_sell_price = pos.avg_cost + self.spec.step
                    target_level = int(round((target_sell_price - self.spec.baseline) / self.spec.step))
                    
                    # 检查是否已经在目标卖出层级挂了卖单
                    if not self._has_pending(target_level, "SELL") and not self._has_real_sell_order_at_price(target_level):
                        # 获取目标层级的现有仓位
                        target_pos = self.pos_book.get(target_level)
                        existing_qty = target_pos.qty if target_pos else 0
                        
                        # 计算需要挂卖的数量（差额）
                        sell_qty = pos.qty - existing_qty
                        
                        if sell_qty > 0:
                            sell_price = target_sell_price
                            
                            self.write_log(f"有仓位立即挂卖单: 买入层级{i} | 买入成本{pos.avg_cost:.6f} | 目标卖出价{sell_price:.6f} | 目标层级{target_level} | 现有仓位{existing_qty} | 需挂卖{sell_qty}")
                            self._place_order_real(target_level, "SELL", sell_qty, sell_price)
                        else:
                            # self.write_log(f"目标层级已有足够仓位，无需挂卖单: 买入层级{i} | 目标层级{target_level} | 现有{existing_qty}")
                            pass
                    else:
                        # self.write_log(f"仓位已在目标层级挂卖单: 买入层级{i} | 目标层级{target_level}")
                        pass  # 暂时注释掉重复的挂单日志
                    break  # 一次只处理一个仓位的卖出
        else:
            # 无仓位：买入逻辑
            # 检查上一网格是否有仓位
            prev_level_pos = self.pos_book.get(level_index + 1)
            
            # 确保当前价格以下4个网格有买入订单
            for i in range(max(self.spec.min_level_index, level_index - 4), level_index ):
                has_pending = self._has_pending(i, "BUY")
                has_real_order = self._has_real_buy_order_at_price(i)######################################
                grid_price_i = self.spec.level_price(i)
                
                # self.write_log(f"[DEBUG] 检查层级{i} 价格{grid_price_i}: 本地挂单={has_pending}, 券商买单={has_real_order}")
                
                if not has_pending and not has_real_order:
                    grid_price_i = self.spec.level_price(i)
                    buy_price_i = grid_price_i  # 买入价格等于网格价格
                    # 价格保护：检查是否超出合理范围
                    if buy_price_i < grid_price_i * 0.9:
                        buy_price_i = grid_price_i - 0.0005
                    
                    self._place_order_real(i, "BUY", qty, buy_price_i)
                    print(f"[批量买入] 当前时间精确到毫秒: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, 买入价格: {buy_price_i:.6f}")
                elif self._has_real_buy_order_at_price(i):########################
                    # self.write_log(f"层级{i}已有券商买单，跳过挂单")
                    pass  # 暂时注释掉跳过挂单日志
            
            # 判断上一网格是否有仓位，若无且当前网格还没挂买入订单的，挂买入订单
            # 避免与批量买入逻辑重复：当前层级不在批量买入范围内
            batch_buy_range = range(max(self.spec.min_level_index, level_index - 4), level_index)
            if (prev_level_pos.qty <= 0 and 
                not self._has_pending(level_index, "BUY") and 
                not self._has_real_buy_order_at_price(level_index) and
                level_index not in batch_buy_range):
                
                # 额外检查：确保当前层级确实没有买单（防止重复挂单）
                current_level_price = self.spec.level_price(level_index)
                has_any_buy_order = False
                
                # 检查批量买入范围内是否已经有相同价格的买单
                for i in batch_buy_range:
                    if self._has_pending(i, "BUY") or self._has_real_buy_order_at_price(i):
                        batch_price = self.spec.level_price(i)
                        if abs(batch_price - current_level_price) < 0.001:  # 价格几乎相同
                            has_any_buy_order = True
                            break
                
                if not has_any_buy_order:
                    buy_price = self.spec.level_price(level_index)
                    # 价格保护：检查是否超出合理范围
                    #if buy_price < grid_price * 0.9:
                    #    buy_price = grid_price - 0.0005
                    
                    self._place_order_real(level_index, "BUY", qty, buy_price)
                    print(f"[单个买入] 当前时间精确到毫秒: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                else:
                    # self.write_log(f"层级{level_index}附近已有买单，跳过重复挂单")
                    pass  # 防止重复挂单
        
        # 4) 成交由实盘回调驱动；不做本地撮合
    
    def _print_local_order_status(self) -> None:#
        """打印当前真实订单状态（包括券商订单ID）"""
        try:
            if not self._pending_orders:
                print('没有可执行订单')
                return
            
            # 收集所有有订单ID的挂单
            real_orders = []
            for (level_idx, side), details in self._pending_details.items():
                if (level_idx, side) in self._pending_orders:
                    order_id = details.get('order_id')
                    if order_id is not None:
                        real_orders.append((level_idx, side, details))
            
            if real_orders:
                self.write_log("=== 当前本地订单状态 ===")
                for level_idx, side, details in real_orders:
                    price = details['price']
                    qty = details['qty']
                    order_id = details['order_id']
                    side_text = "买入" if side == "BUY" else "卖出"
                    self.write_log(f"  {side_text}: 订单{order_id} | 层级{level_idx} | 价格{price:.6f} | 数量{qty}")
                self.write_log("=== 本地订单状态结束 ===")
                pass  # 暂时注释掉订单状态打印
            else:
                self.write_log("=== 当前本地订单（本地挂单状态可能未同步）===")
                pass  # 暂时注释掉订单状态打印
                
        except Exception as e:
            self.write_log(f"打印本地订单状态失败: {e}")
    
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
            
            # 只处理当前价格所在的层级，避免重复触发
            current_level = self.engine.price_to_level_index(current_price)
            if current_level is not None:
                grid_price = self.spec.level_price(current_level)
                self.write_log(f"[DEBUG] 处理层级: {current_level} | 价格: {grid_price:.6f} | 当前价格: {current_price:.6f}")
                self._handle_level_event(current_level, grid_price, current_price)
            else:
                # 如果价格不在任何网格上，但跨越了网格，只处理最后一个跨越的层级
                if crossed:
                    last_crossed = crossed[-1]
                    grid_price = self.spec.level_price(last_crossed)
                    self.write_log(f"[DEBUG] 处理跨越层级: {last_crossed} | 价格: {grid_price:.6f} | 当前价格: {current_price:.6f}")
                    self._handle_level_event(last_crossed, grid_price, current_price)
            
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
        
        # 检查是否与上一个挂单方向相同且价格相同
        if not hasattr(self, '_order_history'):
            self._order_history = []
        
        current_order_key = f"{side}_{price:.6f}"
        
        # 检查最后一个订单是否有相同方向和价格
        if self._order_history and self._order_history[-1] == current_order_key:
            print(f"[防重复] 跳过重复挂单: {side} | 价格: {price:.6f}")
            return
        
        # 在发送给券商之前就记录本地挂单状态，实现双重检查
        self._mark_pending(level_index, side, qty, price)
        
        # 记录这次挂单到历史记录
        self._order_history.append(current_order_key)
        
        # 限制历史记录长度，避免内存无限增长
        #if len(self._order_history) > 100:
        #    self._order_history = self._order_history[-50:]  # 保留最近50个
        
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
            # self.write_log("当前无挂单")
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
        
        # summary_lines.insert(0, f"=== 当前挂单状态 (买入{total_buy_qty}股, 卖出{total_sell_qty}股) ===")
        # summary_lines.append("=== 挂单状态结束 ===")
        
        # for line in summary_lines:
        #     self.write_log(line)
        pass  # 暂时注释掉挂单状态打印
    
    def _has_real_buy_order_at_price(self, level_index: int) -> bool:
        """检查券商是否已经有指定层级的买单（直接查询真实订单）"""
        try:
            # 直接通过trader查询真实订单，不使用缓存
            if not hasattr(self, 'manager') or not self.manager or not hasattr(self.manager, 'trader') or not self.manager.trader:
                return False
            
            # 直接调用get_unfilled_orders获取真实订单
            orders_list = self.manager.trader.get_unfilled_orders(verbose=False)
            if not orders_list:
                return False
            
            target_price = self.spec.level_price(level_index)
            current_stock = self.manager.stock_code
            current_stock_clean = current_stock.replace('.SH', '').replace('.SZ', '')
            
            for order in orders_list:
                stock_code = order.get('stock_code', '')
                order_price = order.get('price', 0)
                order_type = order.get('order_type')
                
                # 检查是否为当前股票的买单
                is_match_stock = (
                    stock_code == current_stock_clean or
                    stock_code == current_stock or
                    stock_code + '.SH' == current_stock or
                    stock_code + '.SZ' == current_stock
                )
                
                # 买单的order_type应该是23
                is_buy_order = order_type == 23
                
                # 检查价格是否匹配（允许小幅差异）
                price_match = abs(order_price - target_price) < 0.001
                
                if is_match_stock and is_buy_order and price_match:
                    return True
                    
            return False
            
        except Exception as e:
            print(f"[GridStrategy] Error checking real buy order at price: {e}")
            return False
    
    def _has_pending(self, level_index: int, side: str | None = None) -> bool:
        """检查是否有挂单 - 增强版本"""
        if side is None:
            return (level_index, "BUY") in self._pending_orders or (level_index, "SELL") in self._pending_orders
        return (level_index, side) in self._pending_orders
    
    def _has_real_sell_order_at_price(self, level_index: int) -> bool:
        """检查券商是否已经有指定层级的卖单（直接查询真实订单）"""
        try:
            # 直接通过trader查询真实订单，不使用缓存
            if not hasattr(self, 'manager') or not self.manager or not hasattr(self.manager, 'trader') or not self.manager.trader:
                return False
            
            # 直接调用get_unfilled_orders获取真实订单
            #print('准备调用 get_unfilled_orders...')
            orders_list = self.manager.trader.get_unfilled_orders(verbose=False)
            print(f'get_unfilled_orders 返回，订单数量: {len(orders_list) if orders_list else 0}')
            if not orders_list:
                return False
            
            target_price = self.spec.level_price(level_index)
            current_stock = self.manager.stock_code
            current_stock_clean = current_stock.replace('.SH', '').replace('.SZ', '')
            
            for order in orders_list:
                stock_code = order.get('stock_code', '')
                order_price = order.get('price', 0)
                order_type = order.get('order_type')
                
                # 检查是否为当前股票的订单
                is_match_stock = (
                    stock_code == current_stock_clean or
                    stock_code == current_stock or
                    stock_code + '.SH' == current_stock or
                    stock_code + '.SZ' == current_stock
                )
                
                if not is_match_stock:
                    continue
                
                # 卖单的order_type应该是24
                is_sell_order = order_type == 24
                
                # 检查价格是否匹配（允许小幅差异）
                price_match = abs(order_price - target_price) < 0.001
                
                if is_match_stock and is_sell_order and price_match:
                    return True
                    
            return False
            
        except Exception as e:
            print(f"[GridStrategy] Error checking real sell order at price: {e}")
            return False
    
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
    
        
    def _sync_order_status(self) -> None:
        """同步券商最新订单状态，清理已成交或已取消的本地挂单状态"""
        try:
            if not hasattr(self, 'manager') or not self.manager or not hasattr(self.manager, 'trader') or not self.manager.trader:
                self._clear_all_pending_orders()
                return
                
            # 调用base_trader_zld的get_unfilled_orders获取未成交订单
            orders_list = self.manager.trader.get_unfilled_orders()
            
            if orders_list:
                # 获取所有未成交的真实订单
                real_orders = {}
                for order in orders_list:
                    order_id = order.get('order_id')
                    stock_code = order.get('stock_code', '')
                    order_status = order.get('order_status')
                    order_volume = order.get('order_volume', 0)
                    traded_volume = order.get('traded_volume', 0)
                    order_price = order.get('price', 0)
                    
                    # 只处理当前股票的订单
                    current_stock = self.manager.stock_code
                    current_stock_clean = current_stock.replace('.SH', '').replace('.SZ', '')
                    
                    is_match = (
                        stock_code == current_stock_clean or
                        stock_code == current_stock or
                        stock_code + '.SH' == current_stock or
                        stock_code + '.SZ' == current_stock
                    )
                    
                    if is_match:
                        remaining_volume = order_volume - traded_volume
                        
                        # get_unfilled_orders返回的都是未成交订单，直接处理
                        if remaining_volume > 0:
                            # 使用order_type字段判断买卖方向：23=买，24=卖
                            order_type = order.get('order_type')
                            
                            if order_type == 23:
                                side = "BUY"
                            elif order_type == 24:
                                side = "SELL"
                            else:
                                # 如果无法从order_type判断，尝试从order_remark判断
                                order_remark = order.get('order_remark', '').lower()
                                if 'buy' in order_remark or '买入' in order_remark:
                                    side = "BUY"
                                elif 'sell' in order_remark or '卖出' in order_remark:
                                    side = "SELL"
                                else:
                                    continue  # 无法判断方向，跳过
                            
                            real_orders[order_id] = {
                                'side': side,
                                'price': order_price,
                                'qty': remaining_volume,
                                'status': order_status
                            }
                
                # 同步本地挂单状态与真实订单
                self._sync_with_real_orders(real_orders)
                
            else:
                # 没有真实订单，清理所有本地挂单
                self._clear_all_pending_orders()
                
        except Exception as e:
            print(f"[GridStrategy] Failed to sync order status: {e}")
            import traceback
            traceback.print_exc()
    
    def _sync_with_real_orders(self, real_orders: dict) -> None:
        """将本地挂单状态与真实订单同步"""
        try:
            # 1) 完整比较本地状态与真实订单状态
            local_to_remove = []
            local_to_update = []
            
            # 检查所有本地挂单
            for (level_idx, side), details in self._pending_details.items():
                if (level_idx, side) in self._pending_orders:
                    local_price = round(details.get('price', 0), 6)
                    local_qty = details.get('qty', 0)
                    local_order_id = details.get('order_id')
                    
                    # 查找匹配的真实订单
                    matched_order = None
                    for order_id, order_info in real_orders.items():
                        if (order_info['side'] == side and 
                            round(order_info['price'], 6) == local_price):
                            matched_order = order_info
                            break
                    
                    if matched_order:
                        # 有匹配的真实订单
                        real_qty = matched_order['qty']
                        real_status = matched_order['status']
                        
                        if real_qty <= 0:
                            # 真实订单已无剩余数量，清理本地记录
                            local_to_remove.append((level_idx, side, "真实订单已成交或撤销"))
                        elif real_qty != local_qty:
                            # 真实订单数量变化，更新本地数量
                            local_to_update.append((level_idx, side, real_qty, matched_order.get('status_desc', '未知')))
                        elif local_order_id != matched_order.get('order_id'):
                            # 订单ID变化，更新本地ID
                            details['order_id'] = matched_order.get('order_id')
                            # self.write_log(f"更新本地订单ID: {side} 层级{level_idx} -> {matched_order.get('order_id')}")
                    else:
                        # 没有匹配的真实订单，清理本地记录
                        local_to_remove.append((level_idx, side, "真实订单已不存在"))
                else:
                    # 本地没有这个挂单，跳过
                    pass
            
            # 2) 执行清理和更新
            for level_idx, side, reason in local_to_remove:
                key = (level_idx, side)
                if key in self._pending_orders:
                    self._pending_orders.remove(key)
                if key in self._pending_details:
                    del self._pending_details[key]
                # self.write_log(f"清理本地挂单: 层级{level_idx} {side} - {reason}")
            
            for level_idx, side, new_qty, status in local_to_update:
                key = (level_idx, side)
                if key in self._pending_details:
                    self._pending_details[key]['qty'] = new_qty
                    # self.write_log(f"更新本地挂单数量: {side} 层级{level_idx} {status} -> {new_qty}")
            
            # 3) 补充缺失的订单ID（针对已有挂单但缺失ID的情况）
            for (level_idx, side), details in self._pending_details.items():
                if (level_idx, side) in self._pending_orders and details.get('order_id') is None:
                    local_price = round(details.get('price', 0), 6)
                    local_qty = details.get('qty', 0)
                    
                    # 查找匹配的真实订单
                    for order_id, order_info in real_orders.items():
                        if (order_info['side'] == side and 
                            round(order_info['price'], 6) == local_price and
                            order_info['qty'] == local_qty):
                            details['order_id'] = order_id
                            # self.write_log(f"补充本地订单ID: {side} 层级{level_idx} 价格{local_price} -> {order_id}")
                            break
                        
        except Exception as e:
            print(f"[GridStrategy] Failed to sync with real orders: {e}")
            import traceback
            traceback.print_exc()
    
    def _clear_all_pending_orders(self) -> None:
        """清理所有本地挂单状态"""
        try:
            keys_to_remove = list(self._pending_orders.copy())
            for key in keys_to_remove:
                self._pending_orders.remove(key)
                if key in self._pending_details:
                    del self._pending_details[key]
            # self.write_log(f"清理了{len(keys_to_remove)}个本地挂单状态")
        except Exception as e:
            self.write_log(f"清理所有挂单状态失败: {e}")

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
        if self.spec:
            grid_price = self.spec.level_price(level_index)
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
                #time.sleep(1)  # 睡眠1秒钟 
                # 获取买入成交价格
                pos = self.pos_book.get(level_index)
                if pos and pos.avg_cost > 0:
                    # 计算新的avg_cost：买入价格+一个网格
                    buy_price = pos.avg_cost  # 这里应该是成交价格，但pos_book中存储的是avg_cost
                    new_avg_cost = buy_price + self.spec.step
                    
                    # 找到avg_cost对应的网格层级
                    avg_cost_level = int(round((new_avg_cost - self.spec.baseline) / self.spec.step))
                    print('判断是否要挂上一网格的卖单')
                    # 确保在网格范围内

                    # 分别测试两个函数，看哪个卡住了

                    
                    #print('开始测试 _has_real_sell_order_at_price...')
                    #has_real_order_result = self._has_real_sell_order_at_price(avg_cost_level)
                    #print(f'_has_real_sell_order_at_price 结果: {has_real_order_result}')

                    #print('ddddddddddddd', has_pending_result, has_real_order_result)
                    print('self._has_pending(avg_cost_level, "SELL")', self._has_pending(avg_cost_level, "SELL"))
                    # 在avg_cost位置挂卖单
                    if not self._has_pending(avg_cost_level, "SELL"):# and not self._has_real_sell_order_at_price(avg_cost_level):
                        sell_qty = pos.qty  # 卖出相同数量
                        sell_price = new_avg_cost  # 在avg_cost位置卖出
                        
                        self._place_order_real(avg_cost_level, "SELL", sell_qty, sell_price)
                        
                        self.write_log(f"买入成交后在avg_cost挂卖单: 层级{avg_cost_level} | 价格{sell_price:.6f} | 数量{sell_qty}")
            
            self.write_log(f"订单成交: {side} | 层级: {level_index} | 挂单状态已清除")
        except Exception as e:
            self.write_log(f"清除挂单状态失败: {e}")
    
    def _sync_positions_with_broker(self) -> None:
        print("开始同步本地仓位")
        """同步真实仓位与本地仓位，如果券商真实仓位少，则删除多余的本地仓位（从成本低开始删）"""
        try:
            # 1) 获取券商真实仓位
            if not hasattr(self, 'manager') or not self.manager or not hasattr(self.manager, 'trader') or not self.manager.trader:
                # self.write_log("[DEBUG] 没有trader实例，跳过仓位同步")
                return  
            
            try:
                positions = self.manager.trader.get_positions()
                if not positions:
                    # self.write_log("[DEBUG] 券商无持仓，清空所有本地仓位")
                    self._clear_all_local_positions()
                    return
                
                # 计算券商总持仓数量
                broker_total_qty = 0
                #self.write_log(f"[DEBUG] 券商返回的仓位数据: {positions}")
                for pos in positions:
                    stock_code = pos.get('stock_code', '')
                    #self.write_log(f"[DEBUG] 检查仓位: 代码={stock_code}, 总数量={pos.get('volume', 0)}, 可用数量={pos.get('can_use_volume', 0)}, 冻结数量={pos.get('frozen_volume', 0)}")
                    if stock_code == self.manager.stock_code or stock_code == self.manager.stock_code.replace('.SH', '').replace('.SZ', ''):
                        # 使用volume而不是can_use_volume进行仓位同步
                        # volume是总持仓，can_use_volume是可用仓位（扣除冻结部分）
                        broker_total_qty += pos.get('volume', 0)
                        #self.write_log(f"[DEBUG] 匹配到目标股票，累计数量: {broker_total_qty}")
                
                # self.write_log(f"[DEBUG] 券商真实持仓数量: {broker_total_qty}")
                
            except Exception as e:
                self.write_log(f"[DEBUG] 获取券商仓位失败: {e}")
                return
            
            # 2) 计算本地总持仓数量
            local_total_qty = 0
            local_positions = []
            
            for level_idx in range(self.spec.min_level_index, self.spec.max_level_index + 1):
                pos = self.pos_book.get(level_idx)
                if pos and pos.qty > 0:
                    local_total_qty += pos.qty
                    local_positions.append({
                        'level_idx': level_idx,
                        'qty': pos.qty,
                        'avg_cost': pos.avg_cost
                    })
            
            # self.write_log(f"[DEBUG] 本地持仓数量: {local_total_qty}")
            
            # 3) 如果券商仓位 >= 本地仓位，不做处理
            if broker_total_qty >= local_total_qty:
                # self.write_log(f"[DEBUG] 券商仓位充足，无需同步")
                return
            
            # 4) 券商仓位 < 本地仓位，需要删除多余的本地仓位
            excess_qty = local_total_qty - broker_total_qty
            # self.write_log(f"[DEBUG] 本地仓位过多，需要删除: {excess_qty}")
            
            # 按成本从低到高排序（优先删除成本低的仓位）
            local_positions.sort(key=lambda x: x['avg_cost'])
            
            # 删除多余的本地仓位
            removed_qty = 0
            for pos_info in local_positions:
                if removed_qty >= excess_qty:
                    break
                
                level_idx = pos_info['level_idx']
                pos_qty = pos_info['qty']
                avg_cost = pos_info['avg_cost']
                
                # 计算需要删除的数量
                qty_to_remove = min(pos_qty, excess_qty - removed_qty)
                
                # 删除本地仓位
                self.pos_book.sell_at_level(level_idx, qty_to_remove)
                removed_qty += qty_to_remove
                
                self.write_log(f"删除本地仓位: 层级{level_idx} | 成本{avg_cost:.6f} | 数量{qty_to_remove}")
            
            # 5) 保存更新后的仓位到文件
            if hasattr(self, 'manager') and self.manager:
                self.manager._save_positions_to_text()
            self.write_log(f"[DEBUG] 仓位同步完成，删除了{removed_qty}个多余仓位")
            
        except Exception as e:
            self.write_log(f"[DEBUG] 仓位同步失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _clear_all_local_positions(self) -> None:
        """清空所有本地仓位"""
        for level_idx in range(self.spec.min_level_index, self.spec.max_level_index + 1):
            pos = self.pos_book.get(level_idx)
            if pos and pos.qty > 0:
                self.pos_book.sell_at_level(level_idx, pos.qty)
        if hasattr(self, 'manager') and self.manager:
            self.manager._save_positions_to_text()
        # self.write_log("[DEBUG] 已清空所有本地仓位")
