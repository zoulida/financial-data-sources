#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间提取测试脚本 - 专门测试时间提取功能
"""

import requests
import re
from bs4 import BeautifulSoup


def test_time_extraction():
    """测试时间提取功能"""
    url = "https://guba.eastmoney.com/list,601669_1.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"请求失败，状态码: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有帖子链接
        post_links = soup.find_all('a', href=re.compile(r'/news,601669,\d+\.html'))
        
        print(f"找到 {len(post_links)} 个帖子链接")
        
        for i, link in enumerate(post_links[:10]):  # 只测试前10个
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            print(f"\n=== 帖子 {i+1} ===")
            print(f"标题: {title}")
            print(f"链接: {href}")
            
            # 查找父元素
            parent = link.find_parent(['div', 'td', 'tr', 'span', 'li'])
            
            if parent:
                parent_text = parent.get_text()
                print(f"父元素文本: {parent_text[:200]}...")
                
                # 测试时间提取
                time_patterns = [
                    r'(\d{2}-\d{2}\s+\d{2}:\d{2})',  # 03-15 09:41
                    r'(\d{2}-\d{2}\s+\d{1,2}:\d{2})',  # 03-15 9:41
                    r'(\d{2}:\d{2})',  # 09:41
                    r'(\d{2}-\d{2})',  # 03-15
                ]
                
                found_times = []
                for pattern in time_patterns:
                    matches = re.findall(pattern, parent_text)
                    if matches:
                        found_times.extend(matches)
                
                print(f"找到的时间: {found_times}")
                
                # 测试作者提取
                author_patterns = [
                    r'股友([a-zA-Z0-9\u4e00-\u9fa5]{2,15})',
                    r'([a-zA-Z0-9\u4e00-\u9fa5]{2,10})(?=\s*\d{2}-\d{2})',
                ]
                
                found_authors = []
                for pattern in author_patterns:
                    matches = re.findall(pattern, parent_text)
                    if matches:
                        found_authors.extend(matches)
                
                print(f"找到的作者: {found_authors}")
                
                # 测试数字提取
                numbers = re.findall(r'(\d+)', parent_text)
                print(f"找到的数字: {numbers[:10]}")  # 只显示前10个数字
                
            else:
                print("未找到父元素")
            
            print("-" * 50)
    
    except Exception as e:
        print(f"测试时出错: {e}")


if __name__ == "__main__":
    test_time_extraction()
