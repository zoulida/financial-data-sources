#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股情绪周期评分计算模块
根据6个硬指标计算每日情绪得分

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

class A股情绪评分计算器:
    """A股情绪周期评分计算器"""
    
    def __init__(self, log_level=logging.INFO):
        """
        初始化评分计算器
        
        Args:
            log_level: 日志级别
        """
        self.setup_logging(log_level)
        
        # 指标权重配置
        self.权重配置 = {
            '成交量': 0.15,
            '涨跌停': 0.25,  # 原0.20 + 北向资金0.05
            '波动率': 0.10,
            '涨跌广度': 0.20,  # 原0.15 + 北向资金0.05
            '融资余额': 0.10
        }
        
        # 注意：权重总和为0.8，剩余0.2为其他因素或预留
        # 调整权重使总和为1.0
        self.权重配置 = {k: v / 0.8 for k, v in self.权重配置.items()}
        
        # 验证权重总和为1
        总权重 = sum(self.权重配置.values())
        if abs(总权重 - 1.0) > 0.001:
            self.logger.warning(f"权重总和不为1: {总权重}")
    
    def setup_logging(self, log_level):
        """设置日志"""
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'a_stock_score_calculator_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def 计算成交量得分(self, 成交额数据: pd.DataFrame) -> pd.DataFrame:
        """
        计算成交量得分（15%权重）
        
        规则：滚动250日分位，前20%给80-100，后20%给0-40，中位40-80，线性插值
        
        Args:
            成交额数据: 包含成交额数据的DataFrame
            
        Returns:
            DataFrame: 包含成交量得分的DataFrame
        """
        self.logger.info("开始计算成交量得分")
        
        结果数据 = 成交额数据.copy()
        
        # 计算250日滚动分位数
        结果数据['成交量_250日分位'] = 结果数据['成交额_万元'].rolling(250, min_periods=50).rank(pct=True)
        
        # 根据分位数计算得分
        def 成交量得分函数(分位值):
            if pd.isna(分位值):
                return 50  # 默认中等分数
            
            if 分位值 >= 0.8:  # 前20%
                return 80 + (分位值 - 0.8) / 0.2 * 20  # 80-100分
            elif 分位值 <= 0.2:  # 后20%
                return 分位值 / 0.2 * 40  # 0-40分
            else:  # 中段60%
                return 40 + (分位值 - 0.2) / 0.6 * 40  # 40-80分
        
        结果数据['成交量得分'] = 结果数据['成交量_250日分位'].apply(成交量得分函数)
        
        self.logger.info(f"成交量得分计算完成，平均得分: {结果数据['成交量得分'].mean():.2f}")
        return 结果数据[['成交量得分']]
    
    def 计算涨跌停得分(self, 涨跌停数据: pd.DataFrame) -> pd.DataFrame:
        """
        计算涨跌停得分（20%权重）
        
        规则：涨停≥50且跌停=0→100分；跌停≥30且涨停<20→0分；其余40-80线性
        
        Args:
            涨跌停数据: 包含涨跌停数据的DataFrame
            
        Returns:
            DataFrame: 包含涨跌停得分的DataFrame
        """
        self.logger.info("开始计算涨跌停得分")
        
        结果数据 = 涨跌停数据.copy()
        
        def 涨跌停得分函数(涨停数, 跌停数):
            if pd.isna(涨停数) or pd.isna(跌停数):
                return 50  # 默认中等分数
            
            # 涨停≥50且跌停=0→100分
            if 涨停数 >= 50 and 跌停数 == 0:
                return 100
            
            # 跌停≥30且涨停<20→0分
            if 跌停数 >= 30 and 涨停数 < 20:
                return 0
            
            # 其余情况40-80分线性插值
            # 基于涨停数和跌停数的比例关系
            涨停比例 = 涨停数 / (涨停数 + 跌停数 + 1)  # 加1避免除零
            return 40 + 涨停比例 * 40
        
        结果数据['涨跌停得分'] = 结果数据.apply(
            lambda row: 涨跌停得分函数(row['涨停家数'], row['跌停家数']), axis=1
        )
        
        self.logger.info(f"涨跌停得分计算完成，平均得分: {结果数据['涨跌停得分'].mean():.2f}")
        return 结果数据[['涨跌停得分']]
    
    def 计算波动率得分(self, 波动率数据: pd.DataFrame) -> pd.DataFrame:
        """
        计算波动率得分（10%权重）
        
        规则：250日分位，前20%（高波动）0-40分；后20%（低波动）80-100分；中段40-80线性
        
        Args:
            波动率数据: 包含波动率数据的DataFrame
            
        Returns:
            DataFrame: 包含波动率得分的DataFrame
        """
        self.logger.info("开始计算波动率得分")
        
        结果数据 = 波动率数据.copy()
        
        # 计算250日滚动分位数
        结果数据['波动率_250日分位'] = 结果数据['波动率'].rolling(250, min_periods=50).rank(pct=True)
        
        # 根据分位数计算得分（注意：高波动得低分，低波动得高分）
        def 波动率得分函数(分位值):
            if pd.isna(分位值):
                return 50  # 默认中等分数
            
            if 分位值 >= 0.8:  # 前20%（高波动）
                return 分位值 / 0.8 * 40  # 0-40分
            elif 分位值 <= 0.2:  # 后20%（低波动）
                return 80 + (0.2 - 分位值) / 0.2 * 20  # 80-100分
            else:  # 中段60%
                return 40 + (0.8 - 分位值) / 0.6 * 40  # 40-80分
        
        结果数据['波动率得分'] = 结果数据['波动率_250日分位'].apply(波动率得分函数)
        
        self.logger.info(f"波动率得分计算完成，平均得分: {结果数据['波动率得分'].mean():.2f}")
        return 结果数据[['波动率得分']]
    
    def 计算北向资金得分(self, 北向资金数据: pd.DataFrame) -> pd.DataFrame:
        """
        计算北向资金得分（10%权重）
        
        规则：连续5日净流入且总量>50亿→100分；连续5日净流出且总量>50亿→0分；其余40-80线性
        
        Args:
            北向资金数据: 包含北向资金数据的DataFrame
            
        Returns:
            DataFrame: 包含北向资金得分的DataFrame
        """
        self.logger.info("开始计算北向资金得分")
        
        结果数据 = 北向资金数据.copy()
        
        # 计算5日滚动净流入累计
        结果数据['北向资金_5日累计'] = 结果数据['净买入额_万元'].rolling(5, min_periods=1).sum()
        
        # 计算5日连续净流入/净流出状态
        结果数据['北向资金_5日连续净流入'] = (
            结果数据['净买入额_万元'].rolling(5, min_periods=1).apply(
                lambda x: 1 if len(x) == 5 and (x > 0).all() else 0
            )
        )
        
        结果数据['北向资金_5日连续净流出'] = (
            结果数据['净买入额_万元'].rolling(5, min_periods=1).apply(
                lambda x: 1 if len(x) == 5 and (x < 0).all() else 0
            )
        )
        
        def 北向资金得分函数(连续净流入, 连续净流出, 累计金额):
            if pd.isna(连续净流入) or pd.isna(连续净流出) or pd.isna(累计金额):
                return 50  # 默认中等分数
            
            # 连续5日净流入且总量>50亿→100分
            if 连续净流入 == 1 and 累计金额 > 500000:  # 50亿万元
                return 100
            
            # 连续5日净流出且总量>50亿→0分
            if 连续净流出 == 1 and abs(累计金额) > 500000:  # 50亿万元
                return 0
            
            # 其余情况40-80分线性插值
            # 基于5日累计净流入金额
            标准化金额 = np.clip(累计金额 / 1000000, -1, 1)  # 标准化到-1到1
            return 40 + (标准化金额 + 1) / 2 * 40  # 40-80分
        
        结果数据['北向资金得分'] = 结果数据.apply(
            lambda row: 北向资金得分函数(
                row['北向资金_5日连续净流入'], 
                row['北向资金_5日连续净流出'], 
                row['北向资金_5日累计']
            ), axis=1
        )
        
        self.logger.info(f"北向资金得分计算完成，平均得分: {结果数据['北向资金得分'].mean():.2f}")
        return 结果数据[['北向资金得分']]
    
    def 计算涨跌广度得分(self, 涨跌广度数据: pd.DataFrame) -> pd.DataFrame:
        """
        计算涨跌广度得分（15%权重）
        
        规则：上涨家数/下跌家数；指数红但比值<0.7额外-10；指数绿但比值>1.5额外+10
        
        Args:
            涨跌广度数据: 包含涨跌广度数据的DataFrame
            
        Returns:
            DataFrame: 包含涨跌广度得分的DataFrame
        """
        self.logger.info("开始计算涨跌广度得分")
        
        结果数据 = 涨跌广度数据.copy()
        
        def 涨跌广度得分函数(涨跌比):
            if pd.isna(涨跌比):
                return 50  # 默认中等分数
            
            # 基础得分：基于涨跌比
            if 涨跌比 >= 2.0:
                基础得分 = 90
            elif 涨跌比 >= 1.5:
                基础得分 = 80
            elif 涨跌比 >= 1.2:
                基础得分 = 70
            elif 涨跌比 >= 1.0:
                基础得分 = 60
            elif 涨跌比 >= 0.8:
                基础得分 = 50
            elif 涨跌比 >= 0.7:
                基础得分 = 40
            else:
                基础得分 = 30
            
            # 额外规则（这里简化处理，假设指数红绿状态）
            # 实际应用中需要获取指数涨跌状态
            额外分数 = 0
            if 涨跌比 < 0.7:  # 假设指数红但比值<0.7
                额外分数 = -10
            elif 涨跌比 > 1.5:  # 假设指数绿但比值>1.5
                额外分数 = 10
            
            return max(0, min(100, 基础得分 + 额外分数))
        
        结果数据['涨跌广度得分'] = 结果数据['涨跌比'].apply(涨跌广度得分函数)
        
        self.logger.info(f"涨跌广度得分计算完成，平均得分: {结果数据['涨跌广度得分'].mean():.2f}")
        return 结果数据[['涨跌广度得分']]
    
    def 计算融资余额得分(self, 融资余额数据: pd.DataFrame) -> pd.DataFrame:
        """
        计算融资余额得分（10%权重）
        
        规则：近250日分位，前20%（大增）→80-100分；后20%（大减）→0-40分；中段40-80分，线性插值
        
        Args:
            融资余额数据: 包含融资余额数据的DataFrame
            
        Returns:
            DataFrame: 包含融资余额得分的DataFrame
        """
        self.logger.info("开始计算融资余额得分")
        
        结果数据 = 融资余额数据.copy()
        
        # 检查字段名并计算250日滚动分位数
        融资余额字段 = None
        for 字段名 in ['融资余额_万元', 'margin_balance', 'rzye']:
            if 字段名 in 结果数据.columns:
                融资余额字段 = 字段名
                break
        
        if 融资余额字段 is None:
            self.logger.error("未找到融资余额字段")
            return pd.DataFrame()
        
        # 将字段转换为万元（如果是原始数据）
        if 融资余额字段 in ['margin_balance', 'rzye']:
            结果数据['融资余额_万元'] = 结果数据[融资余额字段] / 10000
            融资余额字段 = '融资余额_万元'
        
        结果数据['融资余额_250日分位'] = 结果数据[融资余额字段].rolling(250, min_periods=50).rank(pct=True)
        
        # 根据分位数计算得分
        def 融资余额得分函数(分位值):
            if pd.isna(分位值):
                return 50  # 默认中等分数
            
            if 分位值 >= 0.8:  # 前20%（大增）
                return 80 + (分位值 - 0.8) / 0.2 * 20  # 80-100分
            elif 分位值 <= 0.2:  # 后20%（大减）
                return 分位值 / 0.2 * 40  # 0-40分
            else:  # 中段60%
                return 40 + (分位值 - 0.2) / 0.6 * 40  # 40-80分
        
        结果数据['融资余额得分'] = 结果数据['融资余额_250日分位'].apply(融资余额得分函数)
        
        self.logger.info(f"融资余额得分计算完成，平均得分: {结果数据['融资余额得分'].mean():.2f}")
        return 结果数据[['融资余额得分']]
    
    def 计算综合得分(self, 所有数据: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        计算综合得分
        
        Args:
            所有数据: 包含所有指标数据的字典
            
        Returns:
            DataFrame: 包含所有得分和综合得分的DataFrame
        """
        self.logger.info("开始计算综合得分")
        
        # 获取所有日期的并集
        所有日期 = set()
        for 数据 in 所有数据.values():
            if 数据 is not None and not 数据.empty:
                所有日期.update(数据.index)
        
        所有日期 = sorted(所有日期)
        
        # 创建结果DataFrame
        结果数据 = pd.DataFrame(index=所有日期)
        
        # 计算各指标得分
        try:
            成交量得分 = self.计算成交量得分(所有数据['成交量']) if 所有数据['成交量'] is not None else None
            self.logger.info("成交量得分计算完成")
        except Exception as e:
            self.logger.error(f"成交量得分计算失败: {e}")
            成交量得分 = None
            
        try:
            涨跌停得分 = self.计算涨跌停得分(所有数据['涨跌停']) if 所有数据['涨跌停'] is not None else None
            self.logger.info("涨跌停得分计算完成")
        except Exception as e:
            self.logger.error(f"涨跌停得分计算失败: {e}")
            涨跌停得分 = None
            
        try:
            波动率得分 = self.计算波动率得分(所有数据['波动率']) if 所有数据['波动率'] is not None else None
            self.logger.info("波动率得分计算完成")
        except Exception as e:
            self.logger.error(f"波动率得分计算失败: {e}")
            波动率得分 = None
            
        # 北向资金指标已移除
            
        try:
            涨跌广度得分 = self.计算涨跌广度得分(所有数据['涨跌广度']) if 所有数据['涨跌广度'] is not None else None
            self.logger.info("涨跌广度得分计算完成")
        except Exception as e:
            self.logger.error(f"涨跌广度得分计算失败: {e}")
            涨跌广度得分 = None
            
        try:
            融资余额得分 = self.计算融资余额得分(所有数据['融资余额']) if 所有数据['融资余额'] is not None else None
            self.logger.info("融资余额得分计算完成")
        except Exception as e:
            self.logger.error(f"融资余额得分计算失败: {e}")
            融资余额得分 = None
        
        # 合并各指标得分
        if 成交量得分 is not None:
            结果数据 = 结果数据.join(成交量得分, how='left')
        if 涨跌停得分 is not None:
            结果数据 = 结果数据.join(涨跌停得分, how='left')
        if 波动率得分 is not None:
            结果数据 = 结果数据.join(波动率得分, how='left')
        if 涨跌广度得分 is not None:
            结果数据 = 结果数据.join(涨跌广度得分, how='left')
        if 融资余额得分 is not None:
            结果数据 = 结果数据.join(融资余额得分, how='left')
        
        # 计算综合得分
        def 计算综合得分函数(row):
            得分列表 = []
            权重列表 = []
            
            for 指标名, 权重 in self.权重配置.items():
                得分列名 = f'{指标名}得分'
                if 得分列名 in row and not pd.isna(row[得分列名]):
                    得分列表.append(row[得分列名])
                    权重列表.append(权重)
            
            if not 得分列表:
                return np.nan
            
            # 加权平均
            return np.average(得分列表, weights=权重列表)
        
        结果数据['综合得分'] = 结果数据.apply(计算综合得分函数, axis=1)
        
        # 添加日期列
        结果数据['日期'] = 结果数据.index
        
        self.logger.info(f"综合得分计算完成，平均得分: {结果数据['综合得分'].mean():.2f}")
        return 结果数据
    
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
            文件名 = f"a_stock_emotion_score_{时间戳}.csv"
        
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


def main():
    """测试评分计算模块"""
    print("=" * 60)
    print("A股情绪评分计算模块测试")
    print("=" * 60)
    
    # 创建评分计算器
    评分计算器 = A股情绪评分计算器()
    
    # 生成测试数据
    print("\n生成测试数据...")
    测试数据 = {}
    
    # 生成30天的测试数据
    日期范围 = pd.date_range('2025-01-01', '2025-01-30', freq='D')
    
    # 成交量数据
    测试数据['成交量'] = pd.DataFrame({
        '成交额_万元': np.random.normal(8000000, 2000000, len(日期范围))
    }, index=日期范围)
    
    # 涨跌停数据
    测试数据['涨跌停'] = pd.DataFrame({
        '涨停家数': np.random.poisson(30, len(日期范围)),
        '跌停家数': np.random.poisson(10, len(日期范围))
    }, index=日期范围)
    
    # 波动率数据
    测试数据['波动率'] = pd.DataFrame({
        '波动率': np.random.normal(0.2, 0.05, len(日期范围))
    }, index=日期范围)
    
    # 北向资金数据
    测试数据['北向资金'] = pd.DataFrame({
        '净买入额_万元': np.random.normal(500000, 300000, len(日期范围))
    }, index=日期范围)
    
    # 涨跌广度数据
    测试数据['涨跌广度'] = pd.DataFrame({
        '上涨家数': np.random.normal(2500, 800, len(日期范围)),
        '下跌家数': np.random.normal(2500, 800, len(日期范围)),
        '涨跌比': np.random.normal(1.0, 0.3, len(日期范围))
    }, index=日期范围)
    
    # 融资余额数据
    测试数据['融资余额'] = pd.DataFrame({
        '融资余额_万元': np.random.normal(15000000, 2000000, len(日期范围))
    }, index=日期范围)
    
    print("测试数据生成完成")
    
    # 计算综合得分
    print("\n开始计算综合得分...")
    结果数据 = 评分计算器.计算综合得分(测试数据)
    
    print("\n计算结果:")
    print("-" * 40)
    print(结果数据[['成交量得分', '涨跌停得分', '波动率得分', '北向资金得分', '涨跌广度得分', '融资余额得分', '综合得分']].tail())
    
    # 保存结果
    文件路径 = 评分计算器.保存结果(结果数据)
    if 文件路径:
        print(f"\n结果已保存到: {文件路径}")
    
    print("\n测试完成")


if __name__ == "__main__":
    main()
