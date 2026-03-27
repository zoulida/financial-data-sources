# -*- coding: utf-8 -*-
"""
调试RSS解析问题
"""

import feedparser
import requests
from datetime import datetime

def debug_rss():
    """调试RSS解析"""
    print("=" * 60)
    print("RSS解析调试")
    print("=" * 60)
    
    # 测试URL列表
    urls = [
        "https://rss.sina.com.cn/finance/stock/sinastock.xml",
        "https://rss.sina.com.cn/finance/china/finance.xml",
        "https://rss.sina.com.cn/finance/china/macro.xml",
        "https://rss.sina.com.cn/finance/company/company.xml",
        "https://rss.sina.com.cn/finance/market/market.xml",
    ]
    
    for i, url in enumerate(urls, 1):
        print(f"\n{i}. 测试URL: {url}")
        
        try:
            # 先测试HTTP请求
            print("  测试HTTP请求...")
            response = requests.get(url, timeout=10)
            print(f"  状态码: {response.status_code}")
            print(f"  内容类型: {response.headers.get('content-type', 'N/A')}")
            print(f"  内容长度: {len(response.content)}")
            
            if response.status_code == 200:
                # 测试RSS解析
                print("  测试RSS解析...")
                feed = feedparser.parse(url)
                
                print(f"  RSS状态: {'成功' if not feed.bozo else '有警告'}")
                if feed.bozo:
                    print(f"  警告信息: {feed.bozo_exception}")
                
                print(f"  标题: {feed.feed.get('title', 'N/A')}")
                print(f"  描述: {feed.feed.get('description', 'N/A')}")
                print(f"  条目数: {len(feed.entries)}")
                
                if feed.entries:
                    print("  前3条条目:")
                    for j, entry in enumerate(feed.entries[:3], 1):
                        print(f"    {j}. {entry.get('title', 'N/A')}")
                        print(f"       时间: {entry.get('published', 'N/A')}")
                        print(f"       链接: {entry.get('link', 'N/A')}")
                else:
                    print("  无条目数据")
            else:
                print(f"  HTTP请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"  错误: {e}")
    
    # 测试其他RSS源
    print("\n" + "=" * 60)
    print("测试其他RSS源")
    print("=" * 60)
    
    other_urls = [
        "https://rss.sina.com.cn/news/china/focus15.xml",  # 新浪新闻焦点
        "https://rss.sina.com.cn/news/china/focus15.xml",  # 新浪新闻焦点
        "http://rss.sina.com.cn/news/china/focus15.xml",   # HTTP版本
    ]
    
    for i, url in enumerate(other_urls, 1):
        print(f"\n{i}. 测试其他RSS: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                feed = feedparser.parse(url)
                print(f"  RSS状态: {'成功' if not feed.bozo else '有警告'}")
                print(f"  条目数: {len(feed.entries)}")
                
                if feed.entries:
                    print("  前2条条目:")
                    for j, entry in enumerate(feed.entries[:2], 1):
                        print(f"    {j}. {entry.get('title', 'N/A')}")
            else:
                print(f"  HTTP请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"  错误: {e}")

if __name__ == "__main__":
    debug_rss()
