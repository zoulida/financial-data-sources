"""
搜狗搜索「最近一小时」结果数获取模块
免费，无key，通过前端接口获取数据
"""
import requests
import re
import time
from functools import lru_cache
from typing import Optional


class SogouSearchCounter:
    """搜狗搜索结果计数器"""
    
    def __init__(self, delay: float = 0.3):
        """
        初始化搜狗搜索计数器
        
        Args:
            delay: 请求间隔延迟（秒），避免触发反爬机制
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    @lru_cache(maxsize=100)
    def get_hour_count(self, keyword: str, cache_time: int = 300) -> int:
        """
        获取关键词最近一小时的搜索结果数
        
        Args:
            keyword: 搜索关键词
            cache_time: 缓存时间（秒），默认5分钟
            
        Returns:
            搜索结果数量，失败返回0
        """
        try:
            # 计算时间范围（秒级时间戳）
            ts_end = int(time.time())
            ts_start = ts_end - 3600  # 1小时前
            
            # 构建请求参数
            params = {
                'query': keyword,
                'type': '2',              # 2=新闻
                'tsn': '2',               # 2=按时间
                'inter_time': f'{ts_start},{ts_end}'
            }
            
            # 发送请求
            response = self.session.get(
                'https://news.sogou.com/news',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            # 解析结果
            html = response.text
            patterns = [
                r'共约.*?(\d[\d,]*)',
                r'约.*?(\d[\d,]*)',
                r'(\d[\d,]*)条结果',
                r'(\d[\d,]*)个结果'
            ]
            
            match = None
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    break
            
            if match:
                count_str = match.group(1).replace(',', '')
                return int(count_str)
            else:
                print(f"警告: 未找到搜狗搜索结果数量，关键词: {keyword}")
                return 0
                
        except requests.exceptions.RequestException as e:
            print(f"搜狗搜索请求失败: {e}")
            return 0
        except Exception as e:
            print(f"搜狗搜索解析失败: {e}")
            return 0
        finally:
            # 添加延迟避免触发反爬
            time.sleep(self.delay)
    
    def clear_cache(self):
        """清除缓存"""
        self.get_hour_count.cache_clear()


def sogou_hour_cnt(keyword: str) -> int:
    """
    便捷函数：获取搜狗最近一小时搜索结果数
    
    Args:
        keyword: 搜索关键词
        
    Returns:
        搜索结果数量
    """
    counter = SogouSearchCounter()
    return counter.get_hour_count(keyword)


if __name__ == "__main__":
    # 测试代码
    test_keywords = ["央行降准", "股市上涨", "经济数据"]
    
    print("=== 搜狗搜索测试 ===")
    for kw in test_keywords:
        count = sogou_hour_cnt(kw)
        print(f"关键词: {kw} -> 最近1小时结果数: {count}")
        time.sleep(1)  # 测试间隔
