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

# ── 导入K线数据源 ──
# getDayData 优先
_GET_DAY_DATA_OK = False
getDayData = None
batchDownloadDayData = None
try:
    from source.实盘.xuntou.datadownload.合并下载数据 import (
        getDayData as _getDayData,
        batchDownloadDayData as _batchDownloadDayData,
    )
    getDayData = _getDayData
    batchDownloadDayData = _batchDownloadDayData
    _GET_DAY_DATA_OK = True
except ImportError:
    pass

# xtdata 兜底
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

def _fetch_day_k_xt(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """使用 xtdata 获取日K（兜底）。"""
    if not _XT_OK:
        return None
    try:
        try:
            xtdata.download_history_data(code, "1d", start_date, end_date)
        except Exception:
            pass
        data_dict = xtdata.get_market_data_ex(
            [], [code], period="1d",
            start_time=start_date, end_time=end_date,
            count=-1, dividend_type="front",
        )
        if not isinstance(data_dict, dict) or code not in data_dict:
            return None
        df = data_dict[code].reset_index().rename(columns={"index": "date"})
        if "date" in df.columns:
            df["date"] = df["date"].astype(str)
        return df
    except Exception:
        return None


def fetch_day_k(code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """获取单只股票日K线。getDayData 优先，xtdata 兜底。"""
    if _GET_DAY_DATA_OK and getDayData is not None:
        try:
            df = getDayData(
                stock_code=code, start_date=start_date,
                end_date=end_date, is_download=0, dividend_type="front",
            )
            if df is not None and not df.empty:
                df["date"] = df["date"].astype(str)
                return df
        except Exception:
            pass
    return _fetch_day_k_xt(code, start_date, end_date)


def fetch_kline_batch(codes: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
    """
    批量获取K线数据。

    策略：
      1. xtdata 批量下载 + 获取（最快）
      2. batchDownloadDayData 读本地缓存补漏
      3. 逐只 getDayData 兜底（仅处理剩余缺失的）
    """
    result = {}
    missing = list(codes)

    # ── 方式1：xtdata 批量 ──
    if _XT_OK:
        try:
            # 先触发批量下载（异步，不阻塞太久）
            logger.info(f"xtdata 批量下载 {len(missing)} 只...")
            try:
                xtdata.download_history_data2(
                    missing, "1d", start_date, end_date
                )
            except Exception:
                pass
            # 批量获取
            all_data = xtdata.get_market_data_ex(
                [], missing, period="1d",
                start_time=start_date, end_time=end_date,
                count=-1, dividend_type="front",
            )
            if isinstance(all_data, dict):
                for code in missing:
                    df = all_data.get(code)
                    if df is not None and not df.empty:
                        df = df.reset_index().rename(columns={"index": "date"})
                        df = df.sort_values("date").reset_index(drop=True)
                        result[code] = df
            logger.info(f"xtdata批量获取: {len(result)}/{len(codes)}")
            missing = [c for c in codes if c not in result]
        except Exception as e:
            logger.warning(f"xtdata批量失败: {e}")

    # ── 方式2：batchDownloadDayData 读缓存补漏 ──
    if missing and _GET_DAY_DATA_OK and batchDownloadDayData is not None:
        try:
            batch = batchDownloadDayData(
                stock_codes=missing, start_date=start_date,
                end_date=end_date, dividend_type="front", need_download=0,
            )
            if isinstance(batch, dict):
                for code, df in batch.items():
                    if df is not None and not df.empty:
                        result[code] = df
                logger.info(f"缓存补漏: +{len(batch)}, 总计 {len(result)}/{len(codes)}")
                missing = [c for c in codes if c not in result]
        except Exception:
            pass

    # ── 方式3：逐只获取（仅剩余缺失的） ──
    if missing:
        logger.info(f"逐只获取剩余 {len(missing)} 只K线...")
        for i, code in enumerate(missing, 1):
            if i % 50 == 0:
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
    """计算 Wind 资金流向的起止日期（近 N 个交易日）。"""
    end_dt = datetime.now()
    # 往前多推几天，确保覆盖 N 个交易日
    start_dt = end_dt - timedelta(days=WIND_MFD_LOOKBACK_DAYS * 2 + 5)
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


def fetch_wind_capital_flow(codes: List[str]) -> Dict[str, pd.DataFrame]:
    """
    通过 Wind Excel 插件批量获取资金流向数据。

    返回:
        dict: {code: DataFrame}，DataFrame 列为 ["date"] + WIND_MFD_FIELDS
    """
    if not is_wind_available():
        logger.warning("Wind Excel 插件不可用，跳过资金流向数据")
        return {}

    start_date, end_date = _calc_wind_date_range()
    all_result = {}

    # 分批获取
    for i in range(0, len(codes), WIND_BATCH_SIZE):
        batch_codes = codes[i:i + WIND_BATCH_SIZE]
        batch_num = i // WIND_BATCH_SIZE + 1
        total_batches = (len(codes) + WIND_BATCH_SIZE - 1) // WIND_BATCH_SIZE
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
