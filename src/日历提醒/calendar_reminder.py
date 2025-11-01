#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日历提醒程序
功能：
1. 打印未来两周的日历事件
2. 询问OpenAI获取未来两周影响A股的重要会议和事件
"""

import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class CalendarReminder:
    def __init__(self):
        self.csv_file = os.path.join(os.path.dirname(__file__), '日历2026.csv')
        self.openai_api_url = "https://api.laozhang.ai/v1"
        self.openai_token = "sk-bjBm3sO5lEzdzWKM615e8fB7D7B842708b1e250695Df3b11"
        
    def load_calendar_events(self):
        """加载日历事件数据"""
        try:
            df = pd.read_csv(self.csv_file, encoding='utf-8')
            df['日期'] = pd.to_datetime(df['日期'])
            return df
        except Exception as e:
            print(f"❌ 加载日历文件失败: {e}")
            return None
    
    def get_future_two_weeks_events(self):
        """获取未来两周的日历事件"""
        df = self.load_calendar_events()
        if df is None:
            return None
            
        today = datetime.now().date()
        two_weeks_later = today + timedelta(days=14)
        
        # 筛选未来两周的事件
        future_events = df[
            (df['日期'].dt.date >= today) & 
            (df['日期'].dt.date <= two_weeks_later)
        ].sort_values('日期')
        
        return future_events
    
    def print_calendar_events(self):
        """打印未来两周的日历事件"""
        print("📅 未来两周日历事件")
        print("=" * 50)
        
        events = self.get_future_two_weeks_events()
        if events is None or events.empty:
            print("📝 未来两周暂无重要事件")
            return
        
        for _, event in events.iterrows():
            date_str = event['日期'].strftime('%Y-%m-%d (%A)')
            print(f"📆 {date_str}")
            print(f"   📌 {event['事件']}")
            if pd.notna(event['备注']) and event['备注'].strip():
                print(f"   💡 {event['备注']}")
            print()
    
    def ask_openai_about_a_stock_events(self):
        """询问OpenAI关于未来两周影响A股的重要事件"""
        print("🤖 正在查询OpenAI关于未来两周影响A股的重要事件...")
        print("🔒 稳定模式：低随机性，结果更一致")
        print("📊 扩展模式：不限数量，获取尽可能多的事件")
        print("=" * 50)
        
        # 获取未来两周的日期范围
        today = datetime.now().date()
        two_weeks_later = today + timedelta(days=14)
        
        prompt = f"""
请提供从{today}到{two_weeks_later}期间，可能影响A股市场的重要事件信息，包括但不限于：

1. 行业会议（科技、新能源、医药、金融、汽车、房地产、教育、军工等）
2. 政治事件（重要政策发布、领导人讲话、国际会议、外交活动等）
3. 经济数据发布（GDP、CPI、PPI、PMI、社会融资规模、M2等）
4. 金融会议（央行会议、银保监会会议、证监会会议等）
5. 重要产品发布会（苹果、特斯拉、华为、小米、比亚迪等科技巨头）
6. 国际重要事件（美联储会议、G7/G20峰会、WTO会议等）
7. 上市公司重要公告期（三季报、年报预告、重大资产重组等）
8. 行业政策发布（新能源、房地产、教育、医疗、金融等行业政策）
9. 重要节日和假期（可能影响市场交易和资金流向）
10. 国际重要节日（可能影响外资流向和北向资金）

请严格按照以下格式提供信息，并按日期排序：
【事件名称】
预计日期：YYYY-MM-DD
对A股可能的影响：[详细说明]
相关行业或板块：[具体板块]

请提供尽可能多的相关事件信息，不要限制数量，尽量覆盖所有可能影响A股的重要事件。
请确保按日期顺序排列，从{today}开始到{two_weeks_later}结束。
"""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 4000,  # 增加token数量以支持更多事件
                "temperature": 0.1   # 低随机性，稳定输出
            }
            
            response = requests.post(
                f"{self.openai_api_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60  # 增加超时时间
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("🔍 OpenAI分析结果：")
                print(content)
                
                # 统计事件数量
                event_count = content.count('【') or content.count('事件名称') or content.count('1.') or content.count('•')
                print(f"\n📈 本次查询共获取约 {event_count} 个相关事件")
                
            else:
                print(f"❌ OpenAI API调用失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                
        except requests.exceptions.Timeout:
            print("❌ OpenAI API调用超时")
        except requests.exceptions.RequestException as e:
            print(f"❌ OpenAI API调用失败: {e}")
        except Exception as e:
            print(f"❌ 发生未知错误: {e}")
    
    def run(self):
        """运行日历提醒程序"""
        print("🚀 日历提醒程序启动")
        print("=" * 50)
        print()
        
        # 1. 打印未来两周的日历事件
        self.print_calendar_events()
        print()
        
        # 2. 询问OpenAI关于A股相关事件
        self.ask_openai_about_a_stock_events()
        print()
        print("✅ 程序执行完成")

def main():
    """主函数"""
    reminder = CalendarReminder()
    reminder.run()

if __name__ == "__main__":
    main()
