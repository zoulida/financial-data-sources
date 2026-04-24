"""
AKShare 开户数据获取示例代码

数据源: 中国结算 / 东方财富网
接口: stock_account_statistics_em()
更新频率: 月度（每月中旬公布上月数据）

作者: AI Assistant
日期: 2025-10-20
"""

import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta
import time

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False


# ============================================================================
# 1. 基础数据获取
# ============================================================================

def get_basic_data():
    """最简单的数据获取示例"""
    print("=" * 60)
    print("1. 基础数据获取")
    print("=" * 60)
    
    # 获取数据（一次性拉全部历史）
    df = ak.stock_account_statistics_em()
    
    # 查看基本信息
    print(f"\n数据行数: {len(df)}")
    print(f"数据列数: {len(df.columns)}")
    print(f"\n列名:\n{df.columns.tolist()}")
    
    # 查看最近 5 个月
    print(f"\n最近 5 个月数据:")
    print(df.tail())
    
    return df


def get_latest_data():
    """获取最新一条数据"""
    print("\n" + "=" * 60)
    print("2. 获取最新数据")
    print("=" * 60)
    
    df = ak.stock_account_statistics_em()
    
    # 排序并获取最新一行
    latest = df.sort_values('数据日期').iloc[-1]
    
    print(f"\n最新数据:")
    print(f"数据日期: {latest['数据日期']}")
    print(f"新增开户: {latest['新增投资者-数量']:.2f} 万户")
    print(f"期末总量: {latest['期末投资者-总量']:.2f} 万户")
    print(f"上证指数: {latest['上证指数-收盘']:.2f} 点")
    
    return latest


# ============================================================================
# 2. 数据处理与分析
# ============================================================================

def process_data_basic(df):
    """基础数据处理"""
    print("\n" + "=" * 60)
    print("3. 基础数据处理")
    print("=" * 60)
    
    # 复制数据避免修改原始数据
    df = df.copy()
    
    # 转换日期类型
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    
    # 排序
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 设置日期为索引
    df.set_index('数据日期', inplace=True)
    
    print("\n处理后的数据:")
    print(df.tail())
    print(f"\n数据类型:\n{df.dtypes}")
    
    return df


def calculate_derived_metrics(df):
    """计算衍生指标"""
    print("\n" + "=" * 60)
    print("4. 计算衍生指标")
    print("=" * 60)
    
    df = df.copy()
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 1. 增长率
    df['新增_环比'] = df['新增投资者-数量'].pct_change(1) * 100
    df['新增_同比'] = df['新增投资者-数量'].pct_change(12) * 100
    df['总量_同比'] = df['期末投资者-总量'].pct_change(12) * 100
    
    # 2. 移动平均
    df['新增_MA3'] = df['新增投资者-数量'].rolling(window=3).mean()
    df['新增_MA6'] = df['新增投资者-数量'].rolling(window=6).mean()
    df['新增_MA12'] = df['新增投资者-数量'].rolling(window=12).mean()
    
    # 3. 分位数
    df['新增_分位数'] = df['新增投资者-数量'].rank(pct=True)
    
    # 4. 指数变化
    df['指数_环比'] = df['上证指数-收盘'].pct_change(1) * 100
    df['指数_同比'] = df['上证指数-收盘'].pct_change(12) * 100
    
    # 5. 市场阶段判断
    conditions = [
        (df['新增_分位数'] >= 0.8),
        (df['新增_分位数'] >= 0.6),
        (df['新增_分位数'] >= 0.4),
        (df['新增_分位数'] >= 0.2)
    ]
    choices = ['过热', '活跃', '正常', '冷淡']
    df['市场阶段'] = np.select(conditions, choices, default='冰冷')
    
    # 显示结果
    print("\n最近 12 个月的衍生指标:")
    display_cols = ['数据日期', '新增投资者-数量', '新增_环比', '新增_同比', 
                   '新增_MA3', '新增_分位数', '市场阶段']
    print(df[display_cols].tail(12).to_string())
    
    return df


