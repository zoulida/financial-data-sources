"""
微博「最近30分钟转发+评论」统计模块
免登录，通过手机端接口获取数据
"""
import requests
import time
from functools import lru_cache
from typing import Dict, Optional


class WeiboStatsCounter:
    """微博统计数据计数器"""
    
    def __init__(self, delay: float = 0.5):
        """
        初始化微博统计计数器
        
        Args:
            delay: 请求间隔延迟（秒），避免触发反爬机制
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        })
    
    @lru_cache(maxsize=100)
    def get_30min_stats(self, keyword: str, cache_time: int = 300) -> Dict[str, int]:
        """
        获取关键词最近30分钟的转发和评论统计
        
        Args:
            keyword: 搜索关键词
            cache_time: 缓存时间（秒），默认5分钟
            
        Returns:
            包含reposts和comments的字典
        """
        try:
            # 构建请求参数
            params = {
                'containerid': f'100103type=1&q={requests.utils.quote(keyword)}',
                'page_type': 'searchall'
            }
            
            # 发送请求
            response = self.session.get(
                'https://m.weibo.cn/api/container/getIndex',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            # 解析JSON响应
            data = response.json()
            cards = data.get('data', {}).get('cards', [])
            
            reposts = 0
            comments = 0
            
            # 遍历所有卡片，统计转发和评论数
            for card in cards:
                mblog = card.get('mblog')
                if not mblog:
                    continue
                
                # 累加转发数和评论数
                reposts += mblog.get('reposts_count', 0)
                comments += mblog.get('comments_count', 0)
            
            return {
                'reposts': reposts,
                'comments': comments,
                'total': reposts + comments
            }
                
        except requests.exceptions.RequestException as e:
            print(f"微博统计请求失败: {e}")
            return {'reposts': 0, 'comments': 0, 'total': 0}
        except Exception as e:
            print(f"微博统计解析失败: {e}")
            return {'reposts': 0, 'comments': 0, 'total': 0}
        finally:
            # 添加延迟避免触发反爬
            time.sleep(self.delay)
    
    def clear_cache(self):
        """清除缓存"""
        self.get_30min_stats.cache_clear()


def weibo_30min_stat(keyword: str) -> Dict[str, int]:
    """
    便捷函数：获取微博最近30分钟转发评论统计
    
    Args:
        keyword: 搜索关键词
        
    Returns:
        包含reposts、comments和total的字典
    """
    counter = WeiboStatsCounter()
    return counter.get_30min_stats(keyword)


def is_high_heat(keyword: str, threshold: int = 100) -> bool:
    """
    判断关键词是否为高热度（基于微博互动量）
    
    Args:
        keyword: 搜索关键词
        threshold: 热度阈值，默认100
        
    Returns:
        是否为高热度
    """
    stats = weibo_30min_stat(keyword)
    return stats['total'] > threshold


if __name__ == "__main__":
    # 测试代码
    test_keywords = ["央行降准", "股市上涨", "经济数据"]
    
    print("=== 微博统计测试 ===")
    for kw in test_keywords:
        stats = weibo_30min_stat(kw)
        print(f"关键词: {kw}")
        print(f"  转发数: {stats['reposts']}")
        print(f"  评论数: {stats['comments']}")
        print(f"  总互动: {stats['total']}")
        print(f"  是否高热度: {is_high_heat(kw)}")
        print("-" * 30)
        time.sleep(2)  # 测试间隔
