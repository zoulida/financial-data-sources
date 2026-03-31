"""
分歧突破形态筛选策略
筛选条件：
1. 目标分歧日：最近20个交易日内，当日成交量 > 前5日每一天成交量的3倍
2. 历史分歧日：向前回溯找最近的匹配日，收盘价偏差±10%，成交量偏差±20%
3. 股票池：市值70亿以内，当前价不超18元
"""
import sys
from pathlib import Path
from typing import Optional, List, Dict
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


def detect_divergence_breakthrough(
    df: pd.DataFrame,
    lookback_target: int = 20,
    volume_multiplier: float = 3.0,
    price_tolerance: float = 0.10,
    volume_tolerance: float = 0.20
) -> Dict:
    """
    检测单只股票是否存在分歧突破形态
    
    Args:
        df: DataFrame 包含 'close', 'volume', 'date' 列
        lookback_target: 目标分歧日回溯天数（默认20天）
        volume_multiplier: 成交量倍数阈值（默认3倍）
        price_tolerance: 收盘价偏差容忍度（默认10%）
        volume_tolerance: 成交量偏差容忍度（默认20%）
        
    Returns:
        dict: {
            'is_divergence': bool,
            'target_date': 目标分歧日,
            'target_close': 目标分歧日收盘价,
            'target_volume': 目标分歧日成交量,
            'history_date': 历史分歧日,
            'history_close': 历史分歧日收盘价,
            'history_volume': 历史分歧日成交量,
            'days_between': 两个分歧日之间的天数,
            'price_deviation': 价格偏差百分比,
            'volume_deviation': 成交量偏差百分比
        }
    """
    result = {
        'is_divergence': False,
        'target_date': None,
        'target_close': None,
        'target_volume': None,
        'history_date': None,
        'history_close': None,
        'history_volume': None,
        'days_between': None,
        'price_deviation': None,
        'volume_deviation': None
    }
    
    df = df.sort_values("date").reset_index(drop=True)
    
    if len(df) < lookback_target + 5:
        return result
    
    # 取最近lookback_target天数据作为目标分歧日候选范围
    recent_df = df.tail(lookback_target).copy().reset_index(drop=True)
    
    # 遍历最近20天，寻找目标分歧日（从最近的日期开始）
    for i in range(len(recent_df) - 1, 4, -1):  # 至少需要前5天数据
        target_idx_in_df = len(df) - len(recent_df) + i
        
        target_volume = df.iloc[target_idx_in_df]["volume"]
        target_close = df.iloc[target_idx_in_df]["close"]
        target_date = df.iloc[target_idx_in_df]["date"]
        
        # 检查前5天的成交量
        prev_5_volumes = df.iloc[target_idx_in_df - 5:target_idx_in_df]["volume"].values
        
        # 条件：目标分歧日成交量 > 前5日每一天成交量的3倍
        if not all(target_volume > vol * volume_multiplier for vol in prev_5_volumes):
            continue
        
        # 找到目标分歧日，向前回溯寻找历史分歧日
        # 从目标分歧日前一天开始向前搜索
        for j in range(target_idx_in_df - 1, -1, -1):
            history_close = df.iloc[j]["close"]
            history_volume = df.iloc[j]["volume"]
            history_date = df.iloc[j]["date"]
            
            # 计算偏差
            price_deviation = abs(history_close - target_close) / target_close
            volume_deviation = abs(history_volume - target_volume) / target_volume
            
            # 检查是否满足匹配条件
            if price_deviation <= price_tolerance and volume_deviation <= volume_tolerance:
                # 找到历史分歧日
                days_between = target_idx_in_df - j
                
                result = {
                    'is_divergence': True,
                    'target_date': target_date,
                    'target_close': round(target_close, 2),
                    'target_volume': int(target_volume),
                    'history_date': history_date,
                    'history_close': round(history_close, 2),
                    'history_volume': int(history_volume),
                    'days_between': days_between,
                    'price_deviation': round(price_deviation * 100, 2),
                    'volume_deviation': round(volume_deviation * 100, 2)
                }
                return result
    
    return result


