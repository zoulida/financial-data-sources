"""
改进版搜索模块
处理反爬机制和验证问题
"""
import requests
import re
import time
import random
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional, Dict


class ImprovedSearchCounter:
    """改进版搜索计数器"""
    
    def __init__(self, delay: float = 1.0):
        """
        初始化搜索计数器
        
        Args:
            delay: 请求间隔延迟（秒）
        """
        self.delay = delay
        self.session = requests.Session()
        
        # 随机User-Agent列表
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        # 设置随机User-Agent
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_random_delay(self) -> float:
        """获取随机延迟时间"""
        return self.delay + random.uniform(0, 0.5)
    
    def update_user_agent(self):
        """更新User-Agent"""
        self.session.headers['User-Agent'] = random.choice(self.user_agents)
    
    @lru_cache(maxsize=100)
    def get_baidu_count(self, keyword: str, cache_time: int = 300) -> int:
        """
        获取百度搜索结果数（改进版）
        
        Args:
            keyword: 搜索关键词
            cache_time: 缓存时间（秒）
            
        Returns:
            搜索结果数量，失败返回0
        """
        try:
            # 更新User-Agent
            self.update_user_agent()
            
            # 计算时间范围
            t_end = datetime.now()
            t_start = t_end - timedelta(hours=1)
            
            # 构建请求参数
            params = {
                'tn': 'news',
                'rtt': '1',
                'bsst': '1',
                'bt': t_start.strftime('%Y%m%d%H%M'),
                'et': t_end.strftime('%Y%m%d%H%M'),
                'word': keyword
            }
            
            # 添加随机延迟
            time.sleep(self.get_random_delay())
            
            # 发送请求
            response = self.session.get(
                'https://news.baidu.com/ns',
                params=params,
                timeout=15
            )
            
            # 检查是否被重定向到验证页面
            if '安全验证' in response.text or '验证码' in response.text:
                print(f"百度搜索被安全验证拦截: {keyword}")
                return 0
            
            # 解析结果
            html = response.text
            patterns = [
                r'找到相关新闻约.*?(\d[\d,]*)',
                r'共找到.*?(\d[\d,]*)',
                r'约.*?(\d[\d,]*)',
                r'(\d[\d,]*)条相关新闻',
                r'(\d[\d,]*)个结果'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    count_str = match.group(1).replace(',', '')
                    return int(count_str)
            
            print(f"百度搜索未找到结果数量: {keyword}")
            return 0
                
        except Exception as e:
            print(f"百度搜索失败: {e}")
            return 0
    
    @lru_cache(maxsize=100)
    def get_sogou_count(self, keyword: str, cache_time: int = 300) -> int:
        """
        获取搜狗搜索结果数（改进版）
        
        Args:
            keyword: 搜索关键词
            cache_time: 缓存时间（秒）
            
        Returns:
            搜索结果数量，失败返回0
        """
        try:
            # 更新User-Agent
            self.update_user_agent()
            
            # 计算时间范围
            ts_end = int(time.time())
            ts_start = ts_end - 3600
            
            # 构建请求参数
            params = {
                'query': keyword,
                'type': '2',
                'tsn': '2',
                'inter_time': f'{ts_start},{ts_end}'
            }
            
            # 添加随机延迟
            time.sleep(self.get_random_delay())
            
            # 发送请求
            response = self.session.get(
                'https://news.sogou.com/news',
                params=params,
                timeout=15
            )
            
            # 解析结果
            html = response.text
            patterns = [
                r'共约.*?(\d[\d,]*)',
                r'约.*?(\d[\d,]*)',
                r'(\d[\d,]*)条结果',
                r'(\d[\d,]*)个结果'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    count_str = match.group(1).replace(',', '')
                    return int(count_str)
            
            print(f"搜狗搜索未找到结果数量: {keyword}")
            return 0
                
        except Exception as e:
            print(f"搜狗搜索失败: {e}")
            return 0
    
    @lru_cache(maxsize=100)
    def get_weibo_stats(self, keyword: str, cache_time: int = 300) -> Dict[str, int]:
        """
        获取微博统计数据（改进版）
        
        Args:
            keyword: 搜索关键词
            cache_time: 缓存时间（秒）
            
        Returns:
            包含reposts和comments的字典
        """
        try:
            # 更新User-Agent为移动端
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://m.weibo.cn/',
            })
            
            # 构建请求参数
            params = {
                'containerid': f'100103type=1&q={requests.utils.quote(keyword)}',
                'page_type': 'searchall'
            }
            
            # 添加随机延迟
            time.sleep(self.get_random_delay())
            
            # 发送请求
            response = self.session.get(
                'https://m.weibo.cn/api/container/getIndex',
                params=params,
                timeout=15
            )
            
            # 检查是否被重定向到访客系统
            if 'Sina Visitor System' in response.text or 'visitor' in response.text.lower():
                print(f"微博统计被访客系统拦截: {keyword}")
                return {'reposts': 0, 'comments': 0, 'total': 0}
            
            # 解析JSON响应
            try:
                data = response.json()
            except:
                print(f"微博统计JSON解析失败: {keyword}")
                return {'reposts': 0, 'comments': 0, 'total': 0}
            
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
                
        except Exception as e:
            print(f"微博统计失败: {e}")
            return {'reposts': 0, 'comments': 0, 'total': 0}
    
    def get_comprehensive_stats(self, keyword: str) -> Dict:
        """
        获取综合统计数据
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            包含所有平台统计数据的字典
        """
        print(f"正在获取关键词 '{keyword}' 的综合统计数据...")
        
        # 获取各平台数据
        baidu_count = self.get_baidu_count(keyword)
        sogou_count = self.get_sogou_count(keyword)
        weibo_stats = self.get_weibo_stats(keyword)
        
        # 计算总转载量（百度+搜狗）
        total_reposts = baidu_count + sogou_count
        
        # 计算综合热度（转载量+微博互动量）
        total_engagement = total_reposts + weibo_stats['total']
        
        # 判断是否达标
        repost_qualified = total_reposts >= 10
        weibo_high_heat = weibo_stats['total'] > 100
        overall_qualified = total_engagement >= 10
        
        stats = {
            'keyword': keyword,
            'timestamp': datetime.now().isoformat(),
            'baidu_count': baidu_count,
            'sogou_count': sogou_count,
            'total_reposts': total_reposts,
            'weibo_stats': weibo_stats,
            'total_engagement': total_engagement,
            'repost_qualified': repost_qualified,
            'weibo_high_heat': weibo_high_heat,
            'overall_qualified': overall_qualified,
            'thresholds': {
                'repost_threshold': 10,
                'weibo_threshold': 100
            }
        }
        
        return stats
    
    def clear_cache(self):
        """清除缓存"""
        self.get_baidu_count.cache_clear()
        self.get_sogou_count.cache_clear()
        self.get_weibo_stats.cache_clear()


