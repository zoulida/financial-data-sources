#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场情绪监控程序
获取内地市场的涨跌家数统计，包括上涨、平盘、下跌、涨停、跌停家数

作者: AI Assistant
创建时间: 2025-01-29
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

try:
    from WindPy import w
    WIND_AVAILABLE = True
except ImportError:
    WIND_AVAILABLE = False
    print("警告: WindPy 未安装，将使用模拟数据")

class MarketSentimentMonitor:
    """市场情绪监控类"""
    
    def __init__(self, log_level=logging.INFO):
        """
        初始化市场情绪监控器
        
        Args:
            log_level: 日志级别
        """
        self.setup_logging(log_level)
        self.wind_initialized = False
        
        # 字段映射 - 根据field.txt文件
        self.field_mapping = {
            '内地-上涨家数': 'risenumberofshandsz',
            '内地-平盘家数': 'noriseorfalnumberofshandsz', 
            '内地-下跌家数': 'fallnumberofshandsz',
            '内地-涨停家数': 'limitupnumofshandsz',
            '内地-跌停家数': 'limitdownnumofshandsz'
        }
        
        # 初始化Wind接口
        if WIND_AVAILABLE:
            self.init_wind()
    
    def setup_logging(self, log_level):
        """设置日志"""
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'market_sentiment_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_wind(self):
        """初始化Wind接口"""
        try:
            if WIND_AVAILABLE:
                w.start()
                self.wind_initialized = True
                self.logger.info("Wind接口初始化成功")
            else:
                self.logger.warning("WindPy未安装，将使用模拟数据")
        except Exception as e:
            self.logger.error(f"Wind接口初始化失败: {e}")
            self.wind_initialized = False
    
    def get_market_sentiment_data(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取市场情绪数据
        
        Args:
            start_date: 开始日期，格式: '2025-01-01'
            end_date: 结束日期，格式: '2025-01-29'
            
        Returns:
            DataFrame: 包含市场情绪数据的DataFrame
        """
        if not self.wind_initialized:
            self.logger.warning("Wind接口未初始化，返回模拟数据")
            return self._get_mock_data(start_date, end_date)
        
        try:
            # 使用wset接口获取内地涨跌家数统计
            # 根据field.txt文件中的接口: w.wset("numberofchangeindomestic","startdate=2025-09-29;enddate=2025-10-29")
            options = f"startdate={start_date};enddate={end_date}"
            
            self.logger.info(f"正在获取市场情绪数据: {start_date} 到 {end_date}")
            
            data = w.wset("numberofchangeindomestic", options)
            
            if data.ErrorCode != 0:
                self.logger.error(f"Wind数据获取失败，错误代码: {data.ErrorCode}")
                return None
            
            # 检查数据格式
            self.logger.info(f"Wind返回数据: Fields={data.Fields}, Codes={data.Codes}, Data长度={len(data.Data) if data.Data else 0}")
            
            if not data.Data or len(data.Data) == 0:
                self.logger.warning("Wind返回数据为空")
                return None
            
            # 转换为DataFrame - Wind wset数据结构
            try:
                # Wind wset返回的数据：每行是一个字段，每列是一个日期
                # 需要转置才能得到正确的DataFrame（日期为行，字段为列）
                df = pd.DataFrame(data.Data).T
                df.columns = data.Fields
                df.index = data.Codes
                
                self.logger.info(f"DataFrame形状: {df.shape}")
                self.logger.info(f"DataFrame列名: {list(df.columns)}")
                
                # 重命名列以匹配我们的字段映射（注意字段名是小写）
                column_mapping = {
                    'reportdate': '日期',
                    'risenumberofshandsz': '内地-上涨家数',
                    'noriseorfallnumberofshandsz': '内地-平盘家数',
                    'fallnumberofshandsz': '内地-下跌家数',
                    'limitupnumofshandsz': '内地-涨停家数',
                    'limitdownnumofshandsz': '内地-跌停家数'
                }
                
                # 只重命名存在的列
                existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
                df = df.rename(columns=existing_columns)
                
            except Exception as e:
                self.logger.error(f"DataFrame转换失败: {e}")
                return None
            
            # 确保日期列是datetime类型
            if '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.set_index('日期')
            
            self.logger.info(f"成功获取 {len(df)} 条市场情绪数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取市场情绪数据时发生错误: {e}")
            return None
    
    def _get_mock_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        生成模拟数据用于测试
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 模拟的市场情绪数据
        """
        self.logger.info("生成模拟市场情绪数据")
        
        # 生成日期范围
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.date_range(start, end, freq='D')
        
        # 生成模拟数据
        np.random.seed(42)  # 确保结果可重现
        
        data = []
        for date in dates:
            # 模拟合理的市场数据
            total_stocks = 5000  # 假设总股票数
            rise_ratio = np.random.uniform(0.3, 0.7)  # 上涨比例
            flat_ratio = np.random.uniform(0.05, 0.15)  # 平盘比例
            fall_ratio = 1 - rise_ratio - flat_ratio  # 下跌比例
            
            rise_count = int(total_stocks * rise_ratio)
            flat_count = int(total_stocks * flat_ratio)
            fall_count = total_stocks - rise_count - flat_count
            
            # 涨停跌停数量相对较少
            limit_up = np.random.randint(10, 100)
            limit_down = np.random.randint(5, 80)
            
            data.append({
                '日期': date,
                '内地-上涨家数': rise_count,
                '内地-平盘家数': flat_count,
                '内地-下跌家数': fall_count,
                '内地-涨停家数': limit_up,
                '内地-跌停家数': limit_down
            })
        
        df = pd.DataFrame(data)
        df = df.set_index('日期')
        
        return df
    
    def calculate_sentiment_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算市场情绪指标
        
        Args:
            df: 原始市场情绪数据
            
        Returns:
            DataFrame: 包含计算指标的数据
        """
        if df is None or df.empty:
            return df
        
        # 复制数据避免修改原始数据
        result_df = df.copy()
        
        # 计算总股票数
        result_df['总股票数'] = (result_df['内地-上涨家数'] + 
                            result_df['内地-平盘家数'] + 
                            result_df['内地-下跌家数'])
        
        # 计算涨跌比例
        result_df['上涨比例'] = result_df['内地-上涨家数'] / result_df['总股票数']
        result_df['下跌比例'] = result_df['内地-下跌家数'] / result_df['总股票数']
        result_df['平盘比例'] = result_df['内地-平盘家数'] / result_df['总股票数']
        
        # 计算涨跌停比例
        result_df['涨停比例'] = result_df['内地-涨停家数'] / result_df['总股票数']
        result_df['跌停比例'] = result_df['内地-跌停家数'] / result_df['总股票数']
        
        # 计算市场情绪指标
        result_df['涨跌比'] = result_df['内地-上涨家数'] / result_df['内地-下跌家数']
        result_df['涨跌停比'] = result_df['内地-涨停家数'] / result_df['内地-跌停家数']
        
        # 计算市场强度指标
        result_df['市场强度'] = (result_df['上涨比例'] - result_df['下跌比例']) * 100
        
        # 计算情绪指标（-100到100，正值表示乐观）
        result_df['情绪指标'] = ((result_df['上涨比例'] - result_df['下跌比例']) + 
                            (result_df['涨停比例'] - result_df['跌停比例']) * 0.5) * 100
        
        return result_df
    
    def save_data(self, df: pd.DataFrame, filename: Optional[str] = None) -> str:
        """
        保存数据到CSV文件
        
        Args:
            df: 要保存的DataFrame
            filename: 文件名，如果为None则自动生成
            
        Returns:
            str: 保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"market_sentiment_{timestamp}.csv"
        
        # 确保保存目录存在
        save_dir = os.path.join(project_root, 'data')
        os.makedirs(save_dir, exist_ok=True)
        
        filepath = os.path.join(save_dir, filename)
        
        try:
            df.to_csv(filepath, encoding='utf-8-sig')
            self.logger.info(f"数据已保存到: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")
            return ""
    
    def get_latest_data(self, days: int = 5) -> Optional[pd.DataFrame]:
        """
        获取最近几天的市场情绪数据
        
        Args:
            days: 获取最近几天的数据
            
        Returns:
            DataFrame: 最近的市场情绪数据
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        return self.get_market_sentiment_data(start_date, end_date)
    
    def analyze_market_sentiment(self, df: pd.DataFrame) -> Dict:
        """
        分析市场情绪
        
        Args:
            df: 市场情绪数据
            
        Returns:
            Dict: 分析结果
        """
        if df is None or df.empty:
            return {}
        
        analysis = {}
        
        # 最新数据
        latest = df.iloc[-1]
        analysis['最新数据'] = {
            '日期': latest.name.strftime('%Y-%m-%d'),
            '上涨家数': int(latest['内地-上涨家数']),
            '下跌家数': int(latest['内地-下跌家数']),
            '平盘家数': int(latest['内地-平盘家数']),
            '涨停家数': int(latest['内地-涨停家数']),
            '跌停家数': int(latest['内地-跌停家数'])
        }
        
        # 统计信息
        analysis['统计信息'] = {
            '数据天数': len(df),
            '平均上涨家数': int(df['内地-上涨家数'].mean()),
            '平均下跌家数': int(df['内地-下跌家数'].mean()),
            '平均涨停家数': int(df['内地-涨停家数'].mean()),
            '平均跌停家数': int(df['内地-跌停家数'].mean())
        }
        
        # 市场情绪判断
        if '情绪指标' in df.columns:
            latest_sentiment = latest['情绪指标']
            if latest_sentiment > 20:
                sentiment = "极度乐观"
            elif latest_sentiment > 10:
                sentiment = "乐观"
            elif latest_sentiment > -10:
                sentiment = "中性"
            elif latest_sentiment > -20:
                sentiment = "悲观"
            else:
                sentiment = "极度悲观"
            
            analysis['市场情绪'] = {
                '情绪指标': round(latest_sentiment, 2),
                '情绪状态': sentiment
            }
        
        return analysis
    
    def close(self):
        """关闭Wind接口"""
        if self.wind_initialized and WIND_AVAILABLE:
            try:
                w.stop()
                self.logger.info("Wind接口已关闭")
            except Exception as e:
                self.logger.error(f"关闭Wind接口时发生错误: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("市场情绪监控程序")
    print("=" * 60)
    
    # 创建监控器实例
    monitor = MarketSentimentMonitor()
    
    try:
        # 获取最近5天的数据
        print("\n正在获取最近5天的市场情绪数据...")
        df = monitor.get_latest_data(days=5)
        
        if df is not None and not df.empty:
            # 计算情绪指标
            df_with_indicators = monitor.calculate_sentiment_indicators(df)
            
            # 显示数据
            print("\n市场情绪数据:")
            print("-" * 40)
            print(df_with_indicators[['内地-上涨家数', '内地-下跌家数', '内地-平盘家数', 
                                   '内地-涨停家数', '内地-跌停家数', '情绪指标']].tail())
            
            # 分析市场情绪
            analysis = monitor.analyze_market_sentiment(df_with_indicators)
            
            print("\n市场情绪分析:")
            print("-" * 40)
            for key, value in analysis.items():
                print(f"\n{key}:")
                if isinstance(value, dict):
                    for k, v in value.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"  {value}")
            
            # 保存数据
            filepath = monitor.save_data(df_with_indicators)
            if filepath:
                print(f"\n数据已保存到: {filepath}")
        
        else:
            print("未能获取到市场情绪数据")
    
    except Exception as e:
        print(f"程序执行出错: {e}")
        monitor.logger.error(f"程序执行出错: {e}")
    
    finally:
        # 关闭Wind接口
        monitor.close()
        print("\n程序执行完成")


if __name__ == "__main__":
    main()
