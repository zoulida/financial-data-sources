from __future__ import annotations

import argparse
import sys
import time
from typing import Sequence

import pandas as pd

from pathlib import Path

# 确保项目根目录在 sys.path（便于导入 md 与 src 命名空间）
_ROOT = Path(__file__).resolve().parents[1]
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


def build_get_quote(symbols: Sequence[str]):
    def _get() -> pd.DataFrame:
        return fetch_quotes_basic_auto_switch(symbols)

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
    parser.add_argument("--baseline", type=float, default=None, help="若提供则使用该基准价（例如 0.60）；否则用9:30开盘价")

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
    get_quote = build_get_quote(symbols)

    runtime = GridRuntime(cfg, get_quote)
    runtime.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


