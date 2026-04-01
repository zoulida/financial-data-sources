"""
模拟回放器模块

用于非交易时间调试：加载历史 tick 数据，按时间间隔回放，
将 tick 数据推送给策略进行模拟交易。
"""
from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


class MockTickReplayer:
    """
    历史 Tick 数据回放器

    功能：
        1. 从 xtdata 获取指定日期的历史 tick 数据
        2. 按原始时间间隔（可加速）逐条推送给回调函数
        3. 支持启动 / 停止控制

    使用方式：
        replayer = MockTickReplayer("512710.SH", "20260304", 2.0, on_tick_fn)
        replayer.start()   # 启动后台线程
        replayer.stop()    # 停止回放
    """

    def __init__(
        self,
        stock_code: str,
        simulate_date: Optional[str] = None,
        speed_factor: float = 1.0,
        on_tick_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """
        Args:
            stock_code      : 股票代码 (如 "512710.SH")
            simulate_date   : 回放日期 (如 "20260304")；None 则使用今天
            speed_factor    : 回放速度因子 (1.0=原速, 2.0=两倍速)
            on_tick_callback: 每条 tick 的回调函数
        """
        self.stock_code = stock_code
        self.simulate_date = simulate_date or datetime.now().strftime("%Y%m%d")
        self.speed_factor = max(speed_factor, 0.1)
        self._on_tick = on_tick_callback

        # ── 回放控制 ──
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._tick_data: List[Dict[str, Any]] = []
        self._intervals: List[float] = []

    # ==============================================================
    #  公开接口
    # ==============================================================
    def start(self) -> None:
        """加载数据并启动回放线程"""
        self._load_tick_data()
        if not self._tick_data:
            print(f"[MockReplayer] 无 tick 数据可回放: {self.stock_code} @ {self.simulate_date}")
            return

        self._running = True
        self._thread = threading.Thread(target=self._replay_loop, daemon=True)
        self._thread.start()
        print(f"[MockReplayer] 开始回放: {len(self._tick_data)}条 | 速度={self.speed_factor}x")

    def stop(self) -> None:
        """停止回放"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        print("[MockReplayer] 回放已停止")

    def is_running(self) -> bool:
        """回放是否仍在进行"""
        return self._running and self._thread is not None and self._thread.is_alive()

    # ==============================================================
    #  数据加载
    # ==============================================================
    def _load_tick_data(self) -> None:
        """
        从 xtdata 获取历史 tick 数据

        获取指定日期的全天 tick，解析时间戳并计算时间间隔。
        """
        try:
            from xtquant import xtdata

            start_time = f"{self.simulate_date}093000"
            end_time = f"{self.simulate_date}150100"

            print(f"[MockReplayer] 正在获取 tick 数据: {self.stock_code} | {start_time} ~ {end_time}")
            data = xtdata.get_market_data_ex(
                stock_list=[self.stock_code],
                period="tick",
                start_time=start_time,
                end_time=end_time,
            )

            if not data or self.stock_code not in data:
                print("[MockReplayer] 获取 tick 数据为空")
                return

            df = data[self.stock_code]
            if isinstance(df, pd.DataFrame) and not df.empty:
                self._parse_dataframe(df)
            else:
                print("[MockReplayer] tick 数据格式不支持或为空")

        except Exception as e:
            print(f"[MockReplayer] 加载 tick 数据失败: {e}")
            traceback.print_exc()

    def _parse_dataframe(self, df: pd.DataFrame) -> None:
        """
        解析 DataFrame 为 tick 字典列表，并计算时间间隔

        xtdata 的 tick DataFrame 通常包含:
            time (毫秒时间戳), lastPrice, lastClose, volume, amount,
            bidPrice1, askPrice1, bidVol1, askVol1, open, high, low, ...
        """
        beijing_tz = timezone(timedelta(hours=8))

        # ── 解析时间列 ──
        if "time" in df.columns:
            time_col = "time"
        elif df.index.name == "time" or hasattr(df.index, "dtype"):
            df = df.reset_index()
            time_col = df.columns[0]
        else:
            time_col = None

        timestamps = []
        if time_col and time_col in df.columns:
            for val in df[time_col]:
                try:
                    ts_val = float(val)
                    if ts_val > 1e12:
                        # 毫秒时间戳
                        dt = datetime.fromtimestamp(ts_val / 1000, tz=beijing_tz)
                    elif ts_val > 1e9:
                        # 秒时间戳
                        dt = datetime.fromtimestamp(ts_val, tz=beijing_tz)
                    else:
                        dt = datetime.now(tz=beijing_tz)
                    timestamps.append(dt)
                except (ValueError, TypeError, OSError):
                    timestamps.append(datetime.now(tz=beijing_tz))

        # ── 构建 tick 列表 ──
        for i, (_, row) in enumerate(df.iterrows()):
            tick_dict = {
                "lastPrice": row.get("lastPrice", 0),
                "lastClose": row.get("lastClose", row.get("preClose", 0)),
                "volume": row.get("volume", 0),
                "amount": row.get("amount", 0),
                "bidPrice1": row.get("bidPrice1", row.get("bid1", 0)),
                "askPrice1": row.get("askPrice1", row.get("ask1", 0)),
                "bidVol1": row.get("bidVol1", 0),
                "askVol1": row.get("askVol1", 0),
                "open": row.get("open", 0),
                "high": row.get("high", 0),
                "low": row.get("low", 0),
            }

            # 添加涨跌停
            if "upperLimit" in row:
                tick_dict["upperLimit"] = row["upperLimit"]
            if "lowerLimit" in row:
                tick_dict["lowerLimit"] = row["lowerLimit"]

            # 添加时间字符串
            if i < len(timestamps):
                tick_dict["servertime"] = timestamps[i].strftime("%Y-%m-%d %H:%M:%S")
            else:
                tick_dict["servertime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self._tick_data.append(tick_dict)

        # ── 计算时间间隔 ──
        self._intervals = [0.0]  # 第一条无间隔
        for i in range(1, len(timestamps)):
            delta = (timestamps[i] - timestamps[i - 1]).total_seconds()
            delta = max(delta, 0.01)   # 最小间隔 10ms
            delta = min(delta, 10.0)   # 最大间隔 10s
            self._intervals.append(delta)

        # 补齐间隔列表
        while len(self._intervals) < len(self._tick_data):
            self._intervals.append(0.5)

        print(f"[MockReplayer] 解析完成: {len(self._tick_data)}条 tick, "
              f"总时长约{sum(self._intervals):.0f}秒")

    # ==============================================================
    #  回放循环
    # ==============================================================
    def _replay_loop(self) -> None:
        """后台回放线程主循环"""
        try:
            total = len(self._tick_data)
            for i, tick_dict in enumerate(self._tick_data):
                if not self._running:
                    break

                # 推送 tick
                if self._on_tick:
                    try:
                        self._on_tick(tick_dict)
                    except Exception as e:
                        print(f"[MockReplayer] tick 回调异常 #{i}: {e}")

                # 按间隔等待（除最后一条）
                if i < total - 1 and i < len(self._intervals) - 1:
                    wait = self._intervals[i + 1] / self.speed_factor
                    if wait > 0:
                        time.sleep(wait)

            print(f"[MockReplayer] 回放完成: 共推送{total}条 tick")
        except Exception as e:
            print(f"[MockReplayer] 回放异常: {e}")
            traceback.print_exc()
        finally:
            self._running = False
