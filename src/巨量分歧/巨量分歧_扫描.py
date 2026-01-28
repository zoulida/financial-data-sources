import sys
import os
from pathlib import Path
from typing import Optional, List
import pandas as pd
import numpy as np
from datetime import datetime

# 路径设置
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "md" / "获取enddate") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "md" / "获取enddate"))

# 尝试导入 getDayData（优先使用合并下载数据模块）
try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData  # type: ignore
    _GET_DAY_DATA_OK = True
except Exception:
    getDayData = None  # type: ignore
    _GET_DAY_DATA_OK = False

# 备选：xtdata 兜底获取
try:
    from xtquant import xtdata  # type: ignore
    _XT_OK = True
except Exception:
    xtdata = None  # type: ignore
    _XT_OK = False

# 初级股票池
from 基础筛选.filterStocks import get_universe_with_basics
# 日期范围
from md.获取enddate.get_date_range import get_date_range


def _fetch_day_k_xt(stock_code: str, start_date: str, end_date: str, dividend_type: str = "front") -> Optional[pd.DataFrame]:
    """使用 xtdata 获取日K，作为兜底方案。"""
    if not _XT_OK:
        return None
    try:
        # 下载历史数据，保证本地有数据
        try:
            xtdata.download_history_data(stock_code, "1d", start_date, end_date)
        except Exception:
            # 某些环境没有单只下载接口，忽略继续
            pass
        # 读取日K
        data_dict = xtdata.get_market_data_ex(
            [], [stock_code], period="1d", start_time=start_date, end_time=end_date, count=-1, dividend_type=dividend_type
        )
        if not isinstance(data_dict, dict) or stock_code not in data_dict:
            return None
        df = data_dict[stock_code].reset_index().rename(columns={"index": "date"})
        if "date" in df.columns:
            df["date"] = df["date"].astype(str)
        return df
    except Exception:
        return None


def fetch_day_k(stock_code: str, start_date: str, end_date: str, is_download: int = 0, dividend_type: str = "front") -> Optional[pd.DataFrame]:
    """优先使用 getDayData，失败则回退到 xtdata。"""
    # 优先使用合并下载数据
    if _GET_DAY_DATA_OK and getDayData is not None:
        try:
            df = getDayData(stock_code=stock_code, start_date=start_date, end_date=end_date, is_download=is_download, dividend_type=dividend_type)
            if df is not None and not df.empty:
                df["date"] = df["date"].astype(str)
                return df
        except Exception:
            pass
    # 兜底
    return _fetch_day_k_xt(stock_code, start_date, end_date, dividend_type)


def _filter_massive_divergence(
    df: pd.DataFrame, 
    code: str, 
    universe: pd.DataFrame, 
    ma_window: int = 20, 
    ratio: float = 4.0
) -> Optional[dict]:
    """
    筛选巨量分歧：最近一根K线的成交额 > 成交额均线的 ratio 倍。
    1) 对45天以内检测
    2) K线的成交额 > 成交额均线的 ratio 倍，且这个K线是5天内的第一根符合条件的K线
    
    Args:
        df: 股票K线数据
        code: 股票代码
        universe: 股票池数据
        ma_window: 成交额均线窗口
        ratio: 倍数阈值
        
    Returns:
        符合条件的股票信息字典，不符合则返回None
    """
    # 计算成交额均线（使用完整数据确保均线计算准确）
    df = df.sort_values("date").reset_index(drop=True)
    df["ma_amount"] = df["amount"].rolling(window=ma_window, min_periods=ma_window).mean()
    
    # 只在最近45天内寻找符合条件的K线
    recent_45_days = df.tail(45)
    # 进一步限制为最近5天内，找到第一根符合条件的K线
    recent_5_days = recent_45_days.tail(5)
    
    for idx, row in recent_5_days.iterrows():
        ma_val = row.get("ma_amount", np.nan)
        last_amt = row.get("amount", np.nan)
        
        if pd.notna(ma_val) and pd.notna(last_amt) and last_amt > ratio * ma_val:
            return {
                "code": code,
                "date": str(row.get("date", "")),
                "close": row.get("close", np.nan),
                "amount": float(last_amt),
                "ma_amount": float(ma_val),
                "ratio": float(last_amt / ma_val) if ma_val not in (0, np.nan) else np.nan,
                "market_cap": universe.loc[universe["code"] == code, "market_cap"].values[0] if (universe["code"] == code).any() else np.nan,
                "last_price": universe.loc[universe["code"] == code, "last_price"].values[0] if (universe["code"] == code).any() else np.nan,
            }
    
    return None


def scan_massive_divergence(
    max_price: float = 15.0,
    max_mcap: float = 150.0,
    ma_window: int = 20,
    ratio: float = 4.0,
    is_download: int = 0,
    limit: int = 0,
) -> pd.DataFrame:
    """
    扫描"巨量分歧"：最近一根K线的成交额 > 成交额均线的 ratio 倍。
    """
    start_date, end_date, _ = get_date_range()

    # 股票池（价格与市值上限）
    universe = get_universe_with_basics(max_price=max_price, max_mcap=max_mcap)
    codes: List[str] = universe["code"].tolist()
    if limit and limit > 0:
        codes = codes[:limit]

    results = []
    for idx, code in enumerate(codes, 1):
        try:
            df = fetch_day_k(code, start_date, end_date, is_download=is_download, dividend_type="front")
            if df is None or df.empty or "amount" not in df.columns:
                continue
            
            # 使用筛选函数
            result = _filter_massive_divergence(df, code, universe, ma_window, ratio)
            if result is not None:
                results.append(result)
                
        except Exception:
            continue

    result_df = pd.DataFrame(results)
    # 保存CSV
    out_dir = PROJECT_ROOT / "src" / "巨量分歧"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"巨量分歧_{end_date}_ma{ma_window}_x{int(ratio)}.csv"
    result_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"扫描完成：股票池 {len(codes)} 只，命中 {len(result_df)} 只。CSV: {out_path}")
    return result_df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="巨量分歧扫描：最近一根K线成交额 > 成交额均线的N倍")
    parser.add_argument("--max-price", type=float, default=15.0, help="最大价格，默认15")
    parser.add_argument("--max-mcap", type=float, default=150.0, help="最大市值(亿元)，默认150")
    parser.add_argument("--ma", dest="ma_window", type=int, default=20, help="成交额均线窗口，默认20日")
    parser.add_argument("--ratio", type=float, default=4.0, help="倍数阈值，默认4")
    parser.add_argument("--download", dest="is_download", type=int, default=0, help="是否强制重新下载(仅合并下载数据生效)，默认0")
    parser.add_argument("--limit", type=int, default=0, help="调试用，限制前N只股票，默认0为不限")

    args = parser.parse_args()
    scan_massive_divergence(
        max_price=args.max_price,
        max_mcap=args.max_mcap,
        ma_window=args.ma_window,
        ratio=args.ratio,
        is_download=args.is_download,
        limit=args.limit,
    )
