# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


@dataclass
class OpenTdxSectorConfig:
    opentdx_root: Optional[str] = None
    board_types: Sequence[str] = field(default_factory=lambda: ["HY", "GN"])
    min_members: int = 10
    max_members: int = 600
    max_boards: Optional[int] = None
    kline_count: int = 800


def resolve_opentdx_root(opentdx_root: Optional[str] = None) -> Path:
    if opentdx_root:
        root = Path(opentdx_root).expanduser().resolve()
        if not (root / "opentdx").exists():
            raise FileNotFoundError(f"OpenTDX 目录无效: {root}")
        return root

    here = Path(__file__).resolve()
    for base in (here.parent, *here.parents):
        candidate = base / "md" / "通达信" / "opentdx-main"
        if (candidate / "opentdx").exists():
            return candidate
    raise FileNotFoundError("未找到 md/通达信/opentdx-main")


def _ensure_opentdx_path(opentdx_root: Optional[str] = None) -> Path:
    root = resolve_opentdx_root(opentdx_root)
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def _import_opentdx(opentdx_root: Optional[str] = None):
    _ensure_opentdx_path(opentdx_root)
    try:
        from opentdx.client.macStandardClient import MacStandardClient
        from opentdx.const import BOARD_TYPE, MARKET, PERIOD
    except Exception as exc:
        raise ImportError("未能导入 OpenTDX，请确认 md/通达信/opentdx-main 可用") from exc
    return MacStandardClient, BOARD_TYPE, MARKET, PERIOD


def _market_suffix(market: Any) -> Optional[str]:
    name = getattr(market, "name", str(market)).upper()
    if name in {"SH", "SZ", "BJ"}:
        return name
    value = getattr(market, "value", None)
    if value == 1:
        return "SH"
    if value == 0:
        return "SZ"
    if value == 2:
        return "BJ"
    return None


def _member_to_xt_code(item: Mapping[str, Any]) -> Optional[str]:
    code = str(item.get("code", "")).strip()
    suffix = _market_suffix(item.get("market"))
    if not code or not suffix:
        return None
    if len(code) != 6 or not code.isdigit():
        return None
    return f"{code}.{suffix}"


def _normalize_board_type(raw: str, BOARD_TYPE: Any):
    key = str(raw).strip().upper()
    if not key:
        raise ValueError("板块类型不能为空")
    try:
        return getattr(BOARD_TYPE, key)
    except AttributeError as exc:
        valid = ", ".join([name for name in getattr(BOARD_TYPE, "__members__", {})])
        raise ValueError(f"未知 OpenTDX 板块类型: {raw}，可选: {valid}") from exc


def _connect_client(MacStandardClient: Any):
    client = MacStandardClient()
    if client.connect() is None:
        raise ConnectionError("OpenTDX 连接服务器失败")
    return client


def build_opentdx_sector_universe(
    config: OpenTdxSectorConfig | None = None,
    *,
    sector_names: Optional[Sequence[str]] = None,
) -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, Any]]]:
    config = config or OpenTdxSectorConfig()
    MacStandardClient, BOARD_TYPE, _, _ = _import_opentdx(config.opentdx_root)
    wanted = {str(x).strip() for x in sector_names or [] if str(x).strip()}

    universe: Dict[str, List[str]] = {}
    board_meta: Dict[str, Dict[str, Any]] = {}
    seen_codes: set[str] = set()

    client = _connect_client(MacStandardClient)
    try:
        for raw_type in config.board_types:
            board_type = _normalize_board_type(raw_type, BOARD_TYPE)
            boards = client.get_board_list(board_type, count=10000) or []
            for board in boards:
                board_code = str(board.get("code") or board.get("board_symbol") or "").strip()
                board_name = str(board.get("name") or board_code).strip()
                if not board_code or board_code in seen_codes:
                    continue
                if wanted and board_name not in wanted and board_code not in wanted:
                    continue
                seen_codes.add(board_code)

                try:
                    raw_members = client.get_board_members(board_code, count=config.max_members + 1) or []
                except Exception as exc:
                    LOGGER.warning("跳过 OpenTDX 板块 %s/%s（成分获取失败）: %s", board_name, board_code, exc)
                    continue

                members = sorted({c for c in (_member_to_xt_code(item) for item in raw_members) if c})
                if len(members) < config.min_members or len(members) > config.max_members:
                    continue

                sector_key = board_name
                if sector_key in universe:
                    sector_key = f"{board_name}_{board_code}"
                universe[sector_key] = members
                board_meta[sector_key] = {
                    "code": board_code,
                    "name": board_name,
                    "board_type": str(raw_type).upper(),
                    "member_count": len(members),
                }
                if config.max_boards and len(universe) >= config.max_boards:
                    break
            if config.max_boards and len(universe) >= config.max_boards:
                break
    finally:
        client.disconnect()

    LOGGER.info("OpenTDX 最终保留板块 %d 个", len(universe))
    return universe, board_meta


def _bars_to_frame(bars: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    if not bars:
        return pd.DataFrame()
    df = pd.DataFrame(list(bars))
    if "datetime" not in df.columns:
        return pd.DataFrame()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").drop_duplicates("datetime", keep="last")
    df = df.set_index("datetime")
    if "vol" in df.columns and "volume" not in df.columns:
        df["volume"] = df["vol"]
    for col in ("open", "high", "low", "close", "volume", "amount"):
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[["open", "high", "low", "close", "volume", "amount"]]


def load_opentdx_sector_kline_panel(
    board_meta: Mapping[str, Mapping[str, Any]],
    start_time: str,
    end_time: str,
    config: OpenTdxSectorConfig | None = None,
) -> Dict[str, pd.DataFrame]:
    config = config or OpenTdxSectorConfig()
    MacStandardClient, _, MARKET, PERIOD = _import_opentdx(config.opentdx_root)
    start_ts = pd.Timestamp(start_time)
    end_ts = pd.Timestamp(end_time)

    frames: Dict[str, pd.DataFrame] = {}
    client = _connect_client(MacStandardClient)
    try:
        for sector_name, meta in board_meta.items():
            board_code = str(meta.get("code", "")).strip()
            if not board_code:
                continue
            try:
                bars = client.get_symbol_bars(MARKET.SH, board_code, PERIOD.DAILY, count=config.kline_count) or []
            except Exception as exc:
                LOGGER.warning("跳过 OpenTDX 板块K线 %s/%s（获取失败）: %s", sector_name, board_code, exc)
                continue
            df = _bars_to_frame(bars)
            if df.empty:
                continue
            df = df.loc[(df.index >= start_ts) & (df.index <= end_ts)]
            if df.empty:
                continue
            frames[sector_name] = df
    finally:
        client.disconnect()

    if not frames:
        raise ValueError(f"未读取到 OpenTDX 板块K线数据：{start_time} ~ {end_time}")

    all_index = pd.Index(sorted(set().union(*[set(df.index) for df in frames.values()])))
    panel: Dict[str, pd.DataFrame] = {}
    for field_name in ("open", "high", "low", "close", "volume", "amount"):
        wide = pd.DataFrame(
            {sector_name: df[field_name] for sector_name, df in frames.items()},
            index=all_index,
        )
        wide.index = pd.to_datetime(wide.index)
        panel[field_name] = wide.sort_index().astype(float)

    LOGGER.info("OpenTDX 板块K线读取完成：%d 天 × %d 个板块", panel["close"].shape[0], panel["close"].shape[1])
    return panel
