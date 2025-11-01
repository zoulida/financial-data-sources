# 转发量监控模块

本模块实现了百度、搜狗、微博三大平台的「最近一小时」结果数和「30分钟转发评论」统计功能，用于判断新闻事件的传播热度和转载量。

## 功能特性

- **百度搜索**: 获取最近一小时新闻搜索结果数
- **搜狗搜索**: 获取最近一小时新闻搜索结果数  
- **微博统计**: 获取最近30分钟转发+评论数
- **综合判断**: 实现「30分钟转载≥10次」的硬指标判断
- **缓存机制**: LRU缓存避免重复请求
- **错误处理**: 完善的异常处理和重试机制
- **批量监控**: 支持批量关键词监控

## 快速开始

### 安装依赖

```bash
pip install requests
```

### 基本使用

```python
from 转发量 import quick_check, batch_check, RepostMonitor

# 快速检查单个关键词
qualified = quick_check("央行降准")
print(f"是否达标: {qualified}")

# 批量检查多个关键词
keywords = ["央行降准", "股市上涨", "经济数据"]
results = batch_check(keywords)

# 使用监控器类
monitor = RepostMonitor()
stats = monitor.get_comprehensive_stats("央行降准")
print(f"百度结果数: {stats['baidu_count']}")
print(f"搜狗结果数: {stats['sogou_count']}")
print(f"总转载数: {stats['total_reposts']}")
print(f"微博互动: {stats['weibo_stats']['total']}")
print(f"转载达标: {stats['repost_qualified']}")
```

## 详细API

### BaiduSearchCounter

百度搜索结果计数器

```python
from 转发量 import BaiduSearchCounter

counter = BaiduSearchCounter(delay=0.3)
count = counter.get_hour_count("关键词")
```

### SogouSearchCounter

搜狗搜索结果计数器

```python
from 转发量 import SogouSearchCounter

counter = SogouSearchCounter(delay=0.3)
count = counter.get_hour_count("关键词")
```

### WeiboStatsCounter

微博统计数据计数器

```python
from 转发量 import WeiboStatsCounter

counter = WeiboStatsCounter(delay=0.5)
stats = counter.get_30min_stats("关键词")
print(f"转发: {stats['reposts']}, 评论: {stats['comments']}")
```

### RepostMonitor

综合监控器

```python
from 转发量 import RepostMonitor

monitor = RepostMonitor()

# 获取综合统计
stats = monitor.get_comprehensive_stats("关键词")

# 检查是否达标
qualified = monitor.check_repost_threshold("关键词")

# 批量监控
results = monitor.batch_monitor(["关键词1", "关键词2"])

# 获取达标关键词
qualified_list = monitor.get_qualified_keywords(["关键词1", "关键词2"])
```

## 配置参数

### 请求延迟设置

```python
# 自定义延迟时间（秒）
monitor = RepostMonitor(
    baidu_delay=0.3,    # 百度请求延迟
    sogou_delay=0.3,    # 搜狗请求延迟  
    weibo_delay=0.5     # 微博请求延迟
)
```

### 阈值设置

```python
monitor = RepostMonitor()
monitor.repost_threshold = 10    # 转载阈值
monitor.weibo_threshold = 100    # 微博高热度阈值
```

## 数据格式

### 综合统计数据格式

```python
{
    'keyword': '关键词',
    'timestamp': '2025-10-30T11:11:11',
    'baidu_count': 15,           # 百度结果数
    'sogou_count': 8,            # 搜狗结果数
    'total_reposts': 23,         # 总转载数
    'weibo_stats': {             # 微博统计
        'reposts': 45,
        'comments': 12,
        'total': 57
    },
    'total_engagement': 80,      # 总互动量
    'repost_qualified': True,    # 转载是否达标
    'weibo_high_heat': False,    # 微博是否高热度
    'overall_qualified': True,   # 综合是否达标
    'thresholds': {              # 阈值设置
        'repost_threshold': 10,
        'weibo_threshold': 100
    }
}
```

## 注意事项

1. **请求频率**: 建议设置适当的延迟时间，避免触发反爬机制
2. **缓存机制**: 默认5分钟缓存，相同关键词不会重复请求
3. **错误处理**: 网络错误时会返回0或空数据，不会中断程序
4. **接口稳定性**: 基于前端接口，官方可能调整参数格式
5. **数据准确性**: 结果仅供参考，实际数据以官方为准

## 使用建议

1. **监控频率**: 建议30分钟-1小时检查一次
2. **关键词选择**: 选择具体、准确的关键词效果更好
3. **批量处理**: 使用批量监控功能提高效率
4. **结果验证**: 重要决策前建议人工验证数据准确性

## 示例场景

### 新闻热点监控

```python
# 监控财经新闻热点
finance_keywords = [
    "央行降准", "股市上涨", "经济数据", 
    "货币政策", "通胀数据", "GDP增长"
]

monitor = RepostMonitor()
results = monitor.batch_monitor(finance_keywords)

# 筛选出高热度新闻
hot_news = [r for r in results if r.get('overall_qualified', False)]
print(f"发现 {len(hot_news)} 条高热度新闻")
```

### 实时监控

```python
import time
from datetime import datetime

def real_time_monitor(keywords, interval=1800):  # 30分钟间隔
    monitor = RepostMonitor()
    
    while True:
        print(f"\n[{datetime.now()}] 开始监控...")
        results = monitor.batch_monitor(keywords)
        
        # 处理结果
        qualified = [r for r in results if r.get('repost_qualified', False)]
        if qualified:
            print(f"发现 {len(qualified)} 条达标新闻")
            for item in qualified:
                print(f"  - {item['keyword']}: {item['total_reposts']} 次转载")
        
        time.sleep(interval)

# 启动监控
real_time_monitor(["央行降准", "股市上涨"])
```

## 故障排除

### 常见问题

1. **请求失败**: 检查网络连接，增加延迟时间
2. **解析错误**: 接口格式可能变化，检查正则表达式
3. **缓存问题**: 调用 `clear_all_caches()` 清除缓存
4. **频率限制**: 减少请求频率，增加延迟时间

### 调试模式

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 测试单个功能
from 转发量.baidu_search import baidu_hour_cnt
count = baidu_hour_cnt("测试关键词")
print(f"百度结果: {count}")
```
