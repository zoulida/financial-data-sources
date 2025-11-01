"""
转发量监控主模块
整合百度、搜狗、微博三大平台，实现「30分钟转载≥10次」的硬指标判断
"""
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .baidu_search import BaiduSearchCounter
from .sogou_search import SogouSearchCounter
from .weibo_stats import WeiboStatsCounter


class RepostMonitor:
    """转发量监控器"""
    
    def __init__(self, 
                 baidu_delay: float = 0.3,
                 sogou_delay: float = 0.3, 
                 weibo_delay: float = 0.5):
        """
        初始化转发量监控器
        
        Args:
            baidu_delay: 百度请求延迟（秒）
            sogou_delay: 搜狗请求延迟（秒）
            weibo_delay: 微博请求延迟（秒）
        """
        self.baidu_counter = BaiduSearchCounter(delay=baidu_delay)
        self.sogou_counter = SogouSearchCounter(delay=sogou_delay)
        self.weibo_counter = WeiboStatsCounter(delay=weibo_delay)
        
        # 监控配置
        self.repost_threshold = 10  # 转载阈值
        self.weibo_threshold = 100  # 微博高热度阈值
        
    def get_comprehensive_stats(self, keyword: str) -> Dict:
        """
        获取关键词的综合统计数据
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            包含所有平台统计数据的字典
        """
        print(f"正在获取关键词 '{keyword}' 的综合统计数据...")
        
        # 获取各平台数据
        baidu_count = self.baidu_counter.get_hour_count(keyword)
        sogou_count = self.sogou_counter.get_hour_count(keyword)
        weibo_stats = self.weibo_counter.get_30min_stats(keyword)
        
        # 计算总转载量（百度+搜狗）
        total_reposts = baidu_count + sogou_count
        
        # 计算综合热度（转载量+微博互动量）
        total_engagement = total_reposts + weibo_stats['total']
        
        # 判断是否达标
        repost_qualified = total_reposts >= self.repost_threshold
        weibo_high_heat = weibo_stats['total'] > self.weibo_threshold
        overall_qualified = total_engagement >= self.repost_threshold
        
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
                'repost_threshold': self.repost_threshold,
                'weibo_threshold': self.weibo_threshold
            }
        }
        
        return stats
    
    def check_repost_threshold(self, keyword: str) -> bool:
        """
        检查是否达到「30分钟转载≥10次」的硬指标
        
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
                print(f"  百度: {stats['baidu_count']}, 搜狗: {stats['sogou_count']}")
                print(f"  总转载: {stats['total_reposts']}, 微博互动: {stats['weibo_stats']['total']}")
                print(f"  转载达标: {stats['repost_qualified']}, 综合达标: {stats['overall_qualified']}")
                
            except Exception as e:
                print(f"  错误: {e}")
                results.append({
                    'keyword': keyword,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            
            # 添加间隔避免请求过于频繁
            if i < len(keywords):
                time.sleep(1)
        
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
        print("转发量监控结果摘要")
        print("="*60)
        
        total_keywords = len(results)
        qualified_count = sum(1 for r in results if r.get('repost_qualified', False))
        error_count = sum(1 for r in results if 'error' in r)
        
        print(f"总关键词数: {total_keywords}")
        print(f"转载达标数: {qualified_count}")
        print(f"错误数量: {error_count}")
        print(f"达标率: {qualified_count/total_keywords*100:.1f}%")
        
        print("\n达标关键词:")
        for r in results:
            if r.get('repost_qualified', False):
                print(f"  ✓ {r['keyword']} (转载: {r['total_reposts']}, 微博: {r['weibo_stats']['total']})")
        
        if error_count > 0:
            print("\n错误关键词:")
            for r in results:
                if 'error' in r:
                    print(f"  ✗ {r['keyword']}: {r['error']}")
    
    def clear_all_caches(self):
        """清除所有缓存"""
        self.baidu_counter.clear_cache()
        self.sogou_counter.clear_cache()
        self.weibo_counter.clear_cache()
        print("所有缓存已清除")


def quick_check(keyword: str) -> bool:
    """
    快速检查单个关键词是否达标
    
    Args:
        keyword: 搜索关键词
        
    Returns:
        是否达标
    """
    monitor = RepostMonitor()
    return monitor.check_repost_threshold(keyword)


def batch_check(keywords: List[str]) -> List[Dict]:
    """
    批量检查多个关键词
    
    Args:
        keywords: 关键词列表
        
    Returns:
        检查结果列表
    """
    monitor = RepostMonitor()
    results = monitor.batch_monitor(keywords)
    monitor.print_summary(results)
    return results


if __name__ == "__main__":
    # 测试代码
    test_keywords = ["央行降准", "股市上涨", "经济数据", "货币政策"]
    
    print("=== 转发量监控测试 ===")
    
    # 单个关键词测试
    print("\n1. 单个关键词测试:")
    for kw in test_keywords[:2]:
        qualified = quick_check(kw)
        print(f"关键词: {kw} -> 达标: {qualified}")
        time.sleep(2)
    
    # 批量测试
    print("\n2. 批量测试:")
    results = batch_check(test_keywords)
    
    # 获取达标关键词
    monitor = RepostMonitor()
    qualified = monitor.get_qualified_keywords(test_keywords)
    print(f"\n达标关键词: {qualified}")
