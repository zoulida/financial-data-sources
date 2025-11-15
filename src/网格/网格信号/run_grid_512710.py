from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone, timedelta
import sys
from typing import Callable

import pandas as pd

from pathlib import Path

# 确保项目根目录在 sys.path（便于导入 md 与 src 命名空间）
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from md.tdx.xtdata_quote import fetch_quotes_basic_auto_switch
except Exception:  # noqa: BLE001
    print(
        "无法导入 md.tdx.xtdata_quote.fetch_quotes_basic_auto_switch，请确认在项目根目录下运行或检查路径。",
        file=sys.stderr,
    )
    raise

from src.网格.网格信号.runtime import GridRuntime, RuntimeConfig

try:
    from tools.shelveTool import shelve_me_week
except Exception:  # noqa: BLE001
    def shelve_me_week(func):
        return func


def _import_get_tick_data() -> Callable[..., pd.DataFrame] | None:
    try:
        from source.实盘.xuntou.datadownload.合并下载数据 import (  # type: ignore[attr-defined]
            get_tick_data,
        )

        return get_tick_data
    except Exception as exc:  # noqa: BLE001
        print(
            "警告: 无法导入 source.实盘.xuntou.datadownload.合并下载数据.get_tick_data，"
            f"将回退到实时行情接口。原因: {exc}",
            file=sys.stderr,
        )
        return None


