"""
网格策略统一启动入口

支持两种运行模式：
    1. 实盘模式（默认）：连接 QMT，订阅实时行情
    2. 模拟模式 (--simulate)：使用历史 tick 数据回放

使用示例：
    # 实盘模式
    python run.py --symbol 162411.SZ --step 0.001 --baseline 1.076

    # 模拟模式
    python run.py --symbol 162411.SZ --simulate --simulate-date 20260304 --speed-factor 2.0
"""
from __future__ import annotations

import argparse
import atexit
import faulthandler
import importlib.util
import sys
import threading
import time
import traceback
from pathlib import Path

# ============================================================
#  包引导：目录名 "网格实盘3.0" 含 "."，无法直接 import，
#  使用 importlib 将其注册为内部包名 "grid_v3"。
# ============================================================
_PKG_DIR = Path(__file__).resolve().parent
_PKG_NAME = "grid_v3"

# 添加项目根目录到 sys.path（供子模块导入外部依赖）
project_root = _PKG_DIR.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


def _bootstrap_package() -> None:
    """将当前目录注册为名为 grid_v3 的 Python 包，使子模块的相对导入正常工作。"""
    if _PKG_NAME in sys.modules:
        return

    spec = importlib.util.spec_from_file_location(
        _PKG_NAME,
        str(_PKG_DIR / "__init__.py"),
        submodule_search_locations=[str(_PKG_DIR)],
    )
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[_PKG_NAME] = pkg
    spec.loader.exec_module(pkg)


_bootstrap_package()

# 现在可以通过包名导入子模块
from grid_v3.strategy_manager import GridStrategyManager


# ============================================================
#  控制台日志记录器（同时输出到控制台和文件）
# ============================================================
class ConsoleLogger:
    """控制台日志 —— 缓冲写入文件，减少 I/O 频率"""

    FLUSH_SIZE = 4096

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file_handle = open(log_file, "a", encoding="utf-8")
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.buffer: list[str] = []
        self.buffer_size = 0
        self._closed = False

    def write(self, message: str) -> int:
        self.original_stdout.write(message)
        self.original_stdout.flush()
        self.buffer.append(message)
        self.buffer_size += len(message)
        if "\n" in message or self.buffer_size >= self.FLUSH_SIZE:
            self._flush_to_file()
        return len(message)

    def _flush_to_file(self) -> None:
        if self.buffer:
            self.log_file_handle.write("".join(self.buffer))
            self.log_file_handle.flush()
            self.buffer.clear()
            self.buffer_size = 0

    def flush(self) -> None:
        self.original_stdout.flush()
        self._flush_to_file()

    def close(self) -> None:
        if self._closed:
            return
        self._flush_to_file()
        self.log_file_handle.close()
        self._closed = True
        self.original_stdout.write(f"\n日志已保存到: {self.log_file}\n")

    def install(self) -> None:
        sys.stdout = self
        sys.stderr = self
        atexit.register(self.close)


def _install_exception_hooks() -> None:
    def _handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        print("\n[CRITICAL] 未捕获异常，策略即将退出：")
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    def _handle_thread_exception(args) -> None:
        print(f"\n[CRITICAL] 线程未捕获异常: {args.thread.name}")
        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)

    sys.excepthook = _handle_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = _handle_thread_exception


def _install_fault_handler(log_dir: Path):
    crash_log = log_dir / "crash.log"
    crash_handle = open(crash_log, "a", encoding="utf-8")
    faulthandler.enable(file=crash_handle, all_threads=True)
    atexit.register(crash_handle.close)
    return crash_handle


# ============================================================
#  命令行入口
# ============================================================
def main(argv: list[str] | None = None) -> int:
    """命令行主入口"""

    # ── 日志初始化 ──
    log_dir = Path(__file__).parent / "logs"
    log_file = log_dir / "console.log"
    logger = ConsoleLogger(log_file)
    logger.install()
    _install_exception_hooks()
    _install_fault_handler(log_dir)
    print(f"\n========== Grid Strategy 启动: {time.strftime('%Y-%m-%d %H:%M:%S')} ==========")

    # ── 参数解析 ──
    parser = argparse.ArgumentParser(description="网格交易策略 v3.0 启动器")
    parser.add_argument("--symbol", default="162411.SZ", help="股票代码")
    parser.add_argument("--step", type=float, default=0.001, help="网格步长")
    parser.add_argument("--up_grids", type=int, default=1500, help="向上网格数")
    parser.add_argument("--down_grids", type=int, default=1500, help="向下网格数")
    parser.add_argument("--lot_per_grid", type=int, default=1, help="每格手数")
    parser.add_argument("--hand_size", type=int, default=100, help="每手股数")
    parser.add_argument("--out_dir", default="data/grid", help="输出目录")
    parser.add_argument("--baseline", type=float, default=1.006,
                        help="基准价格；若提供则直接使用，否则使用9:30开盘价")
    parser.add_argument("--simulate", action=argparse.BooleanOptionalAction, default=False,
                        help="启用模拟回放模式")
    parser.add_argument("--simulate-date", type=str, default="20260304",
                        help="模拟日期，格式 YYYYMMDD")
    parser.add_argument("--speed-factor", type=float, default=1.0,
                        help="回放速度因子 (1.0=原速, 2.0=两倍速)")

    args = parser.parse_args(argv)

    # ── 构建策略参数 ──
    strategy_params = {
        "step": args.step,
        "up_grids": args.up_grids,
        "down_grids": args.down_grids,
        "lot_per_grid": args.lot_per_grid,
        "hand_size": args.hand_size,
        "baseline": args.baseline,
        "out_dir": args.out_dir,
    }

    # ── 创建策略管理器 ──
    manager = GridStrategyManager(
        stock_code=args.symbol,
        strategy_params=strategy_params,
        simulate=args.simulate,
        simulate_date=args.simulate_date,
        speed_factor=args.speed_factor,
    )

    try:
        # ── 创建策略 ──
        if not manager.create_strategy():
            print("创建策略失败，退出程序")
            return 1

        # ── 订阅行情 / 启动回放 ──
        if not manager.subscribe_stock_quotes():
            print("订阅/启动失败，退出程序")
            return 1

        mode_str = "模拟回放" if args.simulate else "实时行情"
        print(f"\n策略已启动 ({mode_str})，等待行情数据...")
        print("按 Ctrl+C 停止策略\n")

        # ── 主循环 ──
        while True:
            time.sleep(0.1)
            # 模拟模式：回放完成后自动退出
            if args.simulate and manager.mock_replayer and not manager.mock_replayer.is_running():
                print("\n模拟回放已完成")
                if manager.strategy:
                    manager.strategy.on_stop()
                break
    except KeyboardInterrupt:
        print("\n\n收到停止信号...")
        if manager.strategy:
            manager.strategy.on_stop()
        manager.unsubscribe_stock_quotes()
        print("策略已停止")
    except Exception as e:
        print(f"\n[CRITICAL] 主程序异常退出: {e}")
        traceback.print_exc()
        try:
            if manager.strategy:
                manager.strategy.on_stop()
            manager.unsubscribe_stock_quotes()
        except Exception as cleanup_error:
            print(f"[CRITICAL] 异常退出清理失败: {cleanup_error}")
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
