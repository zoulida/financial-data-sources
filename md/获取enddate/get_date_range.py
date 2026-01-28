"""
日期范围获取工具
自动计算start_date和end_date，用于数据获取

规则：
- start_date 永远为 "20241101"
- end_date 逻辑：
  1. 如果当天是交易日：
     - 21点之后：end_date 为当天日期
     - 21点之前：end_date 为上一个交易日
  2. 如果当天不是交易日：end_date 为上一个交易日
"""

import sys
from pathlib import Path
from datetime import datetime
from tools.shelveTool import shelve_me_hour

# 添加工具路径到sys.path
TOOLS_PATH = Path(r"D:\pythonworkspace\zldtools")
if TOOLS_PATH.exists() and str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

try:
    from tools.tradeCal import is_open_day, getLastOpenDay
except ImportError as e:
    print(f"错误：无法导入交易日历工具，请确保路径正确：{e}")
    print(f"当前sys.path: {sys.path}")
    sys.exit(1)

@shelve_me_hour
def get_date_range():
    """
    获取数据查询的日期范围
    
    Returns:
        tuple: (start_date, end_date) 格式为 "YYYYMMDD"
    """
    # start_date 固定为 20241101
    start_date = "20241101"
    
    # 获取当前日期和时间
    now = datetime.now()
    today_str = now.strftime("%Y%m%d")
    current_hour = now.hour
    
    # 判断今天是否为交易日
    is_trading_day = is_open_day(today_str)
    
    if is_trading_day:
        # 今天是交易日
        if current_hour >= 21:
            # 21点之后，使用当天日期
            end_date = today_str
            reason = "今天是交易日且已过21点"
        else:
            # 21点之前，使用上一个交易日
            end_date = getLastOpenDay(today_str)
            reason = "今天是交易日但未到21点"
    else:
        # 今天不是交易日，使用上一个交易日
        end_date = getLastOpenDay(today_str)
        reason = "今天不是交易日"
    
    return start_date, end_date, reason


def format_date_with_dash(date_str):
    """
    将日期格式从 YYYYMMDD 转换为 YYYY-MM-DD
    
    Args:
        date_str (str): 格式为 YYYYMMDD 的日期字符串
        
    Returns:
        str: 格式为 YYYY-MM-DD 的日期字符串
    """
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str


def get_date_range_formatted(with_dash=False):
    """
    获取格式化的日期范围
    
    Args:
        with_dash (bool): 是否使用带横杠的日期格式
        
    Returns:
        tuple: (start_date, end_date, reason)
    """
    start_date, end_date, reason = get_date_range()
    
    if with_dash:
        start_date = format_date_with_dash(start_date)
        end_date = format_date_with_dash(end_date)
    
    return start_date, end_date, reason


def print_date_info():
    """
    打印当前日期信息和计算结果
    """
    now = datetime.now()
    today_str = now.strftime("%Y%m%d")
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    print("=" * 60)
    print("日期范围计算工具")
    print("=" * 60)
    print(f"当前时间: {current_time}")
    print(f"当前日期: {today_str}")
    print(f"是否交易日: {'是' if is_open_day(today_str) else '否'}")
    print("-" * 60)
    
    # 获取不带横杠的日期
    start_date, end_date, reason = get_date_range()
    print(f"计算原因: {reason}")
    print(f"start_date: {start_date}")
    print(f"end_date:   {end_date}")
    print("-" * 60)
    
    # 获取带横杠的日期
    start_date_dash, end_date_dash, _ = get_date_range_formatted(with_dash=True)
    print(f"带横杠格式:")
    print(f"start_date: {start_date_dash}")
    print(f"end_date:   {end_date_dash}")
    print("=" * 60)


if __name__ == "__main__":
    # 测试函数
    try:
        print_date_info()
        
        # 示例：在代码中使用
        print("\n使用示例:")
        print("-" * 60)
        
        # 方式1：获取基本格式（YYYYMMDD）
        start_date, end_date, reason = get_date_range()
        print(f"# 方式1：基本格式")
        print(f"start_date = '{start_date}'")
        print(f"end_date = '{end_date}'")
        print(f"# {reason}")
        
        print()
        
        # 方式2：获取带横杠格式（YYYY-MM-DD）
        start_date, end_date, reason = get_date_range_formatted(with_dash=True)
        print(f"# 方式2：带横杠格式")
        print(f"start_date = '{start_date}'")
        print(f"end_date = '{end_date}'")
        print(f"# {reason}")
        
    except Exception as e:
        print(f"\n错误：{e}")
        import traceback
        traceback.print_exc()

