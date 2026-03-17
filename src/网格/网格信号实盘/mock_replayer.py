"""
模拟tick数据回放器模块
用于在非交易时间调试策略
"""
import time
import threading
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

# 导入模拟模式所需的函数
if __package__ in {None, ""}:
    from src.网格.网格信号实盘.run_grid_512710 import _prepare_tick_dataframe
else:
    from .run_grid_512710 import _prepare_tick_dataframe


class MockTickReplayer:
    """
    模拟tick数据回放器
    用于在非交易时间调试策略
    """
    
    def __init__(
        self,
        symbol: str,
        tick_df: pd.DataFrame,
        callback: callable,
        speed_factor: float = 1.0
    ):
        """
        初始化模拟回放器
        
        Args:
            symbol: 股票代码
            tick_df: 历史tick数据DataFrame
            callback: 回调函数，接收 {symbol: tick_dict} 格式的数据
            speed_factor: 回放速度因子，1.0表示按原始时间间隔，2.0表示2倍速
        """
        self.symbol = symbol
        self.callback = callback
        self.speed_factor = speed_factor
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # 准备tick数据
        if tick_df.empty:
            raise ValueError("tick数据为空，无法进行模拟回放")
        
        # 使用_prepare_tick_dataframe处理数据
        self.tick_df = _prepare_tick_dataframe(symbol, tick_df)
        
        # 解析时间列
        self._parse_time_column()
        
        print(f"模拟回放器初始化完成: {symbol}, 共 {len(self.tick_df)} 条tick数据")
    
    def _parse_time_column(self):
        """解析时间列，计算时间间隔"""
        # 查找时间列
        time_col = None
        for col in ("servertime", "time", "stime", "date"):
            if col in self.tick_df.columns:
                time_col = col
                break
        
        if time_col is None:
            # 如果没有时间列，使用固定间隔（假设1秒一条）
            self.tick_df["_parsed_time"] = pd.date_range(
                start=datetime.now(),
                periods=len(self.tick_df),
                freq="1S"
            )
        else:
            # 解析时间字符串
            try:
                self.tick_df["_parsed_time"] = pd.to_datetime(
                    self.tick_df[time_col],
                    errors='coerce'
                )
                # 如果解析失败，使用固定间隔
                if self.tick_df["_parsed_time"].isna().any():
                    start_time = datetime.now()
                    self.tick_df["_parsed_time"] = pd.date_range(
                        start=start_time,
                        periods=len(self.tick_df),
                        freq="1S"
                    )
            except Exception:
                # 解析失败，使用固定间隔
                start_time = datetime.now()
                self.tick_df["_parsed_time"] = pd.date_range(
                    start=start_time,
                    periods=len(self.tick_df),
                    freq="1S"
                )
        
        # 计算时间间隔（秒）
        if len(self.tick_df) > 1:
            time_diffs = self.tick_df["_parsed_time"].diff().dt.total_seconds()
            time_diffs = time_diffs.fillna(0.0)
            # 将间隔应用速度因子
            self.tick_df["_interval"] = time_diffs / self.speed_factor
        else:
            self.tick_df["_interval"] = 0.0
    
    def _convert_row_to_tick_dict(self, row: pd.Series) -> Dict[str, Any]:
        """将DataFrame行转换为tick字典格式"""
        tick_dict = {
            "lastPrice": float(row.get("price", 0.0)),
            "lastClose": float(row.get("last_close", 0.0)),
            "volume": int(row.get("vol", 0)),
            "amount": float(row.get("amount", 0.0)),
            "bidPrice1": float(row.get("bid1", 0.0)),
            "askPrice1": float(row.get("ask1", 0.0)),
            "bidVol1": int(row.get("bid1", 0) > 0) * 100,  # 模拟值
            "askVol1": int(row.get("ask1", 0) > 0) * 100,  # 模拟值
            "open": float(row.get("open", row.get("price", 0.0))),
            "high": float(row.get("high", row.get("price", 0.0))),
            "low": float(row.get("low", row.get("price", 0.0))),
            "servertime": row.get("servertime", ""),  # 添加原始时间字段
        }
        return tick_dict
    
    def _replay_loop(self):
        """回放循环"""
        try:
            for i, (idx, row) in enumerate(self.tick_df.iterrows()):
                if not self._running:
                    break
                
                # 转换为tick字典
                tick_dict = self._convert_row_to_tick_dict(row)
                
                # 调用回调函数
                self.callback({self.symbol: tick_dict})
                
                # 快速回放：不等待时间间隔
                # if i < len(self.tick_df) - 1:
                #     interval = row.get("_interval", 0.0)
                #     if interval > 0:
                #         time.sleep(interval)
            
            print(f"\n模拟回放完成: {self.symbol}, 共回放 {len(self.tick_df)} 条数据")
            
        except Exception as e:
            print(f"模拟回放出错: {e}")
            traceback.print_exc()
        finally:
            self._running = False
    
    def start(self):
        """开始回放"""
        if self._running:
            print("回放已在运行中")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._replay_loop, daemon=True)
        self._thread.start()
        print(f"开始模拟回放: {self.symbol}")
    
    def stop(self):
        """停止回放"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        print(f"停止模拟回放: {self.symbol}")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running
