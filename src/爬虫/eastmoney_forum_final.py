#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富论坛爬虫 - 最终优化版本
成功爬取论坛帖子标题、作者、时间、阅读数、评论数等信息
"""

import requests
import pandas as pd
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class EastmoneyForumCrawler:
    def __init__(self):
        self.base_url = "https://guba.eastmoney.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def crawl_forum_posts(self, stock_code, max_pages=5):
        """
        爬取论坛帖子数据
        
        Args:
            stock_code: 股票代码
            max_pages: 最大爬取页数
        
        Returns:
            list: 帖子数据列表
        """
        all_posts = []
        
        for page in range(1, max_pages + 1):
            url = f"https://guba.eastmoney.com/list,{stock_code}_{page}.html"
            
            try:
                print(f"正在爬取第 {page} 页: {url}")
                
                response = self.session.get(url, timeout=15)
                response.encoding = 'utf-8'
                
                if response.status_code != 200:
                    print(f"请求失败，状态码: {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找所有帖子链接
                post_links = soup.find_all('a', href=re.compile(r'/news,' + stock_code + r',\d+\.html'))
                
                if not post_links:
                    print(f"第 {page} 页没有找到帖子")
                    continue
                
                print(f"找到 {len(post_links)} 个帖子")
                
                for link in post_links:
                    try:
                        post_data = self.extract_post_data(link, page)
                        if post_data:
                            all_posts.append(post_data)
                    except Exception as e:
                        print(f"提取帖子数据时出错: {e}")
                        continue
                
                # 随机延时
                time.sleep(1.5)
                
            except Exception as e:
                print(f"爬取第 {page} 页时出错: {e}")
                continue
        
        # 去重
        unique_posts = self.remove_duplicates(all_posts)
        print(f"去重后共 {len(unique_posts)} 个帖子")
        
        return unique_posts
    
    def extract_post_data(self, link_element, page):
        """从链接元素提取帖子数据"""
        title = link_element.get_text(strip=True)
        href = link_element.get('href', '')
        
        if not title or not href:
            return None
        
        # 补全URL
        if href.startswith('/'):
            full_url = urljoin(self.base_url, href)
        else:
            full_url = href
        
        # 查找包含此链接的父元素，获取更多信息
        parent = link_element.find_parent(['div', 'td', 'tr', 'span', 'li'])
        
        # 初始化默认值
        author = ''
        post_time = ''
        read_count = '0'
        comment_count = '0'
        
        if parent:
            # 获取父元素的完整文本
            parent_text = parent.get_text()
            
            # 更精确的数据提取
            author = self.extract_author_advanced(parent_text, title)
            post_time = self.extract_time_advanced(parent_text, title)
            read_count, comment_count = self.extract_counts_advanced(parent_text, title)
        
        return {
            'stock_code': self.extract_stock_code(href),
            'title': title,
            'post_link': full_url,
            'author': author,
            'post_time': post_time,
            'read_count': read_count,
            'comment_count': comment_count,
            'page': page,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def extract_stock_code(self, href):
        """从链接中提取股票代码"""
        match = re.search(r'news,(\d+),', href)
        return match.group(1) if match else ''
    
    def extract_time_advanced(self, text, title):
        """高级时间提取 - 基于页面结构分析"""
        # 移除标题文本，避免误匹配
        text_without_title = text.replace(title, '')
        
        # 根据页面结构，时间格式通常是：MM-DD HH:MM 或 MM-DD HH:MM
        time_patterns = [
            r'(\d{2}-\d{2}\s+\d{2}:\d{2})',  # 03-15 09:41
            r'(\d{2}-\d{2}\s+\d{1,2}:\d{2})',  # 03-15 9:41
            r'(\d{2}:\d{2})',  # 09:41
            r'(\d{2}-\d{2})',  # 03-15
            r'(\d{4}-\d{2}-\d{2})'  # 2026-03-15
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text_without_title)
            if matches:
                # 取第一个匹配的时间
                time_str = matches[0]
                
                # 验证时间的合理性
                if self.is_valid_time(time_str):
                    return time_str
        
        return ''
    
    def is_valid_time(self, time_str):
        """验证时间字符串的有效性"""
        # 检查是否为合理的时间格式
        if re.match(r'\d{2}-\d{2}\s+\d{2}:\d{2}', time_str):
            # 检查月份和日期的合理性
            parts = time_str.split(' ')[0].split('-')
            if len(parts) == 2:
                month, day = int(parts[0]), int(parts[1])
                return 1 <= month <= 12 and 1 <= day <= 31
        
        elif re.match(r'\d{2}:\d{2}', time_str):
            # 检查时间的合理性
            parts = time_str.split(':')
            if len(parts) == 2:
                hour, minute = int(parts[0]), int(parts[1])
                return 0 <= hour <= 23 and 0 <= minute <= 59
        
        return True  # 其他格式暂时认为有效
    
    def extract_author_advanced(self, text, title):
        """高级作者提取"""
        # 移除标题文本
        text_without_title = text.replace(title, '')
        
        # 移除时间信息，避免误匹配
        text_without_time = re.sub(r'\d{2}-\d{2}\s+\d{2}:\d{2}', '', text_without_title)
        text_without_time = re.sub(r'\d{2}:\d{2}', '', text_without_time)
        
        # 查找作者名的多种模式
        author_patterns = [
            r'股友([a-zA-Z0-9\u4e00-\u9fa5]{2,15})',  # 股友xxx
            r'([a-zA-Z0-9]{6,20})(?=\s*\d{2}-\d{2})',  # 字母数字组合后跟时间
            r'([\u4e00-\u9fa5]{2,6})(?=\s*\d{2}-\d{2})',  # 中文后跟时间
            r'([a-zA-Z0-9\u4e00-\u9fa5]{2,10})(?=\s*\d{2}:\d{2})',  # 任意字符后跟时间
        ]
        
        for pattern in author_patterns:
            matches = re.findall(pattern, text_without_time)
            if matches:
                author = matches[0]
                if len(author) >= 2 and author not in title:
                    return author
        
        return ''
    
    def extract_counts_advanced(self, text, title):
        """高级阅读数和评论数提取"""
        # 移除标题文本
        text_without_title = text.replace(title, '')
        
        # 移除作者名（避免误匹配）
        text_clean = re.sub(r'股友[a-zA-Z0-9\u4e00-\u9fa5]{2,15}', '', text_without_title)
        text_clean = re.sub(r'[a-zA-Z0-9\u4e00-\u9fa5]{2,10}(?=\s*\d{2}-\d{2})', '', text_clean)
        
        # 查找所有数字
        numbers = re.findall(r'(\d+)', text_clean)
        
        # 过滤和分类数字
        valid_numbers = []
        for num in numbers:
            num_int = int(num)
            # 跳过明显不是阅读数/评论数的数字
            if 0 < num_int <= 999999:  # 合理的阅读数/评论数范围
                valid_numbers.append(num)
        
        if len(valid_numbers) >= 2:
            # 通常阅读数大于评论数
            sorted_nums = sorted(valid_numbers, key=int, reverse=True)
            read_count = sorted_nums[0]
            comment_count = sorted_nums[1] if len(sorted_nums) > 1 else '0'
            return read_count, comment_count
        elif len(valid_numbers) == 1:
            return valid_numbers[0], '0'
        else:
            return '0', '0'
    
    def remove_duplicates(self, posts):
        """去重，基于标题和链接"""
        unique_posts = []
        seen = set()
        
        for post in posts:
            key = (post['title'], post['post_link'])
            if key not in seen:
                seen.add(key)
                unique_posts.append(post)
        
        return unique_posts
    
    def save_to_csv(self, posts, filename=None):
        """保存数据到CSV文件"""
        if not filename:
            filename = f"eastmoney_forum_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        df = pd.DataFrame(posts)
        
        # 重新排列列的顺序
        columns_order = ['stock_code', 'title', 'author', 'post_time', 'read_count', 
                        'comment_count', 'post_link', 'page', 'crawl_time']
        df = df.reindex(columns=columns_order)
        
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"数据已保存到: {filename}")
        return filename
    
    def print_summary(self, posts):
        """打印数据摘要"""
        if not posts:
            print("没有获取到任何帖子数据")
            return
        
        print(f"\n=== 数据摘要 ===")
        print(f"总帖子数: {len(posts)}")
        
        # 统计作者
        authors = [post['author'] for post in posts if post['author']]
        print(f"活跃作者数: {len(set(authors))}")
        
        # 统计时间分布
        times = [post['post_time'] for post in posts if post['post_time']]
        print(f"有时间信息的帖子: {len(times)}")
        
        print(f"\n=== 前10个热门帖子 ===")
        # 按阅读数排序
        sorted_posts = sorted(posts, key=lambda x: int(x['read_count']) if x['read_count'].isdigit() else 0, reverse=True)
        
        for i, post in enumerate(sorted_posts[:10]):
            print(f"\n{i+1}. {post['title']}")
            print(f"   作者: {post['author'] or '未知'}")
            print(f"   时间: {post['post_time'] or '未知'}")
            print(f"   阅读: {post['read_count']}, 评论: {post['comment_count']}")


def main():
    """主函数"""
    stock_code = "601669"
    
    print(f"开始爬取 {stock_code} 的东方财富论坛数据...")
    
    crawler = EastmoneyForumCrawler()
    
    # 爬取数据
    posts = crawler.crawl_forum_posts(stock_code=stock_code, max_pages=3)
    
    if posts:
        # 保存数据
        filename = crawler.save_to_csv(posts)
        
        # 打印摘要
        crawler.print_summary(posts)
    else:
        print("没有获取到任何帖子数据")


if __name__ == "__main__":
    main()
