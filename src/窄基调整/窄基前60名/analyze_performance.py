#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析窄基前60名指数的新纳入股票表现
计算数据截止日和生效日，获取纳入股票前后5个交易日表现
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import glob
import os
import sys
import warnings
import threading
import time
warnings.filterwarnings('ignore')

# 添加项目路径以便导入
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(project_root)

# 导入项目的数据下载模块
try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData
    print("✓ 使用项目数据下载模块")
    USE_PROJECT_MODULE = True
except ImportError as e:
    print(f"✗ 无法导入项目数据下载模块: {e}")
    USE_PROJECT_MODULE = False

class TimeoutError(Exception):
    """超时异常"""
    pass

def with_timeout(timeout_seconds):
    """超时装饰器 - Windows兼容版本"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)
            
            if thread.is_alive():
                print(f"  操作超时 ({timeout_seconds}秒)")
                return None
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        
        return wrapper
    return decorator

class ZhaijiAnalysis:
    def __init__(self):
        """
        初始化分析器
        """
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
    def calculate_cutoff_date(self, effective_date):
        """
        计算数据截止日
        数据截止日 = 生效日前第二个自然月的最后一个自然日
        
        Args:
            effective_date: 生效日
            
        Returns:
            数据截止日
        """
        if isinstance(effective_date, str):
            effective_dt = pd.to_datetime(effective_date)
        else:
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
    
    def get_trading_days(self, start_date, end_date):
        """
        获取交易日列表
        
        Args:
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            
        Returns:
            交易日列表 ['YYYY-MM-DD']
        """
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')
        trading_days = [d.strftime('%Y-%m-%d') for d in date_range]
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
        center_str = pd.to_datetime(center_date).strftime('%Y-%m-%d')
        
        try:
            center_idx = trading_days.index(center_str)
        except ValueError:
            # 如果中心日期不是交易日，找到最近的交易日
            center_dt = pd.to_datetime(center_date)
            for i in range(10):
                test_date = center_dt - timedelta(days=i)
                test_str = test_date.strftime('%Y-%m-%d')
                if test_str in trading_days:
                    center_idx = trading_days.index(test_str)
                    break
            else:
                return []
        
        # 获取窗口
        start_idx = max(0, center_idx - days_before)
        end_idx = min(len(trading_days), center_idx + days_after + 1)
        
        window = trading_days[start_idx:end_idx]
        return window
    
    @with_timeout(2)
    def _fetch_stock_data_with_timeout(self, stock_code, start_date, end_date):
        """
        带超时的股票数据获取方法
        使用项目的数据下载模块
        """
        try:
            # 检查模块是否可用
            if not USE_PROJECT_MODULE:
                return None
            
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            start_str = pd.to_datetime(start_date).strftime('%Y%m%d')
            end_str = pd.to_datetime(end_date).strftime('%Y%m%d')
            
            # 使用项目的getDayData函数
            df = getDayData(
                stock_code=stock_code,
                start_date=start_str,
                end_date=end_str,
                is_download=0,  # 先从缓存读取
                dividend_type='front'  # 前复权
            )
            
            if df is None or len(df) == 0:
                return None
            
            # 确保date列是字符串格式
            if 'date' not in df.columns:
                if df.index.name == 'date' or 'date' in str(df.index.name):
                    df = df.reset_index()
                else:
                    return None
            
            # 转换日期格式为YYYY-MM-DD
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # 筛选日期范围
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            return df
                
        except Exception as e:
            return None
    
    def fetch_stock_data(self, stock_code, start_date, end_date, max_retries=3):
        """
        获取股票日线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            max_retries: 最大重试次数
            
        Returns:
            股票数据DataFrame
        """
        for attempt in range(max_retries):
            try:
                # 只显示第一次尝试或重试时的提示
                if attempt == 0:
                    print(f"    获取: {stock_code}")
                
                result = self._fetch_stock_data_with_timeout(stock_code, start_date, end_date)
                if result is not None and len(result) > 0:
                    print(f"    ✓ 成功获取 {len(result)} 条数据")
                    return result
                elif result is not None and len(result) == 0:
                    print(f"    ⚠ 未获取到数据")
                    return result
                else:
                    if attempt < max_retries - 1:
                        print(f"    ⚠ 第{attempt+1}次尝试失败，重试中...")
                        time.sleep(1)
            except Exception as e:
                print(f"    ✗ 第{attempt+1}次尝试失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        
        print(f"    ✗ 获取失败，已重试{max_retries}次")
        return None
    
    def analyze_stock_performance(self, stock_code, trading_window, center_date):
        """
        分析单只股票的表现
        
        Args:
            stock_code: 股票代码
            trading_window: 交易日窗口
            center_date: 中心日期
            
        Returns:
            表现指标字典
        """
        if not trading_window:
            return None
        
        # 获取股票数据
        stock_df = self.fetch_stock_data(stock_code, trading_window[0], trading_window[-1])
        
        if stock_df is None or len(stock_df) < 2:
            return None
        
        # 确保数据按日期排序
        if 'date' in stock_df.columns:
            stock_df = stock_df.sort_values('date')
        
        # 计算涨跌幅
        stock_df['pct_change'] = stock_df['close'].pct_change() * 100
        
        # 计算累计涨跌幅
        cumulative_return = (stock_df['close'].iloc[-1] / stock_df['close'].iloc[0] - 1) * 100
        
        # 计算胜率
        win_rate = (stock_df['pct_change'] > 0).mean() * 100
        
        # 计算成交量变化率
        avg_volume = stock_df['volume'].mean()
        volume_change_rate = (stock_df['volume'].iloc[-1] / avg_volume - 1) * 100 if avg_volume > 0 else 0
        
        return {
            'stock_code': stock_code,
            'center_date': center_date,
            'trading_days_count': len(stock_df),
            'avg_daily_return': stock_df['pct_change'].mean(),
            'cumulative_return': cumulative_return,
            'win_rate': win_rate,
            'volume_change_rate': volume_change_rate,
            'max_daily_return': stock_df['pct_change'].max(),
            'min_daily_return': stock_df['pct_change'].min(),
            'volatility': stock_df['pct_change'].std()
        }
    
    def analyze_all_indices(self):
        """
        分析所有指数的纳入股票表现
        """
        print("=" * 80)
        print("开始完整分析：计算数据截止日和生效日，获取纳入股票前后5个交易日表现")
        print("=" * 80)
        
        # 读取所有变动数据文件
        change_files = glob.glob('*_changes.csv')
        
        if not change_files:
            print("✗ 未找到变动数据文件")
            print("  请先运行 download_changes.py 下载数据")
            return []
        
        print(f"\n✓ 找到 {len(change_files)} 个指数变动数据文件")
        
        all_results = []
        
        for file in change_files:
            try:
                # 读取数据
                df = pd.read_csv(file)
                
                if len(df) == 0:
                    continue
                
                # 提取指数信息
                parts = file.replace('_changes.csv', '').split('_')
                if len(parts) < 2:
                    continue
                    
                index_name = parts[0]
                index_code = parts[1]
                
                print(f"\n{'='*80}")
                print(f"分析指数: {index_name} ({index_code})")
                print(f"{'='*80}")
                
                # 筛选新纳入股票
                newly_included = df[df['tradestatus'] == '纳入'].copy()
                
                if len(newly_included) == 0:
                    print("  没有新纳入的股票")
                    continue
                
                print(f"  新纳入股票数量: {len(newly_included)}")
                
                # 获取唯一的生效日期
                unique_dates = newly_included['tradedate'].unique()
                
                for effective_date in unique_dates:
                    try:
                        effective_dt = pd.to_datetime(effective_date)
                        
                        print(f"\n  处理生效日: {effective_dt.strftime('%Y-%m-%d')}")
                        
                        # 计算数据截止日
                        cutoff_date = self.calculate_cutoff_date(effective_date)
                        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
                        effective_str = effective_dt.strftime('%Y-%m-%d')
                        
                        print(f"    数据截止日: {cutoff_str}")
                        print(f"    生效日: {effective_str}")
                        
                        # 获取该日期组合下的股票
                        stocks_in_period = newly_included[newly_included['tradedate'] == effective_date]['tradecode'].tolist()
                        
                        # 获取交易日历
                        start_date = (cutoff_date - timedelta(days=30)).strftime('%Y-%m-%d')
                        end_date = (pd.to_datetime(effective_date) + timedelta(days=30)).strftime('%Y-%m-%d')
                        trading_days = self.get_trading_days(start_date, end_date)
                        
                        # 分析数据截止日窗口
                        cutoff_window = self.get_trading_window(cutoff_date, trading_days, 5, 5)
                        if cutoff_window:
                            print(f"    数据截止日窗口: {len(cutoff_window)} 个交易日")
                            # 遍历本期所有新纳入股票
                            for idx, stock in enumerate(stocks_in_period, 1):
                                try:
                                    performance = self.analyze_stock_performance(stock, cutoff_window, cutoff_str)
                                    if performance:
                                        performance['index_name'] = index_name
                                        performance['index_code'] = index_code
                                        performance['effective_date'] = effective_str
                                        performance['window_type'] = 'cutoff_date'
                                        all_results.append(performance)
                                except Exception as e:
                                    print(f"    分析股票 {stock} 时出错: {e}")
                                    continue
                        
                        # 分析生效日窗口
                        effective_window = self.get_trading_window(effective_date, trading_days, 5, 5)
                        if effective_window:
                            print(f"    生效日窗口: {len(effective_window)} 个交易日")
                            for idx, stock in enumerate(stocks_in_period, 1):
                                try:
                                    performance = self.analyze_stock_performance(stock, effective_window, effective_str)
                                    if performance:
                                        performance['index_name'] = index_name
                                        performance['index_code'] = index_code
                                        performance['effective_date'] = effective_str
                                        performance['window_type'] = 'effective_date'
                                        all_results.append(performance)
                                except Exception as e:
                                    print(f"    分析股票 {stock} 时出错: {e}")
                                    continue
                        
                    except Exception as e:
                        print(f"  处理日期 {effective_date} 时出错: {e}")
                        continue
            
            except Exception as e:
                print(f"处理文件 {file} 时出错: {e}")
                import traceback
                traceback.print_exc()
        
        return all_results
    
    def generate_summary_report(self, all_results):
        """
        生成汇总报告
        """
        if not all_results:
            print("✗ 没有分析结果")
            return
        
        results_df = pd.DataFrame(all_results)
        
        # 保存详细结果
        output_file = 'zhaiji_stocks_performance.csv'
        results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✓ 详细结果已保存到: {output_file}")
        
        # 生成汇总报告
        print("\n正在生成汇总报告...")
        
        # 1) 按指数总体汇总（不区分窗口）
        base_group = results_df.groupby('index_name')
        index_summary = base_group.agg({
            'stock_code': 'count',
            'cumulative_return': ['mean', 'std', 'min', 'max'],
            'win_rate': 'mean'
        }).round(2)
        summary_file = 'zhaiji_summary.csv'
        index_summary.to_csv(summary_file, index=False, encoding='utf-8-sig')
        print(f"✓ 汇总报告已保存到: {summary_file}")

        # 2) 按窗口类型分指数汇总（类似 indices_summary_report.csv）
        def positive_rate(s):
            return (s > 0).mean() * 100
        def gt5_rate(s):
            return (s > 5).mean() * 100
        
        per_window = results_df.groupby(['index_name', 'window_type']).agg(
            stock_count=('stock_code', 'count'),
            avg_cumulative_return=('cumulative_return', 'mean'),
            std_cumulative_return=('cumulative_return', 'std'),
            min_return=('cumulative_return', 'min'),
            max_return=('cumulative_return', 'max'),
            avg_win_rate=('win_rate', 'mean'),
            avg_volatility=('volatility', 'mean'),
            positive_return_rate=('cumulative_return', positive_rate),
            gt5_rate=('cumulative_return', gt5_rate)
        ).reset_index()
        per_window = per_window.round(2)
        per_window_file = 'indices_summary_per_window.csv'
        per_window.to_csv(per_window_file, index=False, encoding='utf-8-sig')
        print(f"✓ 按窗口类型分指数汇总已保存到: {per_window_file}")

        # 3) 整体窗口对比（你要求的‘数据截止日优、生效日差’的全局统计）
        overall = results_df.groupby('window_type').agg(
            stock_count=('stock_code', 'count'),
            avg_cumulative_return=('cumulative_return', 'mean'),
            avg_win_rate=('win_rate', 'mean'),
            positive_return_rate=('cumulative_return', positive_rate),
            gt5_rate=('cumulative_return', gt5_rate)
        ).round(2).reset_index()
        overall_file = 'overall_window_stats.csv'
        overall.to_csv(overall_file, index=False, encoding='utf-8-sig')
        print(f"✓ 整体窗口统计已保存到: {overall_file}")
        
        print(f"\n分析完成！")
        print(f"结果文件:")
        print(f"  - {output_file}")
        print(f"  - {summary_file}")

def main():
    """
    主函数
    """
    # 检查数据下载模块是否可用
    if not USE_PROJECT_MODULE:
        print("✗ 错误: 无法导入项目数据下载模块")
        print("  请确保项目路径正确，模块存在")
        return
    
    print(f"✓ 使用项目数据下载模块")
    
    analyzer = ZhaijiAnalysis()
    
    # 分析所有指数
    all_results = analyzer.analyze_all_indices()
    
    # 生成汇总报告
    if all_results:
        analyzer.generate_summary_report(all_results)
    
    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()

