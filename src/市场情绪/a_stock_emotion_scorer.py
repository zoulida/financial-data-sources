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

# 邮件发送工具路径
MAIL_TOOL_PATH = r'D:\pythonworkspace\zldtools'
if MAIL_TOOL_PATH not in sys.path:
    sys.path.append(MAIL_TOOL_PATH)
try:
    from tools.mail.MailtoMe import sendMailWithAttachments, sendMailWithInlineImages
    MAIL_AVAILABLE = True
except Exception as mail_import_error:  # pylint: disable=broad-except
    MAIL_AVAILABLE = False
    print(f"警告: 邮件发送模块不可用: {mail_import_error}")

# 导入自定义模块
from src.市场情绪.data_fetcher import A股数据获取器
from src.市场情绪.score_calculator import A股情绪评分计算器

# 导入日期范围获取工具
try:
    # 添加md目录到路径
    md_path = os.path.join(project_root, 'md', '获取enddate')
    if md_path not in sys.path:
        sys.path.insert(0, md_path)
    from get_date_range import get_date_range_formatted
    DATE_RANGE_AVAILABLE = True
except ImportError as e:
    DATE_RANGE_AVAILABLE = False
    print(f"警告: 无法导入日期范围工具: {e}")

# 导入绘图库
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib
    # 设置中文字体
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS', 'WenQuanYi Micro Hei']
    matplotlib.rcParams['axes.unicode_minus'] = False
    matplotlib.rcParams['font.size'] = 10
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("警告: matplotlib 未安装，无法生成图表")

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
            开始日期: 开始日期，格式: '2025-01-01'，如果为None则使用最近15天
            结束日期: 结束日期，格式: '2025-01-29'，如果为None则通过get_date_range获取
            
        Returns:
            DataFrame: 包含每日情绪得分的DataFrame
        """
        if 结束日期 is None:
            if DATE_RANGE_AVAILABLE:
                try:
                    _, 结束日期, 原因 = get_date_range_formatted(with_dash=True)
                    self.logger.info(f"通过日期范围工具获取结束日期: {结束日期} ({原因})")
                except Exception as e:
                    self.logger.warning(f"获取日期范围失败，使用当前日期: {e}")
                    结束日期 = datetime.now().strftime('%Y-%m-%d')
            else:
                结束日期 = datetime.now().strftime('%Y-%m-%d')
                self.logger.warning("日期范围工具不可用，使用当前日期作为结束日期")
        
        if 开始日期 is None:
            开始日期 = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
        
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
            
            # 步骤5: 过滤无效日期
            if '日期' in 结果数据.columns:
                结果数据 = 结果数据.copy()
                结果数据['日期'] = pd.to_datetime(结果数据['日期'], errors='coerce')
                
                # 过滤掉无效日期（1970年之前的日期，或者未来日期）
                当前日期 = datetime.now()
                未来日期 = 当前日期 + timedelta(days=1)
                结果数据 = 结果数据[
                    (结果数据['日期'] >= pd.Timestamp('2020-01-01')) &
                    (结果数据['日期'] <= pd.Timestamp(未来日期)) &
                    (结果数据['日期'].notna())
                ]
                
                # 只保留最近30天的数据
                if not 结果数据.empty:
                    最近日期 = 结果数据['日期'].max()
                    最早日期 = 最近日期 - timedelta(days=30)
                    结果数据 = 结果数据[结果数据['日期'] >= 最早日期]
                    结果数据 = 结果数据.sort_values('日期')
            
            self.logger.info(f"情绪打分完成，共计算 {len(结果数据)} 天的数据")
            if not 结果数据.empty and '日期' in 结果数据.columns:
                self.logger.info(f"有效日期范围: {结果数据['日期'].min().strftime('%Y-%m-%d')} 到 {结果数据['日期'].max().strftime('%Y-%m-%d')}")
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
    
    def _计算日期刻度间隔(self, 日期列: pd.Series) -> int:
        """
        根据数据天数智能计算日期刻度间隔
        
        Args:
            日期列: 日期序列
            
        Returns:
            int: 刻度间隔（天数）
        """
        数据天数 = len(日期列)
        
        if 数据天数 <= 10:
            # 10天以内，每天显示
            return 1
        elif 数据天数 <= 20:
            # 10-20天，每2天显示
            return 2
        elif 数据天数 <= 30:
            # 20-30天，每3天显示
            return 3
        elif 数据天数 <= 60:
            # 30-60天，每5天显示
            return 5
        else:
            # 60天以上，每7天显示
            return 7
    
    def _设置日期轴(self, ax, 日期列: pd.Series):
        """
        统一设置日期轴格式
        
        Args:
            ax: matplotlib轴对象
            日期列: 日期序列
        """
        # 确保日期列是datetime类型
        if not pd.api.types.is_datetime64_any_dtype(日期列):
            日期列 = pd.to_datetime(日期列)
        
        # 计算合适的间隔
        间隔 = self._计算日期刻度间隔(日期列)
        
        # 设置日期格式和刻度
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=间隔))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def 生成走势图(self, 结果数据: pd.DataFrame, 保存目录: str = None, 显示图表: bool = False) -> List[str]:
        """
        生成情绪得分走势图
        
        Args:
            结果数据: 结果数据
            保存目录: 保存目录，如果为None则使用默认目录
            显示图表: 是否显示图表
            
        Returns:
            List[str]: 保存的文件路径列表
        """
        if not MATPLOTLIB_AVAILABLE:
            self.logger.warning("matplotlib 未安装，无法生成图表")
            return []
        
        if 结果数据.empty:
            self.logger.warning("数据为空，无法生成图表")
            return []
        
        # 设置保存目录
        if 保存目录 is None:
            # 保存到 src/市场情绪/charts 目录下
            当前文件目录 = os.path.dirname(os.path.abspath(__file__))
            保存目录 = os.path.join(当前文件目录, 'charts')
        os.makedirs(保存目录, exist_ok=True)

        # 清空保存目录中的旧图表文件
        try:
            for 文件名 in os.listdir(保存目录):
                文件路径 = os.path.join(保存目录, 文件名)
                if os.path.isfile(文件路径):
                    os.remove(文件路径)
        except Exception as e:
            self.logger.warning(f"清理图表目录失败: {e}")

        时间戳 = datetime.now().strftime("%Y%m%d_%H%M%S")
        保存路径列表 = []
        
        try:
            # 确保日期列为datetime类型
            if '日期' in 结果数据.columns:
                结果数据 = 结果数据.copy()
                结果数据['日期'] = pd.to_datetime(结果数据['日期'], errors='coerce')
                
                # 过滤掉无效日期（比如1970年之前的日期，或者未来日期）
                当前日期 = datetime.now()
                未来日期 = 当前日期 + timedelta(days=1)  # 允许今天的数据
                结果数据 = 结果数据[
                    (结果数据['日期'] >= pd.Timestamp('2020-01-01')) &  # 只保留2020年之后的数据
                    (结果数据['日期'] <= pd.Timestamp(未来日期)) &  # 不包含未来日期
                    (结果数据['日期'].notna())  # 排除NaN日期
                ]
                
                if 结果数据.empty:
                    self.logger.warning("过滤后数据为空，无法生成图表")
                    return []
                
                结果数据 = 结果数据.sort_values('日期')
                日期列 = 结果数据['日期']
                
                # 只保留最近的有效数据（最多30天）
                最近日期 = 日期列.max()
                最早日期 = 最近日期 - timedelta(days=30)
                结果数据 = 结果数据[结果数据['日期'] >= 最早日期]
                日期列 = 结果数据['日期']
                
                self.logger.info(f"数据日期范围: {日期列.min().strftime('%Y-%m-%d')} 到 {日期列.max().strftime('%Y-%m-%d')}, 共 {len(日期列)} 天")
            else:
                self.logger.warning("未找到日期列，无法生成图表")
                return []
            
            # 1. 综合得分走势图
            路径1 = self._绘制综合得分走势图(结果数据, 日期列, 保存目录, 时间戳, 显示图表)
            if 路径1:
                保存路径列表.append(路径1)
            
            # 2. 各指标得分对比图
            路径2 = self._绘制指标得分对比图(结果数据, 日期列, 保存目录, 时间戳, 显示图表)
            if 路径2:
                保存路径列表.append(路径2)
            
            # 3. 综合得分与情绪状态图
            路径3 = self._绘制综合得分与状态图(结果数据, 日期列, 保存目录, 时间戳, 显示图表)
            if 路径3:
                保存路径列表.append(路径3)
            
            # 4. 各指标得分详细图
            路径4 = self._绘制指标得分详细图(结果数据, 日期列, 保存目录, 时间戳, 显示图表)
            if 路径4:
                保存路径列表.append(路径4)
            
            self.logger.info(f"已生成 {len(保存路径列表)} 个图表文件")
            return 保存路径列表
            
        except Exception as e:
            self.logger.error(f"生成走势图时发生错误: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def _绘制综合得分走势图(self, 结果数据: pd.DataFrame, 日期列: pd.Series, 
                         保存目录: str, 时间戳: str, 显示图表: bool) -> Optional[str]:
        """绘制综合得分走势图"""
        try:
            fig, ax = plt.subplots(figsize=(15, 8))
            
            # 绘制综合得分
            ax.plot(日期列, 结果数据['综合得分'], 
                   marker='o', linewidth=2, markersize=4, 
                   color='#1f77b4', label='综合得分', alpha=0.8)
            
            # 添加情绪状态区域背景色
            情绪状态颜色 = {
                '极度乐观': '#ff0000',
                '乐观': '#ff8800',
                '偏乐观': '#ffbb00',
                '中性': '#888888',
                '偏悲观': '#00bbff',
                '悲观': '#0088ff',
                '极度悲观': '#0000ff'
            }
            
            # 添加分界线
            ax.axhline(y=80, color='red', linestyle='--', linewidth=1, alpha=0.5, label='极度乐观线 (80)')
            ax.axhline(y=70, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='乐观线 (70)')
            ax.axhline(y=60, color='yellow', linestyle='--', linewidth=1, alpha=0.5, label='偏乐观线 (60)')
            ax.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='中性线 (50)')
            ax.axhline(y=40, color='lightblue', linestyle='--', linewidth=1, alpha=0.5, label='偏悲观线 (40)')
            ax.axhline(y=30, color='blue', linestyle='--', linewidth=1, alpha=0.5, label='悲观线 (30)')
            
            # 设置图表样式
            ax.set_xlabel('日期', fontsize=12, fontweight='bold')
            ax.set_ylabel('综合得分', fontsize=12, fontweight='bold')
            ax.set_title('A股情绪周期综合得分走势图', fontsize=14, fontweight='bold', pad=20)
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.legend(loc='best', fontsize=9)
            
            # 设置x轴日期格式
            self._设置日期轴(ax, 日期列)
            
            plt.tight_layout()
            
            文件路径 = os.path.join(保存目录, f'emotion_score_trend_{时间戳}.png')
            plt.savefig(文件路径, dpi=300, bbox_inches='tight')
            self.logger.info(f"综合得分走势图已保存: {文件路径}")
            
            if 显示图表:
                plt.show()
            else:
                plt.close()
            
            return 文件路径
        except Exception as e:
            self.logger.error(f"绘制综合得分走势图失败: {e}")
            plt.close()
            return None
    
    def _绘制指标得分对比图(self, 结果数据: pd.DataFrame, 日期列: pd.Series,
                         保存目录: str, 时间戳: str, 显示图表: bool) -> Optional[str]:
        """绘制各指标得分对比图"""
        try:
            # 获取所有得分列
            得分列列表 = [col for col in 结果数据.columns if col.endswith('得分') and col != '综合得分']
            
            if not 得分列列表:
                self.logger.warning("未找到指标得分列")
                return None
            
            fig, ax = plt.subplots(figsize=(15, 8))
            
            # 颜色列表
            颜色列表 = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            
            # 绘制各指标得分
            for i, 列名 in enumerate(得分列列表):
                颜色 = 颜色列表[i % len(颜色列表)]
                指标名 = 列名.replace('得分', '')
                ax.plot(日期列, 结果数据[列名], 
                       marker='o', linewidth=1.5, markersize=3, 
                       color=颜色, label=指标名, alpha=0.7)
            
            # 绘制综合得分（加粗）
            if '综合得分' in 结果数据.columns:
                ax.plot(日期列, 结果数据['综合得分'], 
                       marker='o', linewidth=3, markersize=5, 
                       color='black', label='综合得分', alpha=0.9, zorder=10)
            
            # 设置图表样式
            ax.set_xlabel('日期', fontsize=12, fontweight='bold')
            ax.set_ylabel('得分', fontsize=12, fontweight='bold')
            ax.set_title('A股情绪周期各指标得分对比图', fontsize=14, fontweight='bold', pad=20)
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.legend(loc='best', fontsize=9, ncol=2)
            
            # 设置x轴日期格式
            self._设置日期轴(ax, 日期列)
            
            plt.tight_layout()
            
            文件路径 = os.path.join(保存目录, f'emotion_indicators_comparison_{时间戳}.png')
            plt.savefig(文件路径, dpi=300, bbox_inches='tight')
            self.logger.info(f"指标得分对比图已保存: {文件路径}")
            
            if 显示图表:
                plt.show()
            else:
                plt.close()
            
            return 文件路径
        except Exception as e:
            self.logger.error(f"绘制指标得分对比图失败: {e}")
            plt.close()
            return None
    
    def _绘制综合得分与状态图(self, 结果数据: pd.DataFrame, 日期列: pd.Series,
                           保存目录: str, 时间戳: str, 显示图表: bool) -> Optional[str]:
        """绘制综合得分与情绪状态图"""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
            
            # 上图：综合得分
            ax1.plot(日期列, 结果数据['综合得分'], 
                    marker='o', linewidth=2, markersize=4, 
                    color='#1f77b4', label='综合得分', alpha=0.8)
            ax1.axhline(y=80, color='red', linestyle='--', linewidth=1, alpha=0.5)
            ax1.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            ax1.axhline(y=30, color='blue', linestyle='--', linewidth=1, alpha=0.5)
            ax1.set_ylabel('综合得分', fontsize=12, fontweight='bold')
            ax1.set_title('A股情绪周期综合得分与情绪状态', fontsize=14, fontweight='bold', pad=20)
            ax1.set_ylim(0, 100)
            ax1.grid(True, alpha=0.3, linestyle='--')
            ax1.legend(loc='best')
            
            # 下图：情绪状态（用颜色表示）
            if '情绪状态' in 结果数据.columns:
                状态映射 = {
                    '极度乐观': 7,
                    '乐观': 6,
                    '偏乐观': 5,
                    '中性': 4,
                    '偏悲观': 3,
                    '悲观': 2,
                    '极度悲观': 1,
                    '数据不足': 0
                }
                状态数值 = 结果数据['情绪状态'].map(状态映射).fillna(0)
                
                # 使用散点图显示状态
                颜色映射 = {
                    '极度乐观': '#ff0000',
                    '乐观': '#ff8800',
                    '偏乐观': '#ffbb00',
                    '中性': '#888888',
                    '偏悲观': '#00bbff',
                    '悲观': '#0088ff',
                    '极度悲观': '#0000ff',
                    '数据不足': '#cccccc'
                }
                
                for 状态, 数值 in 状态映射.items():
                    状态数据 = 结果数据[结果数据['情绪状态'] == 状态]
                    if not 状态数据.empty:
                        状态日期 = 日期列[结果数据['情绪状态'] == 状态]
                        ax2.scatter(状态日期, [数值] * len(状态日期),
                                  color=颜色映射.get(状态, '#cccccc'),
                                  label=状态, s=100, alpha=0.7, edgecolors='black', linewidths=0.5)
                
                ax2.set_ylabel('情绪状态', fontsize=12, fontweight='bold')
                ax2.set_ylim(-0.5, 7.5)
                ax2.set_yticks(list(状态映射.values()))
                ax2.set_yticklabels(list(状态映射.keys()))
                ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
                ax2.legend(loc='best', fontsize=8, ncol=4)
            
            # 设置x轴日期格式
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(日期列) // 10)))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            plt.tight_layout()
            
            文件路径 = os.path.join(保存目录, f'emotion_score_and_status_{时间戳}.png')
            plt.savefig(文件路径, dpi=300, bbox_inches='tight')
            self.logger.info(f"综合得分与状态图已保存: {文件路径}")
            
            if 显示图表:
                plt.show()
            else:
                plt.close()
            
            return 文件路径
        except Exception as e:
            self.logger.error(f"绘制综合得分与状态图失败: {e}")
            plt.close()
            return None
    
    def _绘制指标得分详细图(self, 结果数据: pd.DataFrame, 日期列: pd.Series,
                         保存目录: str, 时间戳: str, 显示图表: bool) -> Optional[str]:
        """绘制各指标得分详细图（子图）"""
        try:
            # 获取所有得分列
            得分列列表 = [col for col in 结果数据.columns if col.endswith('得分') and col != '综合得分']
            
            if not 得分列列表:
                self.logger.warning("未找到指标得分列")
                return None
            
            # 计算子图布局
            指标数量 = len(得分列列表)
            行数 = (指标数量 + 1) // 2
            列数 = 2
            
            fig, axes = plt.subplots(行数, 列数, figsize=(15, 4 * 行数))
            fig.suptitle('A股情绪周期各指标得分详细图', fontsize=14, fontweight='bold', y=0.995)
            
            # 如果只有一个子图，确保axes是数组
            if 指标数量 == 1:
                axes = [axes]
            else:
                axes = axes.flatten()
            
            颜色列表 = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            
            for i, 列名 in enumerate(得分列列表):
                ax = axes[i]
                颜色 = 颜色列表[i % len(颜色列表)]
                指标名 = 列名.replace('得分', '')
                
                ax.plot(日期列, 结果数据[列名], 
                       marker='o', linewidth=2, markersize=3, 
                       color=颜色, label=指标名, alpha=0.8)
                ax.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
                ax.set_title(指标名, fontsize=11, fontweight='bold')
                ax.set_ylabel('得分', fontsize=10)
                ax.set_ylim(0, 100)
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.legend(loc='best', fontsize=9)
                
                # 设置x轴日期格式
                self._设置日期轴(ax, 日期列)
            
            # 隐藏多余的子图
            for i in range(指标数量, len(axes)):
                axes[i].set_visible(False)
            
            plt.tight_layout()
            
            文件路径 = os.path.join(保存目录, f'emotion_indicators_detail_{时间戳}.png')
            plt.savefig(文件路径, dpi=300, bbox_inches='tight')
            self.logger.info(f"指标得分详细图已保存: {文件路径}")
            
            if 显示图表:
                plt.show()
            else:
                plt.close()
            
            return 文件路径
        except Exception as e:
            self.logger.error(f"绘制指标得分详细图失败: {e}")
            plt.close()
            return None
    
    def 关闭(self):
        """关闭所有资源"""
        self.数据获取器.close()
        self.logger.info("A股情绪周期打分器已关闭")

    def 发送图表邮件(self, 图表路径列表: List[str]) -> bool:
        """将指定图表通过邮件发送"""
        if not MAIL_AVAILABLE:
            self.logger.warning("邮件发送模块不可用，跳过发送图表邮件")
            return False

        if not 图表路径列表:
            self.logger.warning("没有图表可发送")
            return False

        # 选择需要发送的图表
        附件路径 = []
        for 路径 in 图表路径列表:
            文件名 = os.path.basename(路径)
            if 'indicators_detail' in 文件名 or 'score_trend' in 文件名:
                附件路径.append(路径)

        # 确保只保留需要的两个文件
        附件路径 = 附件路径[:4]  # 容错多余路径

        if not 附件路径:
            self.logger.warning("未找到需要发送的图表附件")
            return False

        邮件日期 = datetime.now().strftime('%Y%m%d')
        主题 = f"{邮件日期}日短线情绪"
        正文 = "附件包含今日短线情绪指标，请查收。"

        try:
            # 将图片内嵌在正文中，同时附带附件以备查阅
            sendMailWithInlineImages(
                主题,
                正文,
                image_paths=附件路径,
                attachments=附件路径
            )
            self.logger.info(f"图表邮件发送成功，共发送 {len(附件路径)} 个附件")
            return True
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(f"发送图表邮件失败: {e}")
            return False


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
            
            # 生成走势图
            print("\n正在生成走势图...")
            图表路径列表 = 打分器.生成走势图(结果数据, 显示图表=False)
            if 图表路径列表:
                print(f"已生成 {len(图表路径列表)} 个图表:")
                for 路径 in 图表路径列表:
                    print(f"  - {路径}")

                # 发送图表邮件
                print("\n正在发送图表邮件...")
                邮件发送成功 = 打分器.发送图表邮件(图表路径列表)
                if 邮件发送成功:
                    print("图表邮件发送成功")
                else:
                    print("图表邮件发送失败或已跳过，详情请查看日志")
            
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
