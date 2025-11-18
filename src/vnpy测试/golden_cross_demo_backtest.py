"""
金叉死叉策略示例 - 回测版本

本文件包含：
1. 基于移动平均线交叉的CTA策略示例
2. 一个辅助函数 ``run_backtesting``，演示如何使用内置的 ``BacktestingEngine`` 运行策略

使用步骤：
- 确保目标合约的历史数据已存在于vn.py数据库中（或根据你的工作流程修改引擎以下载数据）
- 调整文件底部的 ``vt_symbol`` 和回测参数
- 执行 ``python golden_cross_demo_backtest.py`` 运行示例回测
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from vnpy_ctastrategy import CtaTemplate, BarGenerator, ArrayManager
from vnpy_ctastrategy.backtesting import BacktestingEngine
from vnpy.trader.constant import Direction, Interval, Offset
from vnpy_ctastrategy import BarData, TickData, TradeData, OrderData


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
        """Tick数据更新时的回调函数（可选）"""
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


def run_backtesting() -> None:
    """
    快速辅助函数，用于在vn.py中运行上述策略的回测
    修改 vt_symbol、interval 和其他参数以匹配你的数据集
    """
    engine = BacktestingEngine()

    engine.set_parameters(
        vt_symbol="rb2405.SHFE",
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2024, 12, 31),
        rate=1 / 10000,
        slippage=1,
        size=10,
        pricetick=1,
        capital=1_000_000,
    )

    engine.add_strategy(
        GoldenCrossStrategy,
        {
            "fast_window": 5,
            "slow_window": 20,
            "fixed_size": 1,
        },
    )

    # 加载历史数据
    print("正在加载历史数据...")
    engine.load_data()

    # 检查是否有数据
    if not engine.history_data:
        print("\n⚠️  警告：数据库中没有找到历史数据！")
        print("请先运行 generate_random_bars.py 生成并导入测试数据")
        print(f"当前查询的合约: rb2405.SHFE")
        print(f"时间范围: 2023-01-01 至 2024-12-31")
        return

    print(f"[成功] 成功加载 {len(engine.history_data)} 条历史数据")

    # 运行回测
    print("\n开始运行回测...")
    engine.run_backtesting()
    engine.calculate_result()

    # 计算统计指标
    print("\n计算回测统计指标...")
    stats = engine.calculate_statistics()

    if stats:
        print("\n" + "=" * 60)
        print("回测统计结果:")
        print("=" * 60)
        # 显示关键指标
        key_metrics = [
            "total_return",
            "annual_return",
            "max_ddpercent",
            "total_trade_count",
            "sharpe_ratio",
            "total_net_pnl",
        ]
        for key in key_metrics:
            if key in stats:
                value = stats[key]
                if isinstance(value, float):
                    if "return" in key or "percent" in key or "ratio" in key:
                        print(
                            f"  {key:25s}: {value:>10.2%}"
                            if "%" not in str(value)
                            else f"  {key:25s}: {value:>10.2f}"
                        )
                    else:
                        print(f"  {key:25s}: {value:>10.2f}")
                else:
                    print(f"  {key:25s}: {value}")

        print("\n完整统计指标:")
        for key, value in stats.items():
            if key not in key_metrics:
                if isinstance(value, float):
                    print(f"  {key:25s}: {value:>10.2f}")
                else:
                    print(f"  {key:25s}: {value}")
    else:
        print("\n⚠️  回测结果为空，可能原因：")
        print("1. 数据量不足，无法产生交易信号")
        print("2. 策略参数设置不当")
        print("3. 数据时间范围问题")

    # 可选：如果在GUI环境中运行，打开vn.py的HTML图表查看器
    try:
        engine.show_chart()
    except Exception as exc:  # noqa: BLE001
        print(f"\n图表显示已跳过: {exc}")


if __name__ == "__main__":
    run_backtesting()


