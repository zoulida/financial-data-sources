from __future__ import annotations

import hashlib
import json
import math
import pickle
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


@dataclass
class OpenTdxImportContext:
    opentdx_path: Path
    TdxClient: Any
    MARKET: Any
    PERIOD: Any
    ADJUST: Any
    BOARD_TYPE: Any


def resolve_opentdx_path(opentdx_path: str | Path | None = None) -> Path:
    if opentdx_path:
        candidate = Path(str(opentdx_path)).expanduser().resolve()
        if (candidate / "opentdx" / "tdxClient.py").exists():
            return candidate
    here = Path(__file__).resolve()
    for base in (here.parent, *here.parents):
        candidate = base / "md" / "通达信" / "opentdx-main"
        if (candidate / "opentdx" / "tdxClient.py").exists():
            return candidate
    fallback = here.parents[2] / "md" / "通达信" / "opentdx-main"
    return fallback.resolve()


def import_opentdx(opentdx_path: str | Path | None = None) -> OpenTdxImportContext:
    path = resolve_opentdx_path(opentdx_path)
    if not (path / "opentdx" / "tdxClient.py").exists():
        raise FileNotFoundError(f"OpenTDX 路径不可用：{path}")
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    from opentdx.const import ADJUST, BOARD_TYPE, MARKET, PERIOD
    from opentdx.tdxClient import TdxClient

    return OpenTdxImportContext(
        opentdx_path=path,
        TdxClient=TdxClient,
        MARKET=MARKET,
        PERIOD=PERIOD,
        ADJUST=ADJUST,
        BOARD_TYPE=BOARD_TYPE,
    )


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_key(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def read_pickle_cache(path: str | Path, enabled: bool = True, force_refresh: bool = False) -> Any | None:
    p = Path(path)
    if not enabled or force_refresh or not p.exists():
        return None
    try:
        with open(p, "rb") as file:
            return pickle.load(file)
    except Exception:
        return None


def write_pickle_cache(path: str | Path, value: Any, enabled: bool = True) -> None:
    if not enabled:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as file:
        pickle.dump(value, file, protocol=pickle.HIGHEST_PROTOCOL)


def to_code_suffix(market: Any, code: str) -> str:
    market_name = getattr(market, "name", str(market)).upper()
    suffix = "SH" if market_name == "SH" else "BJ" if market_name == "BJ" else "SZ"
    return f"{str(code).zfill(6)}.{suffix}"


def from_code_suffix(code: str, MARKET: Any) -> tuple[Any, str]:
    raw = str(code).strip().upper()
    if raw.endswith(".SH"):
        return MARKET.SH, raw[:6]
    if raw.endswith(".BJ"):
        return MARKET.BJ, raw[:6]
    return MARKET.SZ, raw[:6]


def split_batches(items: list[Any], batch_size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def normalize_records(records: Any) -> list[dict[str, Any]]:
    if records is None:
        return []
    if isinstance(records, pd.DataFrame):
        return records.to_dict(orient="records")
    if isinstance(records, dict):
        data = records.get("data")
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            return [data]
        return [records]
    if isinstance(records, list):
        return [x for x in records if isinstance(x, dict)]
    return []


def extract_numeric(row: dict[str, Any], keys: list[str], default: float | None = None) -> float | None:
    for key in keys:
        if key in row:
            try:
                value = row.get(key)
                if value is None or value == "":
                    continue
                num = float(value)
                # NaN/Inf 当作无效，避免命中后续判断 is not None 时被误用
                if math.isnan(num) or math.isinf(num):
                    continue
                return num
            except (TypeError, ValueError):
                continue
    return default


def estimate_market_cap_yi(row: dict[str, Any]) -> float | None:
    direct = extract_numeric(
        row,
        [
            "total_market_cap_yi",
            "market_cap_yi",
            "total_mv_yi",
            "总市值_亿",
        ],
    )
    if direct is not None:
        return direct
    raw_total = extract_numeric(
        row,
        [
            "total_market_cap",
            "market_cap",
            "total_mv",
            "总市值",
            "mkt_cap",
        ],
    )
    if raw_total is not None:
        return raw_total / 100000000.0 if raw_total > 1000000 else raw_total
    close = extract_numeric(row, ["close", "price", "现价"])
    shares = extract_numeric(
        row,
        [
            "total_shares",
            "capital",
            "total_capital",
            "总股本",
            "zongguben",
        ],
    )
    if close is not None and shares is not None and shares > 0:
        return close * shares / 100000000.0
    float_shares = extract_numeric(
        row,
        [
            "float_shares",
            "circulating_capital",
            "circulating_capital_z",
            "流通股本",
        ],
    )
    if close is not None and float_shares is not None and float_shares > 0:
        return close * float_shares / 100000000.0
    # 回退：报价接口没给股本，但有当日成交量(vol)和换手率(turnover, 单位%)
    # 反推流通股本 ≈ vol / (turnover/100)，再 × close ÷ 1e8 得流通市值（亿）
    vol = extract_numeric(row, ["vol", "volume", "成交量"])
    turnover_rate = extract_numeric(row, ["turnover", "turnover_rate", "换手率"])
    if (
        close is not None
        and vol is not None
        and turnover_rate is not None
        and vol > 0
        and turnover_rate > 0.001
    ):
        float_shares_est = vol / (turnover_rate / 100.0)
        return close * float_shares_est / 100000000.0
    return None


class OpenTdxDataLoader:
    def __init__(
        self,
        opentdx_path: str | Path | None = None,
        cache_dir: str | Path = "cache",
        enable_cache: bool = True,
        force_refresh: bool = False,
    ) -> None:
        self.ctx = import_opentdx(opentdx_path)
        self.cache_dir = ensure_dir(cache_dir)
        self.enable_cache = bool(enable_cache)
        self.force_refresh = bool(force_refresh)

    def cache_stats(self) -> dict[str, Any]:
        files = list(self.cache_dir.rglob("*.pkl")) if self.cache_dir.exists() else []
        size = sum(p.stat().st_size for p in files if p.exists())
        return {"dir": str(self.cache_dir), "count": len(files), "size_bytes": int(size)}

    def clear_cache(self) -> int:
        if not self.cache_dir.exists():
            return 0
        deleted = 0
        for path in self.cache_dir.rglob("*.pkl"):
            try:
                path.unlink()
                deleted += 1
            except OSError:
                pass
        return deleted

    def _cache_path(self, name: str, payload: dict[str, Any]) -> Path:
        return self.cache_dir / f"{name}_{cache_key(payload)}.pkl"

    def load_stock_list(self, markets: list[str]) -> pd.DataFrame:
        payload = {"markets": markets, "opentdx": str(self.ctx.opentdx_path)}
        path = self._cache_path("stock_list", payload)
        cached = read_pickle_cache(path, self.enable_cache, self.force_refresh)
        if cached is not None:
            return cached
        rows: list[dict[str, Any]] = []
        market_map = {"SZ": self.ctx.MARKET.SZ, "SH": self.ctx.MARKET.SH, "BJ": self.ctx.MARKET.BJ}
        with self.ctx.TdxClient() as client:
            for market_name in markets:
                market = market_map.get(str(market_name).upper())
                if market is None:
                    continue
                try:
                    items = client.stock_list(market, count=0)
                except Exception:
                    items = []
                for item in normalize_records(items):
                    code = str(item.get("code", "")).zfill(6)
                    name = str(item.get("name", ""))
                    if not code or code == "000000":
                        continue
                    rows.append({**item, "market_name": market.name, "market": market, "code": code, "ts_code": to_code_suffix(market, code), "name": name})
        df = pd.DataFrame(rows).drop_duplicates(subset=["ts_code"]) if rows else pd.DataFrame()
        write_pickle_cache(path, df, self.enable_cache)
        return df

    def load_quotes(self, ts_codes: list[str], batch_size: int = 80) -> pd.DataFrame:
        payload = {"ts_codes": sorted(ts_codes), "batch_size": batch_size}
        path = self._cache_path("quotes", payload)
        cached = read_pickle_cache(path, self.enable_cache, self.force_refresh)
        if cached is not None:
            # 命中缓存也重新计算市值，保证 estimate_market_cap_yi 的最新公式立即生效
            if isinstance(cached, pd.DataFrame) and not cached.empty:
                cached = cached.copy()
                cached["market_cap_yi"] = cached.apply(lambda row: estimate_market_cap_yi(row.to_dict()), axis=1)
            return cached
        pairs = [from_code_suffix(code, self.ctx.MARKET) for code in ts_codes]
        rows: list[dict[str, Any]] = []
        with self.ctx.TdxClient() as client:
            for batch in split_batches(pairs, batch_size):
                try:
                    records = client.stock_quotes(batch)
                except Exception:
                    records = []
                for row in normalize_records(records):
                    market = row.get("market")
                    code = str(row.get("code", "")).zfill(6)
                    ts_code = to_code_suffix(market, code) if market is not None else code
                    rows.append({**row, "ts_code": ts_code})
                time.sleep(0.02)
        df = pd.DataFrame(rows).drop_duplicates(subset=["ts_code"]) if rows else pd.DataFrame()
        if not df.empty:
            df["close"] = pd.to_numeric(df.get("close"), errors="coerce")
            df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce")
            df["market_cap_yi"] = df.apply(lambda row: estimate_market_cap_yi(row.to_dict()), axis=1)
        write_pickle_cache(path, df, self.enable_cache)
        return df

    def load_kline_panel(self, ts_codes: list[str], count: int = 260) -> dict[str, pd.DataFrame]:
        # 按单只股票为粒度缓存：股票池变化时，已拉过的个股仍能复用，不必整批重拉
        records: dict[str, pd.DataFrame] = {}
        missing: list[tuple[str, Path]] = []
        for ts_code in ts_codes:
            single_path = self._cache_path("kline_single", {"ts_code": ts_code, "count": int(count)})
            cached = read_pickle_cache(single_path, self.enable_cache, self.force_refresh)
            if isinstance(cached, pd.DataFrame) and not cached.empty:
                records[ts_code] = cached
            else:
                missing.append((ts_code, single_path))
        hit = len(ts_codes) - len(missing)
        print(f"  K线缓存命中 {hit}/{len(ts_codes)}，待下载 {len(missing)}", flush=True)
        if missing:
            with self.ctx.TdxClient() as client:
                total = len(missing)
                for idx, (ts_code, single_path) in enumerate(missing, start=1):
                    market, code = from_code_suffix(ts_code, self.ctx.MARKET)
                    try:
                        data = client.stock_kline(market, code, self.ctx.PERIOD.DAILY, count=count, adjust=self.ctx.ADJUST.NONE)
                        df = pd.DataFrame(data)
                    except Exception:
                        df = pd.DataFrame()
                    if not df.empty and "datetime" in df.columns:
                        df["date"] = pd.to_datetime(df["datetime"]).dt.normalize()
                        df = df.sort_values("date").drop_duplicates(subset=["date"])
                        df = df.set_index("date")
                        records[ts_code] = df
                        write_pickle_cache(single_path, df, self.enable_cache)
                    if idx == 1 or idx == total or idx % 20 == 0:
                        print(f"  K线下载进度 {idx}/{total}", flush=True)
                    time.sleep(0.01)
        panel: dict[str, pd.DataFrame] = {}
        for field in ["open", "high", "low", "close", "vol", "amount", "turnover", "float_shares"]:
            pieces: list[pd.Series] = []
            for ts_code, df in records.items():
                if field in df.columns:
                    pieces.append(pd.to_numeric(df[field], errors="coerce").rename(ts_code))
            panel[field] = pd.concat(pieces, axis=1).sort_index() if pieces else pd.DataFrame()
        return panel

    def load_capital_flow(self, ts_codes: list[str]) -> pd.DataFrame:
        # 同样按单只股票粒度缓存
        rows: list[dict[str, Any]] = []
        missing: list[tuple[str, Path]] = []
        cached_rows: dict[str, dict[str, Any]] = {}
        for ts_code in ts_codes:
            single_path = self._cache_path("capital_flow_single", {"ts_code": ts_code})
            cached = read_pickle_cache(single_path, self.enable_cache, self.force_refresh)
            if isinstance(cached, dict):
                cached_rows[ts_code] = cached
            else:
                missing.append((ts_code, single_path))
        hit = len(ts_codes) - len(missing)
        print(f"  资金流缓存命中 {hit}/{len(ts_codes)}，待下载 {len(missing)}", flush=True)
        if missing:
            with self.ctx.TdxClient() as client:
                for idx, (ts_code, single_path) in enumerate(missing, start=1):
                    market, code = from_code_suffix(ts_code, self.ctx.MARKET)
                    try:
                        raw = client.stock_capital_flow(market, code)
                    except Exception:
                        raw = {}
                    data = raw.get("data") if isinstance(raw, dict) else raw
                    row = data if isinstance(data, dict) else {}
                    cached_rows[ts_code] = row
                    write_pickle_cache(single_path, row, self.enable_cache)
                    if idx % 20 == 0:
                        print(f"  资金流下载进度 {idx}/{len(missing)}", flush=True)
                    time.sleep(0.01)
        for ts_code in ts_codes:
            row = cached_rows.get(ts_code, {})
            rows.append({"ts_code": ts_code, **row})
        return pd.DataFrame(rows)

    def load_monitor_events(self, markets: list[str], count: int = 5000) -> pd.DataFrame:
        payload = {"markets": markets, "count": count}
        path = self._cache_path("monitor", payload)
        cached = read_pickle_cache(path, self.enable_cache, self.force_refresh)
        if cached is not None:
            return cached
        market_map = {"SZ": self.ctx.MARKET.SZ, "SH": self.ctx.MARKET.SH, "BJ": self.ctx.MARKET.BJ}
        rows: list[dict[str, Any]] = []
        with self.ctx.TdxClient() as client:
            for market_name in markets:
                market = market_map.get(str(market_name).upper())
                if market is None:
                    continue
                try:
                    records = client.stock_market_monitor(market, count=count)
                except Exception:
                    records = []
                for row in normalize_records(records):
                    code = str(row.get("code", "")).zfill(6)
                    rows.append({**row, "ts_code": to_code_suffix(market, code)})
        df = pd.DataFrame(rows)
        write_pickle_cache(path, df, self.enable_cache)
        return df
