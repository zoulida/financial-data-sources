#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪深300指数行情数据下载脚本
使用合并下载数据模块下载沪深300指数(000300.SH)的行情数据

作者: AI Assistant
创建时间: 2025-01-29
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# 导入合并下载数据模块
try:
    from md.合并下载数据.合并下载数据 import getDayData
    DOWNLOAD_MODULE_AVAILABLE = True
except ImportError:
    DOWNLOAD_MODULE_AVAILABLE = False
    print("警告: 合并下载数据模块未找到")

class 沪深300指数下载器:
    """沪深300指数行情数据下载器"""
    
    def __init__(self, log_level=logging.INFO):
        """
        初始化沪深300指数下载器
        
        Args:
            log_level: 日志级别
        """
        self.setup_logging(log_level)
        self.指数代码 = "000300.SH"  # 沪深300指数代码
    
    def setup_logging(self, log_level):
        """设置日志"""
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'csi300_index_downloader_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def 下载沪深300指数数据(self, 开始日期: str, 结束日期: str, 
                         复权类型: str = 'none', 是否下载: bool = True) -> pd.DataFrame:
        """
        下载沪深300指数的日K线数据
        
        Args:
            开始日期: 开始日期，格式: '20250101'
            结束日期: 结束日期，格式: '20250129'
            复权类型: 复权类型，'front'=前复权，'back'=后复权，'none'=不复权
            是否下载: 是否重新下载数据
            
        Returns:
            DataFrame: 沪深300指数日K线数据
        """
        if not DOWNLOAD_MODULE_AVAILABLE:
            self.logger.error("合并下载数据模块不可用")
            return pd.DataFrame()
        
        try:
            self.logger.info(f"正在下载沪深300指数({self.指数代码})的数据: {开始日期} 到 {结束日期}")
            
            # 调用合并下载数据模块
            数据 = getDayData(
                stock_code=self.指数代码,
                start_date=开始日期,
                end_date=结束日期,
                is_download=1 if 是否下载 else 0,
                dividend_type=复权类型
            )
            
            if 数据 is not None and not 数据.empty:
                self.logger.info(f"成功下载沪深300指数数据，共 {len(数据)} 条记录")
                return 数据
            else:
                self.logger.warning("下载的数据为空")
                return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"下载沪深300指数数据时发生错误: {e}")
            return pd.DataFrame()
    
    def 分析指数数据(self, 数据: pd.DataFrame) -> dict:
        """
        分析沪深300指数数据
        
        Args:
            数据: 指数数据
            
        Returns:
            dict: 分析结果
        """
        if 数据.empty:
            return {}
        
        分析结果 = {}
        
        # 基本统计
        分析结果['基本统计'] = {
            '数据条数': len(数据),
            '开始日期': 数据['date'].iloc[0] if 'date' in 数据.columns else 'N/A',
            '结束日期': 数据['date'].iloc[-1] if 'date' in 数据.columns else 'N/A',
            '数据列数': len(数据.columns)
        }
        
        # 价格统计
        if 'close' in 数据.columns:
            收盘价 = 数据['close']
            分析结果['价格统计'] = {
                '最新收盘价': round(收盘价.iloc[-1], 2),
                '最高价': round(收盘价.max(), 2),
                '最低价': round(收盘价.min(), 2),
                '平均价': round(收盘价.mean(), 2),
                '价格标准差': round(收盘价.std(), 2)
            }
        
        # 成交量统计
        if 'volume' in 数据.columns:
            成交量 = 数据['volume']
            分析结果['成交量统计'] = {
                '最新成交量': int(成交量.iloc[-1]) if pd.notna(成交量.iloc[-1]) else 0,
                '最大成交量': int(成交量.max()) if pd.notna(成交量.max()) else 0,
                '最小成交量': int(成交量.min()) if pd.notna(成交量.min()) else 0,
                '平均成交量': int(成交量.mean()) if pd.notna(成交量.mean()) else 0
            }
        
        # 成交额统计
        if 'amount' in 数据.columns:
            成交额 = 数据['amount']
            分析结果['成交额统计'] = {
                '最新成交额': int(成交额.iloc[-1]) if pd.notna(成交额.iloc[-1]) else 0,
                '最大成交额': int(成交额.max()) if pd.notna(成交额.max()) else 0,
                '最小成交额': int(成交额.min()) if pd.notna(成交额.min()) else 0,
                '平均成交额': int(成交额.mean()) if pd.notna(成交额.mean()) else 0
            }
        
        # 涨跌幅统计
        if 'close' in 数据.columns and len(数据) > 1:
            收盘价 = 数据['close']
            涨跌幅 = 收盘价.pct_change() * 100
            涨跌幅 = 涨跌幅.dropna()
            
            if not 涨跌幅.empty:
                分析结果['涨跌幅统计'] = {
                    '最大涨幅': round(涨跌幅.max(), 2),
                    '最大跌幅': round(涨跌幅.min(), 2),
                    '平均涨跌幅': round(涨跌幅.mean(), 2),
                    '涨跌幅标准差': round(涨跌幅.std(), 2),
                    '上涨天数': int((涨跌幅 > 0).sum()),
                    '下跌天数': int((涨跌幅 < 0).sum()),
                    '平盘天数': int((涨跌幅 == 0).sum())
                }
        
        return 分析结果
    
    def 保存数据(self, 数据: pd.DataFrame, 文件名: str = None) -> str:
        """
        保存数据到CSV文件
        
        Args:
            数据: 要保存的数据
            文件名: 文件名
            
        Returns:
            str: 保存的文件路径
        """
        if 数据.empty:
            self.logger.warning("数据为空，无法保存")
            return ""
        
        if 文件名 is None:
            时间戳 = datetime.now().strftime("%Y%m%d_%H%M%S")
            文件名 = f"csi300_index_{时间戳}.csv"
        
        # 确保保存目录存在
        保存目录 = os.path.join(project_root, 'data')
        os.makedirs(保存目录, exist_ok=True)
        
        文件路径 = os.path.join(保存目录, 文件名)
        
        try:
            数据.to_csv(文件路径, encoding='utf-8-sig', index=False)
            self.logger.info(f"数据已保存到: {文件路径}")
            return 文件路径
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")
            return ""


def main():
    """主函数"""
    print("=" * 60)
    print("沪深300指数行情数据下载程序")
    print("=" * 60)
    
    # 创建下载器
    下载器 = 沪深300指数下载器()
    
    try:
        # 设置下载参数
        开始日期 = "20240101"  # 2024年1月1日
        结束日期 = "20250129"  # 2025年1月29日
        复权类型 = "none"  # 指数数据通常不复权
        
        print(f"\n下载参数:")
        print(f"指数代码: 000300.SH (沪深300指数)")
        print(f"开始日期: {开始日期}")
        print(f"结束日期: {结束日期}")
        print(f"复权类型: {复权类型}")
        
        # 下载数据
        print(f"\n开始下载沪深300指数数据...")
        数据 = 下载器.下载沪深300指数数据(
            开始日期=开始日期,
            结束日期=结束日期,
            复权类型=复权类型,
            是否下载=True
        )
        
        if not 数据.empty:
            print(f"\n下载成功！共获取 {len(数据)} 条数据")
            
            # 显示数据基本信息
            print(f"\n数据基本信息:")
            print(f"数据形状: {数据.shape}")
            print(f"列名: {list(数据.columns)}")
            print(f"\n前5条数据:")
            print(数据.head())
            print(f"\n后5条数据:")
            print(数据.tail())
            
            # 分析数据
            print(f"\n正在分析数据...")
            分析结果 = 下载器.分析指数数据(数据)
            
            # 显示分析结果
            print(f"\n分析结果:")
            print("-" * 40)
            for 类别, 内容 in 分析结果.items():
                print(f"\n{类别}:")
                if isinstance(内容, dict):
                    for 键, 值 in 内容.items():
                        print(f"  {键}: {值}")
                else:
                    print(f"  {内容}")
            
            # 保存数据
            文件路径 = 下载器.保存数据(数据)
            if 文件路径:
                print(f"\n数据已保存到: {文件路径}")
            
        else:
            print("下载失败，未能获取到数据")
    
    except Exception as e:
        print(f"程序执行出错: {e}")
        下载器.logger.error(f"程序执行出错: {e}")
    
    print("\n程序执行完成")


if __name__ == "__main__":
    main()
