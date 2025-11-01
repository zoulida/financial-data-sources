#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股情绪周期日线打分主程序
整合数据获取和评分计算，输出每日情绪得分

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

# 导入自定义模块
from src.市场情绪.data_fetcher import A股数据获取器
from src.市场情绪.score_calculator import A股情绪评分计算器

class A股情绪周期打分器:
    """A股情绪周期日线打分主程序"""
    
    def __init__(self, log_level=logging.INFO):
        """
        初始化A股情绪周期打分器
        
        Args:
            log_level: 日志级别
        """
        self.setup_logging(log_level)
        
        # 初始化数据获取器和评分计算器
        self.数据获取器 = A股数据获取器(log_level)
        self.评分计算器 = A股情绪评分计算器(log_level)
    
    def setup_logging(self, log_level):
        """设置日志"""
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'a_stock_emotion_scorer_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def 运行每日打分(self, 开始日期: str = None, 结束日期: str = None) -> pd.DataFrame:
        """
        运行每日情绪打分
        
        Args:
            开始日期: 开始日期，格式: '2025-01-01'，如果为None则使用最近30天
            结束日期: 结束日期，格式: '2025-01-29'，如果为None则使用今天
            
        Returns:
            DataFrame: 包含每日情绪得分的DataFrame
        """
        if 结束日期 is None:
            结束日期 = datetime.now().strftime('%Y-%m-%d')
        
        if 开始日期 is None:
            开始日期 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        self.logger.info(f"开始运行A股情绪周期打分: {开始日期} 到 {结束日期}")
        
        try:
            # 步骤1: 获取所有数据
            self.logger.info("步骤1: 获取所有指标数据")
            所有数据 = self.数据获取器.获取所有数据(开始日期, 结束日期)
            
            # 检查数据获取结果
            数据获取状态 = {}
            for 指标名, 数据 in 所有数据.items():
                if 数据 is not None and not 数据.empty:
                    数据获取状态[指标名] = f"成功 ({len(数据)} 条记录)"
                else:
                    数据获取状态[指标名] = "失败"
            
            self.logger.info(f"数据获取状态: {数据获取状态}")
            
            # 步骤2: 计算综合得分
            self.logger.info("步骤2: 计算综合得分")
            结果数据 = self.评分计算器.计算综合得分(所有数据)
            
            if 结果数据.empty:
                self.logger.error("计算结果为空")
                return pd.DataFrame()
            
            # 步骤3: 添加情绪状态判断
            self.logger.info("步骤3: 添加情绪状态判断")
            结果数据 = self._添加情绪状态判断(结果数据)
            
            # 步骤4: 重新排列列顺序
            列顺序 = ['日期', '成交量得分', '涨跌停得分', '波动率得分', 
                    '涨跌广度得分', '融资余额得分', 
                    '综合得分', '情绪状态']
            
            现有列 = [col for col in 列顺序 if col in 结果数据.columns]
            结果数据 = 结果数据[现有列]
            
            self.logger.info(f"情绪打分完成，共计算 {len(结果数据)} 天的数据")
            return 结果数据
            
        except Exception as e:
            self.logger.error(f"运行每日打分时发生错误: {e}")
            return pd.DataFrame()
    
    def _添加情绪状态判断(self, 结果数据: pd.DataFrame) -> pd.DataFrame:
        """
        添加情绪状态判断
        
        Args:
            结果数据: 结果数据
            
        Returns:
            DataFrame: 添加情绪状态后的数据
        """
        def 情绪状态判断函数(综合得分):
            if pd.isna(综合得分):
                return "数据不足"
            elif 综合得分 >= 80:
                return "极度乐观"
            elif 综合得分 >= 70:
                return "乐观"
            elif 综合得分 >= 60:
                return "偏乐观"
            elif 综合得分 >= 50:
                return "中性"
            elif 综合得分 >= 40:
                return "偏悲观"
            elif 综合得分 >= 30:
                return "悲观"
            else:
                return "极度悲观"
        
        结果数据['情绪状态'] = 结果数据['综合得分'].apply(情绪状态判断函数)
        return 结果数据
    
    def 打印最新结果(self, 结果数据: pd.DataFrame):
        """
        打印最新一天的结果
        
        Args:
            结果数据: 结果数据
        """
        if 结果数据.empty:
            print("无数据可显示")
            return
        
        最新数据 = 结果数据.iloc[-1]
        
        print("\n" + "=" * 60)
        print("A股情绪周期最新得分")
        print("=" * 60)
        print(f"日期: {最新数据['日期'].strftime('%Y-%m-%d')}")
        print(f"综合得分: {最新数据['综合得分']:.2f}")
        print(f"情绪状态: {最新数据['情绪状态']}")
        print("-" * 40)
        print("各指标得分:")
        
        指标权重 = self.评分计算器.权重配置
        for 指标名, 权重 in 指标权重.items():
            得分列名 = f'{指标名}得分'
            if 得分列名 in 最新数据 and not pd.isna(最新数据[得分列名]):
                得分 = 最新数据[得分列名]
                权重百分比 = 权重 * 100
                print(f"  {指标名:8s}: {得分:6.2f} (权重: {权重百分比:5.1f}%)")
        
        print("=" * 60)
    
    def 保存结果(self, 结果数据: pd.DataFrame, 文件名: str = None) -> str:
        """
        保存结果到CSV文件
        
        Args:
            结果数据: 结果数据
            文件名: 文件名
            
        Returns:
            str: 保存的文件路径
        """
        if 文件名 is None:
            时间戳 = datetime.now().strftime("%Y%m%d_%H%M%S")
            文件名 = f"a_stock_emotion_daily_score_{时间戳}.csv"
        
        # 确保保存目录存在
        保存目录 = os.path.join(project_root, 'data')
        os.makedirs(保存目录, exist_ok=True)
        
        文件路径 = os.path.join(保存目录, 文件名)
        
        try:
            结果数据.to_csv(文件路径, encoding='utf-8-sig', index=False)
            self.logger.info(f"结果已保存到: {文件路径}")
            return 文件路径
        except Exception as e:
            self.logger.error(f"保存结果失败: {e}")
            return ""
    
    def 生成统计报告(self, 结果数据: pd.DataFrame) -> Dict:
        """
        生成统计报告
        
        Args:
            结果数据: 结果数据
            
        Returns:
            Dict: 统计报告
        """
        if 结果数据.empty:
            return {}
        
        报告 = {}
        
        # 基本统计
        报告['基本统计'] = {
            '数据天数': len(结果数据),
            '平均综合得分': round(结果数据['综合得分'].mean(), 2),
            '最高综合得分': round(结果数据['综合得分'].max(), 2),
            '最低综合得分': round(结果数据['综合得分'].min(), 2),
            '综合得分标准差': round(结果数据['综合得分'].std(), 2)
        }
        
        # 情绪状态分布
        情绪状态分布 = 结果数据['情绪状态'].value_counts().to_dict()
        报告['情绪状态分布'] = 情绪状态分布
        
        # 各指标平均得分
        指标平均得分 = {}
        指标权重 = self.评分计算器.权重配置
        for 指标名 in 指标权重.keys():
            得分列名 = f'{指标名}得分'
            if 得分列名 in 结果数据.columns:
                指标平均得分[指标名] = round(结果数据[得分列名].mean(), 2)
        
        报告['各指标平均得分'] = 指标平均得分
        
        # 最近趋势
        if len(结果数据) >= 5:
            最近5日平均 = 结果数据['综合得分'].tail(5).mean()
            前5日平均 = 结果数据['综合得分'].head(5).mean()
            趋势 = "上升" if 最近5日平均 > 前5日平均 else "下降"
            报告['最近趋势'] = {
                '最近5日平均得分': round(最近5日平均, 2),
                '前5日平均得分': round(前5日平均, 2),
                '趋势': 趋势
            }
        
        return 报告
    
    def 关闭(self):
        """关闭所有资源"""
        self.数据获取器.close()
        self.logger.info("A股情绪周期打分器已关闭")


