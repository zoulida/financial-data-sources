# -*- coding: utf-8 -*-
"""
Wind API 新闻下载使用示例
"""

from wind_news_downloader import WindNewsDownloader
from datetime import datetime, timedelta

def example_basic_download():
    """基本下载示例"""
    print("=" * 50)
    print("基本下载示例")
    print("=" * 50)
    
    downloader = WindNewsDownloader()
    
    try:
        # 下载最近3天的公司公告
        df = downloader.download_news(
            start_date=(datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            category="公司公告",
            count=50
        )
        
        if df is not None and not df.empty:
            print("下载成功！")
            print(f"数据条数: {len(df)}")
            print(f"字段: {list(df.columns)}")
            print("\n前5条数据:")
            print(df.head())
        else:
            print("下载失败或无数据")
            
    finally:
        downloader.stop_wind()

def example_multiple_categories():
    """多类型下载示例"""
    print("\n" + "=" * 50)
    print("多类型下载示例")
    print("=" * 50)
    
    downloader = WindNewsDownloader()
    
    try:
        # 下载多种类型的新闻
        all_df = downloader.download_multiple_categories(
            start_date=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            categories=["公司公告", "财经新闻", "研报"],
            count=30
        )
        
        if not all_df.empty:
            print("多类型下载完成！")
            print(f"总数据条数: {len(all_df)}")
            print("\n分类统计:")
            print(all_df['category'].value_counts())
        else:
            print("多类型下载失败或无数据")
            
    finally:
        downloader.stop_wind()

def example_custom_download():
    """自定义下载示例"""
    print("\n" + "=" * 50)
    print("自定义下载示例")
    print("=" * 50)
    
    downloader = WindNewsDownloader()
    
    try:
        # 自定义参数下载
        df = downloader.download_news(
            start_date="2024-01-01",
            end_date="2024-01-31",
            category="公司公告",
            count=200,
            save_file="custom_news_january.csv"
        )
        
        if df is not None and not df.empty:
            print("自定义下载成功！")
            print(f"数据摘要:")
            print(downloader.get_news_summary(df))
        else:
            print("自定义下载失败或无数据")
            
    finally:
        downloader.stop_wind()

if __name__ == "__main__":
    # 运行所有示例
    example_basic_download()
    example_multiple_categories()
    example_custom_download()
    
    print("\n" + "=" * 50)
    print("所有示例运行完成")
    print("=" * 50)
