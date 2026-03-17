#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中证500指数论坛爬虫 - 专门筛选2024年数据
"""

import requests
import pandas as pd
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class ZSSH0003002024Crawler:
    def __init__(self):
        self.base_url = "https://guba.eastmoney.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def crawl_forum_posts(self, stock_code="zssh000300", max_pages=20):
        """爬取论坛帖子数据并筛选2024年数据"""
        all_posts = []
        posts_2024 = []
        
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
                post_links = soup.find_all('a', href=re.compile(f'/news,{stock_code},\\d+\\.html'))
                
                print(f"找到 {len(post_links)} 个帖子链接")
                
                # 获取页面所有文本，用于上下文分析
                page_text = soup.get_text()
                
                for i, link in enumerate(post_links):
                    try:
                        post_data = self.extract_post_data(link, page_text, page, i, stock_code)
                        if post_data:
                            all_posts.append(post_data)
                            # 检查是否是2024年的数据
                            if self.is_2024_data(post_data['post_time']):
                                posts_2024.append(post_data)
                                print(f"找到2024年数据: {post_data['post_time']} - {post_data['title'][:30]}...")
                    except Exception as e:
                        print(f"提取帖子数据时出错: {e}")
                        continue
                
                # 随机延时
                time.sleep(1.5)
                
            except Exception as e:
                print(f"爬取第 {page} 页时出错: {e}")
                continue
        
        # 去重
        unique_posts_2024 = self.remove_duplicates(posts_2024)
        print(f"\n=== 爬取统计 ===")
        print(f"总帖子数: {len(all_posts)}")
        print(f"2024年帖子数: {len(unique_posts_2024)}")
        
        return unique_posts_2024
    
    def extract_post_data(self, link_element, page_text, page, index, stock_code):
        """提取帖子数据"""
        title = link_element.get_text(strip=True)
        href = link_element.get('href', '')
        
        if not title or not href:
            return None
        
        # 补全URL
        if href.startswith('/'):
            full_url = urljoin(self.base_url, href)
        else:
            full_url = href
        
        # 在页面文本中找到标题的位置
        title_positions = []
        start = 0
        while True:
            pos = page_text.find(title, start)
            if pos == -1:
                break
            title_positions.append(pos)
            start = pos + 1
        
        # 使用第index个位置
        if index < len(title_positions):
            title_pos = title_positions[index]
        else:
            title_pos = title_positions[0] if title_positions else 0
        
        # 提取标题周围的上下文
        context_start = max(0, title_pos - 150)
        context_end = min(len(page_text), title_pos + len(title) + 300)
        context = page_text[context_start:context_end]
        
        # 从上下文中提取信息
        post_time = self.extract_time_precise(context, title)
        author = self.extract_author_precise(context, title)
        read_count, comment_count = self.extract_counts_precise(context, title)
        
        return {
            'stock_code': stock_code,
            'title': title,
            'post_link': full_url,
            'author': author,
            'post_time': post_time,
            'read_count': read_count,
            'comment_count': comment_count,
            'page': page,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def extract_time_precise(self, context, title):
        """精确提取时间信息"""
        # 移除标题
        context_without_title = context.replace(title, '')
        
        # 时间模式
        time_patterns = [
            r'(\d{2}-\d{2}\s+\d{2}:\d{2})',  # 03-15 09:41
            r'(\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2})',  # 3-15 9:41
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, context_without_title)
            if matches:
                for time_str in matches:
                    if self.is_valid_time(time_str):
                        return time_str
        
        return ''
    
    def extract_author_precise(self, context, title):
        """精确提取作者信息"""
        # 移除标题
        context_without_title = context.replace(title, '')
        
        # 移除时间信息
        context_clean = re.sub(r'\d{2}-\d{2}\s+\d{2}:\d{2}', '', context_without_title)
        context_clean = re.sub(r'\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}', '', context_clean)
        
        # 作者模式
        author_patterns = [
            r'股友([a-zA-Z0-9\u4e00-\u9fa5]{2,15})',
            r'([a-zA-Z0-9\u4e00-\u9fa5]{3,20})(?=\s*\d{2}-\d{2})',
            r'([a-zA-Z0-9\u4e00-\u9fa5]{3,20})(?=\s*\d{1,2}-\d{1,2})',
        ]
        
        for pattern in author_patterns:
            matches = re.findall(pattern, context_clean)
            if matches:
                author = matches[0]
                if len(author) >= 2 and author not in title and not author.isdigit():
                    return author
        
        return ''
    
    def extract_counts_precise(self, context, title):
        """精确提取阅读数和评论数"""
        # 移除标题
        context_without_title = context.replace(title, '')
        
        # 移除作者信息
        context_clean = re.sub(r'股友[a-zA-Z0-9\u4e00-\u9fa5]{2,15}', '', context_without_title)
        context_clean = re.sub(r'[a-zA-Z0-9\u4e00-\u9fa5]{3,20}(?=\s*\d{2}-\d{2})', '', context_clean)
        
        # 查找所有数字
        numbers = re.findall(r'(\d+)', context_clean)
        
        # 过滤和分类数字
        valid_numbers = []
        for num in numbers:
            try:
                num_int = int(num)
                # 过滤掉明显不是阅读数/评论数的数字
                if 1 <= num_int <= 999999:
                    valid_numbers.append(num)
            except ValueError:
                continue
        
        if len(valid_numbers) >= 2:
            # 按大小排序，通常阅读数最大
            sorted_nums = sorted(valid_numbers, key=int, reverse=True)
            read_count = sorted_nums[0]
            comment_count = sorted_nums[1] if len(sorted_nums) > 1 else '0'
            return read_count, comment_count
        elif len(valid_numbers) == 1:
            return valid_numbers[0], '0'
        else:
            return '0', '0'
    
    def is_valid_time(self, time_str):
        """验证时间字符串的有效性"""
        if re.match(r'\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}', time_str):
            parts = time_str.split(' ')
            if len(parts) == 2:
                date_parts = parts[0].split('-')
                time_parts = parts[1].split(':')
                if len(date_parts) == 2 and len(time_parts) == 2:
                    month, day = int(date_parts[0]), int(date_parts[1])
                    hour, minute = int(time_parts[0]), int(time_parts[1])
                    return (1 <= month <= 12 and 1 <= day <= 31 and 
                           0 <= hour <= 23 and 0 <= minute <= 59)
        return False
    
    def is_2024_data(self, post_time):
        """检查是否是2024年的数据"""
        if not post_time:
            return False
        
        try:
            # 解析帖子时间 (格式: MM-DD HH:MM)
            month_day = post_time.split(' ')[0]
            month, day = month_day.split('-')
            
            # 检查是否可能是2024年的数据
            # 2024年的数据应该是在2024年1月1日之后
            post_date_2024 = datetime(2024, int(month), int(day))
            start_date_2024 = datetime(2024, 1, 1)
            
            return post_date_2024 >= start_date_2024
            
        except Exception as e:
            print(f"时间解析错误: {e}")
            return False
    
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
            filename = f"zssh000300_forum_posts_2024_only_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
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
            print("没有获取到任何2024年的帖子数据")
            return
        
        print(f"\n=== 2024年数据摘要 ===")
        print(f"2024年总帖子数: {len(posts)}")
        
        # 统计有时间的帖子
        posts_with_time = [post for post in posts if post['post_time']]
        print(f"有时间信息的帖子: {len(posts_with_time)} ({len(posts_with_time)/len(posts)*100:.1f}%)")
        
        # 统计有作者的帖子
        posts_with_author = [post for post in posts if post['author']]
        print(f"有作者信息的帖子: {len(posts_with_author)} ({len(posts_with_author)/len(posts)*100:.1f}%)")
        
        # 时间分布统计
        if posts_with_time:
            time_counts = {}
            for post in posts_with_time:
                date = post['post_time'].split(' ')[0]
                time_counts[date] = time_counts.get(date, 0) + 1
            
            print(f"\n=== 2024年时间分布 ===")
            for date, count in sorted(time_counts.items()):
                print(f"{date}: {count} 个帖子")
        
        print(f"\n=== 2024年前10个帖子 ===")
        for i, post in enumerate(posts[:10]):
            print(f"\n{i+1}. {post['title']}")
            print(f"   作者: {post['author'] or '未知'}")
            print(f"   时间: {post['post_time'] or '未知'}")
            print(f"   阅读: {post['read_count']}, 评论: {post['comment_count']}")


def main():
    """主函数"""
    stock_code = "zssh000300"
    
    print(f"开始爬取 {stock_code} 的东方财富论坛数据（专门筛选2024年数据）...")
    
    crawler = ZSSH0003002024Crawler()
    
    # 爬取数据，增加页数以获取更多历史数据
    posts = crawler.crawl_forum_posts(stock_code=stock_code, max_pages=20)
    
    if posts:
        # 保存数据
        filename = crawler.save_to_csv(posts)
        
        # 打印摘要
        crawler.print_summary(posts)
    else:
        print("没有获取到任何2024年的帖子数据")


if __name__ == "__main__":
    main()
