#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场情绪监控程序使用示例
演示如何使用MarketSentimentMonitor类获取和分析市场情绪数据

作者: AI Assistant
创建时间: 2025-01-29
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.市场情绪.market_sentiment_monitor import MarketSentimentMonitor
from src.市场情绪.visualization import MarketSentimentVisualizer

def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("市场情绪监控 - 基本使用示例")
    print("=" * 60)
    
    # 创建监控器
    monitor = MarketSentimentMonitor()
    
    try:
        # 获取最近5天的数据
        print("\n1. 获取最近5天的市场情绪数据...")
        df = monitor.get_latest_data(days=5)
        
        if df is not None and not df.empty:
            print(f"成功获取 {len(df)} 天的数据")
            print("\n原始数据预览:")
            print(df.head())
            
            # 计算情绪指标
            print("\n2. 计算市场情绪指标...")
            df_with_indicators = monitor.calculate_sentiment_indicators(df)
            
            print("\n包含指标的数据预览:")
            print(df_with_indicators[['内地-上涨家数', '内地-下跌家数', '内地-平盘家数', 
                                   '内地-涨停家数', '内地-跌停家数', '情绪指标']].tail())
            
            # 分析市场情绪
            print("\n3. 分析市场情绪...")
            analysis = monitor.analyze_market_sentiment(df_with_indicators)
            
            print("\n市场情绪分析结果:")
            for key, value in analysis.items():
                print(f"\n{key}:")
                if isinstance(value, dict):
                    for k, v in value.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"  {value}")
            
            # 保存数据
            print("\n4. 保存数据...")
            filepath = monitor.save_data(df_with_indicators)
            if filepath:
                print(f"数据已保存到: {filepath}")
        
        else:
            print("未能获取到市场情绪数据")
    
    except Exception as e:
        print(f"示例执行出错: {e}")
    
    finally:
        monitor.close()

def example_visualization():
    """可视化示例"""
    print("\n" + "=" * 60)
    print("市场情绪监控 - 可视化示例")
    print("=" * 60)
    
    # 创建监控器
    monitor = MarketSentimentMonitor()
    
    try:
        # 获取数据
        print("\n1. 获取市场情绪数据...")
        df = monitor.get_latest_data(days=7)
        
        if df is not None and not df.empty:
            # 计算指标
            df_with_indicators = monitor.calculate_sentiment_indicators(df)
            
            # 创建可视化器
            print("\n2. 创建可视化图表...")
            visualizer = MarketSentimentVisualizer()
            
            # 生成各种图表
            charts_dir = "market_sentiment_charts"
            visualizer.create_dashboard(df_with_indicators, charts_dir)
            
            print(f"\n可视化图表已保存到目录: {charts_dir}")
        
        else:
            print("未能获取到市场情绪数据，使用模拟数据进行演示...")
            
            # 使用模拟数据
            dates = pd.date_range('2025-01-25', periods=7, freq='D')
            data = {
                '内地-上涨家数': [3200, 2800, 3500, 3100, 2900, 3300, 3000],
                '内地-下跌家数': [1500, 2000, 1200, 1600, 1800, 1400, 1700],
                '内地-平盘家数': [300, 200, 300, 300, 300, 300, 300],
                '内地-涨停家数': [80, 60, 90, 75, 65, 85, 70],
                '内地-跌停家数': [20, 40, 15, 25, 35, 15, 30]
            }
            
            df = pd.DataFrame(data, index=dates)
            df_with_indicators = monitor.calculate_sentiment_indicators(df)
            
            visualizer = MarketSentimentVisualizer()
            visualizer.create_dashboard(df_with_indicators, "demo_charts")
            print("使用模拟数据生成了演示图表")
    
    except Exception as e:
        print(f"可视化示例执行出错: {e}")
    
    finally:
        monitor.close()

def example_custom_date_range():
    """自定义日期范围示例"""
    print("\n" + "=" * 60)
    print("市场情绪监控 - 自定义日期范围示例")
    print("=" * 60)
    
    monitor = MarketSentimentMonitor()
    
    try:
        # 获取指定日期范围的数据
        start_date = "2025-01-20"
        end_date = "2025-01-29"
        
        print(f"\n获取 {start_date} 到 {end_date} 的市场情绪数据...")
        df = monitor.get_market_sentiment_data(start_date, end_date)
        
        if df is not None and not df.empty:
            print(f"成功获取 {len(df)} 天的数据")
            
            # 计算指标
            df_with_indicators = monitor.calculate_sentiment_indicators(df)
            
            # 显示统计信息
            print("\n数据统计:")
            print(f"数据天数: {len(df_with_indicators)}")
            print(f"平均上涨家数: {df_with_indicators['内地-上涨家数'].mean():.0f}")
            print(f"平均下跌家数: {df_with_indicators['内地-下跌家数'].mean():.0f}")
            print(f"平均涨停家数: {df_with_indicators['内地-涨停家数'].mean():.0f}")
            print(f"平均跌停家数: {df_with_indicators['内地-跌停家数'].mean():.0f}")
            
            if '情绪指标' in df_with_indicators.columns:
                print(f"平均情绪指标: {df_with_indicators['情绪指标'].mean():.2f}")
                print(f"情绪指标范围: {df_with_indicators['情绪指标'].min():.2f} ~ {df_with_indicators['情绪指标'].max():.2f}")
            
            # 保存数据
            filepath = monitor.save_data(df_with_indicators, f"market_sentiment_{start_date}_{end_date}.csv")
            if filepath:
                print(f"\n数据已保存到: {filepath}")
        
        else:
            print("未能获取到指定日期范围的市场情绪数据")
    
    except Exception as e:
        print(f"自定义日期范围示例执行出错: {e}")
    
    finally:
        monitor.close()

def main():
    """主函数 - 运行所有示例"""
    print("市场情绪监控程序使用示例")
    print("=" * 60)
    
    # 运行基本使用示例
    example_basic_usage()
    
    # 运行可视化示例
    example_visualization()
    
    # 运行自定义日期范围示例
    example_custom_date_range()
    
    print("\n" + "=" * 60)
    print("所有示例执行完成")
    print("=" * 60)

if __name__ == "__main__":
    # 导入pandas用于模拟数据
    import pandas as pd
    main()
