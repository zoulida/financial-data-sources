#!/usr/bin/env python3
"""
网格策略交易图表绘制工具
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def plot_trading_charts(symbol="162411SZ", date=None):
    """绘制交易图表"""
    
    # 交易记录文件路径
    base_dir = "d:/pythonProject/数据源/src/网格/网格信号实盘/trading_records"
    symbol_dir = f"{base_dir}/{symbol}"
    
    # 如果没有指定日期，自动查找最新的交易日期
    if date is None:
        if not os.path.exists(symbol_dir):
            print(f"找不到交易记录目录: {symbol_dir}")
            return
        
        # 获取所有日期目录，按日期排序
        date_dirs = [d for d in os.listdir(symbol_dir) if os.path.isdir(os.path.join(symbol_dir, d))]
        date_dirs.sort(reverse=True)  # 最新的在前
        
        if not date_dirs:
            print(f"找不到任何交易记录日期目录: {symbol_dir}")
            return
        
        date = date_dirs[0]  # 使用最新的日期
        print(f"自动选择最新日期: {date}")
    
    trades_file = f"{base_dir}/{symbol}/{date}/trades.csv"
    pairs_file = f"{base_dir}/{symbol}/{date}/pairs.csv"
    positions_file = f"{base_dir}/{symbol}/{date}/positions.csv"
    pnl_file = f"{base_dir}/{symbol}/{date}/pnl.csv"
    
    if not os.path.exists(trades_file):
        print(f"找不到交易记录文件: {trades_file}")
        return
    
    # 读取数据
    print("读取交易数据...")
    trades_df = pd.read_csv(trades_file)
    pairs_df = pd.read_csv(pairs_file) if os.path.exists(pairs_file) else pd.DataFrame()
    positions_df = pd.read_csv(positions_file) if os.path.exists(positions_file) else pd.DataFrame()
    
    # 解析时间 - 修复日期格式问题
    trades_df['datetime'] = pd.to_datetime(trades_df['ts'])
    
    # 提取日期用于标题
    actual_date = trades_df['datetime'].dt.date.iloc[0].strftime('%Y%m%d')
    print(f"实际交易日期: {actual_date}")
    
    # 生成分时线数据（每分钟一个价格点），过滤掉休市时间
    print("生成分时线数据...")
    trades_df['minute'] = trades_df['datetime'].dt.floor('1Min')
    
    # 过滤掉休市时间（11:30-13:00）
    def is_trading_time(dt):
        time = dt.time()
        # 上午：09:30-11:30
        morning_start = datetime.strptime('09:30', '%H:%M').time()
        morning_end = datetime.strptime('11:30', '%H:%M').time()
        # 下午：13:00-15:00
        afternoon_start = datetime.strptime('13:00', '%H:%M').time()
        afternoon_end = datetime.strptime('15:00', '%H:%M').time()
        
        return (morning_start <= time <= morning_end) or (afternoon_start <= time <= afternoon_end)
    
    # 过滤交易数据
    trading_trades = trades_df[trades_df['datetime'].apply(is_trading_time)]
    print(f"过滤后交易数量: {len(trading_trades)} / {len(trades_df)}")
    
    # 按分钟分组，但保持时间顺序
    minute_data = trading_trades.groupby('minute').agg({
        'price': 'first',  # 取该分钟第一个价格作为开盘价
        'qty': 'sum'      # 累计交易量
    }).reset_index()
    
    # 按时间排序
    minute_data = minute_data.sort_values('minute')
    
    # 检测并分割上午和下午的数据，避免跨休市时间连线
    morning_data = minute_data[minute_data['minute'].dt.time < datetime.strptime('11:30', '%H:%M').time()]
    afternoon_data = minute_data[minute_data['minute'].dt.time >= datetime.strptime('13:00', '%H:%M').time()]
    
    print(f"上午数据点: {len(morning_data)}, 下午数据点: {len(afternoon_data)}")
    
    # 创建图表
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle(f'网格策略分时图 - {symbol} ({actual_date})', fontsize=16, fontweight='bold')
    
    # 1. 分时线图 + 交易点
    ax1 = axes[0]
    
    # 绘制分时线 - 分别绘制上午和下午，时间轴不显示11:30-13:00
    if not morning_data.empty and not afternoon_data.empty:
        # 分别绘制上午和下午，时间轴自动跳过11:30-13:00
        ax1.plot(morning_data['minute'], morning_data['price'], 
                'b-', linewidth=2, alpha=0.8, label='上午分时线')
        ax1.fill_between(morning_data['minute'], morning_data['price'], 
                         alpha=0.1, color='blue')
        
        ax1.plot(afternoon_data['minute'], afternoon_data['price'], 
                'b-', linewidth=2, alpha=0.8, label='下午分时线')
        ax1.fill_between(afternoon_data['minute'], afternoon_data['price'], 
                         alpha=0.1, color='blue')
    
    elif not morning_data.empty:
        # 只有上午数据
        ax1.plot(morning_data['minute'], morning_data['price'], 
                'b-', linewidth=2, alpha=0.8, label='上午分时线')
        ax1.fill_between(morning_data['minute'], morning_data['price'], 
                         alpha=0.1, color='blue')
    
    elif not afternoon_data.empty:
        # 只有下午数据
        ax1.plot(afternoon_data['minute'], afternoon_data['price'], 
                'b-', linewidth=2, alpha=0.8, label='下午分时线')
        ax1.fill_between(afternoon_data['minute'], afternoon_data['price'], 
                         alpha=0.1, color='blue')
    
    # 标记买入点 - 更大的标记，过滤休市时间
    buy_trades = trading_trades[trading_trades['side'] == 'BUY']
    if not buy_trades.empty:
        ax1.scatter(buy_trades['datetime'], buy_trades['price'], 
                   color='red', marker='^', s=100, alpha=0.9, 
                   label=f'买入 ({len(buy_trades)}笔)', zorder=5, 
                   edgecolors='darkred', linewidths=1)
        
        # 为买入点添加价格标签（每10个显示一个）
        for i, (_, trade) in enumerate(buy_trades.iterrows()):
            if i % 10 == 0:  # 每10个显示一个标签
                ax1.annotate(f'{trade["price"]:.3f}', 
                           (trade['datetime'], trade['price']),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, color='red',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    # 标记卖出点 - 更大的标记，过滤休市时间
    sell_trades = trading_trades[trading_trades['side'] == 'SELL']
    if not sell_trades.empty:
        ax1.scatter(sell_trades['datetime'], sell_trades['price'], 
                   color='green', marker='v', s=100, alpha=0.9, 
                   label=f'卖出 ({len(sell_trades)}笔)', zorder=5,
                   edgecolors='darkgreen', linewidths=1)
        
        # 为卖出点添加价格标签（每10个显示一个）
        for i, (_, trade) in enumerate(sell_trades.iterrows()):
            if i % 10 == 0:  # 每10个显示一个标签
                ax1.annotate(f'{trade["price"]:.3f}', 
                           (trade['datetime'], trade['price']),
                           xytext=(5, -15), textcoords='offset points',
                           fontsize=8, color='green',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    # 添加午休分隔线
    if not minute_data.empty:
        # 在11:30和13:00添加垂直分隔线
        morning_end = minute_data['minute'].min().replace(hour=11, minute=30)
        afternoon_start = minute_data['minute'].min().replace(hour=13, minute=0)
        
        # 检查时间是否在数据范围内
        time_min = minute_data['minute'].min()
        time_max = minute_data['minute'].max()
        
        if time_min <= morning_end <= time_max:
            ax1.axvline(morning_end, color='red', linestyle='--', alpha=0.7, linewidth=2, label='午休开始')
        
        if time_min <= afternoon_start <= time_max:
            ax1.axvline(afternoon_start, color='green', linestyle='--', alpha=0.7, linewidth=2, label='午休结束')
    
    # 添加网格线
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # 设置标题和标签
    ax1.set_title('分时价格线与交易点', fontsize=14, fontweight='bold')
    ax1.set_ylabel('价格 (元)', fontsize=12)
    ax1.legend(loc='upper left', fontsize=10)
    
    # 设置y轴范围，确保价格变化清晰可见
    price_min = trading_trades['price'].min()
    price_max = trading_trades['price'].max()
    price_range = price_max - price_min
    
    # 如果价格范围太小，扩展显示范围
    if price_range < 0.01:  # 如果价格范围小于1分钱
        price_padding = max(0.003, price_range * 0.3)  # 至少3厘的padding
        ax1.set_ylim(price_min - price_padding, price_max + price_padding)
        
        # 设置y轴刻度格式，显示3位小数
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.3f}'))
        
        # 设置合适的刻度间隔
        if price_range < 0.003:  # 如果范围小于3厘
            ax1.yaxis.set_major_locator(plt.MultipleLocator(0.001))  # 每1厘一个刻度
        elif price_range < 0.006:  # 如果范围小于6厘
            ax1.yaxis.set_major_locator(plt.MultipleLocator(0.002))  # 每2厘一个刻度
        else:
            ax1.yaxis.set_major_locator(plt.MultipleLocator(0.003))  # 每3厘一个刻度
    else:
        # 价格范围较大时的正常处理
        price_padding = price_range * 0.1
        ax1.set_ylim(price_min - price_padding, price_max + price_padding)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.3f}'))
    
    print(f"价格范围: {price_min:.3f} - {price_max:.3f} (差值: {price_range:.3f})")
    
    # 格式化x轴时间 - 修复时间轴显示
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax1.xaxis.set_minor_locator(mdates.MinuteLocator(interval=15))  # 每15分钟一个小刻度
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # 设置x轴范围，确保显示完整的时间段
    if not minute_data.empty:
        time_min = minute_data['minute'].min()
        time_max = minute_data['minute'].max()
        # 扩展时间范围，让图表更美观
        time_min = time_min - pd.Timedelta(minutes=10)
        time_max = time_max + pd.Timedelta(minutes=10)
        ax1.set_xlim(time_min, time_max)
        
        # 设置日期格式器，确保只显示时间部分
        ax1.xaxis_date = ax1.xaxis.get_major_formatter()
        print(f"时间范围: {time_min.strftime('%H:%M')} - {time_max.strftime('%H:%M')}")
    
    # 添加价格统计信息
    price_avg = trading_trades['price'].mean()
    stats_text = f'最高价: {price_max:.3f}\n最低价: {price_min:.3f}\n平均价: {price_avg:.3f}\n波动: {price_range:.3f}'
    ax1.text(0.98, 0.02, stats_text, transform=ax1.transAxes, 
            verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8), fontsize=9)
    
    # 2. 交易量柱状图
    ax2 = axes[1]
    
    # 按分钟统计交易量 - 修复时间轴问题，过滤休市时间
    volume_by_minute = trading_trades.groupby(['minute', 'side'])['qty'].sum().unstack(fill_value=0)
    
    # 分割上午和下午的交易量数据
    morning_volume = volume_by_minute[volume_by_minute.index.time < datetime.strptime('11:30', '%H:%M').time()]
    afternoon_volume = volume_by_minute[volume_by_minute.index.time >= datetime.strptime('13:00', '%H:%M').time()]
    
    # 确保所有时间点都有索引
    full_time_range = None
    if not minute_data.empty:
        full_time_range = pd.date_range(
            start=minute_data['minute'].min(),
            end=minute_data['minute'].max(),
            freq='1Min'
        )
        volume_by_minute = volume_by_minute.reindex(full_time_range, fill_value=0)
    
    # 绘制交易量柱状图 - 分别绘制上午和下午，时间轴不显示11:30-13:00
    if not morning_volume.empty:
        # 绘制上午交易量
        if 'BUY' in morning_volume.columns:
            buy_mask = morning_volume['BUY'] > 0
            if buy_mask.any():
                ax2.bar(morning_volume.index[buy_mask], morning_volume['BUY'][buy_mask], 
                       width=0.0008, color='red', alpha=0.6, label='上午买入量')
        if 'SELL' in morning_volume.columns:
            sell_mask = morning_volume['SELL'] > 0
            if sell_mask.any():
                ax2.bar(morning_volume.index[sell_mask], morning_volume['SELL'][sell_mask], 
                       width=0.0008, color='green', alpha=0.6, label='上午卖出量')
    
    if not afternoon_volume.empty:
        # 绘制下午交易量
        if 'BUY' in afternoon_volume.columns:
            buy_mask = afternoon_volume['BUY'] > 0
            if buy_mask.any():
                ax2.bar(afternoon_volume.index[buy_mask], afternoon_volume['BUY'][buy_mask], 
                       width=0.0008, color='red', alpha=0.6, label='下午买入量')
        if 'SELL' in afternoon_volume.columns:
            sell_mask = afternoon_volume['SELL'] > 0
            if sell_mask.any():
                ax2.bar(afternoon_volume.index[sell_mask], afternoon_volume['SELL'][sell_mask], 
                       width=0.0008, color='green', alpha=0.6, label='下午卖出量')
    
    ax2.set_title('分时交易量分布', fontsize=14, fontweight='bold')
    ax2.set_ylabel('交易量 (股)', fontsize=12)
    ax2.set_xlabel('时间', fontsize=12)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    # 在交易量图上也添加午休分隔线
    if not minute_data.empty:
        morning_end = minute_data['minute'].min().replace(hour=11, minute=30)
        afternoon_start = minute_data['minute'].min().replace(hour=13, minute=0)
        
        time_min = minute_data['minute'].min()
        time_max = minute_data['minute'].max()
        
        if time_min <= morning_end <= time_max:
            ax2.axvline(morning_end, color='red', linestyle='--', alpha=0.7, linewidth=2)
        
        if time_min <= afternoon_start <= time_max:
            ax2.axvline(afternoon_start, color='green', linestyle='--', alpha=0.7, linewidth=2)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax2.xaxis.set_minor_locator(mdates.MinuteLocator(interval=15))  # 每15分钟一个小刻度
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # 设置x轴范围，与价格图保持一致
    if not minute_data.empty:
        time_min = minute_data['minute'].min()
        time_max = minute_data['minute'].max()
        time_min = time_min - pd.Timedelta(minutes=10)
        time_max = time_max + pd.Timedelta(minutes=10)
        ax2.set_xlim(time_min, time_max)
    
    # 添加交易量统计
    total_buy_volume = trading_trades[trading_trades['side'] == 'BUY']['qty'].sum()
    total_sell_volume = trading_trades[trading_trades['side'] == 'SELL']['qty'].sum()
    
    volume_stats = f'总买入量: {total_buy_volume:,}\n总卖出量: {total_sell_volume:,}'
    ax2.text(0.98, 0.98, volume_stats, transform=ax2.transAxes, 
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8), fontsize=9)
    
    plt.tight_layout()
    
    # 保存图表
    chart_file = f"{base_dir}/{symbol}/{date}/intraday_chart.png"
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    print(f"分时图表已保存: {chart_file}")
    
    # 显示图表
    plt.show()
    
    # 输出统计信息
    print("\n=== 交易统计 ===")
    print(f"总交易笔数: {len(trading_trades)} (原始: {len(trades_df)})")
    print(f"买入交易: {len(buy_trades)} 笔")
    print(f"卖出交易: {len(sell_trades)} 笔")
    print(f"价格区间: {price_min:.3f} - {price_max:.3f} 元")
    print(f"平均价格: {price_avg:.3f} 元")
    
    if not pairs_df.empty:
        print(f"配对交易: {len(pairs_df)} 笔")
        print(f"总盈亏: {pairs_df['pnl'].sum():.2f} 元")
        print(f"平均每笔盈亏: {pairs_df['pnl'].mean():.4f} 元")
    
    if not positions_df.empty:
        current_positions = positions_df[positions_df['qty'] > 0]
        if not current_positions.empty:
            print(f"当前持仓: {len(current_positions)} 层")
            total_position_value = (current_positions['qty'] * current_positions['level_px']).sum()
            print(f"持仓总价值: {total_position_value:.2f} 元")

def plot_grid_levels(symbol="162411SZ", date=None):
    """绘制网格层级图"""
    
    base_dir = "d:/pythonProject/数据源/src/网格/网格信号实盘/trading_records"
    symbol_dir = f"{base_dir}/{symbol}"
    
    # 如果没有指定日期，自动查找最新的交易日期
    if date is None:
        if not os.path.exists(symbol_dir):
            print(f"找不到交易记录目录: {symbol_dir}")
            return
        
        # 获取所有日期目录，按日期排序
        date_dirs = [d for d in os.listdir(symbol_dir) if os.path.isdir(os.path.join(symbol_dir, d))]
        date_dirs.sort(reverse=True)  # 最新的在前
        
        if not date_dirs:
            print(f"找不到任何交易记录日期目录: {symbol_dir}")
            return
        
        date = date_dirs[0]  # 使用最新的日期
    
    positions_file = f"{base_dir}/{symbol}/{date}/positions.csv"
    
    if not os.path.exists(positions_file):
        print(f"找不到持仓文件: {positions_file}")
        return
    
    positions_df = pd.read_csv(positions_file)
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 绘制网格层级
    for i, row in positions_df.iterrows():
        level = row['level_idx']
        price = row['level_px']
        qty = row['qty']
        
        if qty > 0:
            # 有持仓的层级用红色
            ax.barh(level, qty, height=0.8, color='red', alpha=0.7)
            ax.text(qty + 5, level, f'{price:.3f}', va='center', fontsize=9)
        else:
            # 无持仓的层级用灰色
            ax.barh(level, 1, height=0.8, color='lightgray', alpha=0.3)
            ax.text(5, level, f'{price:.3f}', va='center', fontsize=8, color='gray')
    
    ax.set_title(f'网格层级分布 - {symbol} ({date})', fontsize=14, fontweight='bold')
    ax.set_xlabel('持仓数量 (股)', fontsize=12)
    ax.set_ylabel('网格层级', fontsize=12)
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    
    # 保存图表
    chart_file = f"{base_dir}/{symbol}/{date}/grid_levels.png"
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    print(f"网格层级图已保存: {chart_file}")
    
    plt.show()

if __name__ == "__main__":
    # 绘制交易图表
    plot_trading_charts()
    
    # 绘制网格层级图
    plot_grid_levels()
