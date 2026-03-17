#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版东方财富论坛爬虫 - 直接解析当前页面结构
"""

import requests
import pandas as pd
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup


def crawl_eastmoney_forum(stock_code="601669", max_pages=3):
    """
    爬取东方财富论坛数据
    
    Args:
        stock_code: 股票代码
        max_pages: 最大爬取页数
    
    Returns:
        list: 帖子数据
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    all_posts = []
    
    for page in range(1, max_pages + 1):
        url = f"https://guba.eastmoney.com/list,{stock_code}_{page}.html"
        
        try:
            print(f"正在爬取第 {page} 页: {url}")
            
            response = session.get(url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有包含帖子信息的链接
            # 从页面分析可知，帖子链接格式为: https://guba.eastmoney.com/news,601669,数字.html
            post_links = soup.find_all('a', href=re.compile(r'guba\.eastmoney\.com/news,' + stock_code + r',\d+\.html'))
            
            if not post_links:
                print(f"第 {page} 页没有找到帖子链接")
                # 尝试其他可能的链接格式
                post_links = soup.find_all('a', href=re.compile(r'news,' + stock_code + r',\d+\.html'))
            
            print(f"找到 {len(post_links)} 个帖子链接")
            
            for link in post_links:
                try:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if not title or not href:
                        continue
                    
                    # 查找该链接的父元素，获取更多信息
                    parent = link.find_parent(['div', 'td', 'tr', 'span'])
                    author = ''
                    post_time = ''
                    read_count = '0'
                    comment_count = '0'
                    
                    if parent:
                        # 在父元素及其兄弟元素中查找作者、时间等信息
                        parent_text = parent.get_text()
                        
                        # 尝试提取作者信息（通常在链接附近）
                        author_match = re.search(r'([a-zA-Z0-9\u4e00-\u9fa5]{2,10})', parent_text)
                        if author_match and author_match.group(1) not in title:
                            author = author_match.group(1)
                        
                        # 尝试提取时间信息
                        time_match = re.search(r'(\d{2}-\d{2}\s+\d{2}:\d{2}|\d{4}-\d{2}-\d{2}|\d{2}:\d{2})', parent_text)
                        if time_match:
                            post_time = time_match.group(1)
                        
                        # 尝试提取数字（可能是阅读数或评论数）
                        numbers = re.findall(r'(\d+)', parent_text)
                        if len(numbers) >= 2:
                            read_count = numbers[0]
                            comment_count = numbers[1]
                        elif len(numbers) == 1:
                            read_count = numbers[0]
                    
                    post_info = {
                        'stock_code': stock_code,
                        'title': title,
                        'post_link': href,
                        'author': author,
                        'post_time': post_time,
                        'read_count': read_count,
                        'comment_count': comment_count,
                        'page': page,
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    all_posts.append(post_info)
                    
                except Exception as e:
                    print(f"处理帖子链接时出错: {e}")
                    continue
            
            # 随机延时
            time.sleep(2)
            
        except Exception as e:
            print(f"爬取第 {page} 页时出错: {e}")
            continue
    
    return all_posts


def save_to_csv(posts, filename=None):
    """保存数据到CSV文件"""
    if not filename:
        filename = f"eastmoney_forum_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    df = pd.DataFrame(posts)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"数据已保存到: {filename}")
    return filename


def main():
    """主函数"""
    stock_code = "601669"
    
    print(f"开始爬取 {stock_code} 的论坛数据...")
    
    posts = crawl_eastmoney_forum(stock_code=stock_code, max_pages=2)
    
    if posts:
        # 去重（基于标题和链接）
        unique_posts = []
        seen = set()
        
        for post in posts:
            key = (post['title'], post['post_link'])
            if key not in seen:
                seen.add(key)
                unique_posts.append(post)
        
        print(f"去重后共 {len(unique_posts)} 个帖子")
        
        # 保存数据
        save_to_csv(unique_posts)
        
        # 显示前几个帖子
        print("\n前10个帖子:")
        for i, post in enumerate(unique_posts[:10]):
            print(f"\n{i+1}. {post['title']}")
            print(f"   作者: {post['author']}")
            print(f"   时间: {post['post_time']}")
            print(f"   阅读: {post['read_count']}, 评论: {post['comment_count']}")
            print(f"   链接: {post['post_link']}")
    else:
        print("没有获取到任何帖子数据")


if __name__ == "__main__":
    main()
