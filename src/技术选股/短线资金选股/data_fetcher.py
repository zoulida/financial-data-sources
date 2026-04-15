"""
数据获取模块
============
- 股票池：xtdata 获取A股 + 市值过滤
- K线：getDayData 优先，xtdata 兜底
- 资金流向：Wind Excel 插件批量获取 mfd 系列字段
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import hashlib
import pickle
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── 路径设置 ──
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

# ── 导入基础股票池 ──
try:
    from 基础筛选.filterStocks import get_universe_with_basics
    _FILTER_OK = True
except ImportError:
    _FILTER_OK = False
    logger.warning("无法导入 基础筛选.filterStocks，股票池功能不可用")

# ── 导入K线数据源（合并下载模块，遵循 .cursorrules 规则） ──
_GET_DAY_DATA_OK = False
getDayData = None
batchDownloadDayData = None
getDayDataCache = None
try:
    from source.实盘.xuntou.datadownload.合并下载数据 import (
        getDayData as _getDayData,
        batchDownloadDayData as _batchDownloadDayData,
        getDayDataCache as _getDayDataCache,
    )
    getDayData = _getDayData
    batchDownloadDayData = _batchDownloadDayData
    getDayDataCache = _getDayDataCache
    _GET_DAY_DATA_OK = True
except ImportError:
    pass

# xtdata 仅用于股票名称/ST过滤等辅助功能，不用于K线获取
_XT_OK = False
try:
    from xtquant import xtdata
    _XT_OK = True
except ImportError:
    pass

# ── 导入日期范围 ──
try:
    from md.获取enddate.get_date_range import get_date_range
except ImportError:
    def get_date_range():
        end = datetime.now()
        start = end - timedelta(days=600)
        return start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), "fallback"

# ── Wind 客户端 ──
from 技术选股.短线资金选股.wind_client import (
    fetch_wsd_batch,
    is_wind_available,
)
from 技术选股.短线资金选股.config import (
    MAX_MARKET_CAP, MAX_PRICE, MIN_PRICE,
    WIND_MFD_FIELDS, WIND_MFD_LOOKBACK_DAYS, WIND_BATCH_SIZE, WIND_TIMEOUT,
    KLINE_DAYS,
)


# ────────────────────────────────────────────────────────────
# 1. 股票池
# ────────────────────────────────────────────────────────────

def get_stock_universe() -> pd.DataFrame:
    """
    获取股票池：市值 < MAX_MARKET_CAP 亿、价格在 [MIN_PRICE, MAX_PRICE] 的沪深A股。

    返回:
        DataFrame(columns=['code', 'market_cap', 'free_float', 'last_price'])
    """
    if not _FILTER_OK:
        raise RuntimeError("基础筛选模块不可用")
    df = get_universe_with_basics(max_price=MAX_PRICE, max_mcap=MAX_MARKET_CAP)
    # 补充最低价格过滤
    if MIN_PRICE > 0:
        df = df[df["last_price"] >= MIN_PRICE].reset_index(drop=True)
    logger.info(f"股票池: {len(df)} 只 (市值<{MAX_MARKET_CAP}亿, 价格{MIN_PRICE}~{MAX_PRICE})")
    return df


# ────────────────────────────────────────────────────────────
# 2. K线数据
# ────────────────────────────────────────────────────────────

def fetch_day_k(code: str, start_date: str, end_date: str, use_cache: bool = False) -> Optional[pd.DataFrame]:
    """
    获取单只股票日K线（遵循 .cursorrules，统一走合并下载模块）。

    参数:
        use_cache: True 时使用 getDayDataCache（LRU缓存），适合重复调用
    """
    if not _GET_DAY_DATA_OK:
        logger.warning(f"合并下载模块不可用，无法获取 {code} K线")
        return None

    try:
        if use_cache and getDayDataCache is not None:
            df = getDayDataCache(
                stock_code=code, start_date=start_date, end_date=end_date,
            )
        else:
            df = getDayData(
                stock_code=code, start_date=start_date,
                end_date=end_date, is_download=0, dividend_type="front",
            )
        if df is not None and not df.empty:
            if "date" in df.columns:
                df["date"] = df["date"].astype(str)
            return df
    except Exception as e:
        logger.debug(f"getDayData({code}) 异常: {e}")
    return None


def fetch_kline_batch(codes: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
    """
    批量获取K线数据（遵循 .cursorrules，统一走合并下载模块）。

    策略：
      1. batchDownloadDayData(need_download=0) 先读缓存
      2. 缺失的再 batchDownloadDayData(need_download=1) 下载
      3. 逐只 getDayData 兜底
    """
    if not _GET_DAY_DATA_OK:
        logger.error("合并下载模块不可用，无法获取K线")
        return {}

    result = {}

    # ── 方式1：batchDownloadDayData 读缓存 ──
    if batchDownloadDayData is not None:
        try:
            logger.info(f"读取K线缓存 {len(codes)} 只...")
            batch = batchDownloadDayData(
                stock_codes=codes, start_date=start_date,
                end_date=end_date, dividend_type="front", need_download=0,
            )
            if isinstance(batch, dict):
                for code, df in batch.items():
                    if df is not None and not df.empty:
                        if "date" in df.columns:
                            df = df.sort_values("date").reset_index(drop=True)
                        result[code] = df
            logger.info(f"缓存命中: {len(result)}/{len(codes)}")
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")

    # ── 方式2：缺失的批量下载 ──
    missing = [c for c in codes if c not in result]
    if missing and batchDownloadDayData is not None:
        try:
            logger.info(f"下载缺失K线 {len(missing)} 只...")
            batch = batchDownloadDayData(
                stock_codes=missing, start_date=start_date,
                end_date=end_date, dividend_type="front", need_download=0,
            )
            if isinstance(batch, dict):
                for code, df in batch.items():
                    if df is not None and not df.empty:
                        if "date" in df.columns:
                            df = df.sort_values("date").reset_index(drop=True)
                        result[code] = df
            logger.info(f"下载补漏后: {len(result)}/{len(codes)}")
        except Exception as e:
            logger.warning(f"批量下载失败: {e}")

    # ── 方式3：逐只 getDayData 兜底 ──
    missing = [c for c in codes if c not in result]
    if missing:
        logger.info(f"getDayData 逐只补漏 {len(missing)} 只...")
        for i, code in enumerate(missing, 1):
            if i % 100 == 0:
                logger.info(f"  逐只进度: {i}/{len(missing)}")
            df = fetch_day_k(code, start_date, end_date)
            if isinstance(df, pd.DataFrame) and not df.empty:
                df = df.sort_values("date").reset_index(drop=True)
                result[code] = df

    logger.info(f"K线获取完成: {len(result)}/{len(codes)}")
    return result


# ────────────────────────────────────────────────────────────
# 3. Wind 资金流向
# ────────────────────────────────────────────────────────────

def _calc_wind_date_range() -> tuple:
    """计算 Wind 资金流向的起止日期（近 N 个交易日）。复用 get_date_range 对齐到最近交易日。"""
    _, end_date_str, _ = get_date_range()  # YYYYMMDD，已对齐到最近交易日
    end_dt = datetime.strptime(end_date_str, "%Y%m%d")
    # 往前多推几天，确保覆盖 N 个交易日
    start_dt = end_dt - timedelta(days=WIND_MFD_LOOKBACK_DAYS * 2 + 5)
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


# ── Wind 资金流向缓存目录 ──
_WIND_CACHE_DIR = Path(__file__).resolve().parents[1].parent / "data" / "cache" / "wind_mfd"


def _wind_cache_path(code: str, end_date: str) -> Path:
    """返回单只股票的 Wind 资金流向缓存文件路径。按 end_date 分目录。"""
    safe_code = code.replace(".", "_")
    return _WIND_CACHE_DIR / end_date.replace("-", "") / f"{safe_code}.pkl"


def _load_wind_cache(codes: List[str], end_date: str) -> Dict[str, pd.DataFrame]:
    """从磁盘加载已缓存的 Wind 资金流向数据。"""
    cached = {}
    for code in codes:
        p = _wind_cache_path(code, end_date)
        if p.exists():
            try:
                with open(p, "rb") as f:
                    df = pickle.load(f)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    cached[code] = df
            except Exception:
                pass
    return cached


def _save_wind_cache(result: Dict[str, pd.DataFrame], end_date: str) -> None:
    """将 Wind 资金流向数据按股票粒度写入磁盘缓存。"""
    for code, df in result.items():
        if df is None or df.empty:
            continue
        p = _wind_cache_path(code, end_date)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(p, "wb") as f:
                pickle.dump(df, f)
        except Exception as e:
            logger.debug(f"Wind 缓存写入失败 {code}: {e}")


def fetch_wind_capital_flow(codes: List[str]) -> Dict[str, pd.DataFrame]:
    """
    通过 Wind Excel 插件批量获取资金流向数据（带磁盘缓存）。

    缓存策略：按 end_date + 股票代码 粒度缓存，同一天内不重复查询。
    中断后重跑可自动续传。

    返回:
        dict: {code: DataFrame}，DataFrame 列为 ["date"] + WIND_MFD_FIELDS
    """
    if not is_wind_available():
        logger.warning("Wind Excel 插件不可用，跳过资金流向数据")
        return {}

    start_date, end_date = _calc_wind_date_range()
    all_result = {}

    # ── 读取缓存 ──
    cached = _load_wind_cache(codes, end_date)
    if cached:
        all_result.update(cached)
        logger.info(f"Wind 缓存命中: {len(cached)}/{len(codes)}")

    # ── 筛选需要下载的 ──
    missing_codes = [c for c in codes if c not in all_result]
    if not missing_codes:
        logger.info(f"Wind 资金流向全部命中缓存, 无需下载")
        return all_result

    logger.info(f"Wind 需下载: {len(missing_codes)}只 (缓存{len(cached)}只)")

    # ── 分批获取 ──
    for i in range(0, len(missing_codes), WIND_BATCH_SIZE):
        batch_codes = missing_codes[i:i + WIND_BATCH_SIZE]
        batch_num = i // WIND_BATCH_SIZE + 1
        total_batches = (len(missing_codes) + WIND_BATCH_SIZE - 1) // WIND_BATCH_SIZE
        logger.info(f"Wind 资金流向 批次 {batch_num}/{total_batches}: {len(batch_codes)}只")

        try:
            batch_result = fetch_wsd_batch(
                codes=batch_codes,
                fields=WIND_MFD_FIELDS,
                start_date=start_date,
                end_date=end_date,
                options="ruleType=10;unit=1",
                timeout=WIND_TIMEOUT,
            )
            all_result.update(batch_result)
            # 每批完成立即写缓存
            _save_wind_cache(batch_result, end_date)
            ok_codes = [c for c, df in batch_result.items() if df is not None and len(df) > 0]
            logger.info(f"Wind 批次 {batch_num} 完成: {len(ok_codes)}/{len(batch_codes)}只有数据, 累计{len(all_result)}只")
        except Exception as e:
            logger.error(f"Wind 批次 {batch_num} 失败: {e}")
            continue

    logger.info(f"Wind 资金流向获取完成: {len(all_result)}/{len(codes)}")
    return all_result


# ────────────────────────────────────────────────────────────
# 4. 名称和ST过滤
# ────────────────────────────────────────────────────────────

def get_stock_name(code: str) -> str:
    """获取股票名称。"""
    if _XT_OK:
        try:
            info = xtdata.get_instrument_detail(code)
            if isinstance(info, dict):
                return info.get("InstrumentName", "") or code
        except Exception:
            pass
    return code


def is_st_stock(name: str) -> bool:
    """判断是否为ST股。"""
    if not isinstance(name, str):
        return False
    s = name.upper().replace("＊", "*").replace(" ", "")
    return "ST" in s


def filter_st_stocks(codes: List[str]) -> List[str]:
    """过滤掉ST股票，返回非ST代码列表。"""
    result = []
    for code in codes:
        name = get_stock_name(code)
        if not is_st_stock(name):
            result.append(code)
    filtered = len(codes) - len(result)
    if filtered > 0:
        logger.info(f"ST过滤: {len(codes)} -> {len(result)} (移除{filtered}只)")
    return result
