"""使用 pytdx 获取实时行情数据的工具函数。"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from typing import Callable, Iterable, List, Sequence, Tuple

import pandas as pd
from pytdx.hq import TdxHq_API

# 导入 IP 池模块用于自动切换 IP
try:
    # 尝试相对导入
    from .tdx_pool import get_fastest_ip
except ImportError:
    try:
        # 尝试同目录导入
        from tdx_pool import get_fastest_ip
    except ImportError:
        # 如果都失败，使用动态导入
        from pathlib import Path
        import importlib.util
        tdx_pool_path = Path(__file__).parent / "tdx_pool.py"
        if tdx_pool_path.exists():
            spec = importlib.util.spec_from_file_location("tdx_pool", tdx_pool_path)
            tdx_pool = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tdx_pool)
            get_fastest_ip = tdx_pool.get_fastest_ip
        else:
            get_fastest_ip = None

# 默认使用你提供的更稳定主站
TDX_DEFAULT_HOST = "123.249.15.60"
TDX_DEFAULT_PORT = 7709


DISPLAY_PRIORITY = [
    "code",
    "servertime",
    "price",
    "ask1",
    "bid1",
    "last_close",
    "open",
    "high",
    "low",
    "vol",
    "cur_vol",
    "amount",
]


def _to_market_tuple(code: str) -> Tuple[int, str]:
    """将带后缀或纯数字代码转换为 pytdx 所需的 (market, code) 格式。"""

    if not code or not isinstance(code, str):
        raise ValueError("股票代码必须是非空字符串。")

    normalized = code.strip().upper()

    if normalized.endswith(".SZ"):
        return 0, normalized[:-3]
    if normalized.endswith(".SH"):
        return 1, normalized[:-3]

    if normalized.startswith(("0", "3")):
        return 0, normalized
    if normalized.startswith("6"):
        return 1, normalized

    raise ValueError(f"无法识别交易所：{code}")


def fetch_quotes_once(
    stock_codes: Sequence[str],
    *,
    host: str = TDX_DEFAULT_HOST,
    port: int = TDX_DEFAULT_PORT,
    api: TdxHq_API | None = None,
) -> pd.DataFrame:
    """获取一次快照行情，返回 DataFrame。"""

    if not stock_codes:
        raise ValueError("请至少提供一个股票代码。")

    requests: List[Tuple[int, str]] = []
    ordered_codes: List[str] = []

    for code in stock_codes:
        market_tuple = _to_market_tuple(code)
        requests.append(market_tuple)
        ordered_codes.append(code.strip().upper())

    owns_api = api is None
    api = api or TdxHq_API()

    try:
        if not api.connect(host, port):
            raise RuntimeError(f"无法连接到通达信行情服务器 {host}:{port}")

        ticks = api.get_security_quotes(requests)
        if not ticks:
            raise RuntimeError("pytdx 返回空行情数据。")

        df = api.to_df(ticks)
        df.index = ordered_codes
        df.index.name = "code"
        return df

    finally:
        if owns_api:
            api.disconnect()


def fetch_quotes_basic(
    stock_codes: Sequence[str],
    *,
    host: str = TDX_DEFAULT_HOST,
    port: int = TDX_DEFAULT_PORT,
    api: TdxHq_API | None = None,
) -> pd.DataFrame:
    """获取快照行情并裁剪为常用核心字段。"""

    df = fetch_quotes_once(stock_codes, host=host, port=port, api=api)
    available_cols = [col for col in DISPLAY_PRIORITY if col in df.columns]

    if not available_cols:
        return df.iloc[:, 0:0].copy()

    return df.loc[:, available_cols].copy()


def fetch_quotes_basic_auto_switch(
    stock_codes: Sequence[str],
) -> pd.DataFrame:
    """
    获取快照行情并裁剪为常用核心字段，支持自动切换IP。
    
    此函数只接受 stock_codes 参数，其他参数使用模块默认值。
    如果获取失败，会自动调用 get_fastest_ip 切换 IP 并重试。
    
    Args:
        stock_codes: 股票代码列表
    
    Returns:
        pd.DataFrame: 包含行情数据的 DataFrame
    
    Raises:
        RuntimeError: 如果获取数据失败且无法切换IP
    """
    if get_fastest_ip is None:
        # 如果无法导入 get_fastest_ip，回退到原始函数
        return fetch_quotes_basic(stock_codes)
    
    # 使用默认 IP 地址
    current_host = TDX_DEFAULT_HOST
    current_port = TDX_DEFAULT_PORT
    max_retries = 2  # 最多重试2次（包括初始尝试和切换IP后的重试）
    
    for attempt in range(max_retries):
        try:
            return fetch_quotes_basic(
                stock_codes, host=current_host, port=current_port
            )
        except Exception as exc:  # noqa: BLE001
            if attempt < max_retries - 1:
                # 尝试切换IP
                try:
                    fastest_ip = get_fastest_ip(
                        sample_size=10, enable_logging=True
                    )
                    current_host, current_port = fastest_ip
                    print(
                        f"[{time.strftime('%H:%M:%S')}] 切换到新IP: {current_host}:{current_port}",
                        file=sys.stderr,
                    )
                except Exception as switch_exc:  # noqa: BLE001
                    # 切换IP失败，抛出原始异常
                    raise RuntimeError(
                        f"获取数据失败: {exc}，且切换IP也失败: {switch_exc}"
                    ) from exc
            else:
                # 最后一次尝试也失败了
                raise RuntimeError(f"获取数据失败，已尝试切换IP: {exc}") from exc
    
    # 理论上不会到达这里
    raise RuntimeError("获取数据失败")


def fetch_quotes_per_second(
    stock_codes: Sequence[str],
    *,
    host: str = TDX_DEFAULT_HOST,
    port: int = TDX_DEFAULT_PORT,
    callback: Callable[[pd.DataFrame], None] | None = None,
    max_iterations: int | None = None,
) -> None:
    """每秒调用一次 fetch_quotes_basic，持续获取行情数据。
    
    Args:
        stock_codes: 股票代码列表
        host: 通达信行情服务器地址
        port: 通达信行情服务器端口
        callback: 每次获取数据后的回调函数，接收 DataFrame 作为参数
        max_iterations: 最大调用次数，None 表示无限循环
    
    Examples:
        >>> # 简单打印每次获取的数据
        >>> fetch_quotes_per_second(["600519.SH"], callback=lambda df: print(df))
        
        >>> # 只调用10次
        >>> fetch_quotes_per_second(["600519.SH"], max_iterations=10)
    """
    iteration = 0
    
    try:
        while True:
            if max_iterations is not None and iteration >= max_iterations:
                break
                
            try:
                df = fetch_quotes_basic(stock_codes, host=host, port=port)
                
                if callback:
                    callback(df)
                else:
                    # 默认行为：打印数据
                    pd.set_option("display.width", 200)
                    pd.set_option("display.max_columns", None)
                    print(f"\n[{time.strftime('%H:%M:%S')}] 第 {iteration + 1} 次获取:")
                    print(df)
                    
            except Exception as exc:  # noqa: BLE001
                print(f"[{time.strftime('%H:%M:%S')}] 获取数据失败: {exc}", file=sys.stderr)
            
            iteration += 1
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%H:%M:%S')}] 已停止监控", file=sys.stderr)


def fetch_quotes_per_second_callback(
    stock_codes: Sequence[str],
    *,
    callback: Callable[[pd.DataFrame], None] | None = None,
    max_iterations: int | None = None,
) -> None:
    """
    每秒调用一次 fetch_quotes_basic_auto_switch，持续获取行情数据。
    如果获取失败，会自动切换 IP 并重试（由 fetch_quotes_basic_auto_switch 内部处理）。
    
    此函数只接受 stock_codes 参数，其他参数使用模块默认值。
    
    Args:
        stock_codes: 股票代码列表
        callback: 每次获取数据后的回调函数，接收 DataFrame 作为参数
        max_iterations: 最大调用次数，None 表示无限循环
    
    Examples:
        >>> # 简单打印每次获取的数据
        >>> fetch_quotes_per_second_auto_switch(["600519.SH"], callback=lambda df: print(df))
        
        >>> # 只调用10次
        >>> fetch_quotes_per_second_auto_switch(["600519.SH"], max_iterations=10)
    """
    iteration = 0
    
    try:
        while True:
            if max_iterations is not None and iteration >= max_iterations:
                break
                
            try:
                # 使用自动切换IP的函数获取数据
                df = fetch_quotes_basic_auto_switch(stock_codes)
                
                if callback:
                    callback(df)
                else:
                    # 默认行为：打印数据
                    pd.set_option("display.width", 200)
                    pd.set_option("display.max_columns", None)
                    print(f"\n[{time.strftime('%H:%M:%S')}] 第 {iteration + 1} 次获取:")
                    print(df)
                    
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[{time.strftime('%H:%M:%S')}] 获取数据失败: {exc}",
                    file=sys.stderr,
                )
            
            iteration += 1
            time.sleep(2)
            
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%H:%M:%S')}] 已停止监控", file=sys.stderr)


class QuoteSubscriber:
    """行情订阅管理器，每1.9秒向订阅者推送一次数据。"""

    def __init__(
        self,
        stock_codes: Sequence[str],
        *,
        host: str = TDX_DEFAULT_HOST,
        port: int = TDX_DEFAULT_PORT,
        interval: float = 1.9,
    ):
        """初始化订阅管理器。

        Args:
            stock_codes: 要订阅的股票代码列表
            host: 通达信行情服务器地址
            port: 通达信行情服务器端口
            interval: 推送间隔（秒），默认1.9秒
        """
        self.stock_codes = stock_codes
        self.host = host
        self.port = port
        self.interval = interval
        self._subscribers: List[Callable[[pd.DataFrame], None]] = []
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False

    def subscribe(self, callback: Callable[[pd.DataFrame], None]) -> None:
        """订阅行情推送。

        Args:
            callback: 回调函数，接收 DataFrame 作为参数，每次推送时调用
        """
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)
                # 如果还没有启动推送线程，则启动
                if not self._running:
                    self._start()

    def unsubscribe(self, callback: Callable[[pd.DataFrame], None]) -> None:
        """取消订阅。

        Args:
            callback: 要取消的回调函数
        """
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
                # 如果没有订阅者了，停止推送线程
                if not self._subscribers and self._running:
                    self._stop()

    def _start(self) -> None:
        """启动推送线程。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._push_loop, daemon=True)
        self._thread.start()

    def _stop(self) -> None:
        """停止推送线程。"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _push_loop(self) -> None:
        """推送循环，在后台线程中运行。"""
        while self._running:
            try:
                # 获取数据（使用自动切换IP的函数）
                df = fetch_quotes_basic_auto_switch(self.stock_codes)

                # 复制订阅者列表，避免在回调时修改列表导致问题
                with self._lock:
                    subscribers = self._subscribers.copy()

                # 向所有订阅者推送数据
                for callback in subscribers:
                    try:
                        callback(df)
                    except Exception as exc:  # noqa: BLE001
                        print(
                            f"[{time.strftime('%H:%M:%S')}] 订阅者回调执行失败: {exc}",
                            file=sys.stderr,
                        )

            except Exception as exc:  # noqa: BLE001
                print(
                    f"[{time.strftime('%H:%M:%S')}] 获取数据失败: {exc}",
                    file=sys.stderr,
                )

            # 等待指定间隔
            time.sleep(self.interval)

    def stop(self) -> None:
        """停止订阅服务。"""
        with self._lock:
            self._subscribers.clear()
            if self._running:
                self._stop()

    def __enter__(self):
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口。"""
        self.stop()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="使用 pytdx 获取实时行情。")
    parser.add_argument("codes", nargs="*", help="股票代码，例如 000001.SZ 600519.SH")
    parser.add_argument("--host", default=TDX_DEFAULT_HOST, help="通达信行情服务器地址")
    parser.add_argument("--port", type=int, default=TDX_DEFAULT_PORT, help="通达信行情服务器端口")

    args = parser.parse_args(list(argv) if argv is not None else None)

    codes = args.codes or ["600519.SH"]

    try:
        df = fetch_quotes_per_second_callback(codes)
    except Exception as exc:  # noqa: BLE001
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)

    display_cols = [col for col in DISPLAY_PRIORITY if col in df.columns]
    if display_cols:
        print(df[display_cols])
    else:
        print(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