def main():
    """主函数"""
    print("=" * 60)
    print("A股情绪周期日线打分程序")
    print("=" * 60)
    
    # 创建打分器
    打分器 = A股情绪周期打分器()
    
    try:
        # 运行每日打分（最近30天）
        print("\n正在运行A股情绪周期打分...")
        结果数据 = 打分器.运行每日打分()
        
        if not 结果数据.empty:
            # 打印最新结果
            打分器.打印最新结果(结果数据)
            
            # 生成统计报告
            print("\n正在生成统计报告...")
            统计报告 = 打分器.生成统计报告(结果数据)
            
            print("\n统计报告:")
            print("-" * 40)
            for 类别, 内容 in 统计报告.items():
                print(f"\n{类别}:")
                if isinstance(内容, dict):
                    for 键, 值 in 内容.items():
                        print(f"  {键}: {值}")
                else:
                    print(f"  {内容}")
            
            # 保存结果
            print("\n正在保存结果...")
            文件路径 = 打分器.保存结果(结果数据)
            if 文件路径:
                print(f"结果已保存到: {文件路径}")
            
            # 显示最近10天的数据
            print(f"\n最近10天数据:")
            print("-" * 80)
            显示列 = ['日期', '综合得分', '情绪状态']
            显示数据 = 结果数据[显示列].tail(10)
            print(显示数据.to_string(index=False))
        
        else:
            print("未能获取到有效数据")
    
    except Exception as e:
        print(f"程序执行出错: {e}")
        打分器.logger.error(f"程序执行出错: {e}")
    
    finally:
        # 关闭资源
        打分器.关闭()
        print("\n程序执行完成")


if __name__ == "__main__":
    main()
