#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创新高创新低监控程序
获取全市场A股创新高和创新低的股票数量

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

class InnovationHighLowMonitor:
    """创新高创新低监控类"""
    
    def __init__(self, log_level=logging.INFO):
        """
        初始化创新高创新低监控器
        
        Args:
            log_level: 日志级别
        """
        self.setup_logging(log_level)
        self.wind_initialized = False
        
        # 初始化Wind接口
        if WIND_AVAILABLE:
            self.init_wind()
    
    def setup_logging(self, log_level):
        """设置日志"""
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'innovation_high_low_{datetime.now().strftime("%Y%m%d")}.log')
        
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
    
    def get_stock_pool(self, date: str = None) -> Optional[List[str]]:
        """
        获取全市场A股股票池
        
        Args:
            date: 日期，格式: '2025-10-29'，如果为None则使用今天
            
        Returns:
            List[str]: 股票代码列表
        """
        if not self.wind_initialized:
            self.logger.warning("Wind接口未初始化，返回模拟股票池")
            return self._get_mock_stock_pool()
        
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            self.logger.info(f"正在获取 {date} 的全市场A股股票池...")
            
            # 获取全市场A股股票池（沪深主板+创业板+科创板）
            stock_list = w.wset("sectorconstituent", f"date={date};sectorid=a001010100000000")
            
            if stock_list.ErrorCode != 0:
                self.logger.error(f"获取股票池失败，错误代码: {stock_list.ErrorCode}")
                return None
            
            if not stock_list.Data or len(stock_list.Data) < 2:
                self.logger.warning("股票池数据为空")
                return None
            
            codes = stock_list.Data[1]  # 股票代码列表
            self.logger.info(f"成功获取 {len(codes)} 只股票")
            
            return codes
            
        except Exception as e:
            self.logger.error(f"获取股票池时发生错误: {e}")
            return None
    
    def _get_mock_stock_pool(self) -> List[str]:
        """生成模拟股票池"""
        self.logger.info("生成模拟股票池")
        
        # 模拟一些股票代码
        mock_codes = [
            "000001.SZ", "000002.SZ", "000858.SZ", "002415.SZ", "300015.SZ",
            "300059.SZ", "300750.SZ", "600000.SH", "600036.SH", "600519.SH",
            "600887.SH", "688001.SH", "688036.SH", "688981.SH"
        ]
        
        return mock_codes
    
    def get_innovation_data(self, date: str = None) -> Optional[pd.DataFrame]:
        """
        获取创新高创新低数据
        
        Args:
            date: 日期，格式: '2025-10-29'，如果为None则使用今天
            
        Returns:
            DataFrame: 包含创新高创新低数据的DataFrame
        """
        if not self.wind_initialized:
            self.logger.warning("Wind接口未初始化，返回模拟数据")
            return self._get_mock_innovation_data(date)
        
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 获取股票池
            codes = self.get_stock_pool(date)
            if not codes:
                return None
            
            self.logger.info(f"正在获取 {date} 的创新高创新低数据...")
            
            # 批量获取创新高/创新低状态
            result = w.wsd(codes, "new_high,new_low", date, date, "")
            
            if result.ErrorCode != 0:
                self.logger.error(f"获取创新高创新低数据失败，错误代码: {result.ErrorCode}")
                self.logger.warning("将使用模拟数据进行演示")
                return self._get_mock_innovation_data(date)
            
            if not result.Data or len(result.Data) < 2:
                self.logger.warning("创新高创新低数据为空")
                return None
            
            # 构建DataFrame
            df = pd.DataFrame({
                '代码': result.Codes,
                '创新高': result.Data[0],
                '创新低': result.Data[1]
            }).dropna()
            
            self.logger.info(f"成功获取 {len(df)} 只股票的创新高创新低数据")
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取创新高创新低数据时发生错误: {e}")
            return None
    
    def _get_mock_innovation_data(self, date: str = None) -> pd.DataFrame:
        """生成模拟创新高创新低数据"""
        self.logger.info("生成模拟创新高创新低数据")
        
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 获取模拟股票池
        codes = self._get_mock_stock_pool()
        
        # 生成模拟数据
        np.random.seed(42)  # 确保结果可重现
        
        data = []
        for code in codes:
            # 模拟创新高创新低状态（大部分为0，少数为1）
            new_high = 1 if np.random.random() < 0.05 else 0  # 5%概率创新高
            new_low = 1 if np.random.random() < 0.03 else 0   # 3%概率创新低
            
            data.append({
                '代码': code,
                '创新高': new_high,
                '创新低': new_low
            })
        
        df = pd.DataFrame(data)
        return df
    
    def analyze_innovation_data(self, df: pd.DataFrame) -> Dict:
        """
        分析创新高创新低数据
        
        Args:
            df: 创新高创新低数据
            
        Returns:
            Dict: 分析结果
        """
        if df is None or df.empty:
            return {}
        
        analysis = {}
        
        # 统计数量
        new_high_count = df[df['创新高'] == 1].shape[0]
        new_low_count = df[df['创新低'] == 1].shape[0]
        total_stocks = len(df)
        
        # 计算比例
        new_high_ratio = new_high_count / total_stocks * 100
        new_low_ratio = new_low_count / total_stocks * 100
        
        # 创新高创新低同时发生的股票
        both_high_low = df[(df['创新高'] == 1) & (df['创新低'] == 1)].shape[0]
        
        analysis['基本统计'] = {
            '总股票数': total_stocks,
            '创新高数量': new_high_count,
            '创新低数量': new_low_count,
            '创新高比例': round(new_high_ratio, 2),
            '创新低比例': round(new_low_ratio, 2),
            '同时创新高创新低': both_high_low
        }
        
        # 市场情绪判断
        if new_high_ratio > 10:
            market_sentiment = "极度乐观"
        elif new_high_ratio > 5:
            market_sentiment = "乐观"
        elif new_low_ratio > 10:
            market_sentiment = "极度悲观"
        elif new_low_ratio > 5:
            market_sentiment = "悲观"
        else:
            market_sentiment = "中性"
        
        analysis['市场情绪'] = {
            '情绪状态': market_sentiment,
            '创新高比例': round(new_high_ratio, 2),
            '创新低比例': round(new_low_ratio, 2)
        }
        
        # 创新高股票列表
        if new_high_count > 0:
            high_stocks = df[df['创新高'] == 1]['代码'].tolist()
            analysis['创新高股票'] = {
                '数量': new_high_count,
                '股票列表': high_stocks[:10] if len(high_stocks) > 10 else high_stocks  # 最多显示10只
            }
        
        # 创新低股票列表
        if new_low_count > 0:
            low_stocks = df[df['创新低'] == 1]['代码'].tolist()
            analysis['创新低股票'] = {
                '数量': new_low_count,
                '股票列表': low_stocks[:10] if len(low_stocks) > 10 else low_stocks  # 最多显示10只
            }
        
        return analysis
    
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
            filename = f"innovation_high_low_{timestamp}.csv"
        
        # 确保保存目录存在
        save_dir = os.path.join(project_root, 'data')
        os.makedirs(save_dir, exist_ok=True)
        
        filepath = os.path.join(save_dir, filename)
        
        try:
            df.to_csv(filepath, encoding='utf-8-sig', index=False)
            self.logger.info(f"数据已保存到: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")
            return ""
    
    def get_today_data(self) -> Optional[pd.DataFrame]:
        """
        获取今日创新高创新低数据
        
        Returns:
            DataFrame: 今日的创新高创新低数据
        """
        today = datetime.now().strftime('%Y-%m-%d')
        return self.get_innovation_data(today)
    
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
    print("创新高创新低监控程序")
    print("=" * 60)
    
    # 创建监控器实例
    monitor = InnovationHighLowMonitor()
    
    try:
        # 获取今日数据
        print("\n正在获取今日创新高创新低数据...")
        df = monitor.get_today_data()
        
        if df is not None and not df.empty:
            # 显示数据
            print(f"\n成功获取 {len(df)} 只股票的数据")
            
            # 分析数据
            analysis = monitor.analyze_innovation_data(df)
            
            print("\n创新高创新低统计:")
            print("-" * 40)
            for key, value in analysis.items():
                print(f"\n{key}:")
                if isinstance(value, dict):
                    for k, v in value.items():
                        if isinstance(v, list):
                            print(f"  {k}: {v}")
                        else:
                            print(f"  {k}: {v}")
                else:
                    print(f"  {value}")
            
            # 保存数据
            filepath = monitor.save_data(df)
            if filepath:
                print(f"\n数据已保存到: {filepath}")
        
        else:
            print("未能获取到创新高创新低数据")
    
    except Exception as e:
        print(f"程序执行出错: {e}")
        monitor.logger.error(f"程序执行出错: {e}")
    
    finally:
        # 关闭Wind接口
        monitor.close()
        print("\n程序执行完成")


if __name__ == "__main__":
    main()
