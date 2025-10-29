"""
Wind API - 融资余额数据获取示例代码
功能：获取融资融券交易数据，包括融资余额、买入额、偿还额等
作者：Auto Generated
日期：2025-10-20
"""

from WindPy import w
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


class MarginTradingAnalyzer:
    """融资融券数据分析器"""
    
    def __init__(self):
        """初始化Wind连接"""
        print("正在连接Wind...")
        w.start()
        print("Wind连接成功！")
        
    def get_margin_data(self, start_date, end_date, exchange='all', frequency='day'):
        """
        获取融资融券数据
        
        参数:
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'
            exchange: 交易所，'all'/'sse'/'szse'
            frequency: 数据频率，'day'/'week'/'month'
            
        返回:
            DataFrame: 融资融券数据
        """
        params = (
            f"exchange={exchange};"
            f"startdate={start_date};"
            f"enddate={end_date};"
            f"frequency={frequency};"
            f"sort=asc"
        )
        
        print(f"\n正在获取数据...")
        print(f"  交易所: {exchange}")
        print(f"  日期范围: {start_date} 至 {end_date}")
        print(f"  数据频率: {frequency}")
        
        data = w.wset("margintradingsizeanalys(value)", params)
        
        if data.ErrorCode != 0:
            raise Exception(f"数据获取失败 - 错误代码: {data.ErrorCode}, 错误信息: {data.Data}")
            
        print(f"✓ 数据获取成功！")
        
        # 打印原始字段信息（用于调试）
        print(f"  返回字段: {data.Fields}")
        print(f"  数据条数: {len(data.Data[0]) if data.Data else 0}")
        
        # 转换为DataFrame
        df = pd.DataFrame(data.Data, index=data.Fields).T
        
        # 设置列名（使用实际返回的字段名）
        df.columns = data.Fields
        
        # 打印实际的列名
        print(f"  实际列名: {list(df.columns)}")
        
        # 字段名映射（英文到中文）- 使用Wind API实际返回的字段名
        column_mapping = {
            'end_date': '日期',
            'date': '日期',
            'trade_date': '日期',
            'exchange': '交易所',
            'margin_balance': '融资余额',
            'rzye': '融资余额',
            'margin_balance_ratio_negmktcap': '融资余额占流通市值(%)',
            'rzyezb': '融资余额占流通市值(%)',
            'margin_amount': '融资余量',
            'rzyl': '融资余量',
            'period_bought_amount': '期间买入额',
            'qjmre': '期间买入额',
            'total_amount_ratio_a-share_amount': '买入额占A股成交额(%)',
            'mrezb': '买入额占A股成交额(%)',
            'period_paid_amount': '期间偿还额',
            'qjche': '期间偿还额',
            'period_net_purchases': '期间净买入额',
            'qjjmre': '期间净买入额',
            'buy_count': '期间融资买入个股数',
            'rzggsl': '期间融资买入个股数',
            'margin_trading_underlying': '占融资标的比(%)',
            'rzbdzb': '占融资标的比(%)'
        }
        
        # 应用映射
        df.rename(columns=column_mapping, inplace=True)
        
        # 数据类型转换 - 日期列
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'])
        
        # 数值列转换为float（使用映射后的中文列名）
        numeric_columns = [
            '融资余额', '融资余额占流通市值(%)', '融资余量',
            '期间买入额', '买入额占A股成交额(%)', '期间偿还额',
            '期间净买入额', '期间融资买入个股数', '占融资标的比(%)'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"✓ 数据转换完成，最终列名: {list(df.columns)}")
        
        return df
    
    def calculate_metrics(self, df):
        """
        计算衍生指标
        
        参数:
            df: 原始数据DataFrame
            
        返回:
            DataFrame: 添加了衍生指标的数据
        """
        df = df.copy()
        
        print("\n正在计算衍生指标...")
        
        # 计算日变化
        df['融资余额日变化'] = df['融资余额'].diff()
        df['融资余额变化率(%)'] = df['融资余额'].pct_change() * 100
        
        # 计算移动平均
        df['融资余额_5日均'] = df['融资余额'].rolling(window=5).mean()
        df['融资余额_20日均'] = df['融资余额'].rolling(window=20).mean()
        
        # 计算净买入占比
        df['净买入占买入比(%)'] = (df['期间净买入额'] / df['期间买入额'] * 100).fillna(0)
        
        # 计算偿还率
        df['偿还率(%)'] = (df['期间偿还额'] / df['期间买入额'] * 100).fillna(0)
        
        print("✓ 衍生指标计算完成")
        
        return df
    
    def get_exchange_comparison(self, start_date, end_date):
        """
        获取交易所对比数据
        
        注意：此API的exchange参数只支持'all'，不支持单独查询sse或szse
        所以这个方法只返回全市场数据
        
        参数:
            start_date: 开始日期
            end_date: 结束日期
            
        返回:
            DataFrame: 全市场数据
        """
        print("\n" + "=" * 60)
        print("获取全市场融资融券数据")
        print("=" * 60)
        print("\n注意：Wind API的此接口只支持全市场数据(exchange=all)")
        print("不支持单独查询上交所或深交所数据")
        
        # 获取全市场数据
        df = self.get_margin_data(start_date, end_date, exchange='all')
        df['市场'] = '全市场'
        
        print("\n✓ 数据获取完成")
        
        return df
    
    def plot_margin_data(self, df, save_path='margin_trading_analysis.png'):
        """
        绘制融资融券数据图表
        
        参数:
            df: 包含融资融券数据的DataFrame
            save_path: 图表保存路径
        """
        print(f"\n正在生成图表...")
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        
        # 1. 融资余额走势
        ax1 = axes[0]
        ax1.plot(df['日期'], df['融资余额'] / 1e8, 'b-', linewidth=2, label='融资余额')
        if '融资余额_5日均' in df.columns:
            ax1.plot(df['日期'], df['融资余额_5日均'] / 1e8, 'r--', 
                    linewidth=1.5, label='5日均线', alpha=0.7)
        if '融资余额_20日均' in df.columns:
            ax1.plot(df['日期'], df['融资余额_20日均'] / 1e8, 'g--', 
                    linewidth=1.5, label='20日均线', alpha=0.7)
        
        ax1.set_title('融资余额走势图', fontsize=14, fontweight='bold')
        ax1.set_ylabel('融资余额（亿元）', fontsize=12)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        # 2. 期间净买入额
        ax2 = axes[1]
        colors = ['green' if x >= 0 else 'red' for x in df['期间净买入额']]
        ax2.bar(df['日期'], df['期间净买入额'] / 1e8, color=colors, alpha=0.6)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.set_title('期间净买入额', fontsize=14, fontweight='bold')
        ax2.set_ylabel('净买入额（亿元）', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        # 3. 融资余额占流通市值比例
        ax3 = axes[2]
        ax3.plot(df['日期'], df['融资余额占流通市值(%)'], 'purple', linewidth=2)
        ax3.fill_between(df['日期'], df['融资余额占流通市值(%)'], alpha=0.3, color='purple')
        ax3.set_title('融资余额占流通市值比例', fontsize=14, fontweight='bold')
        ax3.set_ylabel('比例（%）', fontsize=12)
        ax3.set_xlabel('日期', fontsize=12)
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        # 调整布局
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 保存图表
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ 图表已保存为: {save_path}")
        
        plt.show()
    
    def print_summary(self, df):
        """
        打印数据摘要
        
        参数:
            df: 数据DataFrame
        """
        print("\n" + "=" * 60)
        print("数据摘要")
        print("=" * 60)
        
        print(f"\n数据范围: {df['日期'].min().strftime('%Y-%m-%d')} 至 {df['日期'].max().strftime('%Y-%m-%d')}")
        print(f"数据条数: {len(df)}")
        
        print("\n融资余额统计:")
        print(f"  平均值: {df['融资余额'].mean():,.2f} 元 ({df['融资余额'].mean()/1e8:.2f} 亿元)")
        print(f"  最大值: {df['融资余额'].max():,.2f} 元 ({df['融资余额'].max()/1e8:.2f} 亿元)")
        print(f"  最小值: {df['融资余额'].min():,.2f} 元 ({df['融资余额'].min()/1e8:.2f} 亿元)")
        print(f"  标准差: {df['融资余额'].std():,.2f} 元")
        
        print("\n期间净买入额统计:")
        print(f"  平均值: {df['期间净买入额'].mean():,.2f} 元 ({df['期间净买入额'].mean()/1e8:.2f} 亿元)")
        print(f"  最大值: {df['期间净买入额'].max():,.2f} 元 ({df['期间净买入额'].max()/1e8:.2f} 亿元)")
        print(f"  最小值: {df['期间净买入额'].min():,.2f} 元 ({df['期间净买入额'].min()/1e8:.2f} 亿元)")
        
        print("\n融资余额占流通市值比例:")
        print(f"  平均值: {df['融资余额占流通市值(%)'].mean():.2f}%")
        print(f"  最大值: {df['融资余额占流通市值(%)'].max():.2f}%")
        print(f"  最小值: {df['融资余额占流通市值(%)'].min():.2f}%")
        
        print("\n最新数据（最近5天）:")
        display_columns = ['日期', '融资余额', '期间净买入额', '融资余额占流通市值(%)']
        latest_df = df[display_columns].tail(5).copy()
        latest_df['融资余额'] = latest_df['融资余额'].apply(lambda x: f"{x/1e8:.2f}亿")
        latest_df['期间净买入额'] = latest_df['期间净买入额'].apply(lambda x: f"{x/1e8:.2f}亿")
        latest_df['融资余额占流通市值(%)'] = latest_df['融资余额占流通市值(%)'].apply(lambda x: f"{x:.2f}%")
        print(latest_df.to_string(index=False))
    
    def close(self):
        """关闭Wind连接"""
        w.close()
        print("\n✓ Wind连接已关闭")


def example_1_basic():
    """示例1：基础用法 - 获取最近3个月的数据"""
    print("\n" + "=" * 60)
    print("示例1：基础用法 - 获取最近3个月的融资余额数据")
    print("=" * 60)
    
    analyzer = MarginTradingAnalyzer()
    
    try:
        # 设置日期范围（最近3个月）
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # 获取数据
        df = analyzer.get_margin_data(start_date, end_date, exchange='all')
        
        # 打印摘要
        analyzer.print_summary(df)
        
        # 保存数据
        output_file = 'margin_trading_basic.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✓ 数据已保存到: {output_file}")
        
    finally:
        analyzer.close()


def example_2_with_metrics():
    """示例2：计算衍生指标"""
    print("\n" + "=" * 60)
    print("示例2：计算衍生指标")
    print("=" * 60)
    
    analyzer = MarginTradingAnalyzer()
    
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # 获取数据
        df = analyzer.get_margin_data(start_date, end_date)
        
        # 计算衍生指标
        df = analyzer.calculate_metrics(df)
        
        # 显示衍生指标
        print("\n最新数据（含衍生指标）:")
        display_columns = [
            '日期', '融资余额', '融资余额日变化', 
            '融资余额变化率(%)', '净买入占买入比(%)', '偿还率(%)'
        ]
        latest_df = df[display_columns].tail(5).copy()
        latest_df['融资余额'] = latest_df['融资余额'].apply(lambda x: f"{x/1e8:.2f}亿")
        latest_df['融资余额日变化'] = latest_df['融资余额日变化'].apply(
            lambda x: f"{x/1e8:.2f}亿" if pd.notna(x) else 'N/A'
        )
        latest_df['融资余额变化率(%)'] = latest_df['融资余额变化率(%)'].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else 'N/A'
        )
        latest_df['净买入占买入比(%)'] = latest_df['净买入占买入比(%)'].apply(lambda x: f"{x:.2f}%")
        latest_df['偿还率(%)'] = latest_df['偿还率(%)'].apply(lambda x: f"{x:.2f}%")
        print(latest_df.to_string(index=False))
        
        # 保存数据
        output_file = 'margin_trading_with_metrics.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✓ 数据已保存到: {output_file}")
        
    finally:
        analyzer.close()


