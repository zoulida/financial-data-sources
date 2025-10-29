# -*- coding: utf-8 -*-
"""
测试替代RSS源
"""

import feedparser
import pandas as pd
import datetime
import requests

def test_alternative_rss_sources():
    """测试替代RSS源"""
    print("=" * 60)
    print("测试替代RSS源")
    print("=" * 60)
    
    # 测试各种RSS源
    rss_sources = [
        # 新浪新闻
        ("新浪新闻焦点", "https://rss.sina.com.cn/news/china/focus15.xml"),
        ("新浪新闻国内", "https://rss.sina.com.cn/news/china/national.xml"),
        ("新浪新闻国际", "https://rss.sina.com.cn/news/world/world.xml"),
        
        # 其他财经RSS
        ("东方财富RSS", "http://finance.eastmoney.com/news/rss_2.xml"),
        ("和讯财经RSS", "http://news.hexun.com/rss.xml"),
        ("金融界RSS", "http://finance.jrj.com.cn/rss.xml"),
        
        # 通用新闻RSS
        ("BBC中文", "http://www.bbc.co.uk/zhongwen/simp/rss.xml"),
        ("CNN中文", "http://rss.cnn.com/rss/edition.rss"),
    ]
    
    working_sources = []
    
    for name, url in rss_sources:
        print(f"\n测试 {name}: {url}")
        
        try:
            # 测试HTTP请求
            response = requests.get(url, timeout=10)
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                # 测试RSS解析
                feed = feedparser.parse(url)
                
                if feed.entries:
                    print(f"  ✓ 成功，条目数: {len(feed.entries)}")
                    print(f"  标题: {feed.feed.get('title', 'N/A')}")
                    
                    # 显示前2条新闻
                    print("  前2条新闻:")
                    for i, entry in enumerate(feed.entries[:2], 1):
                        print(f"    {i}. {entry.get('title', 'N/A')}")
                        print(f"       时间: {entry.get('published', 'N/A')}")
                    
                    working_sources.append((name, url, len(feed.entries)))
                else:
                    print(f"  ✗ 无条目数据")
            else:
                print(f"  ✗ HTTP请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ 错误: {e}")
    
    return working_sources

def create_working_rss_downloader(working_sources):
    """基于可用的RSS源创建下载器"""
    if not working_sources:
        print("\n没有可用的RSS源")
        return
    
    print(f"\n找到 {len(working_sources)} 个可用的RSS源")
    
    # 选择最好的源（条目数最多的）
    best_source = max(working_sources, key=lambda x: x[2])
    name, url, count = best_source
    
    print(f"选择最佳源: {name} (条目数: {count})")
    
    # 创建下载器
    try:
        feed = feedparser.parse(url)
        
        if feed.entries:
            # 创建DataFrame
            news_data = []
            for entry in feed.entries:
                news_item = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', ''),
                    'source': name
                }
                news_data.append(news_item)
            
            df = pd.DataFrame(news_data)
            
            # 转换时间
            df['published'] = pd.to_datetime(df['published'], errors='coerce')
            
            # 保存数据
            filename = f"{datetime.date.today()}_rss_news.csv"
            df.to_csv(filename, encoding='utf-8-sig', index=False)
            
            print(f"✓ 数据已保存到: {filename}")
            print(f"数据形状: {df.shape}")
            print(f"字段: {list(df.columns)}")
            
            # 显示统计信息
            print(f"\n数据统计:")
            print(f"总条数: {len(df)}")
            print(f"时间范围: {df['published'].min()} 到 {df['published'].max()}")
            print(f"标题长度: 平均 {df['title'].str.len().mean():.1f}")
            
            # 显示最新新闻
            print(f"\n最新5条新闻:")
            for i, row in df.head().iterrows():
                print(f"{i+1}. {row['title']}")
                print(f"   时间: {row['published']}")
                print(f"   链接: {row['link']}")
                print()
            
            return df
        else:
            print("✗ 无新闻数据")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"✗ 创建下载器失败: {e}")
        return pd.DataFrame()

def main():
    """主函数"""
    # 测试RSS源
    working_sources = test_alternative_rss_sources()
    
    # 创建下载器
    if working_sources:
        df = create_working_rss_downloader(working_sources)
        
        if not df.empty:
            print("\n" + "=" * 60)
            print("RSS新闻获取成功！")
            print("=" * 60)
            print("特点:")
            print("1. 完全免费，无需注册")
            print("2. 实时更新，适合监控")
            print("3. 数据包含标题、链接、时间等")
            print("4. 适合轻量级舆情跟踪")
        else:
            print("\n✗ 无法获取新闻数据")
    else:
        print("\n✗ 没有找到可用的RSS源")

if __name__ == "__main__":
    main()
