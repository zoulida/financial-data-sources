# RSS新闻获取工具

基于RSS源获取新闻数据的Python工具，支持多个新闻源，完全免费使用。

## 功能特点

- 🆓 **完全免费** - 无需注册或付费
- 🔄 **实时更新** - RSS每5-10分钟更新一次
- 📰 **多源支持** - 支持多个RSS新闻源
- 📊 **数据清洗** - 自动清洗和格式化数据
- 💾 **CSV导出** - 支持保存为CSV格式
- 📈 **统计分析** - 提供数据统计和摘要

## 安装依赖

```bash
pip install feedparser pandas requests
```

## 快速开始

### 1. 简单使用

```python
import feedparser
import pandas as pd
import datetime

# 获取新浪新闻
url = "https://rss.sina.com.cn/news/china/focus15.xml"
f = feedparser.parse(url)

if f.entries:
    df = pd.DataFrame([(e.published, e.title, e.link) for e in f.entries],
                      columns=['time', 'title', 'url'])
    df['time'] = pd.to_datetime(df['time']).dt.tz_convert('Asia/Shanghai')
    
    # 保存数据
    filename = f"{datetime.date.today()}_sina_news.csv"
    df.to_csv(filename, encoding='utf-8-sig', index=False)
    print(f"成功获取 {len(df)} 条新闻")
```

### 2. 使用完整工具

```python
from rss_news_downloader import RSSNewsDownloader

# 创建下载器
downloader = RSSNewsDownloader()

# 获取所有可用源的新闻
news = downloader.download_all_sources(50)

# 保存数据
downloader.save_news(news, "news.csv")

# 获取统计信息
print(downloader.get_news_summary(news))
```

## 文件说明

- `rss_news_downloader.py` - 完整的RSS新闻下载工具
- `simple_rss_example.py` - 简单使用示例
- `test_alternative_rss.py` - 测试不同RSS源
- `debug_rss.py` - RSS调试工具
- `README.md` - 说明文档

## 支持的RSS源

### 当前可用的源

1. **新浪新闻焦点** - `https://rss.sina.com.cn/news/china/focus15.xml`
   - 分类：国内新闻
   - 更新频率：每5-10分钟
   - 特点：中文新闻，适合国内舆情跟踪

2. **CNN国际新闻** - `http://rss.cnn.com/rss/edition.rss`
   - 分类：国际新闻
   - 更新频率：实时
   - 特点：英文新闻，适合国际新闻跟踪

### 已失效的源

- 新浪财经RSS（404错误）
- 其他部分RSS源

## 数据字段

下载的新闻数据包含以下字段：

- `title` - 新闻标题
- `link` - 新闻链接
- `published` - 发布时间
- `summary` - 新闻摘要（如果有）
- `author` - 作者（如果有）
- `tags` - 标签（如果有）
- `source_name` - 新闻源名称
- `category` - 新闻分类

## 使用示例

### 基础使用

```python
from rss_news_downloader import RSSNewsDownloader

downloader = RSSNewsDownloader()

# 获取单个源的新闻
news = downloader.download_rss_news('sina_focus', 20)

# 获取所有源的新闻
all_news = downloader.download_all_sources(30)

# 保存数据
downloader.save_news(all_news, "all_news.csv")
```

### 监控新闻更新

```python
# 监控新闻更新（每5分钟检查一次，共10次）
downloader.monitor_news('sina_focus', interval=300, max_runs=10)
```

### 数据分析

```python
# 获取数据统计
summary = downloader.get_news_summary(news)
print(summary)

# 查看最新新闻
print(news.head())
```

## 注意事项

1. **网络连接** - 需要稳定的网络连接访问RSS源
2. **更新频率** - RSS源更新频率不同，建议适当间隔获取
3. **数据质量** - 部分RSS源可能包含HTML标签，已自动清理
4. **时区处理** - 时间已转换为中国时区
5. **反爬虫** - 建议添加适当延迟避免请求过快

## 错误处理

工具包含完善的错误处理机制：

- RSS源不可用时的自动跳过
- 网络请求失败的重试机制
- 数据解析错误的容错处理
- 详细的日志记录

## 日志文件

- `rss_news_download.log` - 详细的运行日志

## 适用场景

1. **个人量化/回测** - 获取新闻数据进行量化分析
2. **舆情监控** - 实时监控新闻热点
3. **数据收集** - 收集新闻数据进行研究
4. **轻量级应用** - 不需要复杂功能的简单新闻获取

## 优势

- ✅ 完全免费，无需注册
- ✅ 实时更新，数据新鲜
- ✅ 多源支持，覆盖面广
- ✅ 易于使用，代码简单
- ✅ 数据清洗，质量保证
- ✅ 统计分析，便于分析

## 限制

- ❌ 数据字段相对简单
- ❌ 依赖RSS源稳定性
- ❌ 部分RSS源可能失效
- ❌ 更新频率依赖源站

## 更新日志

- 2025-10-20: 初始版本，支持基础RSS新闻获取
- 2025-10-20: 添加多源支持和数据清洗功能
- 2025-10-20: 添加监控和统计分析功能
