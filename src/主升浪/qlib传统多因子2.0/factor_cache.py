#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""因子结果磁盘缓存。

设计思路：
- 缓存键 = sha1(factor_name | panel_signature | func_source_hash)
- panel_signature 由 ``close`` 宽表的：起止日期 + 排序后的股票列表 共同决定，
  因此当时间范围或股票池发生变化时，缓存自动失效。
- ``func_source_hash`` 让因子函数本身的代码改动也会让缓存失效，避免吃到旧结果。
- 文件以 pickle 形式落盘，体积通常较小（几十 KB ~ 数 MB）。
"""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

CACHE_FILE_SUFFIX = ".pkl"


def panel_signature(panel: Dict[str, pd.DataFrame]) -> str:
    """根据行情面板生成稳定的指纹字符串。

    使用 ``close`` 宽表作为代表：
    - 起止日期（保证时间范围一致）；
    - 排序后的列名（股票代码集合）。
    """
    close = panel.get("close") if panel else None
    if close is None or close.empty:
        return "empty-panel"

    start = pd.Timestamp(close.index[0]).strftime("%Y-%m-%d")
    end = pd.Timestamp(close.index[-1]).strftime("%Y-%m-%d")
    symbols = ",".join(sorted(map(str, list(close.columns))))
    h = hashlib.sha1()
    h.update(start.encode("utf-8"))
    h.update(b"|")
    h.update(end.encode("utf-8"))
    h.update(b"|")
    h.update(symbols.encode("utf-8"))
    return h.hexdigest()


def legacy_panel_signature(panel: Dict[str, pd.DataFrame]) -> str:
    close = panel.get("close") if panel else None
    if close is None or close.empty:
        return "empty-panel"

    h = hashlib.sha1()
    h.update(str(close.index[0]).encode("utf-8"))
    h.update(b"|")
    h.update(str(close.index[-1]).encode("utf-8"))
    h.update(b"|")
    symbols = ",".join(map(str, list(close.columns)))
    h.update(symbols.encode("utf-8"))
    h.update(b"|")
    try:
        last_row = close.iloc[-1].fillna(0.0).to_numpy()
        h.update(last_row.tobytes())
    except Exception:
        h.update(str(close.shape).encode("utf-8"))
    return h.hexdigest()


def factor_cache_key(factor_name: str, panel_sig: str, func_source: str) -> str:
    """根据因子名、面板指纹、因子源码生成缓存 key。"""
    src_hash = hashlib.sha1(func_source.encode("utf-8", errors="ignore")).hexdigest()
    h = hashlib.sha1()
    h.update(factor_name.encode("utf-8"))
    h.update(b"|")
    h.update(panel_sig.encode("utf-8"))
    h.update(b"|")
    h.update(src_hash.encode("utf-8"))
    return h.hexdigest()


def _key_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}{CACHE_FILE_SUFFIX}"


def load(cache_dir: str | Path, key: str) -> Optional[pd.DataFrame]:
    """读取缓存，命中返回 DataFrame，未命中或失败返回 None。"""
    fp = _key_path(Path(cache_dir), key)
    if not fp.exists():
        return None
    try:
        with open(fp, "rb") as file:
            obj = pickle.load(file)
        if isinstance(obj, pd.DataFrame) and not obj.empty:
            return obj
    except Exception:
        return None
    return None


def save(cache_dir: str | Path, key: str, df: pd.DataFrame) -> bool:
    """写缓存。失败时静默返回 False。"""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return False
    cache_path = Path(cache_dir)
    try:
        cache_path.mkdir(parents=True, exist_ok=True)
        fp = _key_path(cache_path, key)
        with open(fp, "wb") as file:
            pickle.dump(df, file, protocol=pickle.HIGHEST_PROTOCOL)
        return True
    except Exception:
        return False


def clear(cache_dir: str | Path) -> int:
    """清空缓存目录下所有 ``*.pkl`` 文件，返回删除数量。"""
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        return 0
    deleted = 0
    for file in cache_path.glob(f"*{CACHE_FILE_SUFFIX}"):
        try:
            file.unlink()
            deleted += 1
        except Exception:
            continue
    return deleted


def stats(cache_dir: str | Path) -> Dict[str, int]:
    """返回缓存目录统计：``{count, size_bytes}``。"""
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        return {"count": 0, "size_bytes": 0}
    count = 0
    total = 0
    for file in cache_path.glob(f"*{CACHE_FILE_SUFFIX}"):
        try:
            total += file.stat().st_size
            count += 1
        except Exception:
            continue
    return {"count": count, "size_bytes": total}
