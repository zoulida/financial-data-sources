"""
网格策略管理器模块 - 使用推送模式，支持实盘和模拟模式
"""
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from xtquant import xtdata
from vnpy_ctastrategy import BarData, TickData, TradeData, OrderData

from .utils import get_exchange_from_code
from .mock_replayer import MockTickReplayer

# 导入其他模块
if __package__ in {None, ""}:
    from src.网格.网格信号实盘.grid_strategy import GridStrategy
    from src.网格.网格信号实盘.order_sim import Trade
    from src.网格.网格信号实盘.position_book import PositionBook
    from src.网格.网格信号实盘.run_grid_512710 import _load_tick_raw_dataframe
    from md.xtquant交易.base_trader_zld import BaseTrader
else:
    from .grid_strategy import GridStrategy
    from .order_sim import Trade
    from .position_book import PositionBook
    from .run_grid_512710 import _load_tick_raw_dataframe
    from md.xtquant交易.base_trader_zld import BaseTrader


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
        self.trader: Optional[BaseTrader] = None
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
            from vnpy.trader.object import TickData
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
                # 静默使用简化版 cta_engine（不影响实盘交易功能）
            
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
                setting=setting,
                manager=self  # 传递策略管理器引用
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
                        level_index=level_index
                    )
                    self.strategy.trades.append(tr)
                elif side == "SELL":
                    # 卖出成交：从对应网格层级移除仓位
                    self.strategy.pos_book.sell_at_level(level_index, traded_volume)
                    
                    tr = Trade(
                        trade_id=self._next_trade_id(),
                        order_id=int(order_id_int) if order_id_int is not None else int(order_id_str) if order_id_str and order_id_str.isdigit() else 0,
                        ts=ts,
                        side=side,
                        price=traded_price,
                        qty=traded_volume,
                        level_index=level_index
                    )
                    self.strategy.trades.append(tr)
                
                # 调用策略的成交回调方法
                self.strategy.on_order_filled(level_index, side)
                
                self._save_positions_to_text()
            except Exception:
                traceback.print_exc()

        # 尝试创建交易器
        try:
            print(f"[GridTrader] 开始初始化交易器...")
            trader = build_qmt_trader_with_callback(
                on_filled=on_filled,
                path=self.strategy_params.get("qmt_path", r"D:\国金证券QMT交易端\userdata_mini"),
                account=self.strategy_params.get("qmt_account", "8886063599"),
                account_type=self.strategy_params.get("qmt_account_type", "STOCK"),
                session_id=None,  # 让BaseTrader随机生成8位数session_id
            )
            
            print(f"[GridTrader] build_qmt_trader_with_callback返回: {trader}")
            print(f"[GridTrader] trader类型: {type(trader)}")
            
            # 只有连接成功才设置trader
            if trader and hasattr(trader, '_connected') and trader._connected:
                self.trader = trader
                print(f"[GridTrader] 交易器初始化成功，账户: {self.strategy_params.get('qmt_account', '8886063599')}")
            else:
                self.trader = None
                connected_status = getattr(trader, '_connected', 'No _connected attr') if trader else 'trader is None'
                print(f"[GridTrader] 交易器初始化失败，连接未成功。_connected状态: {connected_status}")
                
                # 如果是实盘模式且连接失败，直接退出程序
                if not self.simulate:
                    print("❌ 实盘模式交易器连接失败，策略停止执行")
                    print("请检查：")
                    print("1. QMT客户端是否已启动并登录")
                    print("2. 交易账户是否正确")
                    print("3. 网络连接是否正常")
                    import sys
                    sys.exit(1)
                
        except Exception as e:
            self.trader = None
            print(f"[GridTrader] 交易器初始化异常: {e}")
            traceback.print_exc()
            
            # 如果是实盘模式且初始化异常，直接退出程序
            if not self.simulate:
                print("❌ 实盘模式交易器初始化异常，策略停止执行")
                import sys
                sys.exit(1)

    def _place_real_order(self, level_index: int, side: str, qty: int, price: float) -> None:
        import threading
        import time
        
        from xtquant import xtconstant
        if self.trader is None:
            return
        
        def _order_with_timeout():
            try:
                if side == "BUY":
                    oid = self.trader.buy(
                        stock_code=self.stock_code,
                        volume=qty,
                        price=price,
                        price_type=xtconstant.FIX_PRICE,
                        strategy_name="grid_strategy",
                        order_remark=f"grid_level_{level_index}"
                    )
                else:
                    oid = self.trader.sell(
                        stock_code=self.stock_code,
                        volume=qty,
                        price=price,
                        price_type=xtconstant.FIX_PRICE,
                        strategy_name="grid_strategy",
                        order_remark=f"grid_level_{level_index}"
                    )
                return oid
            except Exception as e:
                print(f"下单异常: {e}")
                return None
        
        # 使用线程和超时来防止阻塞
        result_container = {'result': None, 'done': False}
        
        def worker():
            result_container['result'] = _order_with_timeout()
            result_container['done'] = True
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=5.0)  # 5秒超时
        
        if not result_container['done']:
            print(f"下单超时: {side} | 层级: {level_index} | 价格: {price:.6f} | 数量: {qty}")
            return
        
        oid = result_container['result']
        if oid is None or oid <= 0:
            print(f"下单失败: {side} | 层级: {level_index} | 价格: {price:.6f} | 数量: {qty}")
            return
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
            positions = self.trader.get_positions()
            if not positions:
                return 0
            code6 = self.stock_code.split(".")[0]
            for position in positions:
                if position.get('stock_code', '').split('.')[0] == code6:
                    return int(position.get('volume', 0))
            return 0
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


# 导入交易器构建函数
if __package__ in {None, ""}:
    from src.网格.网格信号实盘.trader import build_qmt_trader_with_callback
else:
    from .trader import build_qmt_trader_with_callback