def statistical_analysis(df):
    """统计分析"""
    print("\n" + "=" * 60)
    print("5. 统计分析")
    print("=" * 60)
    
    df = df.copy()
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    
    # 新增开户数统计
    print("\n【新增开户数统计】")
    print(f"平均值: {df['新增投资者-数量'].mean():.2f} 万户")
    print(f"中位数: {df['新增投资者-数量'].median():.2f} 万户")
    print(f"最大值: {df['新增投资者-数量'].max():.2f} 万户")
    print(f"最小值: {df['新增投资者-数量'].min():.2f} 万户")
    print(f"标准差: {df['新增投资者-数量'].std():.2f} 万户")
    
    # 找出极值
    max_idx = df['新增投资者-数量'].idxmax()
    min_idx = df['新增投资者-数量'].idxmin()
    
    print(f"\n【开户最多月份】")
    print(f"日期: {df.loc[max_idx, '数据日期']}")
    print(f"新增: {df.loc[max_idx, '新增投资者-数量']:.2f} 万户")
    print(f"指数: {df.loc[max_idx, '上证指数-收盘']:.2f} 点")
    
    print(f"\n【开户最少月份】")
    print(f"日期: {df.loc[min_idx, '数据日期']}")
    print(f"新增: {df.loc[min_idx, '新增投资者-数量']:.2f} 万户")
    print(f"指数: {df.loc[min_idx, '上证指数-收盘']:.2f} 点")
    
    # 季节性分析
    df['月份'] = df['数据日期'].dt.month
    monthly_stats = df.groupby('月份')['新增投资者-数量'].agg(['mean', 'std', 'count'])
    monthly_stats.columns = ['平均值', '标准差', '样本数']
    
    print(f"\n【季节性分析 - 各月份平均开户数】")
    print(monthly_stats)


def correlation_analysis(df):
    """相关性分析"""
    print("\n" + "=" * 60)
    print("6. 相关性分析")
    print("=" * 60)
    
    df = df.copy()
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 当期相关性
    corr = df['新增投资者-数量'].corr(df['上证指数-收盘'])
    print(f"\n新增开户数与上证指数相关系数: {corr:.4f}")
    
    # 滞后相关性分析
    print(f"\n【滞后相关性分析】")
    print("正值表示开户数领先指数，负值表示开户数滞后指数")
    print("-" * 50)
    
    for lag in range(-6, 7):
        if lag == 0:
            continue
        corr = df['新增投资者-数量'].corr(df['上证指数-收盘'].shift(lag))
        direction = "开户领先" if lag > 0 else "开户滞后"
        print(f"{direction} {abs(lag):2d} 个月: {corr:7.4f}")


# ============================================================================
# 3. 高级功能
# ============================================================================

def get_data_with_cache(cache_dir='cache', cache_hours=24):
    """带缓存的数据获取"""
    print("\n" + "=" * 60)
    print("7. 带缓存的数据获取")
    print("=" * 60)
    
    cache_path = Path(cache_dir)
    cache_path.mkdir(exist_ok=True)
    cache_file = cache_path / 'account_data.parquet'
    
    # 检查缓存
    if cache_file.exists():
        cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age = datetime.now() - cache_time
        
        if age < timedelta(hours=cache_hours):
            print(f"\n✓ 使用缓存数据")
            print(f"  缓存时间: {cache_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  已缓存: {age.total_seconds() / 3600:.1f} 小时")
            df = pd.read_parquet(cache_file)
            print(f"  数据行数: {len(df)}")
            return df
    
    # 获取新数据
    print(f"\n→ 从 AKShare 获取新数据...")
    df = ak.stock_account_statistics_em()
    
    # 预处理
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 保存缓存
    df.to_parquet(cache_file, index=False)
    print(f"✓ 数据已缓存到: {cache_file}")
    print(f"  数据行数: {len(df)}")
    
    return df


