"""
新闻联播下载器使用示例
"""
from src.新闻公告.新闻联播.xwlb_downloader import XWLBDownloader

# 示例1: 下载最新的新闻联播（默认）
print("=" * 60)
print("示例1: 下载最新的新闻联播")
print("=" * 60)
downloader = XWLBDownloader()
news_data = downloader.download_daily_news()

if news_data:
    print(f"\n标题: {news_data['title']}")
    print(f"日期: {news_data['date']}")
    print(f"内容预览: {news_data['content'][:200]}...")
    print(f"保存路径: {news_data.get('saved_path')}")
else:
    print("未能获取新闻联播内容")

# 示例2: 下载指定日期的新闻联播
print("\n" + "=" * 60)
print("示例2: 下载指定日期的新闻联播")
print("=" * 60)
# news_data = downloader.download_daily_news(date="20221101")

# 示例3: 仅获取内容，不保存
print("\n" + "=" * 60)
print("示例3: 仅获取内容，不保存")
print("=" * 60)
# news_data = downloader.download_daily_news(save=False)

# 示例4: 获取新闻列表
print("\n" + "=" * 60)
print("示例4: 获取最新的新闻联播")
print("=" * 60)
latest_news = downloader.get_latest_news()
if latest_news:
    print(f"标题: {latest_news['title']}")
    print(f"内容条目数: {len(latest_news['paragraphs'])}")
