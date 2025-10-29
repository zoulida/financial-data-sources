# -*- coding: utf-8 -*-
"""
新浪财经RSS新闻获取测试
基于用户提供的代码进行测试
"""

import feedparser
import pandas as pd
import datetime

def test_sina_rss_basic():
    """基础测试 - 使用用户提供的代码"""
    print("=" * 60)
    print("新浪财经RSS基础测试")
    print("=" * 60)
    
    try:
        # 使用用户提供的代码
        url = "https://rss.sina.com.cn/finance/stock/sinastock.xml"  # 新浪股票频道 RSS
        f = feedparser.parse(url)
        
        print(f"RSS解析状态: {'成功' if not f.bozo else '有警告'}")
        print(f"新闻条数: {len(f.entries)}")
        
        if f.entries:
            df = pd.DataFrame([(e.published, e.title, e.link) for e in f.entries],
                              columns=['time', 'title', 'url'])
            df['time'] = pd.to_datetime(df['time']).dt.tz_convert('Asia/Shanghai')
            
            print(f"\n数据形状: {df.shape}")
            print(f"字段: {list(df.columns)}")
            print("\n前5条新闻:")
            print(df.head())
            
            # 保存数据
            filename = f"{datetime.date.today()}_sina_news.csv"
            df.to_csv(filename, encoding='utf-8-sig', index=False)
            print(f"\n✓ 数据已保存到: {filename}")
            
            return df
        else:
            print("✗ 无新闻数据")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return pd.DataFrame()

def test_multiple_channels():
    """测试多个RSS频道"""
    print("\n" + "=" * 60)
    print("测试多个RSS频道")
    print("=" * 60)
    
    channels = {
        '股票': 'https://rss.sina.com.cn/finance/stock/sinastock.xml',
        '财经': 'https://rss.sina.com.cn/finance/china/finance.xml',
        '宏观': 'https://rss.sina.com.cn/finance/china/macro.xml',
        '公司': 'https://rss.sina.com.cn/finance/company/company.xml',
        '市场': 'https://rss.sina.com.cn/finance/market/market.xml',
    }
    
    all_news = []
    
    for name, url in channels.items():
        try:
            print(f"\n测试 {name} 频道...")
            f = feedparser.parse(url)
            
            if f.entries:
                df = pd.DataFrame([(e.published, e.title, e.link) for e in f.entries],
                                  columns=['time', 'title', 'url'])
                df['time'] = pd.to_datetime(df['time']).dt.tz_convert('Asia/Shanghai')
                df['channel'] = name
                
                print(f"  ✓ 成功获取 {len(df)} 条新闻")
                all_news.append(df)
            else:
                print(f"  ✗ 无新闻数据")
                
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")
    
    # 合并所有数据
    if all_news:
        combined_df = pd.concat(all_news, ignore_index=True)
        combined_df = combined_df.sort_values('time', ascending=False)
        
        print(f"\n✓ 合并完成，总计 {len(combined_df)} 条新闻")
        print(f"频道分布:")
        print(combined_df['channel'].value_counts())
        
        # 保存合并数据
        filename = f"{datetime.date.today()}_sina_all_channels.csv"
        combined_df.to_csv(filename, encoding='utf-8-sig', index=False)
        print(f"✓ 合并数据已保存到: {filename}")
        
        return combined_df
    else:
        print("\n✗ 没有获取到任何新闻数据")
        return pd.DataFrame()

def test_news_analysis(df):
    """分析新闻数据"""
    if df.empty:
        print("无数据可分析")
        return
    
    print("\n" + "=" * 60)
    print("新闻数据分析")
    print("=" * 60)
    
    print(f"总条数: {len(df)}")
    print(f"时间范围: {df['time'].min()} 到 {df['time'].max()}")
    
    if 'channel' in df.columns:
        print(f"\n频道分布:")
        print(df['channel'].value_counts())
    
    print(f"\n标题长度统计:")
    print(f"平均长度: {df['title'].str.len().mean():.1f}")
    print(f"最短: {df['title'].str.len().min()}")
    print(f"最长: {df['title'].str.len().max()}")
    
    print(f"\n最新5条新闻:")
    for i, row in df.head().iterrows():
        print(f"{i+1}. [{row.get('channel', 'N/A')}] {row['title']}")
        print(f"   时间: {row['time']}")
        print()

if __name__ == "__main__":
    # 基础测试
    basic_news = test_sina_rss_basic()
    
    # 多频道测试
    all_news = test_multiple_channels()
    
    # 数据分析
    if not all_news.empty:
        test_news_analysis(all_news)
    elif not basic_news.empty:
        test_news_analysis(basic_news)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("新浪RSS特点:")
    print("1. 每5-10分钟更新一次")
    print("2. 适合轻量级舆情/热点跟踪")
    print("3. 完全免费，无需注册")
    print("4. 数据包含标题、链接、时间等基本信息")
