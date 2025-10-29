"""
路径配置文件
用于管理项目中的各种路径设置
"""
import sys
import os

def add_to_path(path):
    """
    将指定路径添加到 Python 路径中
    
    Args:
        path (str): 要添加的路径
    """
    if os.path.exists(path) and path not in sys.path:
        sys.path.append(path)
        print(f"已添加路径到 sys.path: {path}")
    elif not os.path.exists(path):
        print(f"警告: 路径不存在: {path}")
    else:
        print(f"路径已存在: {path}")

# 常用路径配置
FIRSTBAN_PATH = r"D:\pythonProject\firstBan"
DATA_SOURCE_PATH = r"D:\pythonProject\数据源"

# 自动添加常用路径
add_to_path(FIRSTBAN_PATH)
add_to_path(DATA_SOURCE_PATH)

# 导出路径变量供其他模块使用
__all__ = ['add_to_path', 'FIRSTBAN_PATH', 'DATA_SOURCE_PATH']

