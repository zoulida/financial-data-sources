"""行情订阅功能使用示例。

本示例展示如何使用 QuoteSubscriber 订阅实时行情数据。
订阅后，每1.9秒会自动推送一次最新的行情数据。
"""

import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

# 添加当前目录到路径，以便导入 xtdata_quote
sys.path.insert(0, str(Path(__file__).parent))

from xtdata_quote import QuoteSubscriber

if TYPE_CHECKING:
    from collections.abc import Callable


def example1_basic_subscribe() -> None:
    """示例1：基本订阅用法。"""
    print("=" * 60)
    print("示例1：基本订阅用法")
    print("=" * 60)

    def on_data_received(df: pd.DataFrame) -> None:
        """数据推送回调函数。"""
        print(f"\n[{time.strftime('%H:%M:%S')}] 收到行情数据:")
        print(df[["price", "last_close", "vol", "amount"]])

    # 创建订阅管理器
    subscriber = QuoteSubscriber(["600519.SH", "000001.SZ"])

    # 订阅数据推送
    subscriber.subscribe(on_data_received)

    print("已开始订阅，等待数据推送...")
    print("按 Ctrl+C 停止订阅\n")

    try:
        # 保持运行，等待数据推送
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止订阅...")
        subscriber.stop()


def example2_multiple_subscribers() -> None:
    """示例2：多个订阅者同时订阅。"""
    print("=" * 60)
    print("示例2：多个订阅者同时订阅")
    print("=" * 60)

    # 订阅者1：打印价格信息
    def subscriber1(df: pd.DataFrame) -> None:
        print(f"[订阅者1] {time.strftime('%H:%M:%S')} - 价格信息:")
        for code in df.index:
            price = df.loc[code, "price"]
            last_close = df.loc[code, "last_close"]
            change = price - last_close
            change_pct = (change / last_close * 100) if last_close > 0 else 0
            print(f"  {code}: {price:.2f} ({change:+.2f}, {change_pct:+.2f}%)")

    # 订阅者2：打印成交量信息
    def subscriber2(df: pd.DataFrame) -> None:
        print(f"[订阅者2] {time.strftime('%H:%M:%S')} - 成交量信息:")
        for code in df.index:
            vol = df.loc[code, "vol"]
            amount = df.loc[code, "amount"]
            print(f"  {code}: 成交量={vol}, 成交额={amount:.2f}")

    # 创建订阅管理器
    subscriber = QuoteSubscriber(["600519.SH"])

    # 添加多个订阅者
    subscriber.subscribe(subscriber1)
    subscriber.subscribe(subscriber2)

    print("已添加2个订阅者，等待数据推送...")
    print("按 Ctrl+C 停止订阅\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止订阅...")
        subscriber.stop()


def example3_context_manager() -> None:
    """示例3：使用上下文管理器。"""
    print("=" * 60)
    print("示例3：使用上下文管理器")
    print("=" * 60)

    def on_data_received(df: pd.DataFrame) -> None:
        """数据推送回调函数。"""
        print(f"\n[{time.strftime('%H:%M:%S')}] 收到行情数据:")
        print(df[["price", "ask1", "bid1", "vol"]])

    # 使用 with 语句，自动管理资源
    with QuoteSubscriber(["600519.SH"]) as subscriber:
        subscriber.subscribe(on_data_received)
        print("已开始订阅，等待数据推送...")
        print("按 Ctrl+C 停止订阅\n")

        try:
            # 运行10秒后自动停止
            time.sleep(10)
        except KeyboardInterrupt:
            pass

    print("\n订阅已自动停止（上下文管理器退出）")


