#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股情绪周期数据获取模块
负责从不同数据源获取6个硬指标的数据

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

# 导入数据源
try:
    from WindPy import w
    WIND_AVAILABLE = True
except ImportError:
    WIND_AVAILABLE = False
    print("警告: WindPy 未安装")

try:
    from xtquant import xtdata
    XTQUANT_AVAILABLE = True
except ImportError:
    XTQUANT_AVAILABLE = False
    print("警告: xtquant 未安装")

# 导入合并下载数据模块
try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData
    DOWNLOAD_MODULE_AVAILABLE = True
except ImportError:
    DOWNLOAD_MODULE_AVAILABLE = False
    print("警告: 合并下载数据模块未找到")

class A股数据获取器:
    """A股情绪周期数据获取器"""
    
    def __init__(self, log_level=logging.INFO):
        """
        初始化数据获取器
        
        Args:
            log_level: 日志级别
        """
        self.setup_logging(log_level)
        self.wind_initialized = False
        
        # 初始化数据源
        if WIND_AVAILABLE:
            self.init_wind()
    
    def setup_logging(self, log_level):
        """设置日志"""
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'a_stock_data_fetcher_{datetime.now().strftime("%Y%m%d")}.log')
        
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
    
    def 获取成交量数据(self, 开始日期: str, 结束日期: str) -> Optional[pd.DataFrame]:
        """
        获取Wind全A指数成交总额数据
        
        Args:
            开始日期: 开始日期，格式: '2025-01-01'
            结束日期: 结束日期，格式: '2025-01-29'
            
        Returns:
            DataFrame: 包含成交额数据的DataFrame
        """
        if not self.wind_initialized:
            self.logger.warning("Wind接口未初始化，返回模拟数据")
            return self._生成模拟成交量数据(开始日期, 结束日期)
        
        try:
            self.logger.info(f"正在获取Wind全A指数成交额数据: {开始日期} 到 {结束日期}")
            
            # 获取Wind全A指数成交额数据
            data = w.wsd("881001.WI", "amt", 开始日期, 结束日期, "")
            
            if data.ErrorCode != 0:
                self.logger.error(f"获取成交额数据失败，错误代码: {data.ErrorCode}")
                return self._生成模拟成交量数据(开始日期, 结束日期)
            
            if not data.Data or len(data.Data) == 0:
                self.logger.warning("成交额数据为空")
                return self._生成模拟成交量数据(开始日期, 结束日期)
            
            # 转换为DataFrame
            df = pd.DataFrame({
                '日期': data.Times,
                '成交额_万元': [x / 10000 for x in data.Data[0]]  # 转换为万元
            })
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期')
            
            # 对齐日期范围
            df = self._对齐日期范围(df, 开始日期, 结束日期)
            
            self.logger.info(f"成功获取 {len(df)} 天的成交额数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取成交额数据时发生错误: {e}")
            return self._生成模拟成交量数据(开始日期, 结束日期)
    
    def _获取涨跌家数基础数据(self, 开始日期: str, 结束日期: str) -> Optional[pd.DataFrame]:
        """
        获取涨跌家数基础数据（内部函数，供涨跌停和涨跌广度复用）
        
        Args:
            开始日期: 开始日期
            结束日期: 结束日期
            
        Returns:
            DataFrame: 包含涨跌家数基础数据的DataFrame
        """
        if not self.wind_initialized:
            return None
        
        try:
            # 使用wset接口获取内地涨跌家数统计
            options = f"startdate={开始日期};enddate={结束日期}"
            data = w.wset("numberofchangeindomestic", options)
            
            if data.ErrorCode != 0:
                self.logger.error(f"获取涨跌家数数据失败，错误代码: {data.ErrorCode}")
                return None
            
            if not data.Data or len(data.Data) == 0:
                self.logger.warning("涨跌家数数据为空")
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(data.Data).T
            df.columns = data.Fields
            df.index = data.Codes
            
            # 重命名列
            column_mapping = {
                'reportdate': '日期',
                'limitupnumofshandsz': '涨停家数',
                'limitdownnumofshandsz': '跌停家数',
                'risenumberofshandsz': '上涨家数',
                'fallnumberofshandsz': '下跌家数'
            }
            
            existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_columns)
            
            if '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.set_index('日期')
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取涨跌家数数据时发生错误: {e}")
            return None
    
    def 获取涨跌停数据(self, 开始日期: str, 结束日期: str, 基础数据: Optional[pd.DataFrame] = None) -> Optional[pd.DataFrame]:
        """
        获取涨跌停家数数据
        
        Args:
            开始日期: 开始日期
            结束日期: 结束日期
            基础数据: 可选的基础数据，如果提供则直接使用，避免重复调用API
            
        Returns:
            DataFrame: 包含涨跌停数据的DataFrame
        """
        if not self.wind_initialized:
            self.logger.warning("Wind接口未初始化，返回模拟数据")
            return self._生成模拟涨跌停数据(开始日期, 结束日期)
        
        try:
            self.logger.info(f"正在获取涨跌停数据: {开始日期} 到 {结束日期}")
            
            # 如果提供了基础数据，直接使用；否则调用API获取
            if 基础数据 is not None and not 基础数据.empty:
                df = 基础数据.copy()
                self.logger.info("使用已获取的基础数据，节省API调用")
            else:
                df = self._获取涨跌家数基础数据(开始日期, 结束日期)
            
            if df is None or df.empty:
                self.logger.warning("涨跌停数据为空，返回模拟数据")
                return self._生成模拟涨跌停数据(开始日期, 结束日期)
            
            # 只保留涨跌停相关列
            需要的列 = ['涨停家数', '跌停家数']
            现有列 = [col for col in 需要的列 if col in df.columns]
            if 现有列:
                df = df[现有列]
            else:
                self.logger.warning("涨跌停数据中缺少必要列，返回模拟数据")
                return self._生成模拟涨跌停数据(开始日期, 结束日期)
            
            # 对齐日期范围
            df = self._对齐日期范围(df, 开始日期, 结束日期)
            
            self.logger.info(f"成功获取 {len(df)} 天的涨跌停数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取涨跌停数据时发生错误: {e}")
            return self._生成模拟涨跌停数据(开始日期, 结束日期)
    
    def 获取波动率数据(self, 开始日期: str, 结束日期: str) -> Optional[pd.DataFrame]:
        """
        获取沪深300指数波动率数据
        
        Args:
            开始日期: 开始日期，格式: '2025-01-01'
            结束日期: 结束日期，格式: '2025-01-29'
            
        Returns:
            DataFrame: 包含波动率数据的DataFrame，日期对齐到指定范围
        """
        if not DOWNLOAD_MODULE_AVAILABLE:
            self.logger.warning("合并下载数据模块不可用，返回模拟数据")
            return self._生成模拟波动率数据(开始日期, 结束日期)
        
        try:
            self.logger.info(f"正在获取沪深300指数波动率数据: {开始日期} 到 {结束日期}")
            
            # 为了计算20日滚动波动率，需要提前获取更多数据
            # 提前60天（约3个月）以确保有足够的交易日来计算20日波动率
            # 考虑到周末和节假日，60天大约有40-45个交易日，足够计算20日波动率
            开始日期_obj = pd.to_datetime(开始日期)
            提前开始日期 = (开始日期_obj - pd.Timedelta(days=60)).strftime('%Y-%m-%d')
            self.logger.info(f"提前获取数据用于计算波动率: {提前开始日期} 到 {结束日期}（提前60天以确保有足够交易日）")
            
            # 转换日期格式：从 '2025-01-01' 到 '20250101'
            提前开始日期_格式 = 提前开始日期.replace('-', '')
            结束日期_格式 = 结束日期.replace('-', '')
            
            # 使用合并下载数据模块获取沪深300指数数据（提前获取更多数据）
            self.logger.info(f"获取波动率原始数据: {提前开始日期} 到 {结束日期}")
            data = getDayData(
                stock_code="000300.SH",  # 沪深300指数代码
                start_date=提前开始日期_格式,
                end_date=结束日期_格式,
                is_download=1,  # 重新下载
                dividend_type='none'  # 指数数据通常不复权
            )
            
            if data is None or data.empty:
                self.logger.warning("沪深300指数数据为空")
                return self._生成模拟波动率数据(开始日期, 结束日期)
            
            # 检查数据格式
            self.logger.info(f"获取到原始数据 {len(data)} 条，列名: {list(data.columns)}")
            
            # 检查是否有收盘价数据
            if 'close' not in data.columns:
                self.logger.warning(f"沪深300指数数据中缺少收盘价列，可用列: {list(data.columns)}")
                return self._生成模拟波动率数据(开始日期, 结束日期)
            
            # 确保索引是日期类型
            if not isinstance(data.index, pd.DatetimeIndex):
                if 'date' in data.columns:
                    data['date'] = pd.to_datetime(data['date'])
                    data = data.set_index('date')
                    self.logger.info("已将date列设置为索引")
                else:
                    self.logger.warning("数据索引不是日期类型，且没有date列")
            
            # 计算20日历史波动率
            close_prices = data['close'].dropna()
            self.logger.info(f"有效收盘价数据 {len(close_prices)} 天，日期范围: {close_prices.index.min()} 到 {close_prices.index.max()}")
            
            if len(close_prices) < 20:
                self.logger.warning(f"沪深300指数数据不足20天，只有{len(close_prices)}天")
                return self._生成模拟波动率数据(开始日期, 结束日期)
            
            # 计算日收益率
            returns = close_prices.pct_change().dropna()
            
            # 计算20日滚动波动率（年化）
            volatility = returns.rolling(20).std() * np.sqrt(252)
            
            # 创建结果DataFrame
            df = pd.DataFrame({
                '日期': volatility.index,
                '波动率': volatility.values
            })
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期')
            
            # 记录计算后的数据情况
            self.logger.info(f"波动率计算完成，原始数据 {len(df)} 天，有效数据 {len(df.dropna())} 天")
            
            # 先对齐日期范围，再dropna（这样可以保留对齐后的数据）
            开始日期_obj = pd.to_datetime(开始日期)
            结束日期_obj = pd.to_datetime(结束日期)
            
            # 对齐日期范围
            df_aligned = df[(df.index >= 开始日期_obj) & (df.index <= 结束日期_obj)]
            
            # 记录对齐后的数据情况
            对齐后总数 = len(df_aligned)
            对齐后有效数 = len(df_aligned.dropna())
            self.logger.info(f"日期对齐后，数据 {对齐后总数} 天，有效数据 {对齐后有效数} 天")
            
            # 如果有效数据不足，尝试使用更早的数据（但仍在指定日期范围内）
            if 对齐后有效数 < 对齐后总数 * 0.5:  # 如果有效数据少于50%
                self.logger.warning(f"对齐后有效数据较少（{对齐后有效数}/{对齐后总数}），这是因为20日滚动波动率需要20个交易日才能计算")
                self.logger.info("保留所有对齐后的数据，包括NaN值（NaN值在后续计算中会被忽略）")
                # 保留所有数据，包括NaN，让后续计算处理
                df = df_aligned
            else:
                # 只删除NaN值
                df = df_aligned.dropna()
            
            self.logger.info(f"成功获取 {len(df)} 天的波动率数据（包含 {len(df.dropna())} 天有效数据）")
            
            if len(df.dropna()) == 0:
                self.logger.warning("波动率数据对齐后没有有效数据，可能是指定日期范围内没有足够的交易日来计算20日波动率")
                self.logger.warning(f"建议：开始日期至少需要提前20个交易日才能计算出有效的波动率数据")
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取波动率数据时发生错误: {e}")
            return self._生成模拟波动率数据(开始日期, 结束日期)
    
    def 获取北向资金数据(self, 开始日期: str, 结束日期: str) -> Optional[pd.DataFrame]:
        """
        获取北向资金净买入额数据
        
        Args:
            开始日期: 开始日期
            结束日期: 结束日期
            
        Returns:
            DataFrame: 包含北向资金数据的DataFrame
        """
        if not self.wind_initialized:
            self.logger.warning("Wind接口未初始化，返回模拟数据")
            return self._生成模拟北向资金数据(开始日期, 结束日期)
        
        try:
            self.logger.info(f"正在获取北向资金数据: {开始日期} 到 {结束日期}")
            
            # 获取710001.WI净买入额数据
            data = w.wsd("710001.WI", "amt", 开始日期, 结束日期, "")
            
            if data.ErrorCode != 0:
                self.logger.error(f"获取北向资金数据失败，错误代码: {data.ErrorCode}")
                return self._生成模拟北向资金数据(开始日期, 结束日期)
            
            if not data.Data or len(data.Data) == 0:
                self.logger.warning("北向资金数据为空")
                return self._生成模拟北向资金数据(开始日期, 结束日期)
            
            # 转换为DataFrame
            # 处理None值，将None转换为0
            净买入额数据 = []
            for x in data.Data[0]:
                if x is None or pd.isna(x):
                    净买入额数据.append(0)
                else:
                    净买入额数据.append(x / 10000)  # 转换为万元
            
            df = pd.DataFrame({
                '日期': data.Times,
                '净买入额_万元': 净买入额数据
            })
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期')
            
            self.logger.info(f"成功获取 {len(df)} 天的北向资金数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取北向资金数据时发生错误: {e}")
            return self._生成模拟北向资金数据(开始日期, 结束日期)
    
    def 获取涨跌广度数据(self, 开始日期: str, 结束日期: str, 基础数据: Optional[pd.DataFrame] = None) -> Optional[pd.DataFrame]:
        """
        获取涨跌广度数据（上涨家数/下跌家数）
        
        Args:
            开始日期: 开始日期
            结束日期: 结束日期
            基础数据: 可选的基础数据，如果提供则直接使用，避免重复调用API
            
        Returns:
            DataFrame: 包含涨跌广度数据的DataFrame
        """
        if not self.wind_initialized:
            self.logger.warning("Wind接口未初始化，返回模拟数据")
            return self._生成模拟涨跌广度数据(开始日期, 结束日期)
        
        try:
            self.logger.info(f"正在获取涨跌广度数据: {开始日期} 到 {结束日期}")
            
            # 如果提供了基础数据，直接使用；否则调用API获取
            if 基础数据 is not None and not 基础数据.empty:
                df = 基础数据.copy()
                self.logger.info("使用已获取的基础数据，节省API调用")
            else:
                df = self._获取涨跌家数基础数据(开始日期, 结束日期)
            
            if df is None or df.empty:
                self.logger.warning("涨跌广度数据为空，返回模拟数据")
                return self._生成模拟涨跌广度数据(开始日期, 结束日期)
            
            # 只保留涨跌广度相关列
            需要的列 = ['上涨家数', '下跌家数']
            现有列 = [col for col in 需要的列 if col in df.columns]
            if 现有列:
                df = df[现有列]
            else:
                self.logger.warning("涨跌广度数据中缺少必要列，返回模拟数据")
                return self._生成模拟涨跌广度数据(开始日期, 结束日期)
            
            # 计算涨跌比
            if '上涨家数' in df.columns and '下跌家数' in df.columns:
                df['涨跌比'] = df['上涨家数'] / df['下跌家数'].replace(0, np.nan)
                df = df[['上涨家数', '下跌家数', '涨跌比']]
            
            # 对齐日期范围
            df = self._对齐日期范围(df, 开始日期, 结束日期)
            
            self.logger.info(f"成功获取 {len(df)} 天的涨跌广度数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取涨跌广度数据时发生错误: {e}")
            return self._生成模拟涨跌广度数据(开始日期, 结束日期)
    
    def 获取融资余额数据(self, 开始日期: str, 结束日期: str) -> Optional[pd.DataFrame]:
        """
        获取融资余额数据
        
        Args:
            开始日期: 开始日期，格式: '2025-01-01'
            结束日期: 结束日期，格式: '2025-01-29'
            
        Returns:
            DataFrame: 包含融资余额数据的DataFrame
        """
        if not self.wind_initialized:
            self.logger.warning("Wind接口未初始化，返回模拟数据")
            return self._生成模拟融资余额数据(开始日期, 结束日期)
        
        try:
            self.logger.info(f"正在获取融资余额数据: {开始日期} 到 {结束日期}")
            
            # 使用wset接口获取融资融券交易规模分析数据
            parameters = f"exchange=all;startdate={开始日期};enddate={结束日期};frequency=day;sort=asc"
            data = w.wset("margintradingsizeanalys(value)", parameters)
            
            if data.ErrorCode != 0:
                self.logger.error(f"获取融资余额数据失败，错误代码: {data.ErrorCode}")
                return self._生成模拟融资余额数据(开始日期, 结束日期)
            
            if not data.Data or len(data.Data) == 0:
                self.logger.warning("融资余额数据为空")
                return self._生成模拟融资余额数据(开始日期, 结束日期)
            
            # 转换为DataFrame
            df = pd.DataFrame(data.Data, index=data.Fields).T
            df.columns = data.Fields
            
            # 字段映射（Wind API返回的字段名）
            column_mapping = {
                'end_date': '日期',
                'rzye': '融资余额_万元',
                'rzyezb': '融资余额占流通市值_百分比',
                'rzyl': '融资余量',
                'qjmre': '期间买入额_万元',
                'mrezb': '买入额占A股成交额_百分比',
                'qjche': '期间偿还额_万元',
                'qjjmre': '期间净买入额_万元',
                'rzggsl': '期间融资买入个股数',
                'rzbdzb': '占融资标的比_百分比'
            }
            
            # 重命名列
            existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_columns)
            
            # 确保有融资余额_万元字段
            if '融资余额_万元' not in df.columns and 'rzye' in df.columns:
                df['融资余额_万元'] = df['rzye']
            
            # 确保日期列存在并转换为datetime
            if '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.set_index('日期')
            else:
                self.logger.warning("数据中缺少日期字段")
                return self._生成模拟融资余额数据(开始日期, 结束日期)
            
            # 数据类型转换
            numeric_columns = [
                '融资余额_万元', '融资余额占流通市值_百分比', '融资余量',
                '期间买入额_万元', '买入额占A股成交额_百分比', '期间偿还额_万元',
                '期间净买入额_万元', '期间融资买入个股数', '占融资标的比_百分比'
            ]
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 将融资余额从元转换为万元
            if '融资余额_万元' in df.columns:
                df['融资余额_万元'] = df['融资余额_万元'] / 10000
            
            # 将其他金额字段也转换为万元
            amount_columns = ['期间买入额_万元', '期间偿还额_万元', '期间净买入额_万元']
            for col in amount_columns:
                if col in df.columns:
                    df[col] = df[col] / 10000
            
            # 对齐日期范围
            df = self._对齐日期范围(df, 开始日期, 结束日期)
            
            self.logger.info(f"成功获取 {len(df)} 天的融资余额数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取融资余额数据时发生错误: {e}")
            return self._生成模拟融资余额数据(开始日期, 结束日期)
    
    def 获取沪深300指数数据(self, 开始日期: str, 结束日期: str) -> Optional[pd.DataFrame]:
        """
        获取沪深300指数原始行情数据
        
        Args:
            开始日期: 开始日期，格式: '2025-01-01'
            结束日期: 结束日期，格式: '2025-01-29'
            
        Returns:
            DataFrame: 包含沪深300指数行情数据的DataFrame
        """
        if not DOWNLOAD_MODULE_AVAILABLE:
            self.logger.warning("合并下载数据模块不可用，返回模拟数据")
            return self._生成模拟沪深300数据(开始日期, 结束日期)
        
        try:
            self.logger.info(f"正在获取沪深300指数行情数据: {开始日期} 到 {结束日期}")
            
            # 转换日期格式：从 '2025-01-01' 到 '20250101'
            开始日期_格式 = 开始日期.replace('-', '')
            结束日期_格式 = 结束日期.replace('-', '')
            
            # 使用合并下载数据模块获取沪深300指数数据
            data = getDayData(
                stock_code="000300.SH",  # 沪深300指数代码
                start_date=开始日期_格式,
                end_date=结束日期_格式,
                is_download=1,  # 重新下载
                dividend_type='none'  # 指数数据通常不复权
            )
            
            if data is None or data.empty:
                self.logger.warning("沪深300指数数据为空")
                return self._生成模拟沪深300数据(开始日期, 结束日期)
            
            # 修复索引问题：将date列转换为datetime并设置为索引
            if 'date' in data.columns:
                data['date'] = pd.to_datetime(data['date'])
                data = data.set_index('date')
                self.logger.info("沪深300指数数据索引已修复为datetime类型")
            
            self.logger.info(f"成功获取沪深300指数数据，共 {len(data)} 条记录")
            return data
            
        except Exception as e:
            self.logger.error(f"获取沪深300指数数据时发生错误: {e}")
            return self._生成模拟沪深300数据(开始日期, 结束日期)
    
    def _对齐日期范围(self, df: pd.DataFrame, 开始日期: str, 结束日期: str) -> pd.DataFrame:
        """
        对齐DataFrame的日期范围到指定的开始和结束日期
        
        Args:
            df: 需要对齐的DataFrame（索引为日期）
            开始日期: 开始日期，格式: '2025-01-01'
            结束日期: 结束日期，格式: '2025-01-29'
            
        Returns:
            DataFrame: 对齐后的DataFrame
        """
        if df is None or df.empty:
            return df
        
        try:
            # 确保索引是datetime类型
            if not isinstance(df.index, pd.DatetimeIndex):
                if '日期' in df.columns:
                    df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
                    df = df.set_index('日期')
                else:
                    return df
            
            # 转换为日期范围
            开始日期_obj = pd.to_datetime(开始日期)
            结束日期_obj = pd.to_datetime(结束日期)
            
            # 过滤到指定日期范围
            df = df[(df.index >= 开始日期_obj) & (df.index <= 结束日期_obj)]
            
            return df
        except Exception as e:
            self.logger.warning(f"对齐日期范围时发生错误: {e}")
            return df
    
    def 获取所有数据(self, 开始日期: str, 结束日期: str) -> Dict[str, pd.DataFrame]:
        """
        获取所有6个指标的数据，并统一对齐日期范围
        
        Args:
            开始日期: 开始日期
            结束日期: 结束日期
            
        Returns:
            Dict: 包含所有指标数据的字典，所有数据日期已对齐
        """
        self.logger.info(f"开始获取 {开始日期} 到 {结束日期} 的所有数据")
        
        数据字典 = {}
        
        # 获取各个指标数据
        数据字典['成交量'] = self.获取成交量数据(开始日期, 结束日期)
        
        # 涨跌停和涨跌广度共享基础数据，只调用一次API
        if self.wind_initialized:
            self.logger.info("获取涨跌家数基础数据（涨跌停和涨跌广度共享）...")
            涨跌家数基础数据 = self._获取涨跌家数基础数据(开始日期, 结束日期)
            if 涨跌家数基础数据 is not None and not 涨跌家数基础数据.empty:
                # 对齐日期范围
                涨跌家数基础数据 = self._对齐日期范围(涨跌家数基础数据, 开始日期, 结束日期)
                # 使用共享的基础数据
                数据字典['涨跌停'] = self.获取涨跌停数据(开始日期, 结束日期, 基础数据=涨跌家数基础数据)
                数据字典['涨跌广度'] = self.获取涨跌广度数据(开始日期, 结束日期, 基础数据=涨跌家数基础数据)
                self.logger.info("涨跌停和涨跌广度数据已从共享基础数据中提取，节省了一次API调用")
            else:
                # 如果基础数据获取失败，分别调用（会使用模拟数据）
                数据字典['涨跌停'] = self.获取涨跌停数据(开始日期, 结束日期)
                数据字典['涨跌广度'] = self.获取涨跌广度数据(开始日期, 结束日期)
        else:
            # Wind未初始化，使用模拟数据
            数据字典['涨跌停'] = self.获取涨跌停数据(开始日期, 结束日期)
            数据字典['涨跌广度'] = self.获取涨跌广度数据(开始日期, 结束日期)
        
        数据字典['波动率'] = self.获取波动率数据(开始日期, 结束日期)
        数据字典['融资余额'] = self.获取融资余额数据(开始日期, 结束日期)
        
        # 添加沪深300指数原始数据
        数据字典['沪深300指数'] = self.获取沪深300指数数据(开始日期, 结束日期)
        
        # 统一对齐所有数据的日期范围
        self.logger.info("正在对齐所有数据的日期范围...")
        for 指标名, 数据 in 数据字典.items():
            if 数据 is not None and not 数据.empty:
                对齐前数量 = len(数据)
                数据字典[指标名] = self._对齐日期范围(数据, 开始日期, 结束日期)
                对齐后数量 = len(数据字典[指标名])
                if 对齐前数量 != 对齐后数量:
                    self.logger.info(f"{指标名}数据对齐: {对齐前数量} -> {对齐后数量} 天")
        
        self.logger.info("所有数据获取完成，日期已对齐")
        return 数据字典
    
    # 模拟数据生成方法
    def _生成模拟成交量数据(self, 开始日期: str, 结束日期: str) -> pd.DataFrame:
        """生成模拟成交量数据"""
        dates = pd.date_range(开始日期, 结束日期, freq='D')
        np.random.seed(42)
        
        # 模拟成交额数据（万元）
        成交额 = np.random.normal(8000000, 2000000, len(dates))  # 平均8000万，标准差2000万
        成交额 = np.maximum(成交额, 1000000)  # 最小100万
        
        df = pd.DataFrame({
            '日期': dates,
            '成交额_万元': 成交额
        })
        df = df.set_index('日期')
        return df
    
    def _生成模拟涨跌停数据(self, 开始日期: str, 结束日期: str) -> pd.DataFrame:
        """生成模拟涨跌停数据"""
        dates = pd.date_range(开始日期, 结束日期, freq='D')
        np.random.seed(42)
        
        # 模拟涨跌停数据
        涨停家数 = np.random.poisson(30, len(dates))  # 平均30只涨停
        跌停家数 = np.random.poisson(10, len(dates))  # 平均10只跌停
        
        df = pd.DataFrame({
            '日期': dates,
            '涨停家数': 涨停家数,
            '跌停家数': 跌停家数
        })
        df = df.set_index('日期')
        return df
    
    def _生成模拟波动率数据(self, 开始日期: str, 结束日期: str) -> pd.DataFrame:
        """生成模拟波动率数据"""
        dates = pd.date_range(开始日期, 结束日期, freq='D')
        np.random.seed(42)
        
        # 模拟波动率数据（年化）
        波动率 = np.random.normal(0.2, 0.05, len(dates))  # 平均20%，标准差5%
        波动率 = np.maximum(波动率, 0.05)  # 最小5%
        
        df = pd.DataFrame({
            '日期': dates,
            '波动率': 波动率
        })
        df = df.set_index('日期')
        return df
    
    def _生成模拟北向资金数据(self, 开始日期: str, 结束日期: str) -> pd.DataFrame:
        """生成模拟北向资金数据"""
        dates = pd.date_range(开始日期, 结束日期, freq='D')
        np.random.seed(42)
        
        # 模拟北向资金净买入额（万元）
        净买入额 = np.random.normal(500000, 300000, len(dates))  # 平均50亿，标准差30亿
        
        df = pd.DataFrame({
            '日期': dates,
            '净买入额_万元': 净买入额
        })
        df = df.set_index('日期')
        return df
    
    def _生成模拟涨跌广度数据(self, 开始日期: str, 结束日期: str) -> pd.DataFrame:
        """生成模拟涨跌广度数据"""
        dates = pd.date_range(开始日期, 结束日期, freq='D')
        np.random.seed(42)
        
        # 模拟涨跌家数
        上涨家数 = np.random.normal(2500, 800, len(dates))
        下跌家数 = np.random.normal(2500, 800, len(dates))
        上涨家数 = np.maximum(上涨家数, 100)
        下跌家数 = np.maximum(下跌家数, 100)
        
        涨跌比 = 上涨家数 / 下跌家数
        
        df = pd.DataFrame({
            '日期': dates,
            '上涨家数': 上涨家数,
            '下跌家数': 下跌家数,
            '涨跌比': 涨跌比
        })
        df = df.set_index('日期')
        return df
    
    def _生成模拟融资余额数据(self, 开始日期: str, 结束日期: str) -> pd.DataFrame:
        """生成模拟融资余额数据"""
        dates = pd.date_range(开始日期, 结束日期, freq='D')
        np.random.seed(42)
        
        # 模拟融资余额（万元）
        融资余额 = np.random.normal(15000000, 2000000, len(dates))  # 平均1500亿，标准差200亿
        融资余额 = np.maximum(融资余额, 5000000)  # 最小500亿
        
        df = pd.DataFrame({
            '日期': dates,
            '融资余额_万元': 融资余额
        })
        df = df.set_index('日期')
        return df
    
    def _生成模拟沪深300数据(self, 开始日期: str, 结束日期: str) -> pd.DataFrame:
        """生成模拟沪深300指数数据"""
        dates = pd.date_range(开始日期, 结束日期, freq='D')
        np.random.seed(42)
        
        # 模拟沪深300指数数据
        开盘价 = np.random.normal(4000, 200, len(dates))
        最高价 = 开盘价 + np.random.uniform(0, 100, len(dates))
        最低价 = 开盘价 - np.random.uniform(0, 100, len(dates))
        收盘价 = 开盘价 + np.random.normal(0, 50, len(dates))
        成交量 = np.random.normal(100000000, 20000000, len(dates))  # 1亿股左右
        成交额 = 收盘价 * 成交量  # 成交额 = 收盘价 * 成交量
        
        df = pd.DataFrame({
            'date': dates,
            'open': 开盘价,
            'high': 最高价,
            'low': 最低价,
            'close': 收盘价,
            'volume': 成交量,
            'amount': 成交额
        })
        df['date'] = df['date'].astype(str)
        return df
    
    def close(self):
        """关闭Wind接口"""
        if self.wind_initialized and WIND_AVAILABLE:
            try:
                w.stop()
                self.logger.info("Wind接口已关闭")
            except Exception as e:
                self.logger.error(f"关闭Wind接口时发生错误: {e}")


def main():
    """测试数据获取模块"""
    print("=" * 60)
    print("A股数据获取模块测试")
    print("=" * 60)
    
    # 创建数据获取器
    数据获取器 = A股数据获取器()
    
    try:
        # 测试获取最近30天的数据
        结束日期 = datetime.now().strftime('%Y-%m-%d')
        开始日期 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        print(f"\n正在获取 {开始日期} 到 {结束日期} 的数据...")
        
        所有数据 = 数据获取器.获取所有数据(开始日期, 结束日期)
        
        print("\n数据获取结果:")
        print("-" * 40)
        for 指标名, 数据 in 所有数据.items():
            if 数据 is not None and not 数据.empty:
                print(f"{指标名}: {len(数据)} 条记录")
                print(f"  最新数据: {数据.iloc[-1].to_dict()}")
            else:
                print(f"{指标名}: 无数据")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
    
    finally:
        数据获取器.close()
        print("\n测试完成")


if __name__ == "__main__":
    main()
