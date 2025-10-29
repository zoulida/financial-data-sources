# -*- coding: utf-8 -*-
"""
新浪财经RSS新闻获取工具
功能：
    1. 获取新浪财经RSS新闻
    2. 支持多个RSS频道
    3. 自动保存为CSV格式
    4. 支持数据过滤和清洗

依赖安装：
    pip install feedparser pandas
"""

import feedparser
import pandas as pd
import datetime
import time
import logging
import os
from typing import List, Dict, Optional

class SinaRSSNewsDownloader:
    """新浪财经RSS新闻下载器"""
    
    def __init__(self):
        self.setup_logging()
        self.rss_urls = {
            'stock': 'https://rss.sina.com.cn/finance/stock/sinastock.xml',  # 股票频道
            'finance': 'https://rss.sina.com.cn/finance/china/finance.xml',  # 财经频道
            'macro': 'https://rss.sina.com.cn/finance/china/macro.xml',  # 宏观频道
            'company': 'https://rss.sina.com.cn/finance/company/company.xml',  # 公司频道
            'market': 'https://rss.sina.com.cn/finance/market/market.xml',  # 市场频道
        }
    
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('sina_rss_news.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_rss_news(self, channel: str = 'stock', max_entries: int = 100) -> pd.DataFrame:
        """
        获取指定频道的RSS新闻
        
        Parameters:
        -----------
        channel : str
            RSS频道名称，可选：'stock', 'finance', 'macro', 'company', 'market'
        max_entries : int, optional
            最大获取条数，默认100条
        
        Returns:
        --------
        pd.DataFrame
            新闻数据
        """
        if channel not in self.rss_urls:
            self.logger.error(f"不支持的频道: {channel}")
            return pd.DataFrame()
        
        url = self.rss_urls[channel]
        self.logger.info(f"开始获取 {channel} 频道新闻，URL: {url}")
        
        try:
            # 解析RSS
            feed = feedparser.parse(url)
            
            if feed.bozo:
                self.logger.warning(f"RSS解析警告: {feed.bozo_exception}")
            
            if not feed.entries:
                self.logger.warning(f"频道 {channel} 无新闻数据")
                return pd.DataFrame()
            
            # 提取数据
            news_data = []
            for entry in feed.entries[:max_entries]:
                try:
                    news_item = {
                        'channel': channel,
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'summary': entry.get('summary', ''),
                        'author': entry.get('author', ''),
                        'tags': ', '.join([tag.get('term', '') for tag in entry.get('tags', [])]),
                    }
                    news_data.append(news_item)
                except Exception as e:
                    self.logger.warning(f"解析新闻条目失败: {e}")
                    continue
            
            if not news_data:
                self.logger.warning(f"频道 {channel} 无有效新闻数据")
                return pd.DataFrame()
            
            # 创建DataFrame
            df = pd.DataFrame(news_data)
            
            # 数据清洗
            df = self.clean_data(df)
            
            self.logger.info(f"成功获取 {channel} 频道新闻 {len(df)} 条")
            return df
            
        except Exception as e:
            self.logger.error(f"获取 {channel} 频道新闻失败: {e}")
            return pd.DataFrame()
    
    def get_all_channels_news(self, max_entries_per_channel: int = 50) -> pd.DataFrame:
        """
        获取所有频道的新闻
        
        Parameters:
        -----------
        max_entries_per_channel : int, optional
            每个频道最大获取条数，默认50条
        
        Returns:
        --------
        pd.DataFrame
            合并的新闻数据
        """
        self.logger.info("开始获取所有频道新闻")
        
        all_news = []
        
        for channel in self.rss_urls.keys():
            try:
                self.logger.info(f"获取 {channel} 频道新闻...")
                news = self.get_rss_news(channel, max_entries_per_channel)
                
                if not news.empty:
                    all_news.append(news)
                    self.logger.info(f"✓ {channel} 频道: {len(news)} 条")
                else:
                    self.logger.warning(f"✗ {channel} 频道: 无数据")
                
                # 添加延迟避免请求过快
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"获取 {channel} 频道新闻失败: {e}")
        
        # 合并所有数据
        if all_news:
            combined_df = pd.concat(all_news, ignore_index=True)
            combined_df = combined_df.sort_values('published', ascending=False)
            
            self.logger.info(f"合并完成，总计 {len(combined_df)} 条新闻")
            return combined_df
        else:
            self.logger.warning("没有获取到任何新闻数据")
            return pd.DataFrame()
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗数据"""
        if df.empty:
            return df
        
        # 转换时间字段
        if 'published' in df.columns:
            df['published'] = pd.to_datetime(df['published'], errors='coerce')
            # 转换为中国时区
            df['published'] = df['published'].dt.tz_convert('Asia/Shanghai')
        
        # 去除重复数据
        if 'title' in df.columns:
            df = df.drop_duplicates(subset=['title'], keep='first')
        
        # 去除空标题
        if 'title' in df.columns:
            df = df.dropna(subset=['title'])
        
        # 清理标题和摘要中的HTML标签
        if 'title' in df.columns:
            df['title'] = df['title'].str.replace(r'<[^>]+>', '', regex=True)
        if 'summary' in df.columns:
            df['summary'] = df['summary'].str.replace(r'<[^>]+>', '', regex=True)
        
        return df
    
    def save_news(self, df: pd.DataFrame, filename: Optional[str] = None) -> str:
        """
        保存新闻数据到CSV文件
        
        Parameters:
        -----------
        df : pd.DataFrame
            新闻数据
        filename : str, optional
            文件名，默认为自动生成
        
        Returns:
        --------
        str
            保存的文件路径
        """
        if df.empty:
            self.logger.warning("无数据可保存")
            return ""
        
        if filename is None:
            today = datetime.date.today()
            filename = f"{today}_sina_rss_news.csv"
        
        try:
            df.to_csv(filename, encoding='utf-8-sig', index=False)
            self.logger.info(f"新闻数据已保存到: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"保存文件失败: {e}")
            return ""
    
    def get_news_summary(self, df: pd.DataFrame) -> str:
        """获取新闻摘要统计"""
        if df.empty:
            return "无数据"
        
        summary = f"总条数: {len(df)}\n"
        
        # 频道统计
        if 'channel' in df.columns:
            summary += f"频道分布:\n{df['channel'].value_counts().to_string()}\n"
        
        # 时间分析
        if 'published' in df.columns:
            summary += f"时间范围: {df['published'].min()} 到 {df['published'].max()}\n"
        
        # 标题分析
        if 'title' in df.columns:
            summary += f"标题长度统计:\n"
            summary += f"平均长度: {df['title'].str.len().mean():.1f}\n"
            summary += f"最短: {df['title'].str.len().min()}\n"
            summary += f"最长: {df['title'].str.len().max()}\n"
        
        # 标签分析
        if 'tags' in df.columns:
            all_tags = []
            for tags in df['tags'].dropna():
                all_tags.extend([tag.strip() for tag in tags.split(',') if tag.strip()])
            
            if all_tags:
                from collections import Counter
                tag_counts = Counter(all_tags)
                summary += f"热门标签:\n"
                for tag, count in tag_counts.most_common(10):
                    summary += f"  {tag}: {count}\n"
        
        return summary
    
    def monitor_news(self, channel: str = 'stock', interval: int = 300, max_runs: int = 10):
        """
        监控新闻更新
        
        Parameters:
        -----------
        channel : str
            监控的频道
        interval : int
            监控间隔（秒），默认300秒（5分钟）
        max_runs : int
            最大运行次数，默认10次
        """
        self.logger.info(f"开始监控 {channel} 频道新闻，间隔 {interval} 秒")
        
        for run in range(max_runs):
            try:
                self.logger.info(f"第 {run + 1} 次监控")
                
                # 获取新闻
                news = self.get_rss_news(channel, 20)
                
                if not news.empty:
                    # 保存数据
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"sina_{channel}_news_{timestamp}.csv"
                    self.save_news(news, filename)
                    
                    # 显示最新新闻
                    self.logger.info(f"最新 {len(news)} 条新闻:")
                    for i, row in news.head(3).iterrows():
                        self.logger.info(f"  {i+1}. {row['title']}")
                else:
                    self.logger.warning("无新新闻")
                
                # 等待下次监控
                if run < max_runs - 1:
                    self.logger.info(f"等待 {interval} 秒后进行下次监控...")
                    time.sleep(interval)
                
            except KeyboardInterrupt:
                self.logger.info("监控已停止")
                break
            except Exception as e:
                self.logger.error(f"监控过程中出错: {e}")
                time.sleep(60)  # 出错后等待1分钟再继续

def main():
    """主函数 - 测试和示例"""
    downloader = SinaRSSNewsDownloader()
    
    try:
        print("=" * 60)
        print("新浪财经RSS新闻获取工具测试")
        print("=" * 60)
        
        # 测试1：获取股票频道新闻
        print("\n测试1：获取股票频道新闻")
        stock_news = downloader.get_rss_news('stock', 20)
        if not stock_news.empty:
            print(f"✓ 成功获取 {len(stock_news)} 条股票新闻")
            print(downloader.get_news_summary(stock_news))
            
            # 保存数据
            downloader.save_news(stock_news, "sina_stock_news.csv")
        
        # 测试2：获取所有频道新闻
        print("\n测试2：获取所有频道新闻")
        all_news = downloader.get_all_channels_news(10)
        if not all_news.empty:
            print(f"✓ 成功获取 {len(all_news)} 条所有频道新闻")
            print(downloader.get_news_summary(all_news))
            
            # 保存数据
            downloader.save_news(all_news, "sina_all_channels_news.csv")
        
        # 测试3：显示最新新闻
        print("\n测试3：最新新闻预览")
        if not all_news.empty:
            print("最新5条新闻:")
            for i, row in all_news.head().iterrows():
                print(f"{i+1}. [{row['channel']}] {row['title']}")
                print(f"   时间: {row['published']}")
                print(f"   链接: {row['link']}")
                print()
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("注意：")
    print("1. 新浪RSS每5-10分钟更新一次")
    print("2. 适合轻量级舆情/热点跟踪")
    print("3. 数据包含标题、链接、时间等基本信息")
    print("4. 完全免费，无需注册")

if __name__ == "__main__":
    main()
