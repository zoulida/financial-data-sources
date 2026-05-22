#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore
# pyright: reportMissingImports=false, reportMissingModuleSource=false, reportGeneralTypeIssues=false
"""股票池过滤模块。

提供两种静态过滤：

1. **股价过滤** ``filter_by_price``：按"参考股价"位于 ``[min_price, max_price]`` 区间。
   参考股价默认取行情末日 close；也可改为全期均值或中位数。
2. **市值过滤** ``filter_by_market_cap``：按 akshare 实时市值快照位于
   ``[min_yi, max_yi]`` 区间（单位：亿元）。akshare 不需要 token，但需要联网。
   首次拉取后写入本地 CSV 缓存，30 天内复用。

主入口 ``apply``：根据配置一次性应用上述过滤，返回新 panel 与剔除明细。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

LOGGER = logging.getLogger(__name__)
_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_CACHE = _THIS_DIR / "_cache_market_cap.csv"


# ============================================================================
# 股价过滤
# ============================================================================


def _reference_price(close: pd.DataFrame, mode: str) -> pd.Series:
    """根据 mode 计算每只股票的"参考股价"。"""
    if close.empty:
        return pd.Series(dtype=float)
    if mode == "last":
        valid = close.dropna(how="all")
        if valid.empty:
            return pd.Series(dtype=float, index=close.columns)
        return valid.iloc[-1]
    if mode == "mean":
        return close.mean(axis=0, skipna=True)
    if mode == "median":
        return close.median(axis=0, skipna=True)
    raise ValueError(f"未知的参考价模式: {mode}（应为 last/mean/median）")


def filter_by_price(
    panel: Dict[str, pd.DataFrame],
    min_price: float,
    max_price: float,
    mode: str = "last",
) -> Tuple[Dict[str, pd.DataFrame], List[str], List[str]]:
    """根据股价过滤股票池。

    Args:
        panel: 行情宽表字典（columns 是 instrument）。
        min_price / max_price: 价格区间（含端点）。
        mode: 参考价取法，``last``/``mean``/``median``。

    Returns:
        ``(new_panel, kept_codes, dropped_codes)``。
    """
    if "close" not in panel:
        raise KeyError("panel 缺少 close 字段，无法做股价过滤")

    ref = _reference_price(panel["close"], mode)
    mask = (ref >= float(min_price)) & (ref <= float(max_price))
    kept = mask[mask.fillna(False)].index.tolist()
    dropped = [c for c in panel["close"].columns if c not in kept]

    new_panel = {key: df[kept].copy() if not df.empty else df for key, df in panel.items()}
    return new_panel, kept, dropped


# ============================================================================
# 市值过滤（akshare）
# ============================================================================


def _akshare_code_to_qlib(raw: str) -> Optional[str]:
    """把 akshare 6 位股票代码（如 ``600000``）转换为 QLib 风格 ``SH600000``。"""
    s = str(raw).strip().zfill(6)
    if not s.isdigit() or len(s) != 6:
        return None
    if s.startswith(("60", "68", "5", "9")) and not s.startswith(("83", "87", "88", "92")):
        return f"SH{s}"
    if s.startswith(("00", "30", "1", "2")):
        return f"SZ{s}"
    if s.startswith(("4", "8")):
        return f"BJ{s}"
    return None


def fetch_market_cap_akshare(
    cache_path: Path = _DEFAULT_CACHE,
    *,
    force_refresh: bool = False,
    max_age_days: int = 30,
) -> pd.DataFrame:
    """从 akshare 拉取 A 股全市场市值快照，含本地 CSV 缓存。

    Returns:
        ``DataFrame``，``index`` 为 QLib 风格股票代码（如 ``SH600000``），列：

        - ``name``: 中文名
        - ``last_price``: 最新价
        - ``total_cap_yi``: 总市值（亿元）
        - ``float_cap_yi``: 流通市值（亿元）
    """
    cache_path = Path(cache_path)
    if cache_path.exists() and not force_refresh:
        mtime = pd.Timestamp(cache_path.stat().st_mtime, unit="s")
        age_days = (pd.Timestamp.now() - mtime).total_seconds() / 86400.0
        if age_days <= max_age_days:
            try:
                cached = pd.read_csv(cache_path, index_col=0, encoding="utf-8-sig")
                if {"total_cap_yi", "float_cap_yi"}.issubset(cached.columns):
                    LOGGER.info("市值缓存命中: %s（%.1f 天前）", cache_path, age_days)
                    return cached
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("市值缓存读取失败 (%s)，将重新拉取", exc)

    try:
        import akshare as ak
    except ImportError as exc:
        raise ImportError("市值过滤需要先 pip install akshare") from exc

    print("📡 正在通过 akshare 拉取 A 股全市场市值快照（仅首次或缓存过期时执行）...", flush=True)
    df = ak.stock_zh_a_spot_em()  # 实时行情快照
    if df is None or df.empty:
        raise RuntimeError("akshare 返回空数据，请检查网络")

    # akshare 列名：'代码','名称','最新价','总市值','流通市值',...
    expected = {"代码", "名称", "最新价", "总市值", "流通市值"}
    missing = expected - set(df.columns)
    if missing:
        raise RuntimeError(f"akshare 返回缺少列: {missing}")

    qlib_codes = [_akshare_code_to_qlib(x) for x in df["代码"].astype(str).values]
    out = pd.DataFrame(
        {
            "name": df["名称"].astype(str).values,
            "last_price": pd.to_numeric(df["最新价"], errors="coerce").values,
            "total_cap_yi": pd.to_numeric(df["总市值"], errors="coerce").values / 1e8,
            "float_cap_yi": pd.to_numeric(df["流通市值"], errors="coerce").values / 1e8,
        },
        index=pd.Index(qlib_codes, name="instrument"),
    )
    out = out[out.index.notna()]
    out = out[~out.index.duplicated(keep="first")]

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(cache_path, encoding="utf-8-sig")
    print(f"✅ 市值快照已缓存到 {cache_path}（共 {len(out)} 只股票）", flush=True)
    return out


def filter_by_market_cap(
    panel: Dict[str, pd.DataFrame],
    min_yi: float,
    max_yi: float,
    *,
    cap_kind: str = "total",
    cache_path: Path = _DEFAULT_CACHE,
    force_refresh: bool = False,
    max_age_days: int = 30,
) -> Tuple[Dict[str, pd.DataFrame], List[str], List[str], pd.DataFrame]:
    """根据市值过滤股票池。

    Args:
        panel: 行情宽表字典。
        min_yi / max_yi: 市值区间（亿元，含端点）。
        cap_kind: ``total`` 总市值（默认）或 ``float`` 流通市值。

    Returns:
        ``(new_panel, kept_codes, dropped_codes, cap_table)``。
        ``cap_table`` 是用于本次过滤的市值表（同 ``fetch_market_cap_akshare`` 返回结构）。
    """
    if "close" not in panel:
        raise KeyError("panel 缺少 close 字段，无法做市值过滤")

    cap_df = fetch_market_cap_akshare(
        cache_path=cache_path,
        force_refresh=force_refresh,
        max_age_days=max_age_days,
    )
    col = f"{cap_kind}_cap_yi"
    if col not in cap_df.columns:
        raise ValueError(f"未知的 cap_kind={cap_kind}（应为 total 或 float）")

    instruments = list(panel["close"].columns)
    cap_series = cap_df[col].reindex(instruments)
    mask = (cap_series >= float(min_yi)) & (cap_series <= float(max_yi))
    kept = [code for code, ok in mask.items() if bool(ok)]  # NaN/False 都剔除
    dropped = [c for c in instruments if c not in kept]

    new_panel = {key: df[kept].copy() if not df.empty else df for key, df in panel.items()}
    return new_panel, kept, dropped, cap_df


# ============================================================================
# 一站式入口
# ============================================================================


@dataclass
class StockPoolFilterConfig:
    enable_price: bool = True
    min_close_price: float = 2.0
    max_close_price: float = 15.0
    price_mode: str = "last"  # last | mean | median

    enable_market_cap: bool = True
    min_market_cap_yi: float = 20.0
    max_market_cap_yi: float = 150.0
    market_cap_kind: str = "total"  # total | float
    cache_max_age_days: int = 30
    force_refresh_cache: bool = False


def apply(
    panel: Dict[str, pd.DataFrame],
    config: StockPoolFilterConfig,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """按配置应用股价 + 市值两层过滤。

    Returns:
        ``(filtered_panel, report)``。``report`` 包含两轮过滤的剔除统计。
    """
    rows: List[Dict[str, object]] = []
    current_panel = panel
    initial_n = current_panel["close"].shape[1] if "close" in current_panel else 0

    # 1) 市值过滤优先（akshare 一次性确定可保留的股票）
    if config.enable_market_cap:
        try:
            current_panel, kept, dropped, cap_df = filter_by_market_cap(
                current_panel,
                config.min_market_cap_yi,
                config.max_market_cap_yi,
                cap_kind=config.market_cap_kind,
                force_refresh=config.force_refresh_cache,
                max_age_days=config.cache_max_age_days,
            )
            rows.append(
                {
                    "step": f"market_cap [{config.min_market_cap_yi:.0f},{config.max_market_cap_yi:.0f}] 亿",
                    "kept": len(kept),
                    "dropped": len(dropped),
                    "examples": ",".join(dropped[:5]),
                }
            )
            print(
                f"  💰 市值过滤: 保留 {len(kept)} 只，剔除 {len(dropped)} 只 "
                f"（区间 [{config.min_market_cap_yi:.0f}, {config.max_market_cap_yi:.0f}] 亿元，{config.market_cap_kind}）",
                flush=True,
            )
            # 剩 0 只时打印当前股票池的市值分位，提示合理区间
            if len(kept) == 0:
                col = f"{config.market_cap_kind}_cap_yi"
                aligned = cap_df[col].reindex(panel["close"].columns).dropna()
                if not aligned.empty:
                    q = aligned.quantile([0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0])
                    print("  📊 当前股票池市值分位（亿元），可据此调整区间：", flush=True)
                    for p, v in q.items():
                        print(f"     {int(p * 100):>3}%  →  {v:>10.1f}", flush=True)
                    print(
                        f"     👉 当前 market 股票池的市值最小值 {aligned.min():.0f} 亿元，"
                        f"上限设成 {aligned.quantile(0.5):.0f}+ 亿元才能保留一半股票",
                        flush=True,
                    )
        except Exception as exc:
            print(f"  ⚠️ 市值过滤失败（{type(exc).__name__}: {exc}），跳过此步", flush=True)
            rows.append({"step": "market_cap (FAILED)", "kept": initial_n, "dropped": 0, "examples": str(exc)[:50]})

    # 2) 股价过滤
    if config.enable_price:
        before = current_panel["close"].shape[1]
        current_panel, kept, dropped = filter_by_price(
            current_panel,
            config.min_close_price,
            config.max_close_price,
            mode=config.price_mode,
        )
        rows.append(
            {
                "step": f"price [{config.min_close_price:.2f},{config.max_close_price:.2f}] 元 ({config.price_mode})",
                "kept": len(kept),
                "dropped": len(dropped),
                "examples": ",".join(dropped[:5]),
            }
        )
        print(
            f"  💵 股价过滤: 保留 {len(kept)} 只，剔除 {len(dropped)} 只 "
            f"（区间 [{config.min_close_price:.2f}, {config.max_close_price:.2f}] 元，参考价={config.price_mode}）",
            flush=True,
        )

    final_n = current_panel["close"].shape[1] if "close" in current_panel else 0
    rows.append({"step": "FINAL", "kept": final_n, "dropped": initial_n - final_n, "examples": ""})
    report = pd.DataFrame(rows)

    if final_n == 0:
        raise RuntimeError("股票池过滤后剩余 0 只股票，请放宽过滤区间")
    return current_panel, report
