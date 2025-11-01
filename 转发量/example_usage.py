"""
转发量监控模块使用示例
演示各种使用场景和最佳实践
"""
import time
from datetime import datetime

from 转发量 import (
    quick_check,
    batch_check, 
    RepostMonitor,
    baidu_hour_cnt,
    sogou_hour_cnt,
    weibo_30min_stat
)


def example_1_basic_usage():
    """示例1: 基本使用"""
    print("="*50)
    print("示例1: 基本使用")
    print("="*50)
    
    keyword = "央行降准"
    
    # 快速检查是否达标
    qualified = quick_check(keyword)
    print(f"关键词 '{keyword}' 是否达标: {qualified}")
    
    # 获取详细统计
    baidu = baidu_hour_cnt(keyword)
    sogou = sogou_hour_cnt(keyword)
    weibo = weibo_30min_stat(keyword)
    
    print(f"百度结果数: {baidu}")
    print(f"搜狗结果数: {sogou}")
    print(f"微博互动数: {weibo['total']}")
    print(f"总转载数: {baidu + sogou}")


def example_2_batch_monitoring():
    """示例2: 批量监控"""
    print("\n" + "="*50)
    print("示例2: 批量监控")
    print("="*50)
    
    keywords = [
        "央行降准",
        "股市上涨", 
        "经济数据",
        "货币政策",
        "通胀数据"
    ]
    
    print(f"监控关键词: {keywords}")
    results = batch_check(keywords)
    
    # 筛选达标的关键词
    qualified_keywords = [r['keyword'] for r in results if r.get('repost_qualified', False)]
    print(f"\n达标关键词: {qualified_keywords}")


def example_3_custom_monitor():
    """示例3: 自定义监控器"""
    print("\n" + "="*50)
    print("示例3: 自定义监控器")
    print("="*50)
    
    # 创建自定义监控器
    monitor = RepostMonitor(
        baidu_delay=0.5,    # 增加延迟避免反爬
        sogou_delay=0.5,
        weibo_delay=0.8
    )
    
    # 调整阈值
    monitor.repost_threshold = 5  # 降低转载阈值
    monitor.weibo_threshold = 50  # 降低微博阈值
    
    keyword = "股市上涨"
    stats = monitor.get_comprehensive_stats(keyword)
    
    print(f"关键词: {keyword}")
    print(f"转载阈值: {monitor.repost_threshold}")
    print(f"微博阈值: {monitor.weibo_threshold}")
    print(f"转载达标: {stats['repost_qualified']}")
    print(f"微博高热度: {stats['weibo_high_heat']}")


def example_4_real_time_monitoring():
    """示例4: 实时监控"""
    print("\n" + "="*50)
    print("示例4: 实时监控")
    print("="*50)
    
    def monitor_hot_news(keywords, check_interval=60):
        """监控热点新闻"""
        monitor = RepostMonitor()
        
        print(f"开始实时监控，检查间隔: {check_interval}秒")
        print(f"监控关键词: {keywords}")
        
        try:
            while True:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始检查...")
                
                results = monitor.batch_monitor(keywords)
                qualified = [r for r in results if r.get('repost_qualified', False)]
                
                if qualified:
                    print(f"发现 {len(qualified)} 条达标新闻:")
                    for item in qualified:
                        print(f"  - {item['keyword']}: {item['total_reposts']} 次转载")
                else:
                    print("暂无达标新闻")
                
                print(f"等待 {check_interval} 秒...")
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n监控已停止")
    
    # 注意: 实际使用时取消注释下面的代码
    # monitor_hot_news(["央行降准", "股市上涨"], check_interval=30)


def example_5_data_analysis():
    """示例5: 数据分析"""
    print("\n" + "="*50)
    print("示例5: 数据分析")
    print("="*50)
    
    monitor = RepostMonitor()
    keywords = ["央行降准", "股市上涨", "经济数据", "货币政策"]
    
    print("获取统计数据...")
    results = monitor.batch_monitor(keywords)
    
    # 数据分析
    total_keywords = len(results)
    qualified_count = sum(1 for r in results if r.get('repost_qualified', False))
    error_count = sum(1 for r in results if 'error' in r)
    
    # 计算平均数据
    valid_results = [r for r in results if 'error' not in r]
    if valid_results:
        avg_baidu = sum(r['baidu_count'] for r in valid_results) / len(valid_results)
        avg_sogou = sum(r['sogou_count'] for r in valid_results) / len(valid_results)
        avg_weibo = sum(r['weibo_stats']['total'] for r in valid_results) / len(valid_results)
        
        print(f"\n数据分析结果:")
        print(f"总关键词数: {total_keywords}")
        print(f"有效数据数: {len(valid_results)}")
        print(f"错误数量: {error_count}")
        print(f"达标率: {qualified_count/total_keywords*100:.1f}%")
        print(f"平均百度结果: {avg_baidu:.1f}")
        print(f"平均搜狗结果: {avg_sogou:.1f}")
        print(f"平均微博互动: {avg_weibo:.1f}")
    
    # 热度排序
    print(f"\n热度排序 (按总互动量):")
    sorted_results = sorted(valid_results, key=lambda x: x['total_engagement'], reverse=True)
    for i, r in enumerate(sorted_results, 1):
        print(f"{i}. {r['keyword']}: {r['total_engagement']} 总互动")


def example_6_error_handling():
    """示例6: 错误处理"""
    print("\n" + "="*50)
    print("示例6: 错误处理")
    print("="*50)
    
    monitor = RepostMonitor()
    
    # 测试正常关键词
    print("测试正常关键词:")
    try:
        stats = monitor.get_comprehensive_stats("央行降准")
        print(f"  成功: {stats['keyword']} - 转载数: {stats['total_reposts']}")
    except Exception as e:
        print(f"  失败: {e}")
    
    # 测试空关键词
    print("\n测试空关键词:")
    try:
        stats = monitor.get_comprehensive_stats("")
        print(f"  成功: {stats['keyword']} - 转载数: {stats['total_reposts']}")
    except Exception as e:
        print(f"  失败: {e}")
    
    # 测试特殊字符
    print("\n测试特殊字符:")
    try:
        stats = monitor.get_comprehensive_stats("央行@#$%降准")
        print(f"  成功: {stats['keyword']} - 转载数: {stats['total_reposts']}")
    except Exception as e:
        print(f"  失败: {e}")


def main():
    """主函数"""
    print("转发量监控模块使用示例")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        example_1_basic_usage()
        example_2_batch_monitoring()
        example_3_custom_monitor()
        example_4_real_time_monitoring()
        example_5_data_analysis()
        example_6_error_handling()
        
        print("\n" + "="*50)
        print("所有示例运行完成")
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n示例运行被用户中断")
    except Exception as e:
        print(f"\n示例运行过程中发生错误: {e}")


if __name__ == "__main__":
    main()