def scan_divergence_breakthrough(
    max_price: float = 18.0,
    max_mcap: float = 70.0,
    lookback_target: int = 20,
    volume_multiplier: float = 3.0,
    price_tolerance: float = 0.10,
    volume_tolerance: float = 0.20,
    is_download: int = 0,
    limit: int = 0,
    top_n: int = 50
) -> pd.DataFrame:
    """
    扫描"分歧突破"形态：小盘股主力介入筛选
    
    Args:
        max_price: 最大价格（默认18元）
        max_mcap: 最大市值（默认70亿元）
        lookback_target: 目标分歧日回溯天数
        volume_multiplier: 成交量倍数阈值
        price_tolerance: 收盘价偏差容忍度
        volume_tolerance: 成交量偏差容忍度
        is_download: 是否强制重新下载
        limit: 调试用，限制前N只股票
        top_n: 输出Top N结果
        
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
            if df is None or df.empty:
                continue
            
            required_cols = ["close", "volume", "date"]
            if not all(col in df.columns for col in required_cols):
                continue
            
            detection = detect_divergence_breakthrough(
                df, 
                lookback_target=lookback_target,
                volume_multiplier=volume_multiplier,
                price_tolerance=price_tolerance,
                volume_tolerance=volume_tolerance
            )
            
            if detection['is_divergence']:
                # 获取股票基本信息
                stock_info = universe[universe["code"] == code]
                market_cap = stock_info["market_cap"].values[0] if len(stock_info) > 0 else np.nan
                last_price = stock_info["last_price"].values[0] if len(stock_info) > 0 else np.nan
                
                results.append({
                    "code": code,
                    "target_date": detection['target_date'],
                    "target_close": detection['target_close'],
                    "target_volume": detection['target_volume'],
                    "history_date": detection['history_date'],
                    "history_close": detection['history_close'],
                    "history_volume": detection['history_volume'],
                    "days_between": detection['days_between'],
                    "price_deviation": detection['price_deviation'],
                    "volume_deviation": detection['volume_deviation'],
                    "last_price": last_price,
                    "market_cap": market_cap
                })
                
        except Exception as e:
            continue

    result_df = pd.DataFrame(results)
    
    # 按目标分歧日排序（最近的在前），再按间隔天数排序
    if not result_df.empty:
        result_df = result_df.sort_values(
            ["target_date", "days_between"], 
            ascending=[False, True]
        ).head(top_n)
    
    # 保存CSV
    out_dir = Path(__file__).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"分歧突破_{end_date}.csv"
    result_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"扫描完成：股票池 {len(codes)} 只，命中 {len(results)} 只，输出Top {min(top_n, len(results))} 只。CSV: {out_path}")
    return result_df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="分歧突破形态扫描：小盘股主力介入筛选")
    parser.add_argument("--max-price", type=float, default=18.0, help="最大价格，默认18")
    parser.add_argument("--max-mcap", type=float, default=70.0, help="最大市值(亿元)，默认70")
    parser.add_argument("--lookback", type=int, default=20, help="目标分歧日回溯天数，默认20")
    parser.add_argument("--vol-mult", type=float, default=3.0, help="成交量倍数阈值，默认3.0")
    parser.add_argument("--price-tol", type=float, default=0.10, help="收盘价偏差容忍度，默认0.10")
    parser.add_argument("--vol-tol", type=float, default=0.20, help="成交量偏差容忍度，默认0.20")
    parser.add_argument("--download", dest="is_download", type=int, default=0, help="是否强制重新下载，默认0")
    parser.add_argument("--limit", type=int, default=0, help="调试用，限制前N只股票，默认0为不限")
    parser.add_argument("--top", dest="top_n", type=int, default=50, help="输出Top N结果，默认50")

    args = parser.parse_args()
    scan_divergence_breakthrough(
        max_price=args.max_price,
        max_mcap=args.max_mcap,
        lookback_target=args.lookback,
        volume_multiplier=args.vol_mult,
        price_tolerance=args.price_tol,
        volume_tolerance=args.vol_tol,
        is_download=args.is_download,
        limit=args.limit,
        top_n=args.top_n
    )
