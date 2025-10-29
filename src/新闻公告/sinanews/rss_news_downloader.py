# -*- coding: utf-8 -*-
"""
RSS新闻下载工具
基于可用的RSS源获取新闻数据
"""

import feedparser
import pandas as pd
import datetime
import time
import logging
import requests
from typing import List, Dict, Optional

class RSSNewsDownloader:
    """RSS新闻下载器"""
    
    def __init__(self):
        self.setup_logging()
        # 可用的RSS源
        self.rss_sources = {
            'sina_focus': {
                'name': '新浪新闻焦点',
                'url': 'https://rss.sina.com.cn/news/china/focus15.xml',
                'category': '国内新闻'
            },
            'cnn_international': {
                'name': 'CNN国际新闻',
                'url': 'http://rss.cnn.com/rss/edition.rss',
                'category': '国际新闻'
            },
            'sina_finance': {
                'name': '新浪财经',
                'url': 'https://rss.sina.com.cn/finance/stock/sinastock.xml',
                'category': '财经新闻'
            }
        }
    
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('rss_news_download.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def test_rss_source(self, source_key: str) -> bool:
        """测试RSS源是否可用"""
        if source_key not in self.rss_sources:
            return False
        
        source = self.rss_sources[source_key]
        try:
            response = requests.get(source['url'], timeout=10)
            if response.status_code == 200:
                feed = feedparser.parse(source['url'])
                return len(feed.entries) > 0
            return False
        except:
            return False
    
    def get_available_sources(self) -> List[str]:
        """获取可用的RSS源"""
        available = []
        for key in self.rss_sources.keys():
            if self.test_rss_source(key):
                available.append(key)
                self.logger.info(f"✓ {self.rss_sources[key]['name']} 可用")
            else:
                self.logger.warning(f"✗ {self.rss_sources[key]['name']} 不可用")
        return available
    
    def download_rss_news(self, source_key: str, max_entries: int = 50) -> pd.DataFrame:
        """
        下载指定RSS源的新闻
        
        Parameters:
        -----------
        source_key : str
            RSS源键名
        max_entries : int, optional
            最大获取条数，默认50条
        
        Returns:
        --------
        pd.DataFrame
            新闻数据
        """
        if source_key not in self.rss_sources:
            self.logger.error(f"不支持的RSS源: {source_key}")
            return pd.DataFrame()
        
        source = self.rss_sources[source_key]
        self.logger.info(f"开始下载 {source['name']} 新闻")
        
        try:
            # 解析RSS
            feed = feedparser.parse(source['url'])
            
            if feed.bozo:
                self.logger.warning(f"RSS解析警告: {feed.bozo_exception}")
            
            if not feed.entries:
                self.logger.warning(f"{source['name']} 无新闻数据")
                return pd.DataFrame()
            
            # 提取数据
            news_data = []
            for entry in feed.entries[:max_entries]:
                try:
                    news_item = {
                        'source_key': source_key,
                        'source_name': source['name'],
                        'category': source['category'],
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
                self.logger.warning(f"{source['name']} 无有效新闻数据")
                return pd.DataFrame()
            
            # 创建DataFrame
            df = pd.DataFrame(news_data)
            
            # 数据清洗
            df = self.clean_data(df)
            
            self.logger.info(f"成功获取 {source['name']} 新闻 {len(df)} 条")
            return df
            
        except Exception as e:
            self.logger.error(f"下载 {source['name']} 新闻失败: {e}")
            return pd.DataFrame()
    
    def download_all_sources(self, max_entries_per_source: int = 30) -> pd.DataFrame:
        """
        下载所有可用源的新闻
        
        Parameters:
        -----------
        max_entries_per_source : int, optional
            每个源最大获取条数，默认30条
        
        Returns:
        --------
        pd.DataFrame
            合并的新闻数据
        """
        self.logger.info("开始下载所有可用源的新闻")
        
        # 获取可用源
        available_sources = self.get_available_sources()
        
        if not available_sources:
            self.logger.warning("没有可用的RSS源")
            return pd.DataFrame()
        
        all_news = []
        
        for source_key in available_sources:
            try:
                self.logger.info(f"下载 {self.rss_sources[source_key]['name']} 新闻...")
                news = self.download_rss_news(source_key, max_entries_per_source)
                
                if not news.empty:
                    all_news.append(news)
                    self.logger.info(f"✓ {self.rss_sources[source_key]['name']}: {len(news)} 条")
                else:
                    self.logger.warning(f"✗ {self.rss_sources[source_key]['name']}: 无数据")
                
                # 添加延迟避免请求过快
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"下载 {source_key} 新闻失败: {e}")
        
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
            # 尝试转换为中国时区
            try:
                df['published'] = df['published'].dt.tz_convert('Asia/Shanghai')
            except:
                pass  # 如果转换失败，保持原样
        
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
            filename = f"{today}_rss_news.csv"
        
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
        
        # 来源统计
        if 'source_name' in df.columns:
            summary += f"来源分布:\n{df['source_name'].value_counts().to_string()}\n"
        
        if 'category' in df.columns:
            summary += f"分类分布:\n{df['category'].value_counts().to_string()}\n"
        
        # 时间分析
        if 'published' in df.columns:
            valid_times = df['published'].dropna()
            if not valid_times.empty:
                summary += f"时间范围: {valid_times.min()} 到 {valid_times.max()}\n"
        
        # 标题分析
        if 'title' in df.columns:
            summary += f"标题长度统计:\n"
            summary += f"平均长度: {df['title'].str.len().mean():.1f}\n"
            summary += f"最短: {df['title'].str.len().min()}\n"
            summary += f"最长: {df['title'].str.len().max()}\n"
        
        return summary
    
    def monitor_news(self, source_key: str = 'sina_focus', interval: int = 300, max_runs: int = 10):
        """
        监控新闻更新
        
        Parameters:
        -----------
        source_key : str
            监控的RSS源
        interval : int
            监控间隔（秒），默认300秒（5分钟）
        max_runs : int
            最大运行次数，默认10次
        """
        self.logger.info(f"开始监控 {self.rss_sources[source_key]['name']} 新闻，间隔 {interval} 秒")
        
        for run in range(max_runs):
            try:
                self.logger.info(f"第 {run + 1} 次监控")
                
                # 获取新闻
                news = self.download_rss_news(source_key, 20)
                
                if not news.empty:
                    # 保存数据
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"rss_{source_key}_news_{timestamp}.csv"
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
    downloader = RSSNewsDownloader()
    
    try:
        print("=" * 60)
        print("RSS新闻下载工具测试")
        print("=" * 60)
        
        # 测试可用源
        print("\n测试RSS源可用性:")
        available_sources = downloader.get_available_sources()
        
        if not available_sources:
            print("✗ 没有可用的RSS源")
            return
        
        # 测试单个源
        print(f"\n测试单个RSS源: {available_sources[0]}")
        single_news = downloader.download_rss_news(available_sources[0], 20)
        if not single_news.empty:
            print(f"✓ 成功获取 {len(single_news)} 条新闻")
            print(downloader.get_news_summary(single_news))
            
            # 保存数据
            downloader.save_news(single_news, "single_source_news.csv")
        
        # 测试所有源
        print(f"\n测试所有RSS源")
        all_news = downloader.download_all_sources(15)
        if not all_news.empty:
            print(f"✓ 成功获取 {len(all_news)} 条所有源新闻")
            print(downloader.get_news_summary(all_news))
            
            # 保存数据
            downloader.save_news(all_news, "all_sources_news.csv")
            
            # 显示最新新闻
            print(f"\n最新5条新闻:")
            for i, row in all_news.head().iterrows():
                print(f"{i+1}. [{row['source_name']}] {row['title']}")
                print(f"   时间: {row['published']}")
                print(f"   链接: {row['link']}")
                print()
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("RSS新闻特点:")
    print("1. 完全免费，无需注册")
    print("2. 实时更新，适合监控")
    print("3. 数据包含标题、链接、时间等")
    print("4. 适合轻量级舆情跟踪")

if __name__ == "__main__":
    main()