def example4_dynamic_subscribe_unsubscribe() -> None:
    """示例4：动态订阅和取消订阅。"""
    print("=" * 60)
    print("示例4：动态订阅和取消订阅")
    print("=" * 60)

    def callback1(df: pd.DataFrame) -> None:
        print(f"[回调1] {time.strftime('%H:%M:%S')} - 价格: {df.loc['600519.SH', 'price']:.2f}")

    def callback2(df: pd.DataFrame) -> None:
        print(f"[回调2] {time.strftime('%H:%M:%S')} - 成交量: {df.loc['600519.SH', 'vol']}")

    subscriber = QuoteSubscriber(["600519.SH"])

    # 先添加两个订阅者
    subscriber.subscribe(callback1)
    subscriber.subscribe(callback2)
    print("已添加2个订阅者，等待5秒...\n")

    time.sleep(5)

    # 取消订阅者1
    subscriber.unsubscribe(callback1)
    print("\n已取消订阅者1，只剩订阅者2，等待5秒...\n")

    time.sleep(5)

    # 再次添加订阅者1
    subscriber.subscribe(callback1)
    print("\n重新添加订阅者1，等待5秒...\n")

    time.sleep(5)

    subscriber.stop()
    print("\n订阅已停止")


def example5_custom_interval() -> None:
    """示例5：自定义推送间隔。"""
    print("=" * 60)
    print("示例5：自定义推送间隔（3秒）")
    print("=" * 60)

    def on_data_received(df: pd.DataFrame) -> None:
        """数据推送回调函数。"""
        print(f"\n[{time.strftime('%H:%M:%S')}] 收到行情数据（3秒间隔）:")
        print(df[["price", "vol"]])

    # 创建订阅管理器，设置推送间隔为3秒
    subscriber = QuoteSubscriber(["600519.SH"], interval=3.0)
    subscriber.subscribe(on_data_received)

    print("已开始订阅，每3秒推送一次...")
    print("按 Ctrl+C 停止订阅\n")

    try:
        time.sleep(15)  # 运行15秒
    except KeyboardInterrupt:
        pass

    subscriber.stop()
    print("\n订阅已停止")


def example6_data_processing() -> None:
    """示例6：在回调中进行数据处理。"""
    print("=" * 60)
    print("示例6：在回调中进行数据处理")
    print("=" * 60)

    # 存储历史数据
    price_history: list[float] = []

    def process_data(df: pd.DataFrame) -> None:
        """处理数据：计算价格变化趋势。"""
        code = "600519.SH"
        if code not in df.index:
            return

        current_price = df.loc[code, "price"]
        price_history.append(current_price)

        if len(price_history) >= 2:
            # 计算最近两次价格的变化
            change = price_history[-1] - price_history[-2]
            trend = "上涨" if change > 0 else "下跌" if change < 0 else "持平"
            print(
                f"[{time.strftime('%H:%M:%S')}] {code}: "
                f"当前价格={current_price:.2f}, "
                f"变化={change:+.2f}, "
                f"趋势={trend}"
            )

            # 只保留最近10条记录
            if len(price_history) > 10:
                price_history.pop(0)

    subscriber = QuoteSubscriber(["600519.SH"])
    subscriber.subscribe(process_data)

    print("已开始订阅，进行数据处理...")
    print("按 Ctrl+C 停止订阅\n")

    try:
        time.sleep(20)  # 运行20秒
    except KeyboardInterrupt:
        pass

    subscriber.stop()
    print("\n订阅已停止")


def main() -> None:
    """运行所有示例。"""
    examples = [
        ("基本订阅用法", example1_basic_subscribe),
        ("多个订阅者", example2_multiple_subscribers),
        ("上下文管理器", example3_context_manager),
        ("动态订阅/取消订阅", example4_dynamic_subscribe_unsubscribe),
        ("自定义推送间隔", example5_custom_interval),
        ("数据处理", example6_data_processing),
    ]

    print("\n行情订阅功能使用示例\n")
    print("请选择要运行的示例：")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("  0. 运行所有示例")
    print()

    try:
        choice = input("请输入选项 (0-6): ").strip()
        choice_num = int(choice) if choice.isdigit() else 0

        if choice_num == 0:
            # 运行所有示例
            for name, func in examples:
                print(f"\n{'='*60}")
                print(f"运行示例: {name}")
                print(f"{'='*60}\n")
                try:
                    func()
                except KeyboardInterrupt:
                    print("\n示例被中断")
                time.sleep(1)
        elif 1 <= choice_num <= len(examples):
            # 运行指定示例
            name, func = examples[choice_num - 1]
            print(f"\n运行示例: {name}\n")
            func()
        else:
            print("无效选项")

    except (ValueError, KeyboardInterrupt):
        print("\n退出")


if __name__ == "__main__":
    main()

