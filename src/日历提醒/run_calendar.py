#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日历提醒程序运行脚本
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from calendar_reminder import main

if __name__ == "__main__":
    main()
