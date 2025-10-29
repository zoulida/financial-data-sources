#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新纳入股票表现分析
分析中证新能源汽车产业指数新纳入股票在数据截止日和生效日前后5个交易日的表现
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from xtquant import xtdata
import warnings
warnings.filterwarnings('ignore')

class NewlyIncludedStockAnalyzer:
    def __init__(self, csv_file_path):
        """
        初始化分析器
        
        Args:
            csv_file_path: CSV文件路径
        """
        self.csv_file_path = csv_file_path
        self.df = None
        self.newly_included_stocks = None
        self.trading_calendar = None
        
        # 初始化XtQuant
        print("正在初始化XtQuant...")
        # XtQuant不需要设置token，直接使用即可
        
    def load_and_filter_data(self):
        """
        读取CSV文件并筛选出纳入的股票
        """
        print("正在读取CSV文件...")
        self.df = pd.read_csv(self.csv_file_path)
        
        # 筛选出纳入的股票
        self.newly_included_stocks = self.df[self.df['tradestatus'] == '纳入'].copy()
        
        print(f"总记录数: {len(self.df)}")
        print(f"新纳入股票记录数: {len(self.newly_included_stocks)}")
        
        # 计算数据截止日
        self.calculate_cutoff_dates()
        
        return self.newly_included_stocks
    
    def calculate_cutoff_dates(self):
        """
        计算每个生效日对应的数据截止日
        数据截止日 = 生效日前第二个自然月的最后一个自然日
        """
        def get_cutoff_date(effective_date):
            """计算数据截止日"""
            effective_dt = pd.to_datetime(effective_date)
            
            # 生效日前第二个自然月
            if effective_dt.month <= 2:
                prev_month = effective_dt.month - 2 + 12
                prev_year = effective_dt.year - 1
            else:
                prev_month = effective_dt.month - 2
                prev_year = effective_dt.year
            
            # 该月的最后一天
            cutoff_date = pd.Timestamp(year=prev_year, month=prev_month, day=1) + pd.DateOffset(months=1) - pd.DateOffset(days=1)
            return cutoff_date
        
        # 计算数据截止日
        self.newly_included_stocks['cutoff_date'] = self.newly_included_stocks['tradedate'].apply(get_cutoff_date)
        
        print("\n生效日与数据截止日对应关系:")
        date_mapping = self.newly_included_stocks[['tradedate', 'cutoff_date']].drop_duplicates()
        for _, row in date_mapping.iterrows():
            print(f"生效日: {row['tradedate']} → 数据截止日: {row['cutoff_date'].strftime('%Y-%m-%d')}")
    
    def get_trading_calendar(self, start_date, end_date):
        """
        获取交易日历
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            交易日列表
        """
        print(f"正在获取交易日历: {start_date} 至 {end_date}")
        
        try:
            # XtQuant的get_trading_calendar可能不支持，使用工作日作为替代
            print("使用工作日作为交易日历替代方案")
            date_range = pd.date_range(start=start_date, end=end_date, freq='B')
            trading_days = [d.strftime('%Y%m%d') for d in date_range]
            
            print(f"获取到 {len(trading_days)} 个交易日")
            return trading_days
            
        except Exception as e:
            print(f"获取交易日历失败: {e}")
            # 使用工作日作为替代
            date_range = pd.date_range(start=start_date, end=end_date, freq='B')
            trading_days = [d.strftime('%Y%m%d') for d in date_range]
            return trading_days
    
    def get_trading_window(self, center_date, trading_days, days_before=5, days_after=5):
        """
        获取以某个日期为中心的交易日窗口
        
        Args:
            center_date: 中心日期
            trading_days: 交易日列表
            days_before: 前N个交易日
            days_after: 后N个交易日
            
        Returns:
            交易日窗口列表
        """
        center_str = pd.to_datetime(center_date).strftime('%Y%m%d')
        
        try:
            center_idx = trading_days.index(center_str)
        except ValueError:
            # 如果中心日期不是交易日，找到最近的交易日
            center_dt = pd.to_datetime(center_date)
            for i in range(10):  # 最多向前查找10天
                test_date = center_dt - timedelta(days=i)
                test_str = test_date.strftime('%Y%m%d')
                if test_str in trading_days:
                    center_idx = trading_days.index(test_str)
                    break
            else:
                print(f"警告: 无法找到 {center_date} 附近的交易日")
                return []
        
        # 获取窗口
        start_idx = max(0, center_idx - days_before)
        end_idx = min(len(trading_days), center_idx + days_after + 1)
        
        window = trading_days[start_idx:end_idx]
        return window
    
    def fetch_market_data(self, stock_list, start_date, end_date):
        """
        获取股票行情数据
        
        Args:
            stock_list: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            行情数据字典
        """
        print(f"正在获取 {len(stock_list)} 只股票的行情数据: {start_date} 至 {end_date}")
        
        try:
            # 使用XtQuant获取行情数据
            data = xtdata.get_market_data_ex(
                field_list=['close', 'volume'],
                stock_list=stock_list,
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            if data is None:
                print("警告: 未能获取到行情数据")
                return None
            
            print(f"成功获取行情数据")
            return data
            
        except Exception as e:
            print(f"获取行情数据失败: {e}")
            return None
    
    def calculate_performance_metrics(self, stock_code, market_data, trading_window, center_date):
        """
        计算单只股票的表现指标
        
        Args:
            stock_code: 股票代码
            market_data: 行情数据
            trading_window: 交易日窗口
            center_date: 中心日期
            
        Returns:
            表现指标字典
        """
        try:
            # 提取该股票的数据
            if stock_code not in market_data['close']:
                return None
            
            close_prices = market_data['close'][stock_code]
            volumes = market_data['volume'][stock_code]
            
            # 转换为DataFrame
            df_stock = pd.DataFrame({
                'close': close_prices,
                'volume': volumes
            })
            
            # 确保索引是日期格式
            df_stock.index = pd.to_datetime(df_stock.index)
            
            # 筛选交易日窗口内的数据
            window_dates = [pd.to_datetime(d) for d in trading_window]
            df_window = df_stock[df_stock.index.isin(window_dates)].sort_index()
            
            if len(df_window) < 2:
                return None
            
            # 计算涨跌幅
            df_window['pct_change'] = df_window['close'].pct_change() * 100
            
            # 计算累计涨跌幅
            cumulative_return = (df_window['close'].iloc[-1] / df_window['close'].iloc[0] - 1) * 100
            
            # 计算成交量变化率
            avg_volume = df_window['volume'].mean()
            volume_change_rate = (df_window['volume'].iloc[-1] / avg_volume - 1) * 100 if avg_volume > 0 else 0
            
            # 计算胜率（上涨天数占比）
            win_rate = (df_window['pct_change'] > 0).mean() * 100
            
            return {
                'stock_code': stock_code,
                'center_date': center_date,
                'trading_days_count': len(df_window),
                'avg_daily_return': df_window['pct_change'].mean(),
                'cumulative_return': cumulative_return,
                'win_rate': win_rate,
                'volume_change_rate': volume_change_rate,
                'max_daily_return': df_window['pct_change'].max(),
                'min_daily_return': df_window['pct_change'].min(),
                'volatility': df_window['pct_change'].std()
            }
            
        except Exception as e:
            print(f"计算股票 {stock_code} 表现指标失败: {e}")
            return None
    
    def analyze_all_stocks(self):
        """
        分析所有新纳入股票的表现
        """
        print("\n开始分析所有新纳入股票的表现...")
        
        # 获取所有唯一的股票代码和日期
        unique_stocks = self.newly_included_stocks['tradecode'].unique()
        unique_dates = self.newly_included_stocks[['tradedate', 'cutoff_date']].drop_duplicates()
        
        print(f"需要分析的股票数量: {len(unique_stocks)}")
        print(f"需要分析的日期组合: {len(unique_dates)}")
        
        # 确定数据获取的日期范围
        all_dates = []
        for _, row in unique_dates.iterrows():
            effective_date = pd.to_datetime(row['tradedate'])
            cutoff_date = row['cutoff_date']
            
            # 为每个关键日期添加前后10天的缓冲
            all_dates.extend([
                cutoff_date - timedelta(days=10),
                cutoff_date + timedelta(days=10),
                effective_date - timedelta(days=10),
                effective_date + timedelta(days=10)
            ])
        
        start_date = min(all_dates).strftime('%Y-%m-%d')
        end_date = max(all_dates).strftime('%Y-%m-%d')
        
        # 获取交易日历
        trading_days = self.get_trading_calendar(start_date, end_date)
        
        # 获取行情数据
        market_data = self.fetch_market_data(unique_stocks.tolist(), start_date, end_date)
        
        if market_data is None:
            print("无法获取行情数据，分析终止")
            return None
        
        # 分析每只股票的表现
        results = []
        
        for _, row in unique_dates.iterrows():
            effective_date = row['tradedate']
            cutoff_date = row['cutoff_date']
            
            print(f"\n分析日期组合: 生效日 {effective_date}, 数据截止日 {cutoff_date.strftime('%Y-%m-%d')}")
            
            # 获取该日期组合下的股票
            stocks_in_period = self.newly_included_stocks[
                (self.newly_included_stocks['tradedate'] == effective_date) &
                (self.newly_included_stocks['cutoff_date'] == cutoff_date)
            ]['tradecode'].tolist()
            
            print(f"该期间新纳入股票数量: {len(stocks_in_period)}")
            
            # 分析数据截止日窗口
            cutoff_window = self.get_trading_window(cutoff_date, trading_days)
            if cutoff_window:
                print(f"数据截止日窗口: {len(cutoff_window)} 个交易日")
                for stock in stocks_in_period:
                    metrics = self.calculate_performance_metrics(
                        stock, market_data, cutoff_window, cutoff_date
                    )
                    if metrics:
                        metrics['window_type'] = 'cutoff_date'
                        metrics['effective_date'] = effective_date
                        results.append(metrics)
            
            # 分析生效日窗口
            effective_window = self.get_trading_window(effective_date, trading_days)
            if effective_window:
                print(f"生效日窗口: {len(effective_window)} 个交易日")
                for stock in stocks_in_period:
                    metrics = self.calculate_performance_metrics(
                        stock, market_data, effective_window, effective_date
                    )
                    if metrics:
                        metrics['window_type'] = 'effective_date'
                        metrics['effective_date'] = effective_date
                        results.append(metrics)
        
        return pd.DataFrame(results)
    
    def generate_summary_reports(self, results_df):
        """
        生成统计汇总报告
        
        Args:
            results_df: 详细结果DataFrame
        """
        print("\n正在生成统计汇总报告...")
        
        if results_df is None or len(results_df) == 0:
            print("没有数据可生成报告")
            return
        
        # 按窗口类型分组
        cutoff_results = results_df[results_df['window_type'] == 'cutoff_date']
        effective_results = results_df[results_df['window_type'] == 'effective_date']
        
        # 生成数据截止日窗口统计
        cutoff_summary = self.create_summary_stats(cutoff_results, "数据截止日窗口")
        
        # 生成生效日窗口统计
        effective_summary = self.create_summary_stats(effective_results, "生效日窗口")
        
        # 保存详细数据
        results_df.to_csv('newly_included_performance_detail.csv', 
                         index=False, encoding='utf-8-sig')
        print("详细数据已保存到: newly_included_performance_detail.csv")
        
        # 保存汇总报告
        cutoff_summary.to_csv('newly_included_summary_cutoff_date.csv', 
                             index=False, encoding='utf-8-sig')
        effective_summary.to_csv('newly_included_summary_effective_date.csv', 
                                index=False, encoding='utf-8-sig')
        
        print("数据截止日窗口统计已保存到: newly_included_summary_cutoff_date.csv")
        print("生效日窗口统计已保存到: newly_included_summary_effective_date.csv")
        
        # 生成综合分析报告
        self.create_overall_summary_report(cutoff_summary, effective_summary)
    
    def create_summary_stats(self, data, window_name):
        """
        创建汇总统计
        
        Args:
            data: 数据DataFrame
            window_name: 窗口名称
            
        Returns:
            汇总统计DataFrame
        """
        if len(data) == 0:
            return pd.DataFrame()
        
        summary_stats = []
        
        # 按生效日期分组统计
        for effective_date in data['effective_date'].unique():
            period_data = data[data['effective_date'] == effective_date]
            
            stats = {
                'effective_date': effective_date,
                'window_type': window_name,
                'stock_count': len(period_data),
                'avg_daily_return': period_data['avg_daily_return'].mean(),
                'avg_cumulative_return': period_data['cumulative_return'].mean(),
                'win_rate_avg': period_data['win_rate'].mean(),
                'volume_change_rate_avg': period_data['volume_change_rate'].mean(),
                'max_return': period_data['cumulative_return'].max(),
                'min_return': period_data['cumulative_return'].min(),
                'volatility_avg': period_data['volatility'].mean(),
                'positive_return_count': (period_data['cumulative_return'] > 0).sum(),
                'positive_return_rate': (period_data['cumulative_return'] > 0).mean() * 100
            }
            summary_stats.append(stats)
        
        return pd.DataFrame(summary_stats)
    
    def create_overall_summary_report(self, cutoff_summary, effective_summary):
        """
        创建综合分析报告
        
        Args:
            cutoff_summary: 数据截止日汇总
            effective_summary: 生效日汇总
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("中证新能源汽车产业指数新纳入股票表现分析报告")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # 总体统计
        report_lines.append("一、总体统计")
        report_lines.append("-" * 30)
        
        if len(cutoff_summary) > 0:
            total_stocks_cutoff = cutoff_summary['stock_count'].sum()
            avg_return_cutoff = cutoff_summary['avg_cumulative_return'].mean()
            win_rate_cutoff = cutoff_summary['positive_return_rate'].mean()
            
            report_lines.append(f"数据截止日窗口:")
            report_lines.append(f"  总股票数量: {total_stocks_cutoff}")
            report_lines.append(f"  平均累计涨跌幅: {avg_return_cutoff:.2f}%")
            report_lines.append(f"  平均胜率: {win_rate_cutoff:.2f}%")
            report_lines.append("")
        
        if len(effective_summary) > 0:
            total_stocks_effective = effective_summary['stock_count'].sum()
            avg_return_effective = effective_summary['avg_cumulative_return'].mean()
            win_rate_effective = effective_summary['positive_return_rate'].mean()
            
            report_lines.append(f"生效日窗口:")
            report_lines.append(f"  总股票数量: {total_stocks_effective}")
            report_lines.append(f"  平均累计涨跌幅: {avg_return_effective:.2f}%")
            report_lines.append(f"  平均胜率: {win_rate_effective:.2f}%")
            report_lines.append("")
        
        # 按调整批次详细统计
        report_lines.append("二、按调整批次详细统计")
        report_lines.append("-" * 30)
        
        for i, (_, row) in enumerate(cutoff_summary.iterrows(), 1):
            report_lines.append(f"调整批次 {i} (生效日: {row['effective_date']})")
            report_lines.append(f"  数据截止日窗口:")
            report_lines.append(f"    股票数量: {row['stock_count']}")
            report_lines.append(f"    平均累计涨跌幅: {row['avg_cumulative_return']:.2f}%")
            report_lines.append(f"    胜率: {row['positive_return_rate']:.2f}%")
            report_lines.append(f"    最大涨跌幅: {row['max_return']:.2f}%")
            report_lines.append(f"    最小涨跌幅: {row['min_return']:.2f}%")
            
            # 对应的生效日窗口统计
            effective_row = effective_summary[effective_summary['effective_date'] == row['effective_date']]
            if len(effective_row) > 0:
                effective_row = effective_row.iloc[0]
                report_lines.append(f"  生效日窗口:")
                report_lines.append(f"    股票数量: {effective_row['stock_count']}")
                report_lines.append(f"    平均累计涨跌幅: {effective_row['avg_cumulative_return']:.2f}%")
                report_lines.append(f"    胜率: {effective_row['positive_return_rate']:.2f}%")
                report_lines.append(f"    最大涨跌幅: {effective_row['max_return']:.2f}%")
                report_lines.append(f"    最小涨跌幅: {effective_row['min_return']:.2f}%")
            
            report_lines.append("")
        
        # 保存报告
        report_content = "\n".join(report_lines)
        with open('newly_included_overall_summary.txt', 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print("综合分析报告已保存到: newly_included_overall_summary.txt")
        print("\n" + report_content)

def main():
    """
    主函数
    """
    print("=" * 60)
    print("中证新能源汽车产业指数新纳入股票表现分析")
    print("=" * 60)
    
    # 初始化分析器
    analyzer = NewlyIncludedStockAnalyzer('930997_changes_20240101_20251024.csv')
    
    # 加载和筛选数据
    analyzer.load_and_filter_data()
    
    # 分析所有股票
    results = analyzer.analyze_all_stocks()
    
    # 生成汇总报告
    analyzer.generate_summary_reports(results)
    
    print("\n分析完成！")

if __name__ == "__main__":
    main()
