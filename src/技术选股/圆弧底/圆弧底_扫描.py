"""
圆弧底形态筛选策略
筛选条件：近10天内完成圆弧底形态突破的股票
基于核回归平滑识别形态，包含置信度评分
"""
import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.signal import argrelextrema

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


def kernel_regression(y: np.ndarray, bandwidth: float = 3.0) -> np.ndarray:
    """
    核回归平滑处理（高斯核）
    
    Args:
        y: 价格序列
        bandwidth: 带宽参数，控制平滑程度
        
    Returns:
        平滑后的价格序列
    """
    n = len(y)
    x = np.arange(n)
    smoothed = np.zeros(n)
    
    for i in range(n):
        # 高斯核权重
        weights = np.exp(-0.5 * ((x - i) / bandwidth) ** 2)
        weights /= weights.sum()
        smoothed[i] = np.sum(weights * y)
    
    return smoothed


def find_local_extrema(smooth_prices: np.ndarray, window: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    """
    从平滑价格序列中找到局部极值点
    
    Args:
        smooth_prices: 平滑后的价格序列
        window: 极值检测窗口大小
        
    Returns:
        (局部最小值索引数组, 局部最大值索引数组)
    """
    # 使用scipy的argrelextrema找局部极值
    local_min_idx = argrelextrema(smooth_prices, np.less, order=window)[0]
    local_max_idx = argrelextrema(smooth_prices, np.greater, order=window)[0]
    
    return local_min_idx, local_max_idx


def calculate_r_squared(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    计算R²拟合优度
    
    Args:
        actual: 实际值
        predicted: 预测值（理想圆弧）
        
    Returns:
        R²值
    """
    ss_res = np.sum((actual - predicted) ** 2)
    ss_tot = np.sum((actual - np.mean(actual)) ** 2)
    if ss_tot == 0:
        return 0.0
    return max(0.0, 1 - ss_res / ss_tot)


def generate_ideal_arc(n_points: int, start_price: float, bottom_price: float, end_price: float) -> np.ndarray:
    """
    生成理想圆弧曲线用于拟合度计算
    
    Args:
        n_points: 点数
        start_price: 起始价格
        bottom_price: 底部价格
        end_price: 结束价格
        
    Returns:
        理想圆弧价格序列
    """
    # 使用二次函数模拟圆弧底
    x = np.linspace(-1, 1, n_points)
    # 抛物线 y = a*x^2 + c，底部在x=0
    depth = min(start_price, end_price) - bottom_price
    avg_height = (start_price + end_price) / 2
    arc = bottom_price + depth * (x ** 2)
    # 调整两端高度
    arc = arc - arc[0] + start_price
    slope = (end_price - start_price) / (n_points - 1)
    arc = arc + slope * np.arange(n_points) - slope * np.arange(n_points)[0]
    
    return arc


def detect_rounding_bottom(
    df: pd.DataFrame, 
    lookback: int = 180, 
    min_duration: int = 10, 
    max_duration: int = 50,
    breakout_window: int = 20
) -> Dict:
    """
    检测单只股票是否存在圆弧底形态
    
    Args:
        df: DataFrame 包含 'close', 'volume', 'high', 'low' 列
        lookback: 回溯天数（用于核回归平滑）
        min_duration: 最小形态持续时间（半弦长d）
        max_duration: 最大形态持续时间
        breakout_window: 突破确认窗口（近N天内完成）
        
    Returns:
        dict: {
            'is_rounding_bottom': bool,
            'breakout_date': date or None,
            'neckline_price': float,
            'bottom_price': float,
            'bottom_date': date or None,
            'confidence_score': float
        }
    """
    result = {
        'is_rounding_bottom': False,
        'breakout_date': None,
        'neckline_price': None,
        'bottom_price': None,
        'bottom_date': None,
        'confidence_score': 0.0,
        'duration': 0,
        'left_days': 0,
        'right_days': 0
    }
    
    df = df.sort_values("date").reset_index(drop=True)
    
    if len(df) < lookback:
        return result
    
    # 取最近lookback天数据
    df_recent = df.tail(lookback).copy().reset_index(drop=True)
    close_prices = df_recent["close"].values
    volumes = df_recent["volume"].values
    dates = df_recent["date"].values
    
    # 计算200日均线（如果数据足够）
    if len(df) >= 200:
        ma200 = df["close"].rolling(200).mean().values[-len(df_recent):]
    else:
        ma200 = df["close"].rolling(len(df)).mean().values[-len(df_recent):]
    
    # 计算20日均量
    vol_ma20 = pd.Series(volumes).rolling(20, min_periods=1).mean().values
    
    # 核回归平滑
    smooth_prices = kernel_regression(close_prices, bandwidth=5.0)
    
    # 找局部极值点
    local_min_idx, local_max_idx = find_local_extrema(smooth_prices, window=5)
    
    if len(local_min_idx) == 0 or len(local_max_idx) == 0:
        return result
    
    best_score = 0.0
    best_result = result.copy()
    
    # 遍历每个局部最小值点（潜在底部）
    for bottom_idx in local_min_idx:
        # 底部必须在合理范围内（不能太靠近边界）
        if bottom_idx < min_duration or bottom_idx > len(close_prices) - min_duration:
            continue
        
        # 找底部左侧最近的局部最大值作为颈线参考
        left_maxes = local_max_idx[local_max_idx < bottom_idx]
        if len(left_maxes) == 0:
            continue
        
        left_max_idx = left_maxes[-1]  # 最近的左侧极大值
        half_chord = bottom_idx - left_max_idx  # 半弦长d
        
        if half_chord < min_duration or half_chord > max_duration:
            continue
        
        # 在左侧极大值点±20天范围内找真实高点作为颈线位
        search_start = max(0, left_max_idx - 20)
        search_end = min(len(close_prices), left_max_idx + 20)
        neckline_idx = search_start + np.argmax(close_prices[search_start:search_end])
        neckline_price = close_prices[neckline_idx]
        
        bottom_price = close_prices[bottom_idx]
        
        # 取底部前后各d天的价格序列
        left_start = max(0, bottom_idx - half_chord)
        right_end = min(len(close_prices), bottom_idx + half_chord + 1)
        
        left_prices = close_prices[left_start:bottom_idx]
        right_prices = close_prices[bottom_idx:right_end]
        
        if len(left_prices) < min_duration // 2 or len(right_prices) < min_duration // 2:
            continue
        
        # 计算收益率序列
        full_segment = close_prices[left_start:right_end]
        returns = np.abs(np.diff(full_segment) / full_segment[:-1])
        
        # ===== 圆弧底判定条件 =====
        
        # 1. 左侧下跌比例：下跌天数占比 >= 40%
        left_returns = np.diff(left_prices)
        left_down_ratio = np.sum(left_returns < 0) / len(left_returns) if len(left_returns) > 0 else 0
        if left_down_ratio < 0.4:
            continue
        
        # 2. 右侧上涨比例：上涨天数占比 >= 40%
        right_returns = np.diff(right_prices)
        right_up_ratio = np.sum(right_returns > 0) / len(right_returns) if len(right_returns) > 0 else 0
        if right_up_ratio < 0.4:
            continue
        
        # 3. 波动率约束：收益率绝对值标准差 <= 0.03
        returns_std = np.std(returns)
        if returns_std > 0.03:
            continue
        
        # 4. 对称性要求：左侧跌幅与右侧涨幅比值在0.6-1.5之间
        left_drop = (left_prices[0] - bottom_price) / left_prices[0] if left_prices[0] > 0 else 0
        right_rise = (right_prices[-1] - bottom_price) / bottom_price if bottom_price > 0 else 0
        
        if left_drop <= 0 or right_rise <= 0:
            continue
        
        symmetry_ratio = left_drop / right_rise
        if symmetry_ratio < 0.6 or symmetry_ratio > 1.5:
            continue
        
        # ===== 排除条件 =====
        
        # 形态最低价 <= 200日均线的90%
        if not np.isnan(ma200[bottom_idx]) and bottom_price <= ma200[bottom_idx] * 0.9:
            continue
        
        # 形态期间最大回撤 >= 25%
        max_price_in_pattern = np.max(full_segment)
        min_price_in_pattern = np.min(full_segment)
        max_drawdown = (max_price_in_pattern - min_price_in_pattern) / max_price_in_pattern
        if max_drawdown >= 0.25:
            continue
        
        # ===== 突破确认 =====
        
        # 在底部右侧d天范围内，检查是否有突破
        breakout_found = False
        breakout_date = None
        breakout_vol_ratio = 0.0
        days_after_breakout = 0
        
        for i in range(bottom_idx + 1, min(len(close_prices), bottom_idx + half_chord + 1)):
            # 突破条件：收盘价 >= 颈线位 且 站稳200日均线
            if close_prices[i] >= neckline_price:
                if np.isnan(ma200[i]) or close_prices[i] >= ma200[i]:
                    # 成交量确认：突破当日成交量 >= 前20日均量 × 1.5
                    if volumes[i] >= vol_ma20[i] * 1.5:
                        # 时间窗口：突破日在最近breakout_window个交易日内
                        days_from_end = len(close_prices) - 1 - i
                        if days_from_end <= breakout_window:
                            breakout_found = True
                            breakout_date = dates[i]
                            breakout_vol_ratio = volumes[i] / vol_ma20[i] if vol_ma20[i] > 0 else 1.5
                            days_after_breakout = len(close_prices) - 1 - i
                            break
        
        if not breakout_found:
            continue
        
        # ===== 计算置信度评分 =====
        
        # 1. 形态完美度 (0.25): 核回归曲线与标准圆弧的拟合优度R²
        ideal_arc = generate_ideal_arc(len(full_segment), full_segment[0], bottom_price, full_segment[-1])
        r_squared = calculate_r_squared(smooth_prices[left_start:right_end], ideal_arc)
        shape_score = min(1.0, r_squared) * 0.25
        
        # 2. 时间对称性 (0.20): 左半弧天数/右半弧天数，越接近1越高分
        left_days = bottom_idx - left_start
        right_days = right_end - bottom_idx - 1
        time_ratio = min(left_days, right_days) / max(left_days, right_days) if max(left_days, right_days) > 0 else 0
        time_score = time_ratio * 0.20
        
        # 3. 价格对称性 (0.20): 左侧跌幅与右侧涨幅比值，0.8-1.2为满分
        if 0.8 <= symmetry_ratio <= 1.2:
            price_score = 0.20
        elif 0.6 <= symmetry_ratio < 0.8 or 1.2 < symmetry_ratio <= 1.5:
            price_score = 0.10
        else:
            price_score = 0.0
        
        # 4. 成交量配合 (0.20): 突破量/均量倍数，1.5-3.0为满分
        if 1.5 <= breakout_vol_ratio <= 3.0:
            vol_score = 0.20
        elif breakout_vol_ratio > 3.0:
            vol_score = 0.15  # 放量过大扣分
        else:
            vol_score = (breakout_vol_ratio / 1.5) * 0.20
        
        # 5. 突破有效性 (0.15): 突破后站稳天数，>=3天为满分
        if days_after_breakout >= 3:
            breakout_score = 0.15
        else:
            breakout_score = (days_after_breakout / 3) * 0.15
        
        confidence_score = shape_score + time_score + price_score + vol_score + breakout_score
        
        # 更新最佳结果
        if confidence_score > best_score:
            best_score = confidence_score
            best_result = {
                'is_rounding_bottom': True,
                'breakout_date': breakout_date,
                'neckline_price': round(neckline_price, 2),
                'bottom_price': round(bottom_price, 2),
                'bottom_date': dates[bottom_idx],
                'confidence_score': round(confidence_score, 3),
                'duration': half_chord * 2,
                'left_days': left_days,
                'right_days': right_days,
                'symmetry_ratio': round(symmetry_ratio, 2),
                'vol_ratio': round(breakout_vol_ratio, 2),
                'r_squared': round(r_squared, 3)
            }
    
    return best_result


def scan_rounding_bottom(
    max_price: float = 50.0,
    max_mcap: float = 500.0,
    lookback: int = 180,
    min_duration: int = 10,
    max_duration: int = 50,
    breakout_window: int = 10,
    is_download: int = 0,
    limit: int = 0,
    top_n: int = 20
) -> pd.DataFrame:
    """
    扫描"圆弧底"形态：近10天内完成圆弧底突破的股票
    
    Args:
        max_price: 最大价格
        max_mcap: 最大市值(亿元)
        lookback: 回溯天数（用于核回归平滑）
        min_duration: 最小形态持续时间
        max_duration: 最大形态持续时间
        breakout_window: 突破确认窗口（近N天内完成）
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
            
            required_cols = ["close", "volume", "high", "low", "open"]
            if not all(col in df.columns for col in required_cols):
                continue
            
            detection = detect_rounding_bottom(
                df, 
                lookback=lookback,
                min_duration=min_duration,
                max_duration=max_duration,
                breakout_window=breakout_window
            )
            
            if detection['is_rounding_bottom']:
                # 获取股票基本信息
                stock_info = universe[universe["code"] == code]
                market_cap = stock_info["market_cap"].values[0] if len(stock_info) > 0 else np.nan
                last_price = stock_info["last_price"].values[0] if len(stock_info) > 0 else np.nan
                
                results.append({
                    "code": code,
                    "breakout_date": detection['breakout_date'],
                    "bottom_date": detection['bottom_date'],
                    "neckline_price": detection['neckline_price'],
                    "bottom_price": detection['bottom_price'],
                    "confidence_score": detection['confidence_score'],
                    "duration": detection['duration'],
                    "left_days": detection['left_days'],
                    "right_days": detection['right_days'],
                    "symmetry_ratio": detection.get('symmetry_ratio', 0),
                    "vol_ratio": detection.get('vol_ratio', 0),
                    "r_squared": detection.get('r_squared', 0),
                    "last_price": last_price,
                    "market_cap": market_cap
                })
                
        except Exception as e:
            continue

    result_df = pd.DataFrame(results)
    
    # 按置信度排序，取Top N
    if not result_df.empty:
        result_df = result_df.sort_values("confidence_score", ascending=False).head(top_n)
    
    # 保存CSV
    out_dir = Path(__file__).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"圆弧底_{end_date}.csv"
    result_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"扫描完成：股票池 {len(codes)} 只，命中 {len(results)} 只，输出Top {min(top_n, len(results))} 只。CSV: {out_path}")
    return result_df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="圆弧底形态扫描：近10天内完成圆弧底突破的股票")
    parser.add_argument("--max-price", type=float, default=50.0, help="最大价格，默认50")
    parser.add_argument("--max-mcap", type=float, default=500.0, help="最大市值(亿元)，默认500")
    parser.add_argument("--lookback", type=int, default=180, help="回溯天数，默认180")
    parser.add_argument("--min-duration", type=int, default=10, help="最小形态持续时间，默认10")
    parser.add_argument("--max-duration", type=int, default=50, help="最大形态持续时间，默认50")
    parser.add_argument("--breakout-window", type=int, default=10, help="突破确认窗口（近N天），默认10")
    parser.add_argument("--download", dest="is_download", type=int, default=0, help="是否强制重新下载，默认0")
    parser.add_argument("--limit", type=int, default=0, help="调试用，限制前N只股票，默认0为不限")
    parser.add_argument("--top", dest="top_n", type=int, default=20, help="输出Top N结果，默认20")

    args = parser.parse_args()
    scan_rounding_bottom(
        max_price=args.max_price,
        max_mcap=args.max_mcap,
        lookback=args.lookback,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        breakout_window=args.breakout_window,
        is_download=args.is_download,
        limit=args.limit,
        top_n=args.top_n
    )
