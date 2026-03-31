"""
圆弧底形态可视化模块
绘制K线图并标注：颈线位、底部区域、突破点、200日均线
"""
import sys
from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import warnings

warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 路径设置
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "md" / "获取enddate") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "md" / "获取enddate"))

from 圆弧底_扫描 import fetch_day_k, detect_rounding_bottom, kernel_regression
from md.获取enddate.get_date_range import get_date_range

try:
    from xtquant import xtdata
    _xt_ok = True
except Exception:
    xtdata = None
    _xt_ok = False


def get_stock_name(code: str) -> str:
    """
    获取股票名称
    
    Args:
        code: 股票代码
        
    Returns:
        股票名称，获取失败返回空字符串
    """
    if not _xt_ok or xtdata is None:
        return ""
    try:
        info = xtdata.get_instrument_detail(code)
        if isinstance(info, dict):
            return info.get('InstrumentName', '') or info.get('name', '')
    except Exception:
        pass
    return ""


def plot_rounding_bottom(
    code: str,
    detection_result: Optional[Dict] = None,
    lookback: int = 180,
    display_days: int = 120,
    save_path: Optional[str] = None,
    show: bool = True
) -> Optional[plt.Figure]:
    """
    绘制单只股票的圆弧底K线图
    
    Args:
        code: 股票代码
        detection_result: 检测结果字典（可选，若不提供则重新检测）
        lookback: 回溯天数
        display_days: 显示天数
        save_path: 保存路径（可选）
        show: 是否显示图表
        
    Returns:
        matplotlib Figure对象
    """
    # 获取K线数据
    start_date, end_date, _ = get_date_range()
    df = fetch_day_k(code, start_date, end_date, is_download=0, dividend_type="front")
    
    if df is None or df.empty:
        print(f"[错误] {code} 无法获取K线数据")
        return None
    
    df = df.sort_values("date").reset_index(drop=True)
    
    # 如果未提供检测结果，重新检测
    if detection_result is None:
        detection_result = detect_rounding_bottom(df, lookback=lookback)
    
    # 取最近display_days天数据用于显示
    df_display = df.tail(display_days).copy().reset_index(drop=True)
    
    # 计算200日均线
    df["ma200"] = df["close"].rolling(200, min_periods=1).mean()
    ma200_display = df["ma200"].tail(display_days).values
    
    # 计算核回归平滑曲线
    smooth_prices = kernel_regression(df_display["close"].values, bandwidth=5.0)
    
    # 准备绘图数据
    df_display["date_num"] = range(len(df_display))
    ohlc_data = df_display[["date_num", "open", "high", "low", "close"]].values
    
    # 获取股票名称
    stock_name = get_stock_name(code)
    title_text = f"{code} {stock_name} 圆弧底形态分析" if stock_name else f"{code} 圆弧底形态分析"
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                    gridspec_kw={'height_ratios': [3, 1]},
                                    sharex=True)
    fig.suptitle(title_text, fontsize=14, fontweight='bold')
    
    # ===== 上图：K线图 =====
    
    # 绘制K线（使用matplotlib原生方式）
    for i in range(len(df_display)):
        row = df_display.iloc[i]
        color = 'red' if row['close'] >= row['open'] else 'green'
        # 绘制影线
        ax1.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.8)
        # 绘制实体
        body_bottom = min(row['open'], row['close'])
        body_height = abs(row['close'] - row['open'])
        rect = Rectangle((i - 0.3, body_bottom), 0.6, body_height, 
                         facecolor=color, edgecolor=color, alpha=0.9)
        ax1.add_patch(rect)
    
    # 绘制200日均线
    ax1.plot(df_display["date_num"], ma200_display, 
             color='purple', linewidth=1.5, label='MA200', linestyle='--')
    
    # 绘制核回归平滑曲线
    ax1.plot(df_display["date_num"], smooth_prices, 
             color='blue', linewidth=1.2, label='核回归平滑', alpha=0.7)
    
    # 如果检测到圆弧底，标注关键点位
    if detection_result.get('is_rounding_bottom', False):
        neckline_price = detection_result['neckline_price']
        bottom_price = detection_result['bottom_price']
        bottom_date = detection_result['bottom_date']
        breakout_date = detection_result['breakout_date']
        duration = detection_result.get('duration', 30)
        
        # 找到底部和突破点在显示数据中的索引
        bottom_idx = None
        breakout_idx = None
        
        dates_list = df_display["date"].tolist()
        if bottom_date in dates_list:
            bottom_idx = dates_list.index(bottom_date)
        if breakout_date in dates_list:
            breakout_idx = dates_list.index(breakout_date)
        
        # 1. 绘制颈线位（水平虚线）
        ax1.axhline(y=neckline_price, color='orange', linestyle='--', 
                    linewidth=2, label=f'颈线位: {neckline_price:.2f}')
        
        # 2. 标注底部区域（矩形阴影）
        if bottom_idx is not None:
            left_idx = max(0, bottom_idx - duration // 2)
            right_idx = min(len(df_display) - 1, bottom_idx + duration // 2)
            
            # 底部区域的价格范围
            bottom_region_low = bottom_price * 0.98
            bottom_region_high = bottom_price * 1.02
            
            rect = Rectangle(
                (left_idx, bottom_region_low),
                right_idx - left_idx,
                bottom_region_high - bottom_region_low,
                facecolor='lightblue', alpha=0.3, edgecolor='blue',
                linewidth=1.5, linestyle='-', label='底部区域'
            )
            ax1.add_patch(rect)
            
            # 标注底部最低点
            ax1.scatter([bottom_idx], [bottom_price], 
                       color='blue', s=150, marker='^', zorder=5,
                       label=f'底部: {bottom_price:.2f}')
            ax1.annotate(f'底部\n{bottom_price:.2f}', 
                        xy=(bottom_idx, bottom_price),
                        xytext=(bottom_idx - 5, bottom_price * 0.95),
                        fontsize=9, color='blue',
                        arrowprops=dict(arrowstyle='->', color='blue', lw=1))
        
        # 3. 标注突破点
        if breakout_idx is not None:
            breakout_price = df_display.iloc[breakout_idx]["close"]
            ax1.scatter([breakout_idx], [breakout_price], 
                       color='red', s=200, marker='*', zorder=5,
                       label=f'突破点: {breakout_price:.2f}')
            ax1.annotate(f'突破!\n{breakout_price:.2f}', 
                        xy=(breakout_idx, breakout_price),
                        xytext=(breakout_idx + 3, breakout_price * 1.03),
                        fontsize=10, color='red', fontweight='bold',
                        arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
        
        # 添加置信度评分
        confidence = detection_result.get('confidence_score', 0)
        info_text = (f"置信度: {confidence:.3f}\n"
                    f"形态周期: {duration}天\n"
                    f"对称比: {detection_result.get('symmetry_ratio', 0):.2f}\n"
                    f"量比: {detection_result.get('vol_ratio', 0):.2f}x")
        ax1.text(0.02, 0.98, info_text, transform=ax1.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    else:
        ax1.text(0.5, 0.5, '未检测到圆弧底形态', transform=ax1.transAxes,
                fontsize=14, ha='center', va='center', color='gray')
    
    ax1.set_ylabel('价格', fontsize=11)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(-1, len(df_display))
    
    # ===== 下图：成交量 =====
    
    colors = ['red' if df_display.iloc[i]['close'] >= df_display.iloc[i]['open'] 
              else 'green' for i in range(len(df_display))]
    ax2.bar(df_display["date_num"], df_display["volume"] / 1e6, 
            color=colors, alpha=0.7, width=0.6)
    
    # 绘制20日均量线
    vol_ma20 = df_display["volume"].rolling(20, min_periods=1).mean() / 1e6
    ax2.plot(df_display["date_num"], vol_ma20, 
             color='orange', linewidth=1.5, label='20日均量')
    
    # 标注突破日成交量
    if detection_result.get('is_rounding_bottom', False) and breakout_idx is not None:
        breakout_vol = df_display.iloc[breakout_idx]["volume"] / 1e6
        ax2.scatter([breakout_idx], [breakout_vol], 
                   color='red', s=100, marker='*', zorder=5)
    
    ax2.set_ylabel('成交量(百万)', fontsize=11)
    ax2.set_xlabel('交易日', fontsize=11)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # 设置X轴日期标签
    n_ticks = min(10, len(df_display) // 10)
    tick_positions = np.linspace(0, len(df_display) - 1, n_ticks, dtype=int)
    ax2.set_xticks(tick_positions)
    ax2.set_xticklabels([df_display.iloc[i]["date"] for i in tick_positions], 
                        rotation=45, ha='right', fontsize=8)
    
    plt.tight_layout()
    
    # 保存图表
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存: {save_path}")
    
    if show:
        plt.show()
    
    return fig


def plot_batch_from_csv(
    csv_path: str,
    output_dir: Optional[str] = None,
    top_n: int = 10,
    show: bool = False
) -> None:
    """
    批量绘制CSV中的股票圆弧底图表
    
    Args:
        csv_path: CSV文件路径
        output_dir: 输出目录（默认与CSV同目录）
        top_n: 绘制前N只股票
        show: 是否显示图表
    """
    df_results = pd.read_csv(csv_path, encoding="utf-8-sig")
    
    if df_results.empty:
        print("CSV文件为空")
        return
    
    # 设置输出目录
    if output_dir is None:
        output_dir = Path(csv_path).parent / "charts"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 取前N只
    df_top = df_results.head(top_n)
    
    print(f"开始绘制 {len(df_top)} 只股票的圆弧底图表...")
    
    for idx, row in df_top.iterrows():
        code = row["code"]
        
        # 构建检测结果字典
        detection_result = {
            'is_rounding_bottom': True,
            'breakout_date': str(row.get("breakout_date", "")),
            'bottom_date': str(row.get("bottom_date", "")),
            'neckline_price': row.get("neckline_price", 0),
            'bottom_price': row.get("bottom_price", 0),
            'confidence_score': row.get("confidence_score", 0),
            'duration': row.get("duration", 30),
            'symmetry_ratio': row.get("symmetry_ratio", 0),
            'vol_ratio': row.get("vol_ratio", 0),
            'r_squared': row.get("r_squared", 0)
        }
        
        save_path = output_dir / f"{code}_圆弧底.png"
        
        try:
            plot_rounding_bottom(
                code=code,
                detection_result=detection_result,
                save_path=str(save_path),
                show=show
            )
            print(f"[{idx + 1}/{len(df_top)}] {code} 绘制完成")
        except Exception as e:
            print(f"[{idx + 1}/{len(df_top)}] {code} 绘制失败: {e}")
        
        plt.close('all')  # 释放内存
    
    print(f"\n绘制完成！图表保存在: {output_dir}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="圆弧底形态可视化")
    parser.add_argument("--code", type=str, help="单只股票代码")
    parser.add_argument("--csv", type=str, help="CSV文件路径（批量绘制）")
    parser.add_argument("--output", type=str, help="输出目录")
    parser.add_argument("--top", type=int, default=10, help="批量绘制前N只，默认10")
    parser.add_argument("--show", action="store_true", help="是否显示图表")
    
    args = parser.parse_args()
    
    if args.code:
        # 单只股票绘制
        out_dir = Path(__file__).parent / "charts"
        out_dir.mkdir(parents=True, exist_ok=True)
        save_path = out_dir / f"{args.code}_圆弧底.png"
        plot_rounding_bottom(code=args.code, save_path=str(save_path), show=args.show)
    elif args.csv:
        # 批量绘制
        plot_batch_from_csv(
            csv_path=args.csv,
            output_dir=args.output,
            top_n=args.top,
            show=args.show
        )
    else:
        # 默认：查找当前目录最新的CSV文件
        csv_files = list(Path(__file__).parent.glob("圆弧底_*.csv"))
        if csv_files:
            latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
            print(f"使用最新CSV: {latest_csv}")
            plot_batch_from_csv(
                csv_path=str(latest_csv),
                top_n=args.top,
                show=args.show
            )
        else:
            print("未找到CSV文件，请先运行 圆弧底_扫描.py 或指定 --code 参数")