def example_3_exchange_comparison():
    """示例3：全市场数据获取（注：API不支持单独查询交易所）"""
    print("\n" + "=" * 60)
    print("示例3：全市场融资融券数据")
    print("=" * 60)
    
    analyzer = MarginTradingAnalyzer()
    
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # 获取全市场数据
        df = analyzer.get_exchange_comparison(start_date, end_date)
        
        # 显示最新数据
        if len(df) > 0 and '日期' in df.columns:
            latest_date = df['日期'].max()
            df_latest = df[df['日期'] == latest_date]
            
            print(f"\n最新日期 ({latest_date.strftime('%Y-%m-%d')}) 的数据:")
            display_columns = [
                '市场', '融资余额', '期间买入额', 
                '期间净买入额', '融资余额占流通市值(%)'
            ]
            display_df = df_latest[display_columns].copy()
            display_df['融资余额'] = display_df['融资余额'].apply(lambda x: f"{x/1e8:.2f}亿")
            display_df['期间买入额'] = display_df['期间买入额'].apply(lambda x: f"{x/1e8:.2f}亿")
            display_df['期间净买入额'] = display_df['期间净买入额'].apply(lambda x: f"{x/1e8:.2f}亿")
            display_df['融资余额占流通市值(%)'] = display_df['融资余额占流通市值(%)'].apply(lambda x: f"{x:.2f}%")
            print(display_df.to_string(index=False))
            
            # 显示趋势
            print("\n最近一周趋势:")
            recent_df = df.tail(5)[['日期', '融资余额', '期间净买入额']].copy()
            recent_df['融资余额'] = recent_df['融资余额'].apply(lambda x: f"{x/1e8:.2f}亿")
            recent_df['期间净买入额'] = recent_df['期间净买入额'].apply(lambda x: f"{x/1e8:.2f}亿")
            print(recent_df.to_string(index=False))
            
            # 保存数据
            output_file = 'margin_trading_market_data.csv'
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n✓ 数据已保存到: {output_file}")
        else:
            print("\n⚠ 未获取到有效数据")
        
    finally:
        analyzer.close()


