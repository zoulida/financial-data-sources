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
from typing import Any, Dict

# 导入拆分后的模块
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.网格.网格信号实盘.strategy_manager import GridStrategyManager


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
    parser.add_argument("--down_grids", type=int, default=30, help="向下网格数")
    parser.add_argument("--lot_per_grid", type=int, default=1, help="每格手数")
    parser.add_argument("--hand_size", type=int, default=100, help="每手股数")
    parser.add_argument("--out_dir", default="data/grid", help="输出目录")
    parser.add_argument(
        "--baseline",
        type=float,
        default=0.992,
        help="若提供则使用该基准价（例如 0.680）；否则用9:30开盘价",
    )
    parser.add_argument(
        "--simulate",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="启用模拟模式：使用历史tick数据回放进行调试（非交易时间可用）",
    )
    parser.add_argument(
        "--simulate-date",
        type=str,
        default='20260304',
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
