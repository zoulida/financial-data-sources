"""
券商接口封装模块

封装 QMT 交易器的所有交互，包括：
- 交易器初始化与连接
- 买卖下单（带超时保护）
- 查询持仓、订单
- 成交回调处理
"""
from __future__ import annotations

import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import BrokerConfig, OrderType
from .utils import match_stock_code


class BrokerGateway:
    """
    券商网关 —— 封装 QMT 交易接口

    职责：
        1. 管理与 QMT 的连接生命周期
        2. 提供买/卖下单方法（带线程超时保护）
        3. 提供持仓、订单查询方法
        4. 维护 order_id → 元数据 的映射（供成交回调使用）
    """

    def __init__(
        self,
        stock_code: str,
        qmt_path: str = BrokerConfig.DEFAULT_PATH,
        account: str = BrokerConfig.DEFAULT_ACCOUNT,
        account_type: str = BrokerConfig.DEFAULT_ACCOUNT_TYPE,
        on_filled_callback: Optional[Callable] = None,
    ) -> None:
        """
        Args:
            stock_code       : 股票代码 (如 "162411.SZ")
            qmt_path         : QMT 客户端 userdata 路径
            account          : 交易账户
            account_type     : 账户类型
            on_filled_callback: 成交回调函数 (event_dict) -> None
        """
        self.stock_code = stock_code
        self._qmt_path = qmt_path
        self._account = account
        self._account_type = account_type
        self._on_filled_callback = on_filled_callback

        # QMT BaseTrader 实例
        self.trader = None

        # 订单映射: order_id → {level_index, side, qty, price, entry_id}
        self._order_map: Dict[Any, Dict[str, Any]] = {}
        self._trade_seq: int = 0

        # 订单日志文件
        self._orders_log_path = self._build_orders_log_path()
        self._init_orders_log()

    # ==============================================================
    #  初始化
    # ==============================================================
    def connect(self, exit_on_failure: bool = True) -> bool:
        """
        连接 QMT 交易器

        Args:
            exit_on_failure: 连接失败时是否退出程序（实盘模式应为 True）

        Returns:
            是否连接成功
        """
        try:
            from .trader import build_qmt_trader_with_callback

            print(f"[Broker] 开始初始化交易器...")
            trader = build_qmt_trader_with_callback(
                on_filled=self._handle_filled_event,
                path=self._qmt_path,
                account=self._account,
                account_type=self._account_type,
                session_id=None,
            )

            if trader and hasattr(trader, "_connected") and trader._connected:
                self.trader = trader
                print(f"[Broker] 交易器连接成功，账户: {self._account}")
                return True
            else:
                self.trader = None
                status = getattr(trader, "_connected", "N/A") if trader else "trader is None"
                print(f"[Broker] 交易器连接失败。_connected={status}")

                if exit_on_failure:
                    print("❌ 实盘模式交易器连接失败，策略停止执行")
                    print("请检查：\n1. QMT客户端是否已启动并登录\n2. 交易账户是否正确\n3. 网络连接是否正常")
                    import sys
                    sys.exit(1)
                return False

        except Exception as e:
            self.trader = None
            print(f"[Broker] 交易器初始化异常: {e}")
            traceback.print_exc()
            if exit_on_failure:
                import sys
                sys.exit(1)
            return False

    @property
    def is_connected(self) -> bool:
        """交易器是否已连接"""
        return self.trader is not None

    # ==============================================================
    #  下单
    # ==============================================================
    def place_order(
        self,
        level_index: int,
        side: str,
        qty: int,
        price: float,
        entry_id: Optional[str] = None,
        timeout: float = 5.0,
    ) -> Optional[str]:
        """
        下单（带超时保护）

        Args:
            level_index: 网格层级
            side       : "BUY" 或 "SELL"
            qty        : 数量
            price      : 价格
            entry_id   : 本地订单号（写入券商备注）
            timeout    : 超时秒数

        Returns:
            券商订单号字符串，失败返回 None
        """
        if self.trader is None:
            return None

        from xtquant import xtconstant

        result_container: Dict[str, Any] = {"result": None, "done": False}

        def _do_order():
            try:
                if side == "BUY":
                    remark = f"BUY_{entry_id}" if entry_id else f"grid_level_{level_index}"
                    oid = self.trader.buy(
                        stock_code=self.stock_code,
                        volume=qty,
                        price=price,
                        price_type=xtconstant.FIX_PRICE,
                        strategy_name="grid_strategy",
                        order_remark=remark,
                    )
                else:
                    remark = f"SELL_{entry_id}" if entry_id else f"grid_level_{level_index}"
                    oid = self.trader.sell(
                        stock_code=self.stock_code,
                        volume=qty,
                        price=price,
                        price_type=xtconstant.FIX_PRICE,
                        strategy_name="grid_strategy",
                        order_remark=remark,
                    )
                result_container["result"] = oid
            except Exception as e:
                print(f"[Broker] 下单异常: {e}")
            finally:
                result_container["done"] = True

        thread = threading.Thread(target=_do_order, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if not result_container["done"]:
            print(f"[Broker] 下单超时: {side} | 层级{level_index} | 价格{price:.6f} | 数量{qty}")
            return None

        oid = result_container["result"]
        if oid is None or oid <= 0:
            print(f"[Broker] 下单失败: {side} | 层级{level_index} | 价格{price:.6f} | 数量{qty}")
            return None

        # 记录订单映射（同时存 str 和 int 键以兼容回调）
        oid_str = str(oid)
        meta = {"level_index": level_index, "side": side, "qty": qty, "price": price, "entry_id": entry_id}
        self._order_map[oid_str] = meta
        try:
            self._order_map[int(oid)] = meta
        except (ValueError, TypeError):
            pass

        # 记录到订单日志
        self._append_order_log(oid_str, side, level_index, price, qty)
        return oid_str

    def sell_direct(self, qty: int, price: float, order_remark: str = "") -> Optional[str]:
        """
        直接卖出（不经过层级路由，用于 _place_sell_for_pending_positions）

        Returns:
            券商订单号字符串，失败返回 None
        """
        if self.trader is None:
            return None
        try:
            oid = self.trader.sell(
                stock_code=self.stock_code,
                volume=qty,
                price=price,
                order_remark=order_remark,
            )
            return str(oid) if oid else None
        except Exception as e:
            print(f"[Broker] 直接卖出异常: {e}")
            return None

    # ==============================================================
    #  查询
    # ==============================================================
    def get_available_qty(self) -> int:
        """获取当前股票的券商可用仓位数量"""
        if self.trader is None:
            return 0
        try:
            positions = self.trader.get_positions()
            if not positions:
                return 0
            for pos in positions:
                if match_stock_code(pos.get("stock_code", ""), self.stock_code):
                    return int(pos.get("can_use_volume", 0))
            return 0
        except Exception:
            return 0

    def get_unfilled_orders(self) -> List[dict]:
        """获取未成交订单列表"""
        if self.trader is None:
            return []
        try:
            orders = self.trader.get_unfilled_orders(verbose=False)
            return orders if orders else []
        except Exception:
            return []

    def get_all_orders(self) -> List[dict]:
        """获取所有订单列表（含已成交）"""
        if self.trader is None:
            return []
        try:
            orders = self.trader.get_orders()
            return orders if orders else []
        except Exception:
            return []

    def get_my_unfilled_orders(self) -> List[dict]:
        """获取当前股票的未成交订单"""
        all_orders = self.get_unfilled_orders()
        return [o for o in all_orders if match_stock_code(o.get("stock_code", ""), self.stock_code)]

    def get_my_all_orders(self) -> List[dict]:
        """获取当前股票的所有订单"""
        all_orders = self.get_all_orders()
        return [o for o in all_orders if match_stock_code(o.get("stock_code", ""), self.stock_code)]

    # ==============================================================
    #  成交回调（内部）
    # ==============================================================
    def _handle_filled_event(self, event: Dict[str, Any]) -> None:
        """
        处理 QMT 成交回调事件

        从 _order_map 中查找元数据，然后转发给上层 on_filled_callback
        """
        try:
            order_id_raw = event.get("order_id")
            oid_str = str(order_id_raw) if order_id_raw is not None else None
            try:
                oid_int = int(order_id_raw) if order_id_raw is not None else None
            except (ValueError, TypeError):
                oid_int = None

            # 从映射中查找元数据
            meta = None
            if oid_int is not None:
                meta = self._order_map.pop(oid_int, None)
            if meta is None and oid_str is not None:
                meta = self._order_map.pop(oid_str, None)

            if not meta:
                print(f"[Broker] 成交回调: 找不到订单元数据 order_id={order_id_raw}")
                return

            # 补充信息后转发
            event["_meta"] = meta
            event["_trade_seq"] = self._next_trade_id()

            if self._on_filled_callback:
                self._on_filled_callback(event)

        except Exception:
            traceback.print_exc()

    def _next_trade_id(self) -> int:
        self._trade_seq += 1
        return self._trade_seq

    # ==============================================================
    #  订单日志
    # ==============================================================
    def _build_orders_log_path(self) -> Path:
        base = Path(__file__).resolve().parent / "trading_records"
        code_clean = self.stock_code.split(".")[0]
        today = datetime.now().strftime("%Y%m%d")
        return base / code_clean / today / "orders_placed.csv"

    def _init_orders_log(self) -> None:
        """初始化订单记录文件"""
        try:
            import csv
            self._orders_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._orders_log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["order_id", "side", "level_index", "price", "qty", "placed_time", "status"])
        except Exception as e:
            print(f"[Broker] 初始化订单日志失败: {e}")

    def _append_order_log(self, order_id: str, side: str, level_index: int, price: float, qty: int) -> None:
        """追加一条订单记录"""
        try:
            import csv
            with open(self._orders_log_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                placed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([order_id, side, level_index, price, qty, placed_time, "placed"])
        except Exception as e:
            print(f"[Broker] 追加订单日志失败: {e}")
