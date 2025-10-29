#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新纳入股票表现分析 - 模拟数据演示版
用于演示分析功能和输出格式
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class DemoStockAnalyzer:
    def __init__(self, csv_file_path):
        """
        初始化分析器
        
        Args:
            csv_file_path: CSV文件路径
        """
        self.csv_file_path = csv_file_path
        self.df = None
        self.newly_included_stocks = None
        
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
    
    def generate_mock_data(self, stock_code, center_date, window_type):
        """
        生成模拟的股票表现数据
        
        Args:
            stock_code: 股票代码
            center_date: 中心日期
            window_type: 窗口类型 ('cutoff_date' 或 'effective_date')
            
        Returns:
            模拟的表现指标
        """
        # 设置随机种子，确保结果可重现
        np.random.seed(hash(stock_code + str(center_date) + window_type) % 2**32)
        
        # 模拟数据
        trading_days_count = np.random.randint(8, 12)  # 8-11个交易日
        avg_daily_return = np.random.normal(0.5, 2.0)  # 平均日涨跌幅
        cumulative_return = np.random.normal(3.0, 8.0)  # 累计涨跌幅
        win_rate = np.random.uniform(40, 80)  # 胜率
        volume_change_rate = np.random.normal(20, 50)  # 成交量变化率
        max_daily_return = np.random.uniform(2, 8)  # 最大日涨跌幅
        min_daily_return = np.random.uniform(-8, -2)  # 最小日涨跌幅
        volatility = np.random.uniform(1.5, 4.0)  # 波动率
        
        return {
            'stock_code': stock_code,
            'center_date': center_date,
            'trading_days_count': trading_days_count,
            'avg_daily_return': avg_daily_return,
            'cumulative_return': cumulative_return,
            'win_rate': win_rate,
            'volume_change_rate': volume_change_rate,
            'max_daily_return': max_daily_return,
            'min_daily_return': min_daily_return,
            'volatility': volatility
        }
    
    def analyze_all_stocks(self):
        """
        分析所有新纳入股票的表现（使用模拟数据）
        """
        print("\n开始分析所有新纳入股票的表现（模拟数据演示）...")
        
        # 获取所有唯一的股票代码和日期
        unique_stocks = self.newly_included_stocks['tradecode'].unique()
        unique_dates = self.newly_included_stocks[['tradedate', 'cutoff_date']].drop_duplicates()
        
        print(f"需要分析的股票数量: {len(unique_stocks)}")
        print(f"需要分析的日期组合: {len(unique_dates)}")
        
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
            print(f"数据截止日窗口: 模拟生成 {len(stocks_in_period)} 只股票数据")
            for stock in stocks_in_period:
                metrics = self.generate_mock_data(stock, cutoff_date, 'cutoff_date')
                metrics['window_type'] = 'cutoff_date'
                metrics['effective_date'] = effective_date
                results.append(metrics)
            
            # 分析生效日窗口
            print(f"生效日窗口: 模拟生成 {len(stocks_in_period)} 只股票数据")
            for stock in stocks_in_period:
                metrics = self.generate_mock_data(stock, effective_date, 'effective_date')
                metrics['window_type'] = 'effective_date'
                metrics['effective_date'] = effective_date
                results.append(metrics)
        
        return pd.DataFrame(results)
    
    def generate_summary_reports(self, results_df):
        """
        生成统计汇总报告
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
    print("中证新能源汽车产业指数新纳入股票表现分析 - 模拟数据演示版")
    print("=" * 60)
    
    # 初始化分析器
    analyzer = DemoStockAnalyzer('930997_changes_20240101_20251024.csv')
    
    # 加载和筛选数据
    analyzer.load_and_filter_data()
    
    # 分析所有股票
    results = analyzer.analyze_all_stocks()
    
    # 生成汇总报告
    analyzer.generate_summary_reports(results)
    
    print("\n分析完成！")
    print("\n注意：这是模拟数据演示版本，实际使用时需要配置真实的数据源API")

if __name__ == "__main__":
    main()
