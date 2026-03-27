# -*- coding: utf-8 -*-
"""
akshare新闻下载工具
功能：
    1. 下载个股新闻、行业资讯、宏观经济新闻等
    2. 支持批量下载多个股票
    3. 自动保存为CSV格式
    4. 支持数据过滤和清洗

依赖安装：
    pip install akshare pandas
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
import os

class AkshareNewsDownloader:
    """akshare新闻下载器"""
    
    def __init__(self):
        self.setup_logging()
        self.delay = 1  # 请求间隔，避免反爬虫
    
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('akshare_news_download.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def download_stock_news(self, symbol, count=100, save_file=None):
        """
        下载个股新闻
        
        Parameters:
        -----------
        symbol : str
            股票代码，如 '000001'
        count : int, optional
            下载条数，默认100条
        save_file : str, optional
            保存文件名，默认为自动生成
        
        Returns:
        --------
        pd.DataFrame or None
            下载的新闻数据
        """
        self.logger.info(f"开始下载股票 {symbol} 的新闻，条数: {count}")
        
        try:
            # 下载数据
            news = ak.stock_news_em(symbol=symbol)
            
            if news.empty:
                self.logger.warning(f"股票 {symbol} 无新闻数据")
                return pd.DataFrame()
            
            # 限制条数
            if len(news) > count:
                news = news.head(count)
            
            # 添加股票代码
            news['stock_code'] = symbol
            
            # 数据清洗
            news = self.clean_data(news)
            
            # 保存文件
            if save_file is None:
                save_file = f"akshare_stock_news_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv"
            
            news.to_csv(save_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"股票 {symbol} 新闻已保存到: {save_file}")
            
            return news
            
        except Exception as e:
            self.logger.error(f"下载股票 {symbol} 新闻时出错: {e}")
            return None
    
    def download_macro_news(self, count=100, save_file=None):
        """
        下载宏观经济新闻
        
        Parameters:
        -----------
        count : int, optional
            下载条数，默认100条
        save_file : str, optional
            保存文件名，默认为自动生成
        
        Returns:
        --------
        pd.DataFrame or None
            下载的新闻数据
        """
        self.logger.info(f"开始下载宏观经济新闻，条数: {count}")
        
        try:
            # 下载数据
            news = ak.stock_news_em(symbol="macro")
            
            if news.empty:
                self.logger.warning("无宏观经济新闻数据")
                return pd.DataFrame()
            
            # 限制条数
            if len(news) > count:
                news = news.head(count)
            
            # 添加类型标识
            news['news_type'] = 'macro'
            
            # 数据清洗
            news = self.clean_data(news)
            
            # 保存文件
            if save_file is None:
                save_file = f"akshare_macro_news_{datetime.now().strftime('%Y%m%d')}.csv"
            
            news.to_csv(save_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"宏观经济新闻已保存到: {save_file}")
            
            return news
            
        except Exception as e:
            self.logger.error(f"下载宏观经济新闻时出错: {e}")
            return None
    
    def download_finance_news(self, count=100, save_file=None):
        """
        下载财经新闻
        
        Parameters:
        -----------
        count : int, optional
            下载条数，默认100条
        save_file : str, optional
            保存文件名，默认为自动生成
        
        Returns:
        --------
        pd.DataFrame or None
            下载的新闻数据
        """
        self.logger.info(f"开始下载财经新闻，条数: {count}")
        
        try:
            # 下载数据
            news = ak.stock_news_em(symbol="finance")
            
            if news.empty:
                self.logger.warning("无财经新闻数据")
                return pd.DataFrame()
            
            # 限制条数
            if len(news) > count:
                news = news.head(count)
            
            # 添加类型标识
            news['news_type'] = 'finance'
            
            # 数据清洗
            news = self.clean_data(news)
            
            # 保存文件
            if save_file is None:
                save_file = f"akshare_finance_news_{datetime.now().strftime('%Y%m%d')}.csv"
            
            news.to_csv(save_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"财经新闻已保存到: {save_file}")
            
            return news
            
        except Exception as e:
            self.logger.error(f"下载财经新闻时出错: {e}")
            return None
    
    def download_report_news(self, count=100, save_file=None):
        """
        下载研报新闻
        
        Parameters:
        -----------
        count : int, optional
            下载条数，默认100条
        save_file : str, optional
            保存文件名，默认为自动生成
        
        Returns:
        --------
        pd.DataFrame or None
            下载的新闻数据
        """
        self.logger.info(f"开始下载研报新闻，条数: {count}")
        
        try:
            # 下载数据
            news = ak.stock_news_em(symbol="report")
            
            if news.empty:
                self.logger.warning("无研报新闻数据")
                return pd.DataFrame()
            
            # 限制条数
            if len(news) > count:
                news = news.head(count)
            
            # 添加类型标识
            news['news_type'] = 'report'
            
            # 数据清洗
            news = self.clean_data(news)
            
            # 保存文件
            if save_file is None:
                save_file = f"akshare_report_news_{datetime.now().strftime('%Y%m%d')}.csv"
            
            news.to_csv(save_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"研报新闻已保存到: {save_file}")
            
            return news
            
        except Exception as e:
            self.logger.error(f"下载研报新闻时出错: {e}")
            return None
    
    def download_announcement_news(self, count=100, save_file=None):
        """
        下载公告新闻
        
        Parameters:
        -----------
        count : int, optional
            下载条数，默认100条
        save_file : str, optional
            保存文件名，默认为自动生成
        
        Returns:
        --------
        pd.DataFrame or None
            下载的新闻数据
        """
        self.logger.info(f"开始下载公告新闻，条数: {count}")
        
        try:
            # 下载数据
            news = ak.stock_news_em(symbol="announcement")
            
            if news.empty:
                self.logger.warning("无公告新闻数据")
                return pd.DataFrame()
            
            # 限制条数
            if len(news) > count:
                news = news.head(count)
            
            # 添加类型标识
            news['news_type'] = 'announcement'
            
            # 数据清洗
            news = self.clean_data(news)
            
            # 保存文件
            if save_file is None:
                save_file = f"akshare_announcement_news_{datetime.now().strftime('%Y%m%d')}.csv"
            
            news.to_csv(save_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"公告新闻已保存到: {save_file}")
            
            return news
            
        except Exception as e:
            self.logger.error(f"下载公告新闻时出错: {e}")
            return None
    
    def download_multiple_stocks_news(self, stock_codes, count_per_stock=50, save_file=None):
        """
        下载多个股票的新闻
        
        Parameters:
        -----------
        stock_codes : list
            股票代码列表
        count_per_stock : int, optional
            每个股票下载条数，默认50条
        save_file : str, optional
            保存文件名，默认为自动生成
        
        Returns:
        --------
        pd.DataFrame
            合并的新闻数据
        """
        self.logger.info(f"开始下载 {len(stock_codes)} 个股票的新闻")
        
        all_news = []
        
        for i, code in enumerate(stock_codes):
            self.logger.info(f"下载股票 {code} 的新闻 ({i+1}/{len(stock_codes)})")
            
            try:
                news = self.download_stock_news(code, count_per_stock)
                if news is not None and not news.empty:
                    all_news.append(news)
                
                # 添加延迟避免反爬虫
                if i < len(stock_codes) - 1:  # 最后一个不需要延迟
                    time.sleep(self.delay)
                    
            except Exception as e:
                self.logger.error(f"下载股票 {code} 新闻失败: {e}")
        
        # 合并所有数据
        if all_news:
            combined_df = pd.concat(all_news, ignore_index=True)
            combined_df = combined_df.sort_values('发布时间', ascending=False)
            
            # 保存合并数据
            if save_file is None:
                save_file = f"akshare_multiple_stocks_news_{datetime.now().strftime('%Y%m%d')}.csv"
            
            combined_df.to_csv(save_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"合并新闻数据已保存到: {save_file}")
            
            return combined_df
        else:
            self.logger.warning("没有获取到任何新闻数据")
            return pd.DataFrame()
    
    def download_all_types_news(self, count_per_type=50, save_file=None):
        """
        下载所有类型的新闻
        
        Parameters:
        -----------
        count_per_type : int, optional
            每种类型下载条数，默认50条
        save_file : str, optional
            保存文件名，默认为自动生成
        
        Returns:
        --------
        pd.DataFrame
            合并的新闻数据
        """
        self.logger.info("开始下载所有类型的新闻")
        
        all_news = []
        
        # 下载各种类型的新闻
        news_types = [
            ("macro", self.download_macro_news),
            ("finance", self.download_finance_news),
            ("report", self.download_report_news),
            ("announcement", self.download_announcement_news)
        ]
        
        for news_type, download_func in news_types:
            try:
                self.logger.info(f"下载 {news_type} 新闻")
                news = download_func(count_per_type)
                if news is not None and not news.empty:
                    all_news.append(news)
                
                # 添加延迟
                time.sleep(self.delay)
                
            except Exception as e:
                self.logger.error(f"下载 {news_type} 新闻失败: {e}")
        
        # 合并所有数据
        if all_news:
            combined_df = pd.concat(all_news, ignore_index=True)
            combined_df = combined_df.sort_values('发布时间', ascending=False)
            
            # 保存合并数据
            if save_file is None:
                save_file = f"akshare_all_types_news_{datetime.now().strftime('%Y%m%d')}.csv"
            
            combined_df.to_csv(save_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"所有类型新闻已保存到: {save_file}")
            
            return combined_df
        else:
            self.logger.warning("没有获取到任何新闻数据")
            return pd.DataFrame()
    
    def clean_data(self, df):
        """清洗数据"""
        # 转换时间字段
        if '发布时间' in df.columns:
            df['发布时间'] = pd.to_datetime(df['发布时间'], errors='coerce')
        
        # 去除重复数据
        if '新闻标题' in df.columns:
            df = df.drop_duplicates(subset=['新闻标题'], keep='first')
        
        # 去除空标题
        if '新闻标题' in df.columns:
            df = df.dropna(subset=['新闻标题'])
        
        return df
    
    def get_news_summary(self, df):
        """获取新闻摘要统计"""
        if df.empty:
            return "无数据"
        
        summary = f"总条数: {len(df)}\n"
        
        # 类型统计
        if 'news_type' in df.columns:
            summary += f"类型分布:\n{df['news_type'].value_counts().to_string()}\n"
        
        if 'stock_code' in df.columns:
            summary += f"股票分布:\n{df['stock_code'].value_counts().to_string()}\n"
        
        # 时间分析
        if '发布时间' in df.columns:
            summary += f"时间范围: {df['发布时间'].min()} 到 {df['发布时间'].max()}\n"
        
        # 标题分析
        if '新闻标题' in df.columns:
            summary += f"标题长度统计:\n"
            summary += f"平均长度: {df['新闻标题'].str.len().mean():.1f}\n"
            summary += f"最短: {df['新闻标题'].str.len().min()}\n"
            summary += f"最长: {df['新闻标题'].str.len().max()}\n"
        
        # 来源分析
        if '文章来源' in df.columns:
            summary += f"来源分布:\n{df['文章来源'].value_counts().head().to_string()}\n"
        
        return summary

def main():
    """主函数 - 测试和示例"""
    downloader = AkshareNewsDownloader()
    
    try:
        print("=" * 60)
        print("akshare新闻下载工具测试")
        print("=" * 60)
        
        # 测试1：下载个股新闻
        print("\n测试1：下载个股新闻")
        stock_news = downloader.download_stock_news("000001", 50)
        if not stock_news.empty:
            print(f"✓ 成功下载 {len(stock_news)} 条个股新闻")
            print(downloader.get_news_summary(stock_news))
        
        # 测试2：下载宏观经济新闻
        print("\n测试2：下载宏观经济新闻")
        macro_news = downloader.download_macro_news(50)
        if not macro_news.empty:
            print(f"✓ 成功下载 {len(macro_news)} 条宏观经济新闻")
        
        # 测试3：下载多个股票新闻
        print("\n测试3：下载多个股票新闻")
        stock_codes = ["000001", "000002", "600000"]
        multiple_news = downloader.download_multiple_stocks_news(stock_codes, 30)
        if not multiple_news.empty:
            print(f"✓ 成功下载 {len(multiple_news)} 条多股票新闻")
            print(downloader.get_news_summary(multiple_news))
        
        # 测试4：下载所有类型新闻
        print("\n测试4：下载所有类型新闻")
        all_news = downloader.download_all_types_news(30)
        if not all_news.empty:
            print(f"✓ 成功下载 {len(all_news)} 条所有类型新闻")
            print(downloader.get_news_summary(all_news))
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