def example_4_visualization():
    """示例4：数据可视化"""
    print("\n" + "=" * 60)
    print("示例4：数据可视化")
    print("=" * 60)
    
    analyzer = MarginTradingAnalyzer()
    
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # 获取数据
        df = analyzer.get_margin_data(start_date, end_date)
        
        # 计算衍生指标
        df = analyzer.calculate_metrics(df)
        
        # 绘制图表
        analyzer.plot_margin_data(df)
        
    finally:
        analyzer.close()


def example_5_weekly_monthly():
    """示例5：周度和月度数据"""
    print("\n" + "=" * 60)
    print("示例5：获取周度和月度数据")
    print("=" * 60)
    
    analyzer = MarginTradingAnalyzer()
    
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 获取周度数据
        print("\n[1/2] 获取周度数据...")
        df_weekly = analyzer.get_margin_data(start_date, end_date, frequency='week')
        print(f"\n周度数据（最近5周）:")
        print(df_weekly[['日期', '融资余额', '期间净买入额']].tail(5).to_string(index=False))
        
        # 获取月度数据
        print("\n[2/2] 获取月度数据...")
        df_monthly = analyzer.get_margin_data(start_date, end_date, frequency='month')
        print(f"\n月度数据（最近5个月）:")
        print(df_monthly[['日期', '融资余额', '期间净买入额']].tail(5).to_string(index=False))
        
        # 保存数据
        df_weekly.to_csv('margin_trading_weekly.csv', index=False, encoding='utf-8-sig')
        df_monthly.to_csv('margin_trading_monthly.csv', index=False, encoding='utf-8-sig')
        print(f"\n✓ 周度数据已保存到: margin_trading_weekly.csv")
        print(f"✓ 月度数据已保存到: margin_trading_monthly.csv")
        
    finally:
        analyzer.close()


