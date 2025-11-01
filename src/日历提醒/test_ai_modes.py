#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试不同AI模式的结果差异
"""

from calendar_reminder_stable import StableCalendarReminder
import time

def test_ai_modes():
    """测试不同AI模式的结果"""
    reminder = StableCalendarReminder()
    
    print("🧪 AI模式对比测试")
    print("=" * 60)
    print()
    
    # 测试稳定模式
    print("📊 测试1: 稳定模式 (temperature=0.1)")
    print("-" * 40)
    reminder.ask_openai_about_a_stock_events("stable")
    print("\n" + "="*60 + "\n")
    
    time.sleep(2)  # 避免API调用过于频繁
    
    # 测试创意模式
    print("📊 测试2: 创意模式 (temperature=0.8)")
    print("-" * 40)
    reminder.ask_openai_about_a_stock_events("creative")
    print("\n" + "="*60 + "\n")
    
    time.sleep(2)
    
    # 测试平衡模式
    print("📊 测试3: 平衡模式 (temperature=0.7)")
    print("-" * 40)
    reminder.ask_openai_about_a_stock_events("balanced")

if __name__ == "__main__":
    test_ai_modes()
