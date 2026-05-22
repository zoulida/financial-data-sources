# -*- coding: utf-8 -*-
"""板块/概念成分获取与缓存。

- 通过 ``xtquant.xtdata.download_sector_data`` 更新本地板块分类数据。
- 通过 ``xtquant.xtdata.get_sector_list`` 拿到全部板块名称。
- 通过 ``xtquant.xtdata.get_stock_list_in_sector`` 拿到每个板块成分股。
- 结果以 JSON 缓存到本地，避免反复调用 XtQuant 服务。

本模块不依赖 Qlib，只依赖 xtquant；如果 xtquant 不可用会抛出 ImportError。
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .code_utils import filter_a_share_xt

LOGGER = logging.getLogger(__name__)

# 默认排除的板块名（指数、债券、基金、期货、港股、衍生品等）。
# 通过子串匹配，命中即剔除。
_DEFAULT_EXCLUDE_KEYWORDS: tuple = (
    "指数", "ETF", "LOF", "REIT", "基金", "债", "可转债", "国债", "回购",
    "权证", "期货", "期权", "外汇", "黄金", "白银", "港股", "B股",
    "退市", "暂停", "风险", "停牌",
)

# 默认保留的常见板块前缀关键词（行业、概念、地域）。如果板块名以下列任一关键词
# 命中就保留；为空表示不强制要求。本模块默认不强制，因此走"排除法"。
_DEFAULT_INCLUDE_KEYWORDS: tuple = ()


@dataclass
class SectorConfig:
    """板块成分获取与缓存配置。"""

    cache_dir: str = ".sector_cache"
    cache_max_age_hours: int = 24
    min_members: int = 10
    max_members: int = 600
    only_a_share: bool = True
    exclude_keywords: Sequence[str] = field(default_factory=lambda: list(_DEFAULT_EXCLUDE_KEYWORDS))
    include_keywords: Sequence[str] = field(default_factory=lambda: list(_DEFAULT_INCLUDE_KEYWORDS))
    # 板块名长度上限，过长的多为自定义/异常板块
    max_name_length: int = 30


def _safe_filename(name: str) -> str:
    """把板块名转换为安全的文件名片段。"""
    cleaned = re.sub(r"[\\/:*?\"<>|\s]", "_", str(name))
    return cleaned[:80] or "_"


def _cache_root(config: SectorConfig) -> Path:
    cache_dir = Path(config.cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = Path(__file__).resolve().parent / cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _is_cache_fresh(path: Path, max_age_hours: int) -> bool:
    if not path.exists():
        return False
    if max_age_hours <= 0:
        return True
    mtime = _dt.datetime.fromtimestamp(path.stat().st_mtime)
    return (_dt.datetime.now() - mtime) <= _dt.timedelta(hours=max_age_hours)


def _import_xtdata():
    try:
        from xtquant import xtdata  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "未能导入 xtquant.xtdata，请确认已安装 xtquant 并启动 mini-QMT。"
        ) from exc
    return xtdata


def _name_passes_filters(name: str, config: SectorConfig) -> bool:
    if not name:
        return False
    if len(name) > config.max_name_length:
        return False
    for keyword in config.exclude_keywords:
        if keyword and keyword in name:
            return False
    if config.include_keywords:
        return any(keyword in name for keyword in config.include_keywords)
    return True


def update_local_sector_data(force: bool = False) -> None:
    """调用 xtdata.download_sector_data 更新本地板块数据。

    XtQuant 此接口会写入本地缓存目录；第一次使用必须执行，之后建议每天执行一次。
    """
    xtdata = _import_xtdata()
    LOGGER.info("正在调用 xtdata.download_sector_data() 更新本地板块数据 ...")
    try:
        xtdata.download_sector_data()
    except Exception as exc:  # pragma: no cover
        if force:
            raise
        LOGGER.warning("download_sector_data 失败（忽略，使用现有本地缓存）: %s", exc)


def get_sector_names(
    config: Optional[SectorConfig] = None,
    *,
    update: bool = False,
) -> List[str]:
    """获取过滤后的板块名称列表。"""
    config = config or SectorConfig()
    xtdata = _import_xtdata()
    if update:
        update_local_sector_data(force=False)
    raw = xtdata.get_sector_list() or []
    names = [str(n) for n in raw]
    filtered = [n for n in names if _name_passes_filters(n, config)]
    LOGGER.info("板块总数 %d，过滤后保留 %d 个", len(names), len(filtered))
    return filtered


def get_sector_constituents(
    sector_name: str,
    config: Optional[SectorConfig] = None,
    *,
    use_cache: bool = True,
) -> List[str]:
    """获取单个板块的 A 股成分股列表（XtQuant 代码）。"""
    config = config or SectorConfig()
    cache_root = _cache_root(config)
    cache_path = cache_root / f"sector_{_safe_filename(sector_name)}.json"

    if use_cache and _is_cache_fresh(cache_path, config.cache_max_age_hours):
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            cached = payload.get("members", [])
            if isinstance(cached, list) and cached:
                return list(cached)
        except Exception as exc:
            LOGGER.warning("读取板块缓存失败 %s: %s", cache_path, exc)

    xtdata = _import_xtdata()
    members_raw = xtdata.get_stock_list_in_sector(sector_name) or []
    members = [str(c).strip() for c in members_raw if str(c).strip()]
    if config.only_a_share:
        members = filter_a_share_xt(members)
    members = sorted(set(members))

    payload = {
        "sector": sector_name,
        "fetched_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "members": members,
    }
    try:
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        LOGGER.warning("写入板块缓存失败 %s: %s", cache_path, exc)
    return members


def build_sector_universe(
    config: Optional[SectorConfig] = None,
    *,
    update: bool = False,
    sector_names: Optional[Sequence[str]] = None,
) -> Dict[str, List[str]]:
    """构造 ``{板块名: [成分股 XtQuant 代码列表]}`` 的字典。"""
    config = config or SectorConfig()
    if update:
        update_local_sector_data(force=False)

    if sector_names is None:
        names = get_sector_names(config)
    else:
        names = [str(n) for n in sector_names if _name_passes_filters(str(n), config)]

    result: Dict[str, List[str]] = {}
    for name in names:
        try:
            members = get_sector_constituents(name, config)
        except Exception as exc:
            LOGGER.warning("跳过板块 %s（拉取成分失败）: %s", name, exc)
            continue
        if len(members) < config.min_members:
            continue
        if len(members) > config.max_members:
            continue
        result[name] = members

    LOGGER.info("最终保留板块 %d 个", len(result))
    return result


def save_universe_snapshot(universe: Dict[str, List[str]], path: str | os.PathLike) -> None:
    """保存板块全集快照，便于离线训练复用。"""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "n_sectors": len(universe),
        "sectors": universe,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_universe_snapshot(path: str | os.PathLike) -> Dict[str, List[str]]:
    """加载离线快照。"""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    sectors = raw.get("sectors", {})
    return {str(k): [str(c) for c in v] for k, v in sectors.items()}


def collect_all_members(universe: Dict[str, Iterable[str]]) -> List[str]:
    """汇总全部板块涉及的成分股（去重）。"""
    bucket: set = set()
    for members in universe.values():
        bucket.update(members)
    return sorted(bucket)