def main():
    """主函数 - 运行所有示例"""
    print("\n" + "=" * 60)
    print("Wind API - 融资余额数据获取示例")
    print("=" * 60)
    
    examples = {
        '1': ('基础用法', example_1_basic),
        '2': ('计算衍生指标', example_2_with_metrics),
        '3': ('全市场数据获取', example_3_exchange_comparison),
        '4': ('数据可视化', example_4_visualization),
        '5': ('周度和月度数据', example_5_weekly_monthly),
    }
    
    print("\n请选择要运行的示例:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  0. 运行所有示例")
    print("  q. 退出")
    
    choice = input("\n请输入选项 (0-5/q): ").strip()
    
    if choice == 'q':
        print("退出程序")
        return
    elif choice == '0':
        # 运行所有示例
        for key in sorted(examples.keys()):
            name, func = examples[key]
            try:
                func()
                input("\n按回车键继续...")
            except Exception as e:
                print(f"\n❌ 示例 {key} 执行失败: {str(e)}")
                import traceback
                traceback.print_exc()
    elif choice in examples:
        # 运行选定的示例
        name, func = examples[choice]
        try:
            func()
        except Exception as e:
            print(f"\n❌ 示例执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("无效的选项")
    
    print("\n程序结束")


if __name__ == '__main__':
    main()

