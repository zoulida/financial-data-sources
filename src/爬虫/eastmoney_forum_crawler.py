#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富论坛爬虫 - 爬取指定股票的论坛留言内容
目标URL: https://guba.eastmoney.com/list,601669.html
"""

import requests
import pandas as pd
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
import json
import re
import urllib.parse


class EastmoneyForumCrawler:
    def __init__(self):
        self.base_url = "https://guba.eastmoney.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_forum_posts(self, stock_code, page=1, max_pages=10):
        """
        获取论坛帖子列表 - 使用API接口
        
        Args:
            stock_code: 股票代码，如 '601669'
            page: 起始页码
            max_pages: 最大爬取页数
        
        Returns:
            list: 帖子信息列表
        """
        posts = []
        
        for current_page in range(page, page + max_pages):
            try:
                # 构建API请求URL
                api_url = f"https://guba.eastmoney.com/interface/api/GetList.aspx"
                params = {
                    'id': stock_code,
                    'type': '0',
                    'page': current_page,
                    'pageSize': 80,
                    'sort': '1',
                    'sortType': '1'
                }
                
                response = self.session.get(api_url, params=params, timeout=10)
                response.encoding = 'utf-8'
                
                if response.status_code != 200:
                    print(f"请求失败，状态码: {response.status_code}")
                    break
                
                # 解析JSON响应
                try:
                    data = response.json()
                    if data.get('errcode') != 0:
                        print(f"API返回错误: {data.get('errmsg', '未知错误')}")
                        break
                    
                    post_data = data.get('data', {}).get('list', [])
                    
                    if not post_data:
                        print(f"第 {current_page} 页没有找到帖子，停止爬取")
                        break
                    
                    for item in post_data:
                        post_info = self.extract_post_info_from_api(item, stock_code)
                        if post_info:
                            posts.append(post_info)
                    
                    print(f"已爬取第 {current_page} 页，共 {len(post_data)} 个帖子")
                    
                except json.JSONDecodeError as e:
                    print(f"解析JSON数据出错: {e}")
                    # 如果API失败，尝试解析HTML
                    posts.extend(self._fallback_html_crawl(stock_code, current_page))
                
                # 随机延时，避免被封
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"爬取第 {current_page} 页时出错: {e}")
                continue
        
        return posts
    
    def _fallback_html_crawl(self, stock_code, page):
        """备用HTML解析方法"""
        posts = []
        try:
            url = f"https://guba.eastmoney.com/list,{stock_code}_{page}.html"
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 尝试多种可能的选择器
                selectors = [
                    'div.articleh',
                    'div[class*="articleh"]',
                    'tr[class*="articleh"]',
                    'div.post-item',
                    'div[class*="post"]'
                ]
                
                post_items = []
                for selector in selectors:
                    post_items = soup.select(selector)
                    if post_items:
                        break
                
                for item in post_items:
                    post_info = self.extract_post_info_from_html(item, stock_code)
                    if post_info:
                        posts.append(post_info)
                        
        except Exception as e:
            print(f"备用HTML解析出错: {e}")
        
        return posts
    
    def extract_post_info_from_api(self, item, stock_code):
        """从API数据提取帖子信息"""
        try:
            post_info = {
                'stock_code': stock_code,
                'title': item.get('title', '').strip(),
                'post_link': item.get('url', ''),
                'author': item.get('name', '').strip(),
                'post_time': item.get('time', '').strip(),
                'last_reply_time': item.get('lastreply', '').strip(),
                'read_count': str(item.get('read', 0)),
                'comment_count': str(item.get('reply', 0)),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return post_info
            
        except Exception as e:
            print(f"提取API帖子信息时出错: {e}")
            return None
    
    def extract_post_info_from_html(self, item, stock_code):
        """从HTML元素提取帖子信息"""
        try:
            # 尝试多种可能的标签结构
            title_elem = (item.find('span', class_='l3') or 
                         item.find('a', class_='title') or
                         item.find('td', class_='title') or
                         item.find('a'))
            
            if not title_elem:
                return None
                
            title = title_elem.get_text(strip=True)
            if not title:
                return None
                
            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
            post_link = link_elem.get('href', '') if link_elem else ''
            
            # 尝试多种可能的作者选择器
            author_selectors = ['span.l4', 'td.author', 'span.author', '.user-name']
            author = ''
            for selector in author_selectors:
                author_elem = item.select_one(selector)
                if author_elem:
                    author = author_elem.get_text(strip=True)
                    break
            
            # 尝试多种可能的时间选择器
            time_selectors = ['span.l5', 'td.time', 'span.time', '.post-time']
            post_time = ''
            for selector in time_selectors:
                time_elem = item.select_one(selector)
                if time_elem:
                    post_time = time_elem.get_text(strip=True)
                    break
            
            # 尝试多种可能的阅读数选择器
            read_selectors = ['span.l6', 'td.read', 'span.read', '.read-count']
            read_count = '0'
            for selector in read_selectors:
                read_elem = item.select_one(selector)
                if read_elem:
                    read_count = read_elem.get_text(strip=True)
                    break
            
            # 尝试多种可能的评论数选择器
            comment_selectors = ['span.l7', 'td.reply', 'span.reply', '.comment-count']
            comment_count = '0'
            for selector in comment_selectors:
                comment_elem = item.select_one(selector)
                if comment_elem:
                    comment_count = comment_elem.get_text(strip=True)
                    break
            
            post_info = {
                'stock_code': stock_code,
                'title': title,
                'post_link': post_link,
                'author': author,
                'post_time': post_time,
                'last_reply_time': '',  # HTML中可能没有
                'read_count': read_count,
                'comment_count': comment_count,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return post_info
            
        except Exception as e:
            print(f"提取HTML帖子信息时出错: {e}")
            return None
    
    def get_post_details(self, post_link):
        """获取帖子详细内容"""
        if not post_link.startswith('http'):
            post_link = self.base_url + post_link
        
        try:
            response = self.session.get(post_link, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"获取帖子详情失败，状态码: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取帖子内容
            content_elem = soup.find('div', class_='stockcodec .l2')
            content = content_elem.get_text(strip=True) if content_elem else ''
            
            # 提取评论
            comments = self.extract_comments(soup)
            
            return {
                'content': content,
                'comments': comments
            }
            
        except Exception as e:
            print(f"获取帖子详情时出错: {e}")
            return None
    
    def extract_comments(self, soup):
        """提取评论内容"""
        comments = []
        
        try:
            comment_items = soup.find_all('div', class_='articleh')
            
            for item in comment_items:
                try:
                    comment_author = item.find('span', class_='l4')
                    comment_time = item.find('span', class_='l5')
                    comment_content = item.find('div', class_='l2')
                    
                    comment_info = {
                        'author': comment_author.get_text(strip=True) if comment_author else '',
                        'time': comment_time.get_text(strip=True) if comment_time else '',
                        'content': comment_content.get_text(strip=True) if comment_content else ''
                    }
                    
                    if comment_info['content']:
                        comments.append(comment_info)
                        
                except Exception as e:
                    print(f"解析评论时出错: {e}")
                    continue
                    
        except Exception as e:
            print(f"提取评论时出错: {e}")
        
        return comments
    
    def save_to_csv(self, posts, filename=None):
        """保存数据到CSV文件"""
        if not filename:
            filename = f"eastmoney_forum_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        df = pd.DataFrame(posts)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"数据已保存到: {filename}")
        return filename
    
    def crawl_forum(self, stock_code, max_pages=10, save_csv=True, get_details=False):
        """
        爬取论坛数据的主函数
        
        Args:
            stock_code: 股票代码
            max_pages: 最大爬取页数
            save_csv: 是否保存到CSV
            get_details: 是否获取帖子详情
        
        Returns:
            list: 帖子数据
        """
        print(f"开始爬取 {stock_code} 的论坛数据...")
        
        posts = self.get_forum_posts(stock_code, page=1, max_pages=max_pages)
        
        if get_details:
            print("开始获取帖子详情...")
            for i, post in enumerate(posts):
                if post.get('post_link'):
                    details = self.get_post_details(post['post_link'])
                    if details:
                        post['content'] = details.get('content', '')
                        post['comments'] = json.dumps(details.get('comments', []), ensure_ascii=False)
                
                if (i + 1) % 10 == 0:
                    print(f"已处理 {i + 1}/{len(posts)} 个帖子详情")
                    time.sleep(random.uniform(2, 5))
        
        if save_csv:
            self.save_to_csv(posts)
        
        print(f"爬取完成，共获取 {len(posts)} 个帖子")
        return posts


def main():
    """主函数"""
    # 默认爬取601669的论坛数据
    stock_code = "601669"
    
    crawler = EastmoneyForumCrawler()
    
    # 爬取论坛数据
    posts = crawler.crawl_forum(
        stock_code=stock_code,
        max_pages=5,  # 爬取前5页
        save_csv=True,
        get_details=False  # 暂时不获取详情，加快速度
    )
    
    # 打印前几条数据
    if posts:
        print("\n前5条帖子信息:")
        for i, post in enumerate(posts[:5]):
            print(f"\n{i+1}. {post['title']}")
            print(f"   作者: {post['author']}")
            print(f"   时间: {post['post_time']}")
            print(f"   阅读: {post['read_count']}, 评论: {post['comment_count']}")


if __name__ == "__main__":
    main()
