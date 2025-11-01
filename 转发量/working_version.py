"""
工作版本 - 基于搜狗搜索的转发量监控
由于百度和微博的反爬机制，目前只有搜狗搜索能正常工作
"""
import requests
import re
import time
import random
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List


class WorkingRepostMonitor:
    """工作版转发量监控器（基于搜狗搜索）"""
    
    def __init__(self, delay: float = 1.0):
        """
        初始化监控器
        
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
        
        # 监控配置
        self.repost_threshold = 10  # 转载阈值
        self.weibo_threshold = 100  # 微博高热度阈值（暂时不可用）
    
    def get_random_delay(self) -> float:
        """获取随机延迟时间"""
        return self.delay + random.uniform(0, 0.5)
    
    def update_user_agent(self):
        """更新User-Agent"""
        self.session.headers['User-Agent'] = random.choice(self.user_agents)
    
    @lru_cache(maxsize=100)
    def get_sogou_count(self, keyword: str, cache_time: int = 300) -> int:
        """
        获取搜狗搜索结果数
        
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
            ts_start = ts_end - 3600  # 1小时前
            
            # 构建请求参数
            params = {
                'query': keyword,
                'type': '2',  # 2=新闻
                'tsn': '2',   # 2=按时间
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
    
    def get_comprehensive_stats(self, keyword: str) -> Dict:
        """
        获取综合统计数据（基于搜狗搜索）
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            包含统计数据的字典
        """
        print(f"正在获取关键词 '{keyword}' 的统计数据...")
        
        # 获取搜狗数据
        sogou_count = self.get_sogou_count(keyword)
        
        # 计算总转载量（目前只有搜狗）
        total_reposts = sogou_count
        
        # 判断是否达标
        repost_qualified = total_reposts >= self.repost_threshold
        
        stats = {
            'keyword': keyword,
            'timestamp': datetime.now().isoformat(),
            'sogou_count': sogou_count,
            'total_reposts': total_reposts,
            'repost_qualified': repost_qualified,
            'threshold': self.repost_threshold,
            'note': '基于搜狗搜索，百度和微博暂时不可用'
        }
        
        return stats
    
    def check_repost_threshold(self, keyword: str) -> bool:
        """
        检查是否达到转载阈值
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            是否达标
        """
        stats = self.get_comprehensive_stats(keyword)
        return stats['repost_qualified']
    
    def batch_monitor(self, keywords: List[str]) -> List[Dict]:
        """
        批量监控多个关键词
        
        Args:
            keywords: 关键词列表
            
        Returns:
            所有关键词的统计数据列表
        """
        results = []
        
        print(f"开始批量监控 {len(keywords)} 个关键词...")
        
        for i, keyword in enumerate(keywords, 1):
            print(f"\n[{i}/{len(keywords)}] 处理关键词: {keyword}")
            
            try:
                stats = self.get_comprehensive_stats(keyword)
                results.append(stats)
                
                # 打印简要结果
                print(f"  搜狗结果: {stats['sogou_count']}")
                print(f"  总转载: {stats['total_reposts']}")
                print(f"  转载达标: {stats['repost_qualified']}")
                
            except Exception as e:
                print(f"  错误: {e}")
                results.append({
                    'keyword': keyword,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            
            # 添加间隔避免请求过于频繁
            if i < len(keywords):
                time.sleep(2)
        
        return results
    
    def get_qualified_keywords(self, keywords: List[str]) -> List[str]:
        """
        获取达标的关键词列表
        
        Args:
            keywords: 关键词列表
            
        Returns:
            达标的关键词列表
        """
        results = self.batch_monitor(keywords)
        qualified = [r['keyword'] for r in results if r.get('repost_qualified', False)]
        return qualified
    
    def print_summary(self, results: List[Dict]):
        """
        打印监控结果摘要
        
        Args:
            results: 监控结果列表
        """
        print("\n" + "="*60)
        print("转发量监控结果摘要（基于搜狗搜索）")
        print("="*60)
        
        total_keywords = len(results)
        qualified_count = sum(1 for r in results if r.get('repost_qualified', False))
        error_count = sum(1 for r in results if 'error' in r)
        
        print(f"总关键词数: {total_keywords}")
        print(f"转载达标数: {qualified_count}")
        print(f"错误数量: {error_count}")
        print(f"达标率: {qualified_count/total_keywords*100:.1f}%")
        print(f"转载阈值: {self.repost_threshold}")
        
        print("\n达标关键词:")
        for r in results:
            if r.get('repost_qualified', False):
                print(f"  ✓ {r['keyword']} (搜狗: {r['sogou_count']})")
        
        if error_count > 0:
            print("\n错误关键词:")
            for r in results:
                if 'error' in r:
                    print(f"  ✗ {r['keyword']}: {r['error']}")
    
    def clear_cache(self):
        """清除缓存"""
        self.get_sogou_count.cache_clear()


def quick_check(keyword: str) -> bool:
    """
    快速检查单个关键词是否达标
    
    Args:
        keyword: 搜索关键词
        
    Returns:
        是否达标
    """
    monitor = WorkingRepostMonitor()
    return monitor.check_repost_threshold(keyword)


def batch_check(keywords: List[str]) -> List[Dict]:
    """
    批量检查多个关键词
    
    Args:
        keywords: 关键词列表
        
    Returns:
        检查结果列表
    """
    monitor = WorkingRepostMonitor()
    results = monitor.batch_monitor(keywords)
    monitor.print_summary(results)
    return results


def main():
    """主函数"""
    print("工作版转发量监控（基于搜狗搜索）")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("注意：由于反爬机制，目前只有搜狗搜索可用")
    
    # 测试关键词
    test_keywords = [
        "央行降准", "股市上涨", "经济数据", 
        "货币政策", "通胀数据", "GDP增长",
        "美联储", "加息", "降息", "量化宽松"
    ]
    
    print(f"\n测试关键词: {test_keywords}")
    
    # 批量检查
    results = batch_check(test_keywords)
    
    # 获取达标关键词
    monitor = WorkingRepostMonitor()
    qualified = monitor.get_qualified_keywords(test_keywords)
    print(f"\n达标关键词: {qualified}")
    
    # 单个关键词测试
    print(f"\n单个关键词测试:")
    for kw in ["央行降准", "股市上涨"]:
        qualified = quick_check(kw)
        print(f"  {kw}: {'达标' if qualified else '未达标'}")


if __name__ == "__main__":
    main()
