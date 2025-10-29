# -*- coding: utf-8 -*-
"""
简单的RSS新闻获取示例
基于用户提供的代码进行简化
"""

import feedparser
import pandas as pd
import datetime

def get_sina_news_simple():
    """简单获取新浪新闻"""
    print("=" * 50)
    print("简单RSS新闻获取示例")
    print("=" * 50)
    
    # 可用的RSS源
    rss_urls = [
        "https://rss.sina.com.cn/news/china/focus15.xml",  # 新浪新闻焦点
        "http://rss.cnn.com/rss/edition.rss",  # CNN国际新闻
    ]
    
    all_news = []
    
    for i, url in enumerate(rss_urls, 1):
        print(f"\n{i}. 获取RSS新闻: {url}")
        
        try:
            # 解析RSS
            f = feedparser.parse(url)
            
            if f.entries:
                print(f"  ✓ 成功获取 {len(f.entries)} 条新闻")
                
                # 创建DataFrame
                df = pd.DataFrame([(e.published, e.title, e.link) for e in f.entries],
                                  columns=['time', 'title', 'url'])
                
                # 转换时间
                df['time'] = pd.to_datetime(df['time'])
                # 尝试转换时区，如果失败则保持原样
                try:
                    df['time'] = df['time'].dt.tz_convert('Asia/Shanghai')
                except:
                    pass
                
                # 添加来源
                source_name = "新浪新闻" if "sina" in url else "CNN新闻"
                df['source'] = source_name
                
                all_news.append(df)
                
                print(f"  最新3条新闻:")
                for j, row in df.head(3).iterrows():
                    print(f"    {j+1}. {row['title']}")
            else:
                print(f"  ✗ 无新闻数据")
                
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")
    
    # 合并所有新闻
    if all_news:
        combined_df = pd.concat(all_news, ignore_index=True)
        combined_df = combined_df.sort_values('time', ascending=False)
        
        print(f"\n✓ 合并完成，总计 {len(combined_df)} 条新闻")
        
        # 保存数据
        filename = f"{datetime.date.today()}_rss_news.csv"
        combined_df.to_csv(filename, encoding='utf-8-sig', index=False)
        print(f"✓ 数据已保存到: {filename}")
        
        # 显示统计信息
        print(f"\n数据统计:")
        print(f"总条数: {len(combined_df)}")
        print(f"来源分布:")
        print(combined_df['source'].value_counts())
        print(f"时间范围: {combined_df['time'].min()} 到 {combined_df['time'].max()}")
        
        return combined_df
    else:
        print("\n✗ 没有获取到任何新闻数据")
        return pd.DataFrame()

def get_single_source_news():
    """获取单个源的新闻（用户原始代码的改进版）"""
    print("\n" + "=" * 50)
    print("单个RSS源新闻获取")
    print("=" * 50)
    
    # 使用可用的RSS源
    url = "https://rss.sina.com.cn/news/china/focus15.xml"
    
    try:
        f = feedparser.parse(url)
        
        if f.entries:
            df = pd.DataFrame([(e.published, e.title, e.link) for e in f.entries],
                              columns=['time', 'title', 'url'])
            df['time'] = pd.to_datetime(df['time'])
            # 尝试转换时区，如果失败则保持原样
            try:
                df['time'] = df['time'].dt.tz_convert('Asia/Shanghai')
            except:
                pass
            
            # 保存数据
            filename = f"{datetime.date.today()}_sina_news.csv"
            df.to_csv(filename, encoding='utf-8-sig', index=False)
            
            print(f"✓ 成功获取 {len(df)} 条新闻")
            print(f"✓ 数据已保存到: {filename}")
            print(f"\n前5条新闻:")
            print(df.head())
            
            return df
        else:
            print("✗ 无新闻数据")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"✗ 获取失败: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # 运行示例
    get_sina_news_simple()
    get_single_source_news()
    
    print("\n" + "=" * 50)
    print("RSS新闻获取完成")
    print("=" * 50)
    print("特点:")
    print("1. 完全免费，无需注册")
    print("2. 每5-10分钟更新一次")
    print("3. 适合轻量级舆情/热点跟踪")
    print("4. 数据包含标题、链接、时间等基本信息")
