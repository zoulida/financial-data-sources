"""
转发量监控模块演示脚本
快速演示核心功能
"""
import sys
import time
from datetime import datetime

# 添加父目录到路径
sys.path.append('..')

def demo_quick_check():
    """演示快速检查功能"""
    print("="*60)
    print("演示1: 快速检查功能")
    print("="*60)
    
    from 转发量 import quick_check
    
    test_keywords = ["央行降准", "股市上涨", "经济数据"]
    
    for keyword in test_keywords:
        print(f"\n检查关键词: {keyword}")
        try:
            qualified = quick_check(keyword)
            status = "✓ 达标" if qualified else "✗ 未达标"
            print(f"结果: {status}")
        except Exception as e:
            print(f"错误: {e}")
        
        time.sleep(1)  # 避免请求过快


def demo_detailed_stats():
    """演示详细统计功能"""
    print("\n" + "="*60)
    print("演示2: 详细统计功能")
    print("="*60)
    
    from 转发量 import RepostMonitor
    
    monitor = RepostMonitor()
    keyword = "央行降准"
    
    print(f"获取关键词 '{keyword}' 的详细统计...")
    
    try:
        stats = monitor.get_comprehensive_stats(keyword)
        
        print(f"\n=== 统计结果 ===")
        print(f"关键词: {stats['keyword']}")
        print(f"时间戳: {stats['timestamp']}")
        print(f"百度结果数: {stats['baidu_count']}")
        print(f"搜狗结果数: {stats['sogou_count']}")
        print(f"总转载数: {stats['total_reposts']}")
        print(f"微博转发: {stats['weibo_stats']['reposts']}")
        print(f"微博评论: {stats['weibo_stats']['comments']}")
        print(f"微博总互动: {stats['weibo_stats']['total']}")
        print(f"总互动量: {stats['total_engagement']}")
        print(f"转载达标: {'是' if stats['repost_qualified'] else '否'}")
        print(f"微博高热度: {'是' if stats['weibo_high_heat'] else '否'}")
        print(f"综合达标: {'是' if stats['overall_qualified'] else '否'}")
        
    except Exception as e:
        print(f"获取统计失败: {e}")


def demo_batch_monitoring():
    """演示批量监控功能"""
    print("\n" + "="*60)
    print("演示3: 批量监控功能")
    print("="*60)
    
    from 转发量 import batch_check
    
    keywords = ["央行降准", "股市上涨", "经济数据"]
    
    print(f"批量监控关键词: {keywords}")
    print("正在获取数据，请稍候...")
    
    try:
        results = batch_check(keywords)
        
        print(f"\n=== 批量监控结果 ===")
        print(f"总关键词数: {len(results)}")
        
        qualified_count = sum(1 for r in results if r.get('repost_qualified', False))
        print(f"达标关键词数: {qualified_count}")
        print(f"达标率: {qualified_count/len(results)*100:.1f}%")
        
        print(f"\n详细结果:")
        for i, result in enumerate(results, 1):
            if 'error' in result:
                print(f"{i}. {result['keyword']}: 错误 - {result['error']}")
            else:
                status = "✓ 达标" if result['repost_qualified'] else "✗ 未达标"
                print(f"{i}. {result['keyword']}: {status} (转载:{result['total_reposts']}, 微博:{result['weibo_stats']['total']})")
        
    except Exception as e:
        print(f"批量监控失败: {e}")


def demo_individual_platforms():
    """演示各平台独立功能"""
    print("\n" + "="*60)
    print("演示4: 各平台独立功能")
    print("="*60)
    
    from 转发量 import baidu_hour_cnt, sogou_hour_cnt, weibo_30min_stat
    
    keyword = "央行降准"
    
    print(f"测试关键词: {keyword}")
    
    # 百度搜索
    print(f"\n1. 百度搜索:")
    try:
        baidu_count = baidu_hour_cnt(keyword)
        print(f"   最近1小时结果数: {baidu_count}")
    except Exception as e:
        print(f"   错误: {e}")
    
    time.sleep(1)
    
    # 搜狗搜索
    print(f"\n2. 搜狗搜索:")
    try:
        sogou_count = sogou_hour_cnt(keyword)
        print(f"   最近1小时结果数: {sogou_count}")
    except Exception as e:
        print(f"   错误: {e}")
    
    time.sleep(1)
    
    # 微博统计
    print(f"\n3. 微博统计:")
    try:
        weibo_stats = weibo_30min_stat(keyword)
        print(f"   转发数: {weibo_stats['reposts']}")
        print(f"   评论数: {weibo_stats['comments']}")
        print(f"   总互动: {weibo_stats['total']}")
    except Exception as e:
        print(f"   错误: {e}")


def main():
    """主演示函数"""
    print("转发量监控模块演示")
    print(f"演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("本演示将展示转发量监控模块的核心功能")
    
    try:
        # 运行各个演示
        demo_quick_check()
        demo_detailed_stats()
        demo_batch_monitoring()
        demo_individual_platforms()
        
        print("\n" + "="*60)
        print("演示完成")
        print("="*60)
        print("更多功能请参考:")
        print("- README.md: 详细文档")
        print("- example_usage.py: 使用示例")
        print("- test_repost_monitor.py: 测试脚本")
        
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"\n演示过程中发生错误: {e}")
        print("请检查网络连接和依赖安装")


if __name__ == "__main__":
    main()