def test_improved_search():
    """测试改进版搜索"""
    print("="*60)
    print("测试改进版搜索功能")
    print("="*60)
    
    counter = ImprovedSearchCounter(delay=1.0)
    
    test_keywords = ["央行降准", "股市上涨", "经济数据"]
    
    for keyword in test_keywords:
        print(f"\n测试关键词: {keyword}")
        
        # 测试各平台
        print("  百度搜索...")
        baidu_count = counter.get_baidu_count(keyword)
        print(f"    结果数: {baidu_count}")
        
        print("  搜狗搜索...")
        sogou_count = counter.get_sogou_count(keyword)
        print(f"    结果数: {sogou_count}")
        
        print("  微博统计...")
        weibo_stats = counter.get_weibo_stats(keyword)
        print(f"    转发: {weibo_stats['reposts']}, 评论: {weibo_stats['comments']}, 总计: {weibo_stats['total']}")
        
        # 综合统计
        print("  综合统计...")
        stats = counter.get_comprehensive_stats(keyword)
        print(f"    总转载: {stats['total_reposts']}")
        print(f"    总互动: {stats['total_engagement']}")
        print(f"    转载达标: {stats['repost_qualified']}")
        print(f"    综合达标: {stats['overall_qualified']}")
        
        print("-" * 40)


if __name__ == "__main__":
    test_improved_search()