def get_data_safe(max_retries=3, retry_delay=5):
    """安全的数据获取（带重试）"""
    print("\n" + "=" * 60)
    print("8. 安全数据获取（带重试）")
    print("=" * 60)
    
    for attempt in range(max_retries):
        try:
            print(f"\n尝试 {attempt + 1}/{max_retries}...")
            df = ak.stock_account_statistics_em()
            
            # 数据验证
            if df is None or len(df) == 0:
                raise ValueError("返回数据为空")
            
            required_cols = ['数据日期', '新增投资者-数量', '期末投资者-总量', '上证指数-收盘']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"缺少必要字段: {missing_cols}")
            
            print(f"✓ 数据获取成功，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            print(f"✗ 失败: {str(e)}")
            if attempt < max_retries - 1:
                print(f"  {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print("✗ 达到最大重试次数")
                return None


def check_alert(threshold_percentile=0.8):
    """开户数告警检测"""
    print("\n" + "=" * 60)
    print("9. 开户数告警检测")
    print("=" * 60)
    
    # 获取数据
    df = ak.stock_account_statistics_em()
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 获取最新数据
    latest = df.iloc[-1]
    
    # 计算分位数
    percentile = (df['新增投资者-数量'] <= latest['新增投资者-数量']).sum() / len(df)
    
    # 判断告警
    is_alert = percentile >= threshold_percentile
    
    print(f"\n【告警检测结果】")
    print(f"数据日期: {latest['数据日期'].strftime('%Y-%m')}")
    print(f"新增开户: {latest['新增投资者-数量']:.2f} 万户")
    print(f"历史分位数: {percentile:.2%}")
    print(f"告警阈值: {threshold_percentile:.0%}")
    print(f"上证指数: {latest['上证指数-收盘']:.2f} 点")
    print(f"\n{'⚠️  告警: 开户数处于历史高位，市场可能过热' if is_alert else '✅ 正常: 开户数在合理范围'}")
    
    return is_alert, percentile


# ============================================================================
# 4. 数据可视化
# ============================================================================

def plot_basic_chart(df, save_path='开户数据_基础图表.png'):
    """基础图表"""
    print("\n" + "=" * 60)
    print("10. 绘制基础图表")
    print("=" * 60)
    
    df = df.copy()
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # 子图1: 新增开户数
    ax1 = axes[0]
    ax1.plot(df['数据日期'], df['新增投资者-数量'], 'b-', linewidth=2, label='新增开户数')
    ax1.fill_between(df['数据日期'], df['新增投资者-数量'], alpha=0.3)
    ax1.set_title('新增投资者数量（月度）', fontsize=14, fontweight='bold')
    ax1.set_xlabel('日期', fontsize=12)
    ax1.set_ylabel('新增开户数（万户）', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    
    # 子图2: 上证指数
    ax2 = axes[1]
    ax2.plot(df['数据日期'], df['上证指数-收盘'], 'r-', linewidth=2, label='上证指数')
    ax2.set_title('上证指数（月末收盘）', fontsize=14, fontweight='bold')
    ax2.set_xlabel('日期', fontsize=12)
    ax2.set_ylabel('指数点位', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ 图表已保存: {save_path}")
    plt.close()


def plot_advanced_chart(df, save_path='开户数据_高级图表.png'):
    """高级图表（包含移动平均和市场阶段）"""
    print("\n" + "=" * 60)
    print("11. 绘制高级图表")
    print("=" * 60)
    
    df = df.copy()
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 计算移动平均
    df['MA3'] = df['新增投资者-数量'].rolling(window=3).mean()
    df['MA6'] = df['新增投资者-数量'].rolling(window=6).mean()
    df['MA12'] = df['新增投资者-数量'].rolling(window=12).mean()
    
    # 计算分位数
    df['分位数'] = df['新增投资者-数量'].rank(pct=True)
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # 子图1: 新增开户数 + 移动平均
    ax1 = axes[0]
    ax1.plot(df['数据日期'], df['新增投资者-数量'], 'b-', linewidth=1.5, 
             label='新增开户数', alpha=0.7)
    ax1.plot(df['数据日期'], df['MA3'], 'g--', linewidth=1.5, label='3月均线')
    ax1.plot(df['数据日期'], df['MA6'], 'orange', linewidth=1.5, label='6月均线')
    ax1.plot(df['数据日期'], df['MA12'], 'r-', linewidth=2, label='12月均线')
    
    # 标注高位区域
    high_percentile = df['新增投资者-数量'].quantile(0.8)
    ax1.axhline(y=high_percentile, color='red', linestyle=':', alpha=0.5, label='80分位线')
    ax1.fill_between(df['数据日期'], high_percentile, df['新增投资者-数量'].max(), 
                     where=(df['新增投资者-数量'] >= high_percentile), alpha=0.1, color='red')
    
    ax1.set_title('新增开户数与移动平均', fontsize=14, fontweight='bold')
    ax1.set_ylabel('新增开户数（万户）', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9, loc='upper left')
    
    # 子图2: 同比环比增长
    ax2 = axes[1]
    df['环比'] = df['新增投资者-数量'].pct_change(1) * 100
    df['同比'] = df['新增投资者-数量'].pct_change(12) * 100
    
    ax2.bar(df['数据日期'], df['环比'], width=20, alpha=0.6, label='环比增长', color='steelblue')
    ax2.plot(df['数据日期'], df['同比'], 'r-', linewidth=2, label='同比增长', marker='o', markersize=3)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax2.set_title('新增开户数增长率', fontsize=14, fontweight='bold')
    ax2.set_ylabel('增长率（%）', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=9)
    
    # 子图3: 双轴图（开户数 vs 指数）
    ax3 = axes[2]
    ax3_twin = ax3.twinx()
    
    # 绘制开户数（左轴）
    line1 = ax3.plot(df['数据日期'], df['新增投资者-数量'], 'b-', 
                     linewidth=2, label='新增开户数', marker='o', markersize=3)
    ax3.set_ylabel('新增开户数（万户）', fontsize=12, color='b')
    ax3.tick_params(axis='y', labelcolor='b')
    
    # 绘制指数（右轴）
    line2 = ax3_twin.plot(df['数据日期'], df['上证指数-收盘'], 'r-', 
                          linewidth=2, label='上证指数', marker='s', markersize=3)
    ax3_twin.set_ylabel('上证指数', fontsize=12, color='r')
    ax3_twin.tick_params(axis='y', labelcolor='r')
    
    ax3.set_title('新增开户数 vs 上证指数', fontsize=14, fontweight='bold')
    ax3.set_xlabel('日期', fontsize=12)
    ax3.grid(True, alpha=0.3)
    
    # 合并图例
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax3.legend(lines, labels, fontsize=9, loc='upper left')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ 图表已保存: {save_path}")
    plt.close()


# ============================================================================
# 5. 数据导出
# ============================================================================

def export_data(df, output_dir='output'):
    """导出数据到多种格式"""
    print("\n" + "=" * 60)
    print("12. 数据导出")
    print("=" * 60)
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    df = df.copy()
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 导出 CSV
    csv_file = output_path / '开户数据.csv'
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"✓ CSV: {csv_file}")
    
    # 导出 Excel
    excel_file = output_path / '开户数据.xlsx'
    df.to_excel(excel_file, index=False, sheet_name='开户数据')
    print(f"✓ Excel: {excel_file}")
    
    # 导出 Parquet
    parquet_file = output_path / '开户数据.parquet'
    df.to_parquet(parquet_file, index=False)
    print(f"✓ Parquet: {parquet_file}")
    
    print(f"\n✓ 数据已导出到目录: {output_path.absolute()}")


# ============================================================================
# 6. 主程序
# ============================================================================

def main():
    """主程序"""
    print("\n" + "=" * 60)
    print("AKShare 开户数据获取 - 完整示例")
    print("=" * 60)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 基础功能
        df = get_basic_data()
        latest = get_latest_data()
        
        # 2. 数据处理
        df_processed = process_data_basic(df)
        df_with_metrics = calculate_derived_metrics(df)
        
        # 3. 统计分析
        statistical_analysis(df)
        correlation_analysis(df)
        
        # 4. 高级功能
        df_cached = get_data_with_cache(cache_hours=24)
        df_safe = get_data_safe(max_retries=3)
        
        # 5. 告警检测
        is_alert, percentile = check_alert(threshold_percentile=0.8)
        
        # 6. 数据可视化
        plot_basic_chart(df, save_path='开户数据_基础图表.png')
        plot_advanced_chart(df, save_path='开户数据_高级图表.png')
        
        # 7. 数据导出
        export_data(df_with_metrics, output_dir='output')
        
        print("\n" + "=" * 60)
        print("✓ 所有示例运行完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

