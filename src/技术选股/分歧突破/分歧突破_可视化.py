"""
分歧突破形态可视化程序
展示目标分歧日与历史分歧日的判断逻辑
"""
import sys
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，避免弹窗
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# 设置中文字体
from matplotlib.font_manager import FontProperties
import os

# Windows系统字体路径
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"  # 微软雅黑
if not os.path.exists(FONT_PATH):
    FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"  # 黑体
if not os.path.exists(FONT_PATH):
    FONT_PATH = r"C:\Windows\Fonts\simsun.ttc"  # 宋体

CHINESE_FONT = FontProperties(fname=FONT_PATH, size=10)
CHINESE_FONT_SMALL = FontProperties(fname=FONT_PATH, size=9)
CHINESE_FONT_TITLE = FontProperties(fname=FONT_PATH, size=14)

plt.rcParams['axes.unicode_minus'] = False

# 尝试导入xtquant获取股票名称
try:
    from xtquant import xtdata
    _xt_ok = True
except Exception:
    xtdata = None
    _xt_ok = False


def get_stock_name(code: str) -> str:
    """获取股票名称"""
    if not _xt_ok or xtdata is None:
        return ""
    try:
        info = xtdata.get_instrument_detail(code)
        if isinstance(info, dict):
            return info.get('InstrumentName', '') or info.get('name', '')
    except Exception:
        pass
    return ""


# 路径设置
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "md" / "获取enddate") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "md" / "获取enddate"))

# 导入 getDayDataWithTimeout
from source.实盘.xuntou.datadownload.合并下载数据 import getDayDataWithTimeout  # type: ignore
from md.获取enddate.get_date_range import get_date_range


def fetch_day_k(
    stock_code: str, 
    start_date: str, 
    end_date: str, 
    is_download: int = 0, 
    dividend_type: str = "front"
) -> Optional[pd.DataFrame]:
    """获取日K数据"""
    try:
        df = getDayDataWithTimeout(
            stock_code=stock_code, 
            start_date=start_date, 
            end_date=end_date, 
            is_download=is_download, 
            dividend_type=dividend_type
        )
        if df is not None and not df.empty:
            df["date"] = pd.to_datetime(df["date"].astype(str))
            return df
        return None
    except Exception as e:
        print(f"[错误] {stock_code} 获取数据异常: {e}")
        return None


