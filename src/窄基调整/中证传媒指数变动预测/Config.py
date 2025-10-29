#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存配置文件
用于shelveTool模块的缓存目录配置
"""

from enum import Enum

class CustomEnum(Enum):
    def __repr__(self):
        return "%s.%s" % (self.__class__.__name__, self._name_)

class FILEPATH(CustomEnum):
    # 缓存目录路径，请根据实际情况修改
    SHELVEDIR = "D:\\pythonProject\\数据源\\cache\\shelve"
