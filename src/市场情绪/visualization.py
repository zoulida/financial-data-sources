#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场情绪数据可视化模块
提供市场情绪数据的图表展示功能

作者: AI Assistant
创建时间: 2025-01-29
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
import seaborn as sns
from typing import Optional, List, Dict
import os

# 设置中文字体
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS', 'WenQuanYi Micro Hei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 10

# 尝试设置中文字体
try:
    import matplotlib.font_manager as fm
    # 查找系统中可用的中文字体
    chinese_fonts = []
    for font in fm.fontManager.ttflist:
        if any(name in font.name.lower() for name in ['simhei', 'microsoft', 'yahei', 'wenquanyi', 'dejavu']):
            chinese_fonts.append(font.name)
    
    if chinese_fonts:
        matplotlib.rcParams['font.sans-serif'] = chinese_fonts[:3] + ['DejaVu Sans']
        print(f"使用中文字体: {chinese_fonts[:3]}")
    else:
        print("未找到中文字体，使用默认字体")
except Exception as e:
    print(f"字体设置失败: {e}")

class MarketSentimentVisualizer:
    """市场情绪数据可视化类"""
    
    def __init__(self, style='seaborn-v0_8'):
        """
        初始化可视化器
        
        Args:
            style: matplotlib样式
        """
        plt.style.use(style)
        self.colors = {
            '上涨': '#ff4444',
            '下跌': '#4444ff', 
            '平盘': '#888888',
            '涨停': '#ff0000',
            '跌停': '#0000ff',
            '情绪指标': '#ff6600'
        }
    
    def plot_sentiment_overview(self, df: pd.DataFrame, save_path: Optional[str] = None) -> None:
        """
        绘制市场情绪概览图
        
        Args:
            df: 市场情绪数据
            save_path: 保存路径，如果为None则显示图表
        """
        if df is None or df.empty:
            print("数据为空，无法绘制图表")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('市场情绪概览', fontsize=16, fontweight='bold')
        
        # 1. 涨跌家数对比
        ax1 = axes[0, 0]
        ax1.plot(df.index, df['内地-上涨家数'], label='上涨家数', color=self.colors['上涨'], linewidth=2)
        ax1.plot(df.index, df['内地-下跌家数'], label='下跌家数', color=self.colors['下跌'], linewidth=2)
        ax1.set_title('涨跌家数对比')
        ax1.set_ylabel('家数')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 涨跌停家数
        ax2 = axes[0, 1]
        ax2.plot(df.index, df['内地-涨停家数'], label='涨停家数', color=self.colors['涨停'], linewidth=2)
        ax2.plot(df.index, df['内地-跌停家数'], label='跌停家数', color=self.colors['跌停'], linewidth=2)
        ax2.set_title('涨跌停家数')
        ax2.set_ylabel('家数')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 市场强度
        if '市场强度' in df.columns:
            ax3 = axes[1, 0]
            ax3.plot(df.index, df['市场强度'], label='市场强度', color=self.colors['情绪指标'], linewidth=2)
            ax3.axhline(y=0, color='black', linestyle='--', alpha=0.5)
            ax3.set_title('市场强度指标')
            ax3.set_ylabel('强度值')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # 4. 情绪指标
        if '情绪指标' in df.columns:
            ax4 = axes[1, 1]
            ax4.plot(df.index, df['情绪指标'], label='情绪指标', color=self.colors['情绪指标'], linewidth=2)
            ax4.axhline(y=0, color='black', linestyle='--', alpha=0.5)
            ax4.axhline(y=20, color='red', linestyle='--', alpha=0.5, label='极度乐观线')
            ax4.axhline(y=-20, color='blue', linestyle='--', alpha=0.5, label='极度悲观线')
            ax4.set_title('市场情绪指标')
            ax4.set_ylabel('情绪值')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        # 设置x轴日期格式
        for ax in axes.flat:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        else:
            plt.show()
    
    def plot_sentiment_heatmap(self, df: pd.DataFrame, save_path: Optional[str] = None) -> None:
        """
        绘制市场情绪热力图
        
        Args:
            df: 市场情绪数据
            save_path: 保存路径
        """
        if df is None or df.empty:
            print("数据为空，无法绘制图表")
            return
        
        # 选择要可视化的列
        heatmap_data = df[['内地-上涨家数', '内地-下跌家数', '内地-平盘家数', 
                          '内地-涨停家数', '内地-跌停家数']].T
        
        plt.figure(figsize=(12, 6))
        sns.heatmap(heatmap_data, 
                   cmap='RdYlBu_r', 
                   annot=True, 
                   fmt='d',
                   cbar_kws={'label': '家数'})
        
        plt.title('市场情绪热力图', fontsize=14, fontweight='bold')
        plt.xlabel('日期')
        plt.ylabel('指标类型')
        
        # 设置x轴日期格式
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"热力图已保存到: {save_path}")
        else:
            plt.show()
    
    def plot_sentiment_distribution(self, df: pd.DataFrame, save_path: Optional[str] = None) -> None:
        """
        绘制市场情绪分布图
        
        Args:
            df: 市场情绪数据
            save_path: 保存路径
        """
        if df is None or df.empty:
            print("数据为空，无法绘制图表")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('市场情绪分布分析', fontsize=16, fontweight='bold')
        
        # 1. 上涨比例分布
        if '上涨比例' in df.columns:
            ax1 = axes[0, 0]
            ax1.hist(df['上涨比例'], bins=20, alpha=0.7, color=self.colors['上涨'], edgecolor='black')
            ax1.set_title('上涨比例分布')
            ax1.set_xlabel('上涨比例')
            ax1.set_ylabel('频次')
            ax1.grid(True, alpha=0.3)
        
        # 2. 下跌比例分布
        if '下跌比例' in df.columns:
            ax2 = axes[0, 1]
            ax2.hist(df['下跌比例'], bins=20, alpha=0.7, color=self.colors['下跌'], edgecolor='black')
            ax2.set_title('下跌比例分布')
            ax2.set_xlabel('下跌比例')
            ax2.set_ylabel('频次')
            ax2.grid(True, alpha=0.3)
        
        # 3. 情绪指标分布
        if '情绪指标' in df.columns:
            ax3 = axes[1, 0]
            ax3.hist(df['情绪指标'], bins=20, alpha=0.7, color=self.colors['情绪指标'], edgecolor='black')
            ax3.axvline(x=0, color='black', linestyle='--', alpha=0.5, label='中性线')
            ax3.set_title('情绪指标分布')
            ax3.set_xlabel('情绪指标值')
            ax3.set_ylabel('频次')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # 4. 涨跌比分布
        if '涨跌比' in df.columns:
            ax4 = axes[1, 1]
            ax4.hist(df['涨跌比'], bins=20, alpha=0.7, color='purple', edgecolor='black')
            ax4.axvline(x=1, color='black', linestyle='--', alpha=0.5, label='平衡线')
            ax4.set_title('涨跌比分布')
            ax4.set_xlabel('涨跌比')
            ax4.set_ylabel('频次')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"分布图已保存到: {save_path}")
        else:
            plt.show()
    
    def plot_sentiment_trend(self, df: pd.DataFrame, save_path: Optional[str] = None) -> None:
        """
        绘制市场情绪趋势图
        
        Args:
            df: 市场情绪数据
            save_path: 保存路径
        """
        if df is None or df.empty:
            print("数据为空，无法绘制图表")
            return
        
        plt.figure(figsize=(15, 8))
        
        # 创建双y轴
        fig, ax1 = plt.subplots(figsize=(15, 8))
        ax2 = ax1.twinx()
        
        # 绘制涨跌家数
        line1 = ax1.plot(df.index, df['内地-上涨家数'], 
                        label='上涨家数', color=self.colors['上涨'], linewidth=2)
        line2 = ax1.plot(df.index, df['内地-下跌家数'], 
                        label='下跌家数', color=self.colors['下跌'], linewidth=2)
        
        # 绘制情绪指标
        if '情绪指标' in df.columns:
            line3 = ax2.plot(df.index, df['情绪指标'], 
                            label='情绪指标', color=self.colors['情绪指标'], 
                            linewidth=3, linestyle='--')
        
        # 设置标签和标题
        ax1.set_xlabel('日期')
        ax1.set_ylabel('家数', color='black')
        ax2.set_ylabel('情绪指标值', color=self.colors['情绪指标'])
        ax1.set_title('市场情绪趋势分析', fontsize=16, fontweight='bold')
        
        # 合并图例
        lines = line1 + line2
        if '情绪指标' in df.columns:
            lines += line3
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left')
        
        # 添加网格
        ax1.grid(True, alpha=0.3)
        
        # 设置x轴日期格式
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"趋势图已保存到: {save_path}")
        else:
            plt.show()
    
    def create_dashboard(self, df: pd.DataFrame, save_dir: str = "charts") -> None:
        """
        创建完整的市场情绪仪表板
        
        Args:
            df: 市场情绪数据
            save_dir: 保存目录
        """
        if df is None or df.empty:
            print("数据为空，无法创建仪表板")
            return
        
        # 创建保存目录
        os.makedirs(save_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成各种图表
        print("正在生成市场情绪仪表板...")
        
        # 1. 概览图
        overview_path = os.path.join(save_dir, f"sentiment_overview_{timestamp}.png")
        self.plot_sentiment_overview(df, overview_path)
        
        # 2. 热力图
        heatmap_path = os.path.join(save_dir, f"sentiment_heatmap_{timestamp}.png")
        self.plot_sentiment_heatmap(df, heatmap_path)
        
        # 3. 分布图
        distribution_path = os.path.join(save_dir, f"sentiment_distribution_{timestamp}.png")
        self.plot_sentiment_distribution(df, distribution_path)
        
        # 4. 趋势图
        trend_path = os.path.join(save_dir, f"sentiment_trend_{timestamp}.png")
        self.plot_sentiment_trend(df, trend_path)
        
        print(f"仪表板图表已保存到目录: {save_dir}")


def main():
    """测试可视化功能"""
    # 创建示例数据
    dates = pd.date_range('2025-01-25', periods=5, freq='D')
    
    data = {
        '内地-上涨家数': [3200, 2800, 3500, 3100, 2900],
        '内地-下跌家数': [1500, 2000, 1200, 1600, 1800],
        '内地-平盘家数': [300, 200, 300, 300, 300],
        '内地-涨停家数': [80, 60, 90, 75, 65],
        '内地-跌停家数': [20, 40, 15, 25, 35]
    }
    
    df = pd.DataFrame(data, index=dates)
    
    # 计算指标
    df['总股票数'] = df['内地-上涨家数'] + df['内地-下跌家数'] + df['内地-平盘家数']
    df['上涨比例'] = df['内地-上涨家数'] / df['总股票数']
    df['下跌比例'] = df['内地-下跌家数'] / df['总股票数']
    df['市场强度'] = (df['上涨比例'] - df['下跌比例']) * 100
    df['情绪指标'] = ((df['上涨比例'] - df['下跌比例']) + 
                     (df['内地-涨停家数'] / df['总股票数'] - df['内地-跌停家数'] / df['总股票数']) * 0.5) * 100
    
    # 创建可视化器
    visualizer = MarketSentimentVisualizer()
    
    # 生成仪表板
    visualizer.create_dashboard(df, "market_sentiment_charts")


if __name__ == "__main__":
    main()
