#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整分析：计算数据截止日和生效日，获取纳入股票前后5个交易日表现
使用XtQuant获取真实股票日线数据
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
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from xtquant import xtdata
    USE_XTQUANT = True
    print("使用XtQuant API")
except ImportError:
    USE_XTQUANT = False
    print("XtQuant不可用")
    try:
        import WindPy as w
        USE_WIND = True
        w.start()
        print("使用Wind API作为替代")
    except:
        USE_WIND = False
        print("无可用API")

# 尝试导入项目的数据下载模块
try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData, batchDownloadDayData
    USE_PROJECT_MODULE = True
    print("使用项目数据下载模块")
except ImportError as e:
    USE_PROJECT_MODULE = False
    print(f"项目数据下载模块不可用: {e}")

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

class CompleteAnalysis:
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
    
    def fetch_stock_data(self, stock_code, start_date, end_date, max_retries=3):
        """
        获取股票日线数据
        优先使用项目的getDayData函数，带缓存机制和超时重试
        
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
                result = self._fetch_stock_data_with_timeout(stock_code, start_date, end_date)
                if result is not None:
                    return result
                else:
                    print(f"  第{attempt+1}次尝试超时，重试中...")
                    time.sleep(1)  # 等待1秒后重试
            except Exception as e:
                print(f"  第{attempt+1}次尝试失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                else:
                    print(f"  股票 {stock_code} 获取失败，已重试{max_retries}次")
                    return None
        
        return None
    
    @with_timeout(2)  # 3秒超时
    def _fetch_stock_data_with_timeout(self, stock_code, start_date, end_date):
        """
        带超时的股票数据获取方法
        """
        try:
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            start_str = pd.to_datetime(start_date).strftime('%Y%m%d')
            end_str = pd.to_datetime(end_date).strftime('%Y%m%d')
            
            # 使用项目的数据下载模块
            if USE_PROJECT_MODULE:
                try:
                    print(f"  尝试从缓存读取: {stock_code} ({start_str} 至 {end_str})")
                    df = getDayData(
                        stock_code=stock_code,
                        start_date=start_str,
                        end_date=end_str,
                        is_download=0,  # 先从缓存读取
                        dividend_type='front'  # 前复权
                    )
                    
                    if df is not None and len(df) > 0:
                        print(f"  成功从缓存读取，共 {len(df)} 条数据")
                        # 确保date列是字符串格式
                        if 'date' not in df.columns:
                            df = df.reset_index().rename(columns={'index': 'date'})
                        df['date'] = df['date'].astype(str)
                        # 转换日期格式为YYYY-MM-DD
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                        
                        # 筛选日期范围
                        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                        
                        print(f"  筛选后共 {len(df)} 条数据")
                        return df
                    else:
                        print(f"  缓存中无数据，尝试下载: {stock_code}")
                        df = getDayData(
                            stock_code=stock_code,
                            start_date=start_str,
                            end_date=end_str,
                            is_download=1,  # 重新下载
                            dividend_type='front'
                        )
                        if df is not None and len(df) > 0:
                            print(f"  成功下载，共 {len(df)} 条数据")
                            if 'date' not in df.columns:
                                df = df.reset_index().rename(columns={'index': 'date'})
                            df['date'] = df['date'].astype(str)
                            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                            return df
                except Exception as e:
                    print(f"  项目模块获取失败: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 备用方案：使用XtQuant
            if USE_XTQUANT:
                try:
                    print(f"  尝试使用XtQuant获取: {stock_code}")
                    data = xtdata.get_market_data_ex(
                        field_list=['close', 'volume'],
                        stock_list=[stock_code],
                        period='1d',
                        start_time=start_date,
                        end_time=end_date,
                        dividend_type='front'
                    )
                    
                    print(f"  XtQuant返回数据类型: {type(data)}")
                    print(f"  XtQuant返回数据: {data}")
                    
                    if data is None:
                        print(f"  XtQuant返回None")
                        return None
                    
                    if not isinstance(data, dict):
                        print(f"  XtQuant返回的不是字典类型")
                        return None
                    
                    if 'close' not in data:
                        print(f"  XtQuant返回数据中没有'close'字段")
                        return None
                    
                    if stock_code not in data.get('close', {}):
                        print(f"  XtQuant返回数据中没有股票 {stock_code}")
                        return None
                    
                    print(f"  XtQuant成功获取数据")
                    close_prices = data['close'][stock_code]
                    volumes = data['volume'][stock_code]
                    
                    df = pd.DataFrame({
                        'date': pd.to_datetime(data.index).strftime('%Y-%m-%d'),
                        'close': close_prices,
                        'volume': volumes
                    })
                    
                    print(f"  构建DataFrame，共 {len(df)} 条数据")
                    return df
                    
                except Exception as e:
                    print(f"  XtQuant获取失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
            
            # 最后方案：使用Wind API
            if USE_WIND:
                data = w.wsd(stock_code, "close,volume", start_date, end_date, "PriceAdj=F")
                
                if data.ErrorCode != 0:
                    return None
                
                df = pd.DataFrame({
                    'close': data.Data[0],
                    'volume': data.Data[1]
                })
                df.index = pd.to_datetime(data.Times)
                
                df = df.reset_index()
                df.columns = ['date', 'close', 'volume']
                df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                
                return df
                
        except Exception as e:
            print(f"  获取数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        
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
        
        print(f"\n找到 {len(change_files)} 个指数变动数据文件")
        
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
                    print("没有新纳入的股票")
                    continue
                
                print(f"新纳入股票数量: {len(newly_included)}")
                
                # 获取唯一的生效日期
                unique_dates = newly_included['tradedate'].unique()
                
                for effective_date in unique_dates:
                    try:
                        print(f"\n处理生效日: {effective_date}")
                        
                        # 计算数据截止日
                        cutoff_date = self.calculate_cutoff_date(effective_date)
                        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
                        effective_str = pd.to_datetime(effective_date).strftime('%Y-%m-%d')
                        
                        print(f"数据截止日: {cutoff_str}")
                        print(f"生效日: {effective_str}")
                        
                        # 获取该日期组合下的股票
                        stocks_in_period = newly_included[newly_included['tradedate'] == effective_date]['tradecode'].tolist()
                        
                        # 获取交易日历
                        start_date = (cutoff_date - timedelta(days=30)).strftime('%Y-%m-%d')
                        end_date = (pd.to_datetime(effective_date) + timedelta(days=30)).strftime('%Y-%m-%d')
                        trading_days = self.get_trading_days(start_date, end_date)
                        
                        # 分析数据截止日窗口
                        cutoff_window = self.get_trading_window(cutoff_date, trading_days, 5, 5)
                        if cutoff_window:
                            print(f"数据截止日窗口: {len(cutoff_window)} 个交易日 ({cutoff_window[0]} 至 {cutoff_window[-1]})")
                            
                            # 批量获取所有股票数据，避免重复下载
                            print(f"  开始批量分析 {len(stocks_in_period)} 只股票...")
                            for idx, stock in enumerate(stocks_in_period, 1):
                                if idx % 10 == 0:
                                    print(f"  进度: {idx}/{len(stocks_in_period)}")
                                try:
                                    performance = self.analyze_stock_performance(stock, cutoff_window, cutoff_str)
                                    if performance:
                                        performance['index_name'] = index_name
                                        performance['index_code'] = index_code
                                        performance['effective_date'] = effective_str
                                        performance['window_type'] = 'cutoff_date'
                                        performance['window_dates'] = f"{cutoff_window[0]} to {cutoff_window[-1]}"
                                        all_results.append(performance)
                                except Exception as e:
                                    print(f"  分析股票 {stock} 时出错: {e}")
                                    continue
                        
                        # 分析生效日窗口
                        effective_window = self.get_trading_window(effective_date, trading_days, 5, 5)
                        if effective_window:
                            print(f"生效日窗口: {len(effective_window)} 个交易日 ({effective_window[0]} 至 {effective_window[-1]})")
                            
                            print(f"  开始批量分析 {len(stocks_in_period)} 只股票...")
                            for idx, stock in enumerate(stocks_in_period, 1):
                                if idx % 10 == 0:
                                    print(f"  进度: {idx}/{len(stocks_in_period)}")
                                try:
                                    performance = self.analyze_stock_performance(stock, effective_window, effective_str)
                                    if performance:
                                        performance['index_name'] = index_name
                                        performance['index_code'] = index_code
                                        performance['effective_date'] = effective_str
                                        performance['window_type'] = 'effective_date'
                                        performance['window_dates'] = f"{effective_window[0]} to {effective_window[-1]}"
                                        all_results.append(performance)
                                except Exception as e:
                                    print(f"  分析股票 {stock} 时出错: {e}")
                                    continue
                    
                    except Exception as e:
                        print(f"处理日期 {effective_date} 时出错: {e}")
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
            print("没有分析结果")
            return
        
        results_df = pd.DataFrame(all_results)
        
        # 保存详细结果
        output_file = 'all_stocks_performance_detail.csv'
        results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n详细结果已保存到: {output_file}")
        
        # 生成汇总报告
        print("\n正在生成汇总报告...")
        
        # 1. 按指数汇总统计
        print("1. 生成按指数汇总统计...")
        index_summary = results_df.groupby('index_name').agg({
            'stock_code': 'count',
            'cumulative_return': ['mean', 'std', 'min', 'max'],
            'win_rate': 'mean',
            'volatility': 'mean'
        }).round(2)
        
        # 计算正收益股票数量和占比
        positive_counts = results_df.groupby('index_name').apply(
            lambda x: (x['cumulative_return'] > 0).sum(), include_groups=False
        )
        positive_rates = results_df.groupby('index_name').apply(
            lambda x: (x['cumulative_return'] > 0).mean() * 100, include_groups=False
        )
        
        # 重新整理数据
        index_summary_clean = pd.DataFrame({
            'index_name': index_summary.index,
            'stock_count': index_summary[('stock_code', 'count')],
            'avg_cumulative_return': index_summary[('cumulative_return', 'mean')],
            'std_cumulative_return': index_summary[('cumulative_return', 'std')],
            'min_return': index_summary[('cumulative_return', 'min')],
            'max_return': index_summary[('cumulative_return', 'max')],
            'avg_win_rate': index_summary[('win_rate', 'mean')],
            'avg_volatility': index_summary[('volatility', 'mean')],
            'positive_return_count': positive_counts.values,
            'positive_return_rate': positive_rates.values
        })
        
        index_summary_clean.to_csv('indices_summary_report.csv', index=False, encoding='utf-8-sig')
        print(f"  已生成 indices_summary_report.csv，包含 {len(index_summary_clean)} 个指数")
        
        # 2. 按窗口类型分指数对比
        print("2. 生成按窗口类型分指数对比...")
        
        # 数据截止日统计
        cutoff_stats = results_df[results_df['window_type'] == 'cutoff_date'].groupby('index_name').agg({
            'stock_code': 'count',
            'cumulative_return': 'mean',
            'win_rate': 'mean'
        })
        
        cutoff_positive = results_df[results_df['window_type'] == 'cutoff_date'].groupby('index_name').apply(
            lambda x: (x['cumulative_return'] > 0).mean() * 100, include_groups=False
        )
        
        # 生效日统计
        effective_stats = results_df[results_df['window_type'] == 'effective_date'].groupby('index_name').agg({
            'stock_code': 'count',
            'cumulative_return': 'mean',
            'win_rate': 'mean'
        })
        
        effective_positive = results_df[results_df['window_type'] == 'effective_date'].groupby('index_name').apply(
            lambda x: (x['cumulative_return'] > 0).mean() * 100, include_groups=False
        )
        
        # 合并数据
        window_comparison = pd.DataFrame({
            'index_name': cutoff_stats.index,
            'stock_count': cutoff_stats['stock_code'],
            'cutoff_avg_return': cutoff_stats['cumulative_return'].round(2),
            'cutoff_win_rate': cutoff_stats['win_rate'].round(2),
            'cutoff_positive_rate': cutoff_positive.round(2),
            'effective_avg_return': effective_stats['cumulative_return'].round(2),
            'effective_win_rate': effective_stats['win_rate'].round(2),
            'effective_positive_rate': effective_positive.round(2)
        })
        
        # 添加指数代码
        index_codes = results_df.groupby('index_name')['index_code'].first()
        window_comparison['index_code'] = window_comparison['index_name'].map(index_codes)
        
        # 重新排列列顺序
        window_comparison = window_comparison[['index_name', 'index_code', 'stock_count', 
                                             'cutoff_avg_return', 'cutoff_win_rate', 'cutoff_positive_rate',
                                             'effective_avg_return', 'effective_win_rate', 'effective_positive_rate']]
        
        window_comparison.to_csv('window_analysis_summary.csv', index=False, encoding='utf-8-sig')
        print(f"  已生成 window_analysis_summary.csv，包含 {len(window_comparison)} 个指数")
        
        # 3. 整体统计
        print("3. 生成整体统计...")
        cutoff_data = results_df[results_df['window_type'] == 'cutoff_date']
        effective_data = results_df[results_df['window_type'] == 'effective_date']
        
        overall_stats = pd.DataFrame({
            'window_type': ['cutoff_date', 'effective_date'],
            'stock_count': [len(cutoff_data), len(effective_data)],
            'avg_cumulative_return': [cutoff_data['cumulative_return'].mean(), effective_data['cumulative_return'].mean()],
            'avg_win_rate': [cutoff_data['win_rate'].mean(), effective_data['win_rate'].mean()],
            'positive_return_rate': [(cutoff_data['cumulative_return'] > 0).mean() * 100, 
                                    (effective_data['cumulative_return'] > 0).mean() * 100],
            'avg_volatility': [cutoff_data['volatility'].mean(), effective_data['volatility'].mean()]
        }).round(2)
        
        overall_stats.to_csv('overall_statistics.csv', index=False, encoding='utf-8-sig')
        print(f"  已生成 overall_statistics.csv")
        
        # 按窗口类型分组统计
        print("\n" + "=" * 80)
        print("汇总统计报告")
        print("=" * 80)
        
        # 数据截止日窗口统计
        if len(cutoff_data) > 0:
            print(f"\n数据截止日窗口:")
            print(f"  股票数量: {len(cutoff_data)}")
            print(f"  平均累计涨跌幅: {cutoff_data['cumulative_return'].mean():.2f}%")
            print(f"  平均胜率: {cutoff_data['win_rate'].mean():.2f}%")
            print(f"  正收益股票占比: {(cutoff_data['cumulative_return'] > 0).mean()*100:.1f}%")
        
        # 生效日窗口统计
        if len(effective_data) > 0:
            print(f"\n生效日窗口:")
            print(f"  股票数量: {len(effective_data)}")
            print(f"  平均累计涨跌幅: {effective_data['cumulative_return'].mean():.2f}%")
            print(f"  平均胜率: {effective_data['win_rate'].mean():.2f}%")
            print(f"  正收益股票占比: {(effective_data['cumulative_return'] > 0).mean()*100:.1f}%")
        
        print(f"\n汇总报告生成完成！")
        print(f"文件列表:")
        print(f"  - all_stocks_performance_detail.csv: 详细股票表现数据")
        print(f"  - indices_summary_report.csv: 按指数汇总统计")
        print(f"  - window_analysis_summary.csv: 按窗口类型分指数对比")
        print(f"  - overall_statistics.csv: 整体统计")

def main():
    """
    主函数
    """
    analyzer = CompleteAnalysis()
    
    # 分析所有指数
    all_results = analyzer.analyze_all_indices()
    
    # 生成汇总报告
    analyzer.generate_summary_report(all_results)
    
    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()