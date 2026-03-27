#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪深300行情数据下载脚本
使用合并下载数据模块下载沪深300成分股的行情数据

作者: AI Assistant
创建时间: 2025-01-29
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# 导入合并下载数据模块
try:
    from md.合并下载数据.合并下载数据 import getDayData, batchDownloadDayData
    DOWNLOAD_MODULE_AVAILABLE = True
except ImportError:
    DOWNLOAD_MODULE_AVAILABLE = False
    print("警告: 合并下载数据模块未找到")

# 导入Wind API
try:
    from WindPy import w
    WIND_AVAILABLE = True
except ImportError:
    WIND_AVAILABLE = False
    print("警告: WindPy 未安装")

class 沪深300数据下载器:
    """沪深300行情数据下载器"""
    
    def __init__(self, log_level=logging.INFO):
        """
        初始化沪深300数据下载器
        
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
        
        log_file = os.path.join(log_dir, f'csi300_downloader_{datetime.now().strftime("%Y%m%d")}.log')
        
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
    
    def 获取沪深300成分股列表(self, 日期: str = None) -> List[str]:
        """
        获取沪深300成分股列表
        
        Args:
            日期: 日期，格式: '2025-01-29'，如果为None则使用今天
            
        Returns:
            List[str]: 沪深300成分股代码列表
        """
        if not self.wind_initialized:
            self.logger.warning("Wind接口未初始化，返回模拟成分股列表")
            return self._生成模拟沪深300成分股列表()
        
        if 日期 is None:
            日期 = datetime.now().strftime('%Y-%m-%d')
        
        try:
            self.logger.info(f"正在获取 {日期} 的沪深300成分股列表...")
            
            # 获取沪深300成分股
            data = w.wset("indexconstituent", f"date={日期};windcode=000300.SH")
            
            if data.ErrorCode != 0:
                self.logger.error(f"获取沪深300成分股失败，错误代码: {data.ErrorCode}")
                return self._生成模拟沪深300成分股列表()
            
            if not data.Data or len(data.Data) < 2:
                self.logger.warning("沪深300成分股数据为空")
                return self._生成模拟沪深300成分股列表()
            
            # 提取股票代码
            成分股列表 = data.Data[1]  # 第二列是股票代码
            
            self.logger.info(f"成功获取 {len(成分股列表)} 只沪深300成分股")
            return 成分股列表
            
        except Exception as e:
            self.logger.error(f"获取沪深300成分股时发生错误: {e}")
            return self._生成模拟沪深300成分股列表()
    
    def _生成模拟沪深300成分股列表(self) -> List[str]:
        """生成模拟沪深300成分股列表"""
        self.logger.info("生成模拟沪深300成分股列表")
        
        # 模拟一些主要的沪深300成分股
        模拟成分股 = [
            "000001.SZ", "000002.SZ", "000858.SZ", "002415.SZ", "300015.SZ",
            "300059.SZ", "300750.SZ", "600000.SH", "600036.SH", "600519.SH",
            "600887.SH", "600900.SH", "601318.SH", "601398.SH", "601939.SH",
            "601988.SH", "000001.SZ", "000002.SZ", "000858.SZ", "002415.SZ",
            "300015.SZ", "300059.SZ", "300750.SZ", "600000.SH", "600036.SH",
            "600519.SH", "600887.SH", "600900.SH", "601318.SH", "601398.SH"
        ]
        
        return 模拟成分股[:30]  # 返回前30只作为示例
    
    def 下载单只股票数据(self, 股票代码: str, 开始日期: str, 结束日期: str, 
                       复权类型: str = 'front', 是否下载: bool = True) -> Optional[pd.DataFrame]:
        """
        下载单只股票的日K线数据
        
        Args:
            股票代码: 股票代码，如"600519.SH"
            开始日期: 开始日期，格式: '20250101'
            结束日期: 结束日期，格式: '20250129'
            复权类型: 复权类型，'front'=前复权，'back'=后复权，'none'=不复权
            是否下载: 是否重新下载数据
            
        Returns:
            DataFrame: 股票日K线数据
        """
        if not DOWNLOAD_MODULE_AVAILABLE:
            self.logger.error("合并下载数据模块不可用")
            return None
        
        try:
            self.logger.info(f"正在下载 {股票代码} 的数据: {开始日期} 到 {结束日期}")
            
            # 调用合并下载数据模块
            数据 = getDayData(
                stock_code=股票代码,
                start_date=开始日期,
                end_date=结束日期,
                is_download=1 if 是否下载 else 0,
                dividend_type=复权类型
            )
            
            self.logger.info(f"成功下载 {股票代码} 的数据，共 {len(数据)} 条记录")
            return 数据
            
        except Exception as e:
            self.logger.error(f"下载 {股票代码} 数据时发生错误: {e}")
            return None
    
    def 批量下载沪深300数据(self, 开始日期: str, 结束日期: str, 
                          复权类型: str = 'front', 是否下载: bool = True) -> Dict[str, pd.DataFrame]:
        """
        批量下载沪深300成分股的日K线数据
        
        Args:
            开始日期: 开始日期，格式: '20250101'
            结束日期: 结束日期，格式: '20250129'
            复权类型: 复权类型，'front'=前复权，'back'=后复权，'none'=不复权
            是否下载: 是否重新下载数据
            
        Returns:
            Dict: 股票代码为键，DataFrame为值的字典
        """
        if not DOWNLOAD_MODULE_AVAILABLE:
            self.logger.error("合并下载数据模块不可用")
            return {}
        
        # 获取沪深300成分股列表
        成分股列表 = self.获取沪深300成分股列表()
        
        if not 成分股列表:
            self.logger.error("无法获取沪深300成分股列表")
            return {}
        
        self.logger.info(f"开始批量下载 {len(成分股列表)} 只沪深300成分股的数据")
        
        try:
            # 调用批量下载函数
            结果数据 = batchDownloadDayData(
                stock_codes=成分股列表,
                start_date=开始日期,
                end_date=结束日期,
                dividend_type=复权类型,
                need_download=1 if 是否下载 else 0
            )
            
            self.logger.info(f"批量下载完成，成功下载 {len(结果数据)} 只股票的数据")
            return 结果数据
            
        except Exception as e:
            self.logger.error(f"批量下载沪深300数据时发生错误: {e}")
            return {}
    
    def 分析下载结果(self, 结果数据: Dict[str, pd.DataFrame]) -> Dict:
        """
        分析下载结果
        
        Args:
            结果数据: 下载结果数据
            
        Returns:
            Dict: 分析结果
        """
        if not 结果数据:
            return {}
        
        分析结果 = {}
        
        # 基本统计
        分析结果['基本统计'] = {
            '总股票数': len(结果数据),
            '成功下载数': len([df for df in 结果数据.values() if df is not None and not df.empty]),
            '失败下载数': len([df for df in 结果数据.values() if df is None or df.empty])
        }
        
        # 数据完整性分析
        数据完整性 = []
        for 股票代码, 数据 in 结果数据.items():
            if 数据 is not None and not 数据.empty:
                数据完整性.append({
                    '股票代码': 股票代码,
                    '数据条数': len(数据),
                    '开始日期': 数据['date'].iloc[0] if 'date' in 数据.columns else 'N/A',
                    '结束日期': 数据['date'].iloc[-1] if 'date' in 数据.columns else 'N/A'
                })
        
        分析结果['数据完整性'] = 数据完整性
        
        # 统计信息
        if 数据完整性:
            数据条数列表 = [item['数据条数'] for item in 数据完整性]
            分析结果['统计信息'] = {
                '平均数据条数': round(np.mean(数据条数列表), 2),
                '最少数据条数': min(数据条数列表),
                '最多数据条数': max(数据条数列表),
                '数据条数标准差': round(np.std(数据条数列表), 2)
            }
        
        return 分析结果
    
    def 保存分析结果(self, 分析结果: Dict, 文件名: str = None) -> str:
        """
        保存分析结果到CSV文件
        
        Args:
            分析结果: 分析结果
            文件名: 文件名
            
        Returns:
            str: 保存的文件路径
        """
        if 文件名 is None:
            时间戳 = datetime.now().strftime("%Y%m%d_%H%M%S")
            文件名 = f"csi300_analysis_{时间戳}.csv"
        
        # 确保保存目录存在
        保存目录 = os.path.join(project_root, 'data')
        os.makedirs(保存目录, exist_ok=True)
        
        文件路径 = os.path.join(保存目录, 文件名)
        
        try:
            # 将数据完整性分析结果保存为CSV
            if '数据完整性' in 分析结果:
                数据完整性_df = pd.DataFrame(分析结果['数据完整性'])
                数据完整性_df.to_csv(文件路径, encoding='utf-8-sig', index=False)
                self.logger.info(f"分析结果已保存到: {文件路径}")
                return 文件路径
            else:
                self.logger.warning("没有数据完整性信息可保存")
                return ""
                
        except Exception as e:
            self.logger.error(f"保存分析结果失败: {e}")
            return ""
    
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
    print("沪深300行情数据下载程序")
    print("=" * 60)
    
    # 创建下载器
    下载器 = 沪深300数据下载器()
    
    try:
        # 设置下载参数
        开始日期 = "20250101"
        结束日期 = "20250129"
        复权类型 = "front"  # 前复权
        
        print(f"\n下载参数:")
        print(f"开始日期: {开始日期}")
        print(f"结束日期: {结束日期}")
        print(f"复权类型: {复权类型}")
        
        # 获取沪深300成分股列表
        print(f"\n正在获取沪深300成分股列表...")
        成分股列表 = 下载器.获取沪深300成分股列表()
        print(f"获取到 {len(成分股列表)} 只成分股")
        print(f"前10只成分股: {成分股列表[:10]}")
        
        # 批量下载数据
        print(f"\n开始批量下载沪深300数据...")
        结果数据 = 下载器.批量下载沪深300数据(
            开始日期=开始日期,
            结束日期=结束日期,
            复权类型=复权类型,
            是否下载=True
        )
        
        if 结果数据:
            print(f"\n下载完成！成功下载 {len(结果数据)} 只股票的数据")
            
            # 分析下载结果
            print(f"\n正在分析下载结果...")
            分析结果 = 下载器.分析下载结果(结果数据)
            
            # 显示分析结果
            print(f"\n分析结果:")
            print("-" * 40)
            for 类别, 内容 in 分析结果.items():
                print(f"\n{类别}:")
                if isinstance(内容, dict):
                    for 键, 值 in 内容.items():
                        print(f"  {键}: {值}")
                elif isinstance(内容, list):
                    print(f"  共 {len(内容)} 条记录")
                    if len(内容) <= 5:
                        for 项 in 内容:
                            print(f"    {项}")
                    else:
                        print(f"    前5条: {内容[:5]}")
                        print(f"    ...")
                else:
                    print(f"  {内容}")
            
            # 保存分析结果
            文件路径 = 下载器.保存分析结果(分析结果)
            if 文件路径:
                print(f"\n分析结果已保存到: {文件路径}")
            
            # 显示部分数据示例
            print(f"\n数据示例（前3只股票）:")
            print("-" * 60)
            计数 = 0
            for 股票代码, 数据 in 结果数据.items():
                if 数据 is not None and not 数据.empty and 计数 < 3:
                    print(f"\n{股票代码}:")
                    print(f"  数据条数: {len(数据)}")
                    print(f"  列名: {list(数据.columns)}")
                    if len(数据) > 0:
                        print(f"  最新数据:")
                        print(f"    {数据.iloc[-1].to_dict()}")
                    计数 += 1
        
        else:
            print("下载失败，未能获取到任何数据")
    
    except Exception as e:
        print(f"程序执行出错: {e}")
        下载器.logger.error(f"程序执行出错: {e}")
    
    finally:
        # 关闭Wind接口
        下载器.close()
        print("\n程序执行完成")


if __name__ == "__main__":
    main()
