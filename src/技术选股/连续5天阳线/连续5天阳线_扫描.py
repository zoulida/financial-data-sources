"""
连续5天阳线筛选策略
筛选条件：30天内，存在连续收阳线5天，每个阳线涨幅小于等于3%
"""
import sys
import os
from pathlib import Path
from typing import Optional, List
import pandas as pd
import numpy as np
from datetime import datetime

# 路径设置
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "md" / "获取enddate") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "md" / "获取enddate"))

# 导入 getDayDataWithTimeout（带超时重试机制）
from source.实盘.xuntou.datadownload.合并下载数据 import getDayDataWithTimeout  # type: ignore

# 初级股票池
from 基础筛选.filterStocks import get_universe_with_basics
# 日期范围
from md.获取enddate.get_date_range import get_date_range


def fetch_day_k(
    stock_code: str, 
    start_date: str, 
    end_date: str, 
    is_download: int = 0, 
    dividend_type: str = "front"
) -> Optional[pd.DataFrame]:
    """
    使用 getDayDataWithTimeout 获取日K数据（内置超时重试机制）。
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        is_download: 是否强制重新下载
        dividend_type: 复权类型
        
    Returns:
        K线数据DataFrame，失败返回None
    """
    try:
        df = getDayDataWithTimeout(
            stock_code=stock_code, 
            start_date=start_date, 
            end_date=end_date, 
            is_download=is_download, 
            dividend_type=dividend_type
        )
        if df is not None and not df.empty:
            df["date"] = df["date"].astype(str)
            return df
        return None
    except Exception as e:
        print(f"[错误] {stock_code} 获取数据异常: {e}")
        return None


def _filter_consecutive_positive(
    df: pd.DataFrame, 
    code: str, 
    universe: pd.DataFrame, 
    consecutive_days: int = 5,
    max_daily_gain: float = 3.0,
    lookback_days: int = 30
) -> Optional[dict]:
    """
    筛选连续阳线：在最近 lookback_days 天内，存在连续 consecutive_days 天收阳线，
    且每根阳线涨幅 <= max_daily_gain%。
    
    阳线定义：收盘价 > 开盘价
    涨幅计算：(收盘价 - 前一日收盘价) / 前一日收盘价 * 100
    
    Args:
        df: 股票K线数据
        code: 股票代码
        universe: 股票池数据
        consecutive_days: 连续阳线天数
        max_daily_gain: 每日最大涨幅(%)
        lookback_days: 回溯天数
        
    Returns:
        符合条件的股票信息字典，不符合则返回None
    """
    df = df.sort_values("date").reset_index(drop=True)
    
    # 计算涨幅（相对于前一日收盘价）
    df["pct_change"] = df["close"].pct_change() * 100
    
    # 判断是否为阳线（收盘价 > 开盘价）
    df["is_positive"] = df["close"] > df["open"]
    
    # 只在最近 lookback_days 天内寻找
    recent_days = df.tail(lookback_days).copy()
    
    if len(recent_days) < consecutive_days:
        return None
    
    # 滑动窗口检测连续阳线
    for i in range(len(recent_days) - consecutive_days + 1):
        window = recent_days.iloc[i:i + consecutive_days]
        
        # 检查是否全部为阳线
        if not window["is_positive"].all():
            continue
        
        # 检查每根阳线涨幅是否 <= max_daily_gain%
        if (window["pct_change"] > max_daily_gain).any():
            continue
        
        # 符合条件，返回结果
        start_date = window.iloc[0]["date"]
        end_date = window.iloc[-1]["date"]
        total_gain = (window.iloc[-1]["close"] / window.iloc[0]["open"] - 1) * 100
        
        return {
            "code": code,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "consecutive_days": consecutive_days,
            "total_gain": round(total_gain, 2),
            "avg_daily_gain": round(window["pct_change"].mean(), 2),
            "max_daily_gain": round(window["pct_change"].max(), 2),
            "close": window.iloc[-1]["close"],
            "market_cap": universe.loc[universe["code"] == code, "market_cap"].values[0] if (universe["code"] == code).any() else np.nan,
            "last_price": universe.loc[universe["code"] == code, "last_price"].values[0] if (universe["code"] == code).any() else np.nan,
        }
    
    return None


def scan_consecutive_positive(
    max_price: float = 15.0,
    max_mcap: float = 150.0,
    consecutive_days: int = 5,
    max_daily_gain: float = 3.0,
    lookback_days: int = 30,
    is_download: int = 0,
    limit: int = 0,
) -> pd.DataFrame:
    """
    扫描"连续阳线"：在最近 lookback_days 天内，存在连续 consecutive_days 天收阳线，
    且每根阳线涨幅 <= max_daily_gain%。
    
    Args:
        max_price: 最大价格
        max_mcap: 最大市值(亿元)
        consecutive_days: 连续阳线天数
        max_daily_gain: 每日最大涨幅(%)
        lookback_days: 回溯天数
        is_download: 是否强制重新下载
        limit: 调试用，限制前N只股票
        
    Returns:
        符合条件的股票DataFrame
    """
    start_date, end_date, _ = get_date_range()

    # 股票池（价格与市值上限）
    universe = get_universe_with_basics(max_price=max_price, max_mcap=max_mcap)
    codes: List[str] = universe["code"].tolist()
    if limit and limit > 0:
        codes = codes[:limit]

    results = []
    total = len(codes)
    for idx, code in enumerate(codes, 1):
        if idx % 100 == 0:
            print(f"进度: {idx}/{total}")
        try:
            df = fetch_day_k(code, start_date, end_date, is_download=is_download, dividend_type="front")
            if df is None or df.empty or "close" not in df.columns or "open" not in df.columns:
                continue
            
            result = _filter_consecutive_positive(
                df, code, universe, 
                consecutive_days=consecutive_days,
                max_daily_gain=max_daily_gain,
                lookback_days=lookback_days
            )
            if result is not None:
                results.append(result)
                
        except Exception:
            continue

    result_df = pd.DataFrame(results)
    
    # 保存CSV
    out_dir = Path(__file__).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"连续{consecutive_days}天阳线_{end_date}_max{int(max_daily_gain)}pct.csv"
    result_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"扫描完成：股票池 {len(codes)} 只，命中 {len(result_df)} 只。CSV: {out_path}")
    return result_df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="连续阳线扫描：30天内连续5天阳线，每日涨幅<=3%")
    parser.add_argument("--max-price", type=float, default=15.0, help="最大价格，默认15")
    parser.add_argument("--max-mcap", type=float, default=150.0, help="最大市值(亿元)，默认150")
    parser.add_argument("--days", dest="consecutive_days", type=int, default=5, help="连续阳线天数，默认5")
    parser.add_argument("--max-gain", dest="max_daily_gain", type=float, default=3.0, help="每日最大涨幅(%)，默认3")
    parser.add_argument("--lookback", dest="lookback_days", type=int, default=30, help="回溯天数，默认30")
    parser.add_argument("--download", dest="is_download", type=int, default=0, help="是否强制重新下载，默认0")
    parser.add_argument("--limit", type=int, default=0, help="调试用，限制前N只股票，默认0为不限")

    args = parser.parse_args()
    scan_consecutive_positive(
        max_price=args.max_price,
        max_mcap=args.max_mcap,
        consecutive_days=args.consecutive_days,
        max_daily_gain=args.max_daily_gain,
        lookback_days=args.lookback_days,
        is_download=args.is_download,
        limit=args.limit,
    )
