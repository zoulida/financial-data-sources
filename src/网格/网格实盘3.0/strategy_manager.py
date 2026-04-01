"""
策略管理器模块

负责策略的生命周期管理，包括：
- 策略实例的创建与配置
- 行情数据订阅（实盘 / 模拟回放）
- Tick 数据转换与转发
- 成交回调路由
- 仓位文本状态管理（持仓数量显示）
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .broker import BrokerGateway
from .config import BrokerConfig, PositionStatus
from .grid_strategy import GridStrategy
from .mock_replayer import MockTickReplayer
from .tick_converter import convert_xtdata_to_tick


class GridStrategyManager:
    """
    网格策略管理器

    职责：
        1. 创建并初始化策略实例 (GridStrategy)
        2. 创建并管理券商网关 (BrokerGateway)
        3. 订阅实时行情或启动模拟回放
        4. 接收 tick 数据并转发给策略
        5. 处理成交回调，路由到策略

    使用方式：
        manager = GridStrategyManager("162411.SZ", params)
        manager.create_strategy()
        manager.subscribe_stock_quotes()  # 或启动模拟回放
    """

    def __init__(
        self,
        stock_code: str,
        strategy_params: Dict[str, Any],
        simulate: bool = False,
        simulate_date: Optional[str] = None,
        speed_factor: float = 1.0,
    ) -> None:
        """
        Args:
            stock_code     : 股票代码 (如 "162411.SZ")
            strategy_params: 策略参数字典 {step, up_grids, down_grids, ...}
            simulate       : 是否启用模拟回放模式
            simulate_date  : 模拟回放日期 (如 "20260304")
            speed_factor   : 回放速度因子 (1.0=原速, 2.0=两倍速)
        """
        self.stock_code = stock_code
        self.strategy_params = strategy_params
        self._simulate = simulate
        self._simulate_date = simulate_date
        self._speed_factor = speed_factor

        # ── 核心组件 ──
        self.strategy: Optional[GridStrategy] = None
        self.broker: Optional[BrokerGateway] = None
        self.mock_replayer: Optional[MockTickReplayer] = None

        # ── 行情订阅 ID ──
        self._subscribe_id: Optional[int] = None

    # ==============================================================
    #  策略创建
    # ==============================================================
    def create_strategy(self) -> bool:
        """
        创建策略实例并完成初始化

        流程：
            1. 构建策略参数
            2. 实盘模式下初始化券商网关
            3. 创建 GridStrategy 实例
            4. 加载已有仓位
            5. 注入下单函数
            6. 启动策略

        Returns:
            是否创建成功
        """
        try:
            # ── 1. 实盘模式：初始化券商 ──
            if not self._simulate:
                self.broker = BrokerGateway(
                    stock_code=self.stock_code,
                    qmt_path=BrokerConfig.DEFAULT_PATH,
                    account=BrokerConfig.DEFAULT_ACCOUNT,
                    account_type=BrokerConfig.DEFAULT_ACCOUNT_TYPE,
                    on_filled_callback=self._on_broker_filled,
                )
                if not self.broker.connect(exit_on_failure=True):
                    return False
            else:
                # 模拟模式下创建一个未连接的 broker 占位
                self.broker = BrokerGateway(
                    stock_code=self.stock_code,
                    on_filled_callback=self._on_broker_filled,
                )

            # ── 2. 构建策略 setting ──
            setting = dict(self.strategy_params)
            setting["simulate_mode"] = self._simulate

            # ── 3. 创建策略实例 ──
            self.strategy = GridStrategy(
                cta_engine=None,
                strategy_name="GridStrategy",
                vt_symbol=self.stock_code,
                setting=setting,
                manager=self,
            )

            # ── 4. 加载已有仓位 ──
            self._load_existing_positions()

            # ── 5. 注入下单函数 ──
            self.strategy.set_order_placer(self._place_real_order)

            # ── 6. 启动策略 ──
            self.strategy.on_init()
            self.strategy.on_start()

            print(f"[Manager] 策略创建成功: {self.stock_code}")
            return True

        except Exception as e:
            print(f"[Manager] 策略创建失败: {e}")
            traceback.print_exc()
            return False

    # ==============================================================
    #  行情订阅 / 模拟回放
    # ==============================================================
    def subscribe_stock_quotes(self) -> bool:
        """
        订阅行情数据（实盘）或启动模拟回放

        Returns:
            是否成功
        """
        if self._simulate:
            return self._start_mock_replay()
        else:
            return self._subscribe_realtime()

    def unsubscribe_stock_quotes(self) -> None:
        """取消行情订阅"""
        if self._simulate and self.mock_replayer:
            self.mock_replayer.stop()
            print("[Manager] 模拟回放已停止")
        elif self._subscribe_id is not None:
            try:
                from xtquant import xtdata
                xtdata.unsubscribe_quote(self._subscribe_id)
                print("[Manager] 已取消行情订阅")
            except Exception as e:
                print(f"[Manager] 取消订阅失败: {e}")

    def _subscribe_realtime(self) -> bool:
        """订阅 xtdata 实时行情"""
        try:
            from xtquant import xtdata
            print(f"[Manager] 订阅行情: {self.stock_code}")
            self._subscribe_id = xtdata.subscribe_whole_quote(
                code_list=[self.stock_code],
                callback=self._on_xtdata_callback,
            )
            if self._subscribe_id:
                print(f"[Manager] 行情订阅成功，ID={self._subscribe_id}")
                return True
            else:
                print("[Manager] 行情订阅失败")
                return False
        except Exception as e:
            print(f"[Manager] 行情订阅异常: {e}")
            traceback.print_exc()
            return False

    def _start_mock_replay(self) -> bool:
        """启动模拟回放"""
        try:
            self.mock_replayer = MockTickReplayer(
                stock_code=self.stock_code,
                simulate_date=self._simulate_date,
                speed_factor=self._speed_factor,
                on_tick_callback=self._on_mock_tick,
            )
            self.mock_replayer.start()
            print(f"[Manager] 模拟回放已启动: {self.stock_code} | 日期={self._simulate_date} | 速度={self._speed_factor}x")
            return True
        except Exception as e:
            print(f"[Manager] 模拟回放启动失败: {e}")
            traceback.print_exc()
            return False

    # ==============================================================
    #  Tick 数据回调
    # ==============================================================
    def _on_xtdata_callback(self, data: Dict[str, Any]) -> None:
        """
        xtdata 行情推送回调

        将原始数据转换为 TickData 后转发给策略
        """
        try:
            if self.stock_code not in data:
                return

            tick_raw = data[self.stock_code]
            tick = convert_xtdata_to_tick(self.stock_code, tick_raw)
            if tick is None:
                return

            if self.strategy:
                self.strategy.on_tick(tick)

        except Exception as e:
            print(f"[Manager] tick回调处理失败: {e}")
            traceback.print_exc()

    def _on_mock_tick(self, tick_dict: Dict[str, Any]) -> None:
        """
        模拟回放 tick 回调

        将回放数据转换为 TickData 后转发给策略
        """
        try:
            tick = convert_xtdata_to_tick(self.stock_code, tick_dict)
            if tick is None:
                return
            if self.strategy:
                self.strategy.on_tick(tick)
        except Exception as e:
            print(f"[Manager] 模拟tick回调失败: {e}")

    # ==============================================================
    #  下单路由
    # ==============================================================
    def _place_real_order(
        self,
        level_index: int,
        side: str,
        qty: int,
        price: float,
        entry_id: Optional[str] = None,
    ) -> None:
        """
        真实下单路由 —— 由策略调用

        通过 BrokerGateway 下单，成功后通知策略挂单确认
        """
        if self._simulate or not self.broker or not self.broker.is_connected:
            return

        order_id = self.broker.place_order(
            level_index=level_index,
            side=side,
            qty=qty,
            price=price,
            entry_id=entry_id,
        )

        if order_id and self.strategy:
            self.strategy.on_order_placed(level_index, side, qty, price, order_id)

            # 买单：回填 buy_order_id 到仓位记录
            if side == "BUY" and entry_id:
                self.strategy.pos_book.update_buy_order_id(entry_id, order_id)
                self.strategy.pos_book.save_to_csv()
                print(f"[Manager] 买单已提交: order_id={order_id} | entry_id={entry_id}")

    # ==============================================================
    #  成交回调路由
    # ==============================================================
    def _on_broker_filled(self, event: Dict[str, Any]) -> None:
        """
        券商成交回调处理

        从 event["_meta"] 中获取订单元数据，
        路由到策略的 on_order_filled 方法
        """
        try:
            meta = event.get("_meta")
            if not meta:
                print(f"[Manager] 成交回调: 无元数据")
                return

            level_index = meta["level_index"]
            side = meta["side"]
            entry_id = meta.get("entry_id")
            fill_price = event.get("traded_price", meta.get("price", 0))
            qty = event.get("traded_volume", meta.get("qty", 0))
            trade_id = event.get("traded_id") or event.get("order_id")

            if self.strategy:
                self.strategy.on_order_filled(
                    level_index=level_index,
                    side=side,
                    fill_price=fill_price,
                    qty=qty,
                    trade_id=str(trade_id) if trade_id else None,
                    entry_id=entry_id,
                )

        except Exception as e:
            print(f"[Manager] 成交回调处理异常: {e}")
            traceback.print_exc()

    # ==============================================================
    #  仓位加载
    # ==============================================================
    def _load_existing_positions(self) -> None:
        """加载已有的仓位 CSV 文件"""
        if not self.strategy:
            return

        csv_path = self.strategy.pos_book.csv_path
        if csv_path and os.path.exists(csv_path):
            self.strategy.pos_book.load_from_csv()
            count = len(self.strategy.pos_book.entries)
            if count > 0:
                print(f"[Manager] 已加载{count}条仓位记录: {csv_path}")
                self.strategy._pos_loaded_from_text = True
            else:
                print(f"[Manager] 仓位文件为空: {csv_path}")
        else:
            print(f"[Manager] 无历史仓位文件")
