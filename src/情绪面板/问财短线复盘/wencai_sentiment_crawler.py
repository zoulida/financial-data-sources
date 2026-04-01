#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问财短线复盘情绪温度爬取与绘图程序
针对 pywencai 返回的字典嵌套结构进行了深度适配
"""

import os
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 使用 Agg 后端，避免在无 GUI 环境下运行报错
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pywencai

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def fetch_sentiment_data():
    """
    使用pywencai爬取短线复盘数据并解析情绪温度
    """
    print("正在从问财爬取短线复盘数据...")
    try:
        query = "短线复盘"
        res = pywencai.get(question=query, loop=True)
        
        if res is None:
            print("未能获取到数据。")
            return None
        
        df = None
        if isinstance(res, dict):
            # 1. 尝试直接寻找包含温度关键字的 key
            target_key = next((k for k in res.keys() if '情绪温度' in k or '温度' in k), None)
            
            if target_key:
                val = res[target_key]
                # 根据调试结果，这里可能是一个字典，包含 'line3' 键，对应 DataFrame
                if isinstance(val, dict) and 'line3' in val:
                    df = val['line3']
                elif isinstance(val, pd.DataFrame):
                    df = val
            
            # 2. 如果没找到，遍历所有层级寻找符合条件的 DataFrame
            if df is None:
                for k, v in res.items():
                    if isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            if isinstance(sub_v, pd.DataFrame) and not sub_v.empty:
                                # 检查列名中是否有时间或温度特征
                                if any('时间' in str(c) or '日期' in str(c) for c in sub_v.columns):
                                    df = sub_v
                                    break
                    if df is not None: break

        if isinstance(df, pd.DataFrame):
            print(f"数据爬取并解析成功！共 {len(df)} 行数据。")
            # 打印列名以便确认（即使有乱码）
            print(f"原始列名: {list(df.columns)}")
            return df
        else:
            print("未能定位到情绪温度数据表。")
            return None
            
    except Exception as e:
        print(f"发生错误: {e}")
        return None

def plot_sentiment_temperature(df):
    """
    本地画图显示情绪温度
    """
    if df is None or df.empty:
        return

    print("正在清洗数据并绘图...")
    
    # 转换所有列名为字符串，处理可能的乱码匹配
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    
    # 自动识别列：第一列通常是温度值，最后一列通常是时间序列
    # 或者通过关键字匹配
    date_col = next((c for c in df.columns if '时间' in c or '日期' in c), df.columns[-1])
    temp_col = next((c for c in df.columns if '温度' in c or '情绪' in c), df.columns[0])

    print(f"识别到列: 时间列=[{date_col}], 温度列=[{temp_col}]")

    # 格式化时间列 (格式通常为 20260401)
    df[date_col] = pd.to_datetime(df[date_col].astype(str), errors='coerce')
    # 格式化温度列
    df[temp_col] = pd.to_numeric(df[temp_col], errors='coerce')
    
    # 剔除无效行并排序
    df = df.dropna(subset=[date_col, temp_col])
    df = df.sort_values(by=date_col)

    if df.empty:
        print("数据转换后为空，请检查数据格式。")
        return

    # 绘图
    plt.figure(figsize=(12, 6), dpi=100)
    plt.plot(df[date_col], df[temp_col], 
             color='#FF4500', marker='o', markersize=4, 
             linewidth=2, label='情绪温度')
    
    # 区域填充
    plt.fill_between(df[date_col], df[temp_col], color='#FF4500', alpha=0.1)

    # 辅助线（通常0-100范围，50为中轴）
    plt.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
    plt.axhline(y=80, color='red', linestyle=':', alpha=0.3, label='活跃区')
    plt.axhline(y=20, color='green', linestyle=':', alpha=0.3, label='低迷区')

    plt.title('问财短线复盘 - 情绪温度走势图', fontsize=16, pad=20)
    plt.xlabel('交易日期')
    plt.ylabel('温度值')
    
    # 日期格式优化
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gcf().autofmt_xdate()
    
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    
    # 保存图片
    current_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(current_dir, 'wencai_sentiment_plot.png')
    plt.savefig(save_path, bbox_inches='tight')
    print(f"图表已保存至: {save_path}")
    
    plt.show()

if __name__ == "__main__":
    data = fetch_sentiment_data()
    if isinstance(data, pd.DataFrame):
        # 保存历史数据 CSV 备份
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, "wencai_sentiment_history.csv")
        data.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"历史数据已保存: {csv_path}")
        # 绘图
        plot_sentiment_temperature(data)
    else:
        print("未能获取到有效的 DataFrame 行情数据，请检查爬取结果或网络连接。")
