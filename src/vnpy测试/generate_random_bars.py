"""
生成随机K线数据并导入到vnpy数据库的示例

这个脚本演示如何：
1. 生成随机K线数据
2. 将数据导入到vnpy的SQLite数据库中
3. 供回测引擎使用
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List

from vnpy.trader.database import get_database
from vnpy.trader.constant import Interval, Exchange
from vnpy_ctastrategy import BarData


def generate_random_bars(
    symbol: str,
    exchange: Exchange,
    start_date: datetime,
    days: int,
    base_price: float = 100.0,
    volatility: float = 0.02,
) -> List[BarData]:
    """
    生成随机K线数据
    
    参数:
        symbol: 合约代码
        exchange: 交易所
        start_date: 起始日期
        days: 生成天数
        base_price: 基础价格
        volatility: 波动率
    
    返回:
        BarData列表
    """
    bars: List[BarData] = []
    current_price = base_price
    current_date = start_date
    
    for i in range(days):
        # 生成随机价格变动（随机游走）
        change_pct = random.uniform(-volatility, volatility)
        current_price = current_price * (1 + change_pct)
        
        # 确保价格为正
        if current_price <= 0:
            current_price = base_price
        
        # 生成OHLC数据
        high = current_price * random.uniform(1.0, 1.02)
        low = current_price * random.uniform(0.98, 1.0)
        open_price = current_price * random.uniform(0.99, 1.01)
        close_price = current_price
        
        # 确保 high >= max(open, close) 且 low <= min(open, close)
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)
        
        # 生成成交量和成交额
        volume = random.randint(1000, 100000)
        turnover = volume * close_price
        
        # 创建BarData对象
        bar = BarData(
            symbol=symbol,
            exchange=exchange,
            datetime=current_date.replace(hour=15, minute=0, second=0, microsecond=0),
            interval=Interval.DAILY,
            volume=volume,
            open_price=open_price,
            high_price=high,
            low_price=low,
            close_price=close_price,
            turnover=turnover,
            open_interest=0,
            gateway_name="DEMO",
        )
        
        bars.append(bar)
        current_date += timedelta(days=1)
    
    return bars


def import_bars_to_database(
    symbol: str,
    exchange: Exchange,
    bars: List[BarData],
) -> None:
    """
    将K线数据导入到vnpy数据库
    
    参数:
        symbol: 合约代码
        exchange: 交易所
        bars: K线数据列表
    """
    # 获取数据库实例
    database = get_database()
    
    print(f"正在导入 {len(bars)} 条K线数据到数据库...")
    print(f"合约: {symbol}.{exchange.value}")
    
    # 导入数据
    database.save_bar_data(bars)
    
    print(f"✓ 成功导入 {len(bars)} 条数据")
    print(f"  时间范围: {bars[0].datetime.date()} 至 {bars[-1].datetime.date()}")


def main():
    """主函数：生成并导入随机K线数据"""
    # 配置参数
    symbol = "rb2405"
    exchange = Exchange.SHFE
    start_date = datetime(2023, 1, 1)
    days = 365  # 生成一年的数据
    base_price = 3500.0  # 螺纹钢基础价格
    volatility = 0.015  # 1.5%的日波动率
    
    print("=" * 60)
    print("随机K线数据生成和导入示例")
    print("=" * 60)
    print(f"\n配置参数:")
    print(f"  合约代码: {symbol}")
    print(f"  交易所: {exchange.value}")
    print(f"  起始日期: {start_date.date()}")
    print(f"  生成天数: {days}")
    print(f"  基础价格: {base_price}")
    print(f"  波动率: {volatility * 100:.2f}%")
    print()
    
    # 生成随机K线数据
    print("正在生成随机K线数据...")
    bars = generate_random_bars(
        symbol=symbol,
        exchange=exchange,
        start_date=start_date,
        days=days,
        base_price=base_price,
        volatility=volatility,
    )
    print(f"✓ 成功生成 {len(bars)} 条K线数据")
    
    # 显示前几条数据示例
    print("\n前5条数据示例:")
    for i, bar in enumerate(bars[:5], 1):
        print(f"  {i}. {bar.datetime.date()} | "
              f"O:{bar.open_price:.2f} H:{bar.high_price:.2f} "
              f"L:{bar.low_price:.2f} C:{bar.close_price:.2f} | "
              f"V:{bar.volume}")
    
    # 导入到数据库
    print()
    import_bars_to_database(
        symbol=symbol,
        exchange=exchange,
        bars=bars,
    )
    
    print("\n" + "=" * 60)
    print("数据导入完成！现在可以运行回测了。")
    print("=" * 60)
    print(f"\n提示: 在回测代码中使用以下参数:")
    print(f"  vt_symbol = '{symbol}.{exchange.value}'")
    print(f"  start = datetime({start_date.year}, {start_date.month}, {start_date.day})")
    end_date = start_date + timedelta(days=days-1)
    print(f"  end = datetime({end_date.year}, {end_date.month}, {end_date.day})")


if __name__ == "__main__":
    main()