def visualize_divergence(
    stock_code: str,
    lookback_target: int = 20,
    volume_multiplier: float = 3.0,
    price_tolerance: float = 0.10,
    volume_tolerance: float = 0.20,
    display_days: int = 120,
    save_path: Optional[str] = None
):
    """
    可视化分歧突破形态
    
    Args:
        stock_code: 股票代码
        lookback_target: 目标分歧日回溯天数
        volume_multiplier: 成交量倍数阈值
        price_tolerance: 收盘价偏差容忍度
        volume_tolerance: 成交量偏差容忍度
        display_days: 显示的天数
        save_path: 保存路径，None则显示
    """
    start_date, end_date, _ = get_date_range()
    
    df = fetch_day_k(stock_code, start_date, end_date, is_download=0, dividend_type="front")
    if df is None or df.empty:
        print(f"[错误] {stock_code} 无法获取数据")
        return
    
    df = df.sort_values("date").reset_index(drop=True)
    
    # 取最近display_days天用于显示
    if len(df) > display_days:
        df_display = df.tail(display_days).copy().reset_index(drop=True)
    else:
        df_display = df.copy()
    
    # 检测分歧日
    target_info = None
    history_info = None
    
    if len(df) >= lookback_target + 5:
        recent_df = df.tail(lookback_target).copy().reset_index(drop=True)
        
        for i in range(len(recent_df) - 1, 4, -1):
            target_idx_in_df = len(df) - len(recent_df) + i
            
            target_volume = df.iloc[target_idx_in_df]["volume"]
            target_close = df.iloc[target_idx_in_df]["close"]
            target_date = df.iloc[target_idx_in_df]["date"]
            
            prev_5_volumes = df.iloc[target_idx_in_df - 5:target_idx_in_df]["volume"].values
            
            if not all(target_volume > vol * volume_multiplier for vol in prev_5_volumes):
                continue
            
            target_info = {
                'date': target_date,
                'close': target_close,
                'volume': target_volume,
                'idx': target_idx_in_df
            }
            
            # 寻找历史分歧日
            for j in range(target_idx_in_df - 1, -1, -1):
                history_close = df.iloc[j]["close"]
                history_volume = df.iloc[j]["volume"]
                history_date = df.iloc[j]["date"]
                
                price_deviation = abs(history_close - target_close) / target_close
                volume_deviation = abs(history_volume - target_volume) / target_volume
                
                if price_deviation <= price_tolerance and volume_deviation <= volume_tolerance:
                    history_info = {
                        'date': history_date,
                        'close': history_close,
                        'volume': history_volume,
                        'idx': j,
                        'price_deviation': price_deviation * 100,
                        'volume_deviation': volume_deviation * 100
                    }
                    break
            
            if target_info:
                break
    
    # 创建图表
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [2, 1, 1]})
    stock_name = get_stock_name(stock_code)
    title = f'{stock_code} {stock_name} 分歧突破形态分析' if stock_name else f'{stock_code} 分歧突破形态分析'
    fig.suptitle(title, fontproperties=CHINESE_FONT_TITLE, fontweight='bold')
    
    dates = df_display["date"].values
    closes = df_display["close"].values
    volumes = df_display["volume"].values
    highs = df_display["high"].values
    lows = df_display["low"].values
    opens = df_display["open"].values
    
    # 使用索引作为x轴，避免节假日空白
    x_indices = np.arange(len(df_display))
    
    # 创建日期到索引的映射
    date_to_idx = {d: i for i, d in enumerate(dates)}
    
    # 设置x轴刻度标签（每隔一定间隔显示日期）
    tick_interval = max(1, len(x_indices) // 10)  # 大约显示10个刻度
    tick_positions = x_indices[::tick_interval]
    tick_labels = [pd.Timestamp(dates[i]).strftime('%m-%d') for i in tick_positions]
    
    # ===== 子图1: K线图 =====
    ax1 = axes[0]
    
    # 绘制K线
    for i in range(len(df_display)):
        color = 'red' if closes[i] >= opens[i] else 'green'
        # 实体
        ax1.bar(x_indices[i], abs(closes[i] - opens[i]), 
                bottom=min(opens[i], closes[i]), 
                color=color, width=0.8, edgecolor=color)
        # 上下影线
        ax1.plot([x_indices[i], x_indices[i]], [lows[i], highs[i]], color=color, linewidth=0.8)
    
    # 标记目标分歧日和历史分歧日
    if target_info:
        target_date = target_info['date']
        if target_date in date_to_idx:
            target_x = date_to_idx[target_date]
            ax1.axvline(x=target_x, color='blue', linestyle='--', linewidth=2, alpha=0.7)
            ax1.scatter([target_x], [target_info['close']], color='blue', s=200, zorder=5, marker='*')
            ax1.annotate(f"Target\nClose: {target_info['close']:.2f}", 
                        xy=(target_x, target_info['close']),
                        xytext=(10, 30), textcoords='offset points',
                        fontsize=9, color='blue',
                        arrowprops=dict(arrowstyle='->', color='blue', alpha=0.7))
    
    if history_info:
        history_date = history_info['date']
        if history_date in date_to_idx:
            history_x = date_to_idx[history_date]
            ax1.axvline(x=history_x, color='orange', linestyle='--', linewidth=2, alpha=0.7)
            ax1.scatter([history_x], [history_info['close']], color='orange', s=200, zorder=5, marker='*')
            ax1.annotate(f"History\nClose: {history_info['close']:.2f}", 
                        xy=(history_x, history_info['close']),
                        xytext=(10, -40), textcoords='offset points',
                        fontsize=9, color='orange',
                        arrowprops=dict(arrowstyle='->', color='orange', alpha=0.7))
    
    # 如果有两个分歧日，绘制价格容忍区间
    if target_info and history_info:
        target_date = target_info['date']
        history_date = history_info['date']
        if target_date in date_to_idx and history_date in date_to_idx:
            price_upper = target_info['close'] * (1 + price_tolerance)
            price_lower = target_info['close'] * (1 - price_tolerance)
            ax1.axhline(y=price_upper, color='gray', linestyle=':', alpha=0.5)
            ax1.axhline(y=price_lower, color='gray', linestyle=':', alpha=0.5)
            ax1.fill_between(x_indices, price_lower, price_upper, alpha=0.1, color='blue')
    
    ax1.set_ylabel('Price', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(tick_positions)
    ax1.set_xticklabels(tick_labels, rotation=45)
    
    # ===== 子图2: 成交量图 =====
    ax2 = axes[1]
    
    # 成交量柱状图
    colors = ['red' if closes[i] >= opens[i] else 'green' for i in range(len(df_display))]
    ax2.bar(x_indices, volumes, color=colors, width=0.8, alpha=0.7)
    
    # 标记目标分歧日和历史分歧日的成交量
    if target_info:
        target_date = target_info['date']
        if target_date in date_to_idx:
            target_x = date_to_idx[target_date]
            ax2.bar(target_x, volumes[target_x], color='blue', width=0.8, edgecolor='blue', linewidth=2)
            ax2.annotate(f"Target: {target_info['volume']/10000:.0f}W", 
                        xy=(target_x, target_info['volume']),
                        xytext=(10, 10), textcoords='offset points',
                        fontsize=9, color='blue')
    
    if history_info:
        history_date = history_info['date']
        if history_date in date_to_idx:
            history_x = date_to_idx[history_date]
            ax2.bar(history_x, volumes[history_x], color='orange', width=0.8, edgecolor='orange', linewidth=2)
            ax2.annotate(f"History: {history_info['volume']/10000:.0f}W", 
                        xy=(history_x, history_info['volume']),
                        xytext=(10, 10), textcoords='offset points',
                        fontsize=9, color='orange')
    
    # 成交量容忍区间
    if target_info:
        vol_upper = target_info['volume'] * (1 + volume_tolerance)
        vol_lower = target_info['volume'] * (1 - volume_tolerance)
        ax2.axhline(y=vol_upper, color='gray', linestyle=':', alpha=0.5)
        ax2.axhline(y=vol_lower, color='gray', linestyle=':', alpha=0.5)
        ax2.fill_between(x_indices, vol_lower, vol_upper, alpha=0.1, color='blue')
    
    ax2.set_ylabel('Volume', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(tick_positions)
    ax2.set_xticklabels(tick_labels, rotation=45)
    
    # ===== 子图3: 成交量倍数分析 =====
    ax3 = axes[2]
    
    # 计算每日成交量相对于前5日最大成交量的倍数
    # 前5天用0填充，保持与上面子图对齐
    vol_ratios = [0] * 5  # 前5天无数据
    for i in range(5, len(df_display)):
        prev_5_max = max(volumes[i-5:i])
        ratio = volumes[i] / prev_5_max if prev_5_max > 0 else 0
        vol_ratios.append(ratio)
    
    colors_ratio = ['blue' if r >= volume_multiplier else 'gray' for r in vol_ratios]
    ax3.bar(x_indices, vol_ratios, color=colors_ratio, width=0.8, alpha=0.7)
    ax3.axhline(y=volume_multiplier, color='red', linestyle='--', linewidth=2)
    
    # 标记目标分歧日
    if target_info:
        target_date = target_info['date']
        if target_date in date_to_idx:
            target_x = date_to_idx[target_date]
            if target_x >= 5:
                ax3.bar(target_x, vol_ratios[target_x], color='blue', width=0.8, 
                       edgecolor='darkblue', linewidth=2)
                ax3.annotate(f"Ratio: {vol_ratios[target_x]:.1f}x", 
                            xy=(target_x, vol_ratios[target_x]),
                            xytext=(10, 10), textcoords='offset points',
                            fontsize=9, color='blue')
    
    ax3.set_ylabel('Vol/Max5D', fontsize=10)
    ax3.set_xlabel('Date', fontsize=10)
    ax3.grid(True, alpha=0.3)
    ax3.set_xticks(tick_positions)
    ax3.set_xticklabels(tick_labels, rotation=45)
    ax3.set_xlim(ax1.get_xlim())  # 与子图1对齐
    
    # 添加信息文本框
    info_text = f"Parameters:\n"
    info_text += f"- Lookback: {lookback_target}D\n"
    info_text += f"- Vol Mult: {volume_multiplier}x\n"
    info_text += f"- Price Tol: +/-{price_tolerance*100:.0f}%\n"
    info_text += f"- Vol Tol: +/-{volume_tolerance*100:.0f}%\n"
    
    if target_info and history_info:
        info_text += f"\nResult:\n"
        info_text += f"- Target: {target_info['date'].strftime('%Y-%m-%d')}\n"
        info_text += f"- History: {history_info['date'].strftime('%Y-%m-%d')}\n"
        info_text += f"- Days: {target_info['idx'] - history_info['idx']}\n"
        info_text += f"- Price Dev: {history_info['price_deviation']:.1f}%\n"
        info_text += f"- Vol Dev: {history_info['volume_deviation']:.1f}%"
    elif target_info:
        info_text += f"\nResult:\n"
        info_text += f"- Target: {target_info['date'].strftime('%Y-%m-%d')}\n"
        info_text += f"- No matching history"
    else:
        info_text += f"\nResult:\n"
        info_text += f"- No target found"
    
    fig.text(0.02, 0.02, info_text, fontsize=9, verticalalignment='bottom',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.18)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存: {save_path}")
    else:
        plt.show()
    
    plt.close()


def batch_visualize(
    csv_path: Optional[str] = None,
    top_n: int = 10,
    save_dir: Optional[str] = None,
    show_last_only: bool = True
):
    """
    批量可视化CSV中的股票
    
    Args:
        csv_path: CSV文件路径，None则使用最新的扫描结果
        top_n: 可视化前N只股票
        save_dir: 保存目录，None则显示
        show_last_only: 只弹出最后一张图（前面的只保存不显示）
    """
    if csv_path is None:
        # 查找最新的扫描结果
        out_dir = Path(__file__).parent
        csv_files = list(out_dir.glob("分歧突破_*.csv"))
        if not csv_files:
            print("[错误] 未找到扫描结果CSV文件")
            return
        csv_path = str(max(csv_files, key=lambda x: x.stat().st_mtime))
    
    df = pd.read_csv(csv_path)
    if df.empty:
        print("[错误] CSV文件为空")
        return
    
    codes = df["code"].head(top_n).tolist()
    
    # 如果没有指定保存目录，创建默认目录
    if save_dir is None:
        save_dir = Path(__file__).parent / "charts"
    else:
        save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    
    import os
    last_save_path = None
    
    for i, code in enumerate(codes):
        print(f"正在可视化: {code} ({i+1}/{len(codes)})")
        save_path = str(save_dir / f"{code}_分歧突破.png")
        visualize_divergence(code, save_path=save_path)
        last_save_path = save_path
    
    # 打开最后一张图片
    if show_last_only and last_save_path and os.path.exists(last_save_path):
        print(f"\n打开最后一张图片: {last_save_path}")
        os.startfile(last_save_path)  # Windows系统用默认程序打开


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="分歧突破形态可视化")
    parser.add_argument("--code", type=str, default=None, help="单只股票代码")
    parser.add_argument("--csv", type=str, default=None, help="CSV文件路径")
    parser.add_argument("--top", type=int, default=50, help="批量可视化前N只")
    parser.add_argument("--save-dir", type=str, default=None, help="保存目录")
    parser.add_argument("--lookback", type=int, default=20, help="目标分歧日回溯天数")
    parser.add_argument("--vol-mult", type=float, default=3.0, help="成交量倍数阈值")
    parser.add_argument("--price-tol", type=float, default=0.10, help="收盘价偏差容忍度")
    parser.add_argument("--vol-tol", type=float, default=0.20, help="成交量偏差容忍度")
    parser.add_argument("--days", type=int, default=120, help="显示天数")

    args = parser.parse_args()
    
    if args.code:
        # 单只股票可视化
        save_path = None
        if args.save_dir:
            save_dir = Path(args.save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = str(save_dir / f"{args.code}_分歧突破.png")
        
        visualize_divergence(
            args.code,
            lookback_target=args.lookback,
            volume_multiplier=args.vol_mult,
            price_tolerance=args.price_tol,
            volume_tolerance=args.vol_tol,
            display_days=args.days,
            save_path=save_path
        )
    else:
        # 批量可视化
        batch_visualize(
            csv_path=args.csv,
            top_n=args.top,
            save_dir=args.save_dir
        )