def _prepare_tick_dataframe(symbol: str, tick_df: pd.DataFrame) -> pd.DataFrame:
    if tick_df.empty:
        raise ValueError("get_tick_data 返回空数据，无法进入调试模式。")

    df = tick_df.copy()
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    for col in ("time", "stime", "date"):
        if col in df.columns:
            df = df.sort_values(col)
            df["servertime"] = df[col].astype(str)
            break
    else:
        df["servertime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rename_map = {
        "lastPrice": "price",
        "askPrice1": "ask1",
        "bidPrice1": "bid1",
        "lastClose": "last_close",
        "open": "open",
        "high": "high",
        "low": "low",
        "amount": "amount",
        "volume": "vol",
    }

    for src, dest in rename_map.items():
        if src in df.columns:
            df[dest] = pd.to_numeric(df[src], errors="coerce")

    if "price" not in df.columns:
        candidate_cols = ["close", "成交价", "lastPrice"]
        for col in candidate_cols:
            if col in df.columns:
                df["price"] = pd.to_numeric(df[col], errors="coerce")
                break

    if "ask1" not in df.columns and "askPrice1" in df.columns:
        df["ask1"] = pd.to_numeric(df["askPrice1"], errors="coerce")
    if "bid1" not in df.columns and "bidPrice1" in df.columns:
        df["bid1"] = pd.to_numeric(df["bidPrice1"], errors="coerce")

    if "vol" in df.columns:
        df["cur_vol"] = (
            df["vol"].diff().where(lambda s: s > 0).fillna(df["vol"]).astype(float)
        )

    keep_cols = [
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
    existing_cols = [col for col in keep_cols if col in df.columns]

    return df[existing_cols].reset_index(drop=True)


class TickReplayer:
    def __init__(self, symbol: str, raw_tick: pd.DataFrame):
        self.symbol = symbol
        self.tick_df = _prepare_tick_dataframe(symbol, raw_tick)
        self._idx = 0
        self._total = len(self.tick_df)

    def next_snapshot(self) -> pd.DataFrame:
        if self.tick_df.empty:
            raise RuntimeError("tick 数据为空，无法提供调试快照。")

        if self._idx >= self._total:
            raise StopIteration

        row = self.tick_df.iloc[self._idx]
        self._idx += 1

        data = row.to_dict()
        frame = pd.DataFrame([data], index=[self.symbol])
        frame.index.name = "code"
        return frame


@shelve_me_week(1)
def _load_tick_raw_dataframe(
    symbol: str, start_time: str
) -> pd.DataFrame:
    get_tick_data_fn = _import_get_tick_data()
    if get_tick_data_fn is None:
        return pd.DataFrame()
    tick_raw = get_tick_data_fn(stock_list=[symbol], start_time=start_time)
    
    # 统一转换为 DataFrame
    if isinstance(tick_raw, pd.DataFrame):
        df = tick_raw
    elif isinstance(tick_raw, dict):
        df = pd.DataFrame(tick_raw.get(symbol, pd.DataFrame()))
    else:
        df = pd.DataFrame(tick_raw)
    
    # 如果 DataFrame 为空，直接返回
    if df.empty:
        return df
    
    # 处理时间戳列，转换为北京时间
    beijing_tz = timezone(timedelta(hours=8))
    for col in ("time", "stime", "date"):
        if col in df.columns:
            try:
                # 检查是否为时间戳格式（毫秒级，通常大于1e12）
                sample_val = df[col].iloc[0] if not df.empty else None
                if sample_val is not None:
                    ts_val = pd.to_numeric(sample_val, errors='coerce')
                    if pd.notna(ts_val) and ts_val > 1e12:
                        # 是毫秒级时间戳，转换为北京时间
                        ts_series = pd.to_numeric(df[col], errors='coerce')
                        dt_utc = pd.to_datetime(ts_series, unit='ms', errors='coerce', utc=True)
                        dt_beijing = dt_utc.dt.tz_convert(beijing_tz)
                        # 更新原列的时间戳为北京时间字符串
                        df[col] = dt_beijing.dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                # 转换失败，保持原值
                pass
            break
    
    return df


def build_get_quote(symbols: Sequence[str], debug: bool) -> Callable[[], pd.DataFrame]:
    if debug:
        symbol = symbols[0]

        today = datetime.now().strftime("%Y%m%d")
        today = '20251112'
        start_time = f"{today}093000"
        raw_df = _load_tick_raw_dataframe(symbol, start_time)

        if not raw_df.empty:
            replayer = TickReplayer(symbol, raw_df)

            def _debug_get_quote() -> pd.DataFrame:
                return replayer.next_snapshot()

            _debug_get_quote._is_debug_source = True  # type: ignore[attr-defined]

            print(
                f"调试模式启用: 使用 {symbol} {len(replayer.tick_df)} 条 tick 数据回放。",
                file=sys.stderr,
            )
            return _debug_get_quote

        print("get_tick_data 返回空数据，调试模式回退到实时行情。", file=sys.stderr)

    def _get() -> pd.DataFrame:
        return fetch_quotes_basic_auto_switch(symbols)

    _get._is_debug_source = False  # type: ignore[attr-defined]

    return _get


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run grid signal simulator for 512710.SH")
    parser.add_argument("--symbol", default="512710.SH")
    parser.add_argument("--step", type=float, default=0.001)
    parser.add_argument("--up_grids", type=int, default=10)
    parser.add_argument("--down_grids", type=int, default=20)
    parser.add_argument("--lot_per_grid", type=int, default=10)
    parser.add_argument("--hand_size", type=int, default=100)
    parser.add_argument("--out_dir", default="data/grid")
    parser.add_argument("--tick_interval", type=float, default=1.9)
    parser.add_argument(
        "--baseline",
        type=float,
        default=0.680,
        help="若提供则使用该基准价（例如 0.60）；否则用9:30开盘价",
    )
    parser.add_argument(
        "--debug",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="开启调试模式：使用本地tick数据回放；使用 --no-debug 时改为实时行情",
    )

    args = parser.parse_args(argv)
    cfg = RuntimeConfig(
        symbol=args.symbol,
        step=args.step,
        up_grids=args.up_grids,
        down_grids=args.down_grids,
        lot_per_grid=args.lot_per_grid,
        hand_size=args.hand_size,
        out_dir=args.out_dir,
        tick_interval=args.tick_interval,
        baseline=args.baseline,
    )
    symbols = [cfg.symbol]
    get_quote = build_get_quote(symbols, args.debug)

    runtime = GridRuntime(cfg, get_quote)
    runtime.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

