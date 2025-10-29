#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查API是否可用

注意：
- download_changes.py 需要 Wind API
- analyze_performance.py 使用项目的数据下载模块（不需要额外API）
"""

import os
import sys

print("=" * 60)
print("检查数据API可用性")
print("=" * 60)

# 检查 Wind API（用于下载变动数据）
print("\n1. 检查 Wind API（下载变动数据需要）...")
try:
    import WindPy as w
    w.start()
    
    # 测试一个简单的查询
    test_data = w.wsd("000001.SZ", "close", "20240101", "20240105", "PriceAdj=F")
    if test_data.ErrorCode == 0:
        print("  ✓ Wind API 可用 (测试查询成功)")
        USE_WIND = True
        w.stop()
    else:
        print(f"  ✗ Wind API 测试查询失败，错误代码: {test_data.ErrorCode}")
        USE_WIND = False
        w.stop()
except Exception as e:
    print(f"  ✗ Wind API 不可用: {e}")
    USE_WIND = False

# 检查项目数据下载模块（用于分析股票表现）
print("\n2. 检查项目数据下载模块（分析股票表现使用）...")
try:
    # 添加项目路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    sys.path.append(project_root)
    
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData
    print("  ✓ 项目数据下载模块可用")
    USE_PROJECT_MODULE = True
except ImportError as e:
    print(f"  ✗ 项目数据下载模块不可用: {e}")
    USE_PROJECT_MODULE = False

# 总结
print("\n" + "=" * 60)
print("API 可用性总结")
print("=" * 60)
print(f"Wind API:          {'✓ 可用' if USE_WIND else '✗ 不可用'} (下载变动数据需要)")
print(f"项目数据下载模块: {'✓ 可用' if USE_PROJECT_MODULE else '✗ 不可用'} (分析股票表现需要)")

print("\n使用说明:")
print("  1. 运行 download_changes.py → 需要 Wind API")
print("  2. 运行 analyze_performance.py → 需要项目数据下载模块")

if not USE_WIND:
    print("\n⚠ 警告: Wind API 不可用，无法下载指数变动数据")
    print("  请安装并启动 Wind 终端")

if not USE_PROJECT_MODULE:
    print("\n⚠ 警告: 项目数据下载模块不可用，无法分析股票表现")
    print("  请确保项目路径正确")

