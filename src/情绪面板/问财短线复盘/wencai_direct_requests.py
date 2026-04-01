#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
不使用 pywencai 模块，尝试使用原生 requests 爬取问财数据
"""

import os
import time
import json
import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def fetch_data_direct():
    """
    尝试直接通过 API 接口获取数据
    """
    url = "https://www.iwencai.com/unifiedwap/unified-wap/v2/result/get-robot-data"
    
    # 模拟移动端浏览器的 Headers
    headers = {
        'Host': 'www.iwencai.com',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.iwencai.com',
        'Referer': 'https://www.iwencai.com/unifiedwap/result?w=%E7%9F%AD%E7%BA%BF%E5%A4%8D%E7%9B%98&querytype=stock',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    # 构造请求参数
    # 注意：这里的 sign 和 v 参数通常是动态生成的，手动固定可能很快失效
    payload = {
        'question': '短线复盘',
        'perpage': '100',
        'page': '1',
        'secondary_intent': 'stock',
        'log_info': '{"input_type":"typewrite"}',
        'source': 'Ths_iwencai_Xuangu',
        'version': '2.0',
        'query_area': '',
        'block_list': '',
        'add_info': '{"urp":{"scene":1,"company":1,"business":1},"parent_method":"get_robot_data","is_v2":true}'
    }
    
    print("正在尝试使用原生 requests 直接请求问财接口...")
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        
        if response.status_code != 200:
            print(f"请求失败，状态码: {response.status_code}")
            return None
            
        data = response.json()
        
        # 问财的返回结构非常复杂，我们需要深入嵌套寻找包含"情绪温度"的组件
        # 这种手工解析非常脆弱，这也是 pywencai 存在的意义
        components = data.get('data', {}).get('answer', [{}])[0].get('components', [])
        
        df = None
        for comp in components:
            if comp.get('type') == 'table' or comp.get('type') == 'common_table':
                table_data = comp.get('data', {}).get('datas', [])
                if table_data:
                    df = pd.DataFrame(table_data)
                    # 检查是否包含情绪温度相关信息
                    if any('情绪' in str(c) or '温度' in str(c) for c in df.columns):
                        print("直接请求成功，已找到数据表。")
                        return df
        
        print("未能从响应中解析出情绪温度表格。可能是由于缺少动态令牌(v参数)导致返回了空结果。")
        return None
        
    except Exception as e:
        print(f"原生请求发生异常: {e}")
        return None

def plot_data(df):
    if df is None or df.empty:
        return
    
    # 复用之前的清洗和绘图逻辑
    df.columns = [str(c) for c in df.columns]
    date_col = next((c for c in df.columns if '时间' in c or '日期' in c), df.columns[-1])
    temp_col = next((c for c in df.columns if '温度' in c or '情绪' in c), df.columns[0])
    
    df[date_col] = pd.to_datetime(df[date_col].astype(str), errors='coerce')
    df[temp_col] = pd.to_numeric(df[temp_col], errors='coerce')
    df = df.dropna(subset=[date_col, temp_col]).sort_values(by=date_col)
    
    plt.figure(figsize=(10, 5))
    plt.plot(df[date_col], df[temp_col], 'b-o', markersize=4, label='原生爬取-情绪温度')
    plt.title('问财原生请求测试 - 情绪温度')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    save_path = os.path.join(os.path.dirname(__file__), 'wencai_direct_test.png')
    plt.savefig(save_path)
    print(f"原生请求测试图表已保存: {save_path}")

if __name__ == "__main__":
    df = fetch_data_direct()
    if df is not None:
        plot_data(df)
    else:
        print("\n--- 实验结论 ---")
        print("在不使用 pywencai 的情况下，直接使用 requests 会被问财的反爬系统拦截。")
        print("主要障碍是 Cookie 中的 'v' 参数（10位加密指纹），它是通过复杂的 JS 在客户端动态计算生成的。")
        print("如果一定要手动实现，需要引入 ExecJS 调用 Node 运行其加密脚本，这本质上就是在复刻 pywencai 的功能。")

