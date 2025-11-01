"""
转发量监控模块测试脚本
"""
import sys
import time
from datetime import datetime

# 添加父目录到路径，以便导入模块
sys.path.append('..')

from 转发量 import (
    baidu_hour_cnt, 
    sogou_hour_cnt, 
    weibo_30min_stat,
    quick_check,
    batch_check,
    RepostMonitor
)


def test_individual_functions():
    """测试各个独立功能"""
    print("="*60)
    print("测试各个独立功能")
    print("="*60)
    
    test_keyword = "央行降准"
    
    # 测试百度搜索
    print(f"\n1. 测试百度搜索: {test_keyword}")
    try:
        baidu_count = baidu_hour_cnt(test_keyword)
        print(f"   百度最近1小时结果数: {baidu_count}")
    except Exception as e:
        print(f"   百度搜索失败: {e}")
    
    time.sleep(1)
    
    # 测试搜狗搜索
    print(f"\n2. 测试搜狗搜索: {test_keyword}")
    try:
        sogou_count = sogou_hour_cnt(test_keyword)
        print(f"   搜狗最近1小时结果数: {sogou_count}")
    except Exception as e:
        print(f"   搜狗搜索失败: {e}")
    
    time.sleep(1)
    
    # 测试微博统计
    print(f"\n3. 测试微博统计: {test_keyword}")
    try:
        weibo_stats = weibo_30min_stat(test_keyword)
        print(f"   微博转发数: {weibo_stats['reposts']}")
        print(f"   微博评论数: {weibo_stats['comments']}")
        print(f"   微博总互动: {weibo_stats['total']}")
    except Exception as e:
        print(f"   微博统计失败: {e}")


def test_monitor_class():
    """测试监控器类"""
    print("\n" + "="*60)
    print("测试监控器类")
    print("="*60)
    
    monitor = RepostMonitor()
    test_keyword = "股市上涨"
    
    print(f"\n测试关键词: {test_keyword}")
    
    try:
        # 获取综合统计
        stats = monitor.get_comprehensive_stats(test_keyword)
        
        print(f"百度结果数: {stats['baidu_count']}")
        print(f"搜狗结果数: {stats['sogou_count']}")
        print(f"总转载数: {stats['total_reposts']}")
        print(f"微博转发: {stats['weibo_stats']['reposts']}")
        print(f"微博评论: {stats['weibo_stats']['comments']}")
        print(f"微博总互动: {stats['weibo_stats']['total']}")
        print(f"总互动量: {stats['total_engagement']}")
        print(f"转载达标: {stats['repost_qualified']}")
        print(f"微博高热度: {stats['weibo_high_heat']}")
        print(f"综合达标: {stats['overall_qualified']}")
        
    except Exception as e:
        print(f"监控器测试失败: {e}")


def test_batch_monitoring():
    """测试批量监控"""
    print("\n" + "="*60)
    print("测试批量监控")
    print("="*60)
    
    test_keywords = ["央行降准", "股市上涨", "经济数据"]
    
    print(f"测试关键词列表: {test_keywords}")
    
    try:
        # 使用便捷函数
        results = batch_check(test_keywords)
        
        print(f"\n批量监控完成，共处理 {len(results)} 个关键词")
        
        # 统计结果
        qualified_count = sum(1 for r in results if r.get('repost_qualified', False))
        error_count = sum(1 for r in results if 'error' in r)
        
        print(f"转载达标: {qualified_count} 个")
        print(f"错误数量: {error_count} 个")
        
    except Exception as e:
        print(f"批量监控失败: {e}")


def test_quick_check():
    """测试快速检查"""
    print("\n" + "="*60)
    print("测试快速检查")
    print("="*60)
    
    test_keywords = ["央行降准", "股市上涨", "经济数据"]
    
    for keyword in test_keywords:
        try:
            qualified = quick_check(keyword)
            print(f"关键词: {keyword} -> 达标: {qualified}")
            time.sleep(1)  # 避免请求过快
        except Exception as e:
            print(f"关键词: {keyword} -> 错误: {e}")


def test_threshold_adjustment():
    """测试阈值调整"""
    print("\n" + "="*60)
    print("测试阈值调整")
    print("="*60)
    
    monitor = RepostMonitor()
    test_keyword = "央行降准"
    
    # 原始阈值
    print(f"\n原始阈值测试: {test_keyword}")
    stats1 = monitor.get_comprehensive_stats(test_keyword)
    print(f"转载阈值: {monitor.repost_threshold}, 达标: {stats1['repost_qualified']}")
    
    # 调整阈值
    monitor.repost_threshold = 5  # 降低阈值
    print(f"\n调整阈值测试 (阈值=5): {test_keyword}")
    stats2 = monitor.get_comprehensive_stats(test_keyword)
    print(f"转载阈值: {monitor.repost_threshold}, 达标: {stats2['repost_qualified']}")
    
    # 恢复原始阈值
    monitor.repost_threshold = 10


def main():
    """主测试函数"""
    print("转发量监控模块测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 运行各项测试
        test_individual_functions()
        test_monitor_class()
        test_quick_check()
        test_batch_monitoring()
        test_threshold_adjustment()
        
        print("\n" + "="*60)
        print("所有测试完成")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")


if __name__ == "__main__":
    main()
