"""
金叉死叉策略示例 - 用于 ``@vnpy测试`` 目录

本文件包含：
1. 基于移动平均线交叉的CTA策略示例（使用推送模式）
2. 使用 xtdata 的 subscribe_stock_quotes 进行实时数据推送

使用步骤：
- 设置 xtdata token
- 调整文件底部的股票代码列表
- 执行 ``python golden_cross_demo.py`` 运行实时策略
"""
from __future__ import annotations

import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from xtquant import xtdata
from vnpy_ctastrategy import CtaTemplate, BarGenerator, ArrayManager
from vnpy.trader.constant import Direction, Interval, Offset, Exchange
from vnpy_ctastrategy import BarData, TickData, TradeData, OrderData


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


class GoldenCrossStrategy(CtaTemplate):
    """
    简单的移动平均线交叉策略：
    - 当快线向上穿越慢线时做多（金叉）
    - 当快线向下穿越慢线时做空（死叉）
    """

    author = "金叉死叉策略示例"

    fast_window: int = 5
    slow_window: int = 20
    fixed_size: int = 1

    parameters = ["fast_window", "slow_window", "fixed_size"]
    variables = ["fast_ma", "slow_ma", "cross_value", "pos"]

    def __init__(
        self,
        cta_engine,
        strategy_name: str,
        vt_symbol: str,
        setting: Dict[str, Any],
    ) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        if self.fast_window >= self.slow_window:
            raise ValueError("快线周期必须小于慢线周期")

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager(self.slow_window + 50)

        self.fast_ma: float = 0.0
        self.slow_ma: float = 0.0
        self.cross_value: float = 0.0

    def on_init(self) -> None:
        """策略初始化时的回调函数"""
        self.write_log("金叉死叉策略已初始化")
        self.load_bar(self.slow_window + 50)

    def on_start(self) -> None:
        """策略启动时的回调函数"""
        self.write_log("金叉死叉策略已启动")

    def on_stop(self) -> None:
        """策略停止时的回调函数"""
        self.write_log("金叉死叉策略已停止")

    def on_tick(self, tick: TickData) -> None:
        """Tick数据更新时的回调函数（推送模式）"""
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        """基于K线数据的主要信号逻辑"""
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        self.fast_ma = self.am.sma(self.fast_window)
        self.slow_ma = self.am.sma(self.slow_window)
        self.cross_value = self.fast_ma - self.slow_ma

        if self.cross_value > 0 and self.pos <= 0:
            # 检测到金叉 -> 做多
            if self.pos < 0:
                self.cover(bar.close_price, abs(self.pos))
            self.buy(bar.close_price, self.fixed_size)

        elif self.cross_value < 0 and self.pos >= 0:
            # 检测到死叉 -> 做空
            if self.pos > 0:
                self.sell(bar.close_price, abs(self.pos))
            self.short(bar.close_price, self.fixed_size)

        self.put_event()

    def on_order(self, order: OrderData) -> None:
        """订单状态变化时的回调函数"""
        pass

    def on_trade(self, trade: TradeData) -> None:
        """成交时的回调函数"""
        self.put_event()


class GoldenCrossStrategyManager:
    """金叉死叉策略管理器 - 使用推送模式"""
    
    def __init__(self, stock_codes: List[str], strategy_params: Optional[Dict[str, Any]] = None):
        """
        初始化策略管理器
        
        Args:
            stock_codes: 股票代码列表，如 ["000001.SZ", "159100.SZ"]
            strategy_params: 策略参数字典
        """
        self.stock_codes = stock_codes
        self.strategy_params = strategy_params or {
            "fast_window": 5,
            "slow_window": 20,
            "fixed_size": 1,
        }
        
        # 为每个股票创建策略实例
        self.strategies: Dict[str, GoldenCrossStrategy] = {}
        self.subscription_id: Optional[int] = None
        
        # 初始化策略实例（这里简化处理，实际可能需要 cta_engine）
        # 注意：由于策略需要 cta_engine，这里创建一个简化版本用于演示
        print(f"初始化策略管理器，监控 {len(stock_codes)} 只股票")
        for code in stock_codes:
            print(f"  - {code}")
    
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
            for stock_code, tick_data in datas.items():
                # 转换为 TickData
                tick = self._convert_xtdata_to_tick(stock_code, tick_data)
                if tick is None:
                    continue
                
                # 获取或创建策略实例
                if stock_code not in self.strategies:
                    # 这里简化处理，实际需要传入 cta_engine
                    # 由于策略需要完整的 cta_engine，这里只做数据打印
                    print(f"[{stock_code}] 收到 tick 数据: 价格={tick.last_price:.2f}, "
                          f"成交量={tick.volume}, 涨跌={(tick.last_price - tick.pre_close) / tick.pre_close * 100:.2f}%")
                    
                    # TODO: 实际使用时，需要将 tick 传递给策略的 on_tick 方法
                    # strategy = self.strategies[stock_code]
                    # strategy.on_tick(tick)
                else:
                    strategy = self.strategies[stock_code]
                    strategy.on_tick(tick)
                    
        except Exception as e:
            print(f"处理 tick 数据失败: {e}")
            traceback.print_exc()
    
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
                code_list=self.stock_codes,
                callback=self.on_tick_data
            )
            
            print(f"订阅成功，ID: {self.subscription_id}，订阅 {len(self.stock_codes)} 只股票")
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
    运行实时策略 - 使用推送模式获取数据
    """
    # 设置 xtdata token（需要根据实际情况设置）
    # xtdata.set_token('your_token_here')
    
    # 配置股票代码列表
    stock_codes = ["000001.SZ", "159100.SZ"]  # 可以根据需要修改
    
    # 策略参数
    strategy_params = {
        "fast_window": 5,
        "slow_window": 20,
        "fixed_size": 1,
    }
    
    # 创建策略管理器
    manager = GoldenCrossStrategyManager(stock_codes, strategy_params)
    
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
        manager.unsubscribe_stock_quotes()
        print("策略已停止")


if __name__ == "__main__":
    run_realtime_strategy()

