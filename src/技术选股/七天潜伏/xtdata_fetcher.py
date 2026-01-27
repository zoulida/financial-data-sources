import os
import sys
import pandas as pd
from typing import List, Dict, Optional
import importlib.util

# 全局动态加载hbdl（合并下载数据）工具
hbdl = None
try:
    from source.实盘.xuntou.datadownload import 合并下载数据 as hbdl
except ImportError:
    # 本地绝对路径查找
    local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../md/合并下载数据/合并下载数据.py'))
    spec = importlib.util.spec_from_file_location('hbdl', local_path)
    hbdl = importlib.util.module_from_spec(spec)
    sys.modules['hbdl'] = hbdl
    spec.loader.exec_module(hbdl)


def fetch_daily_bars(stock_list: List[str], start_date: str, end_date: str, dividend_type: str = 'front', need_download: int = 1) -> Dict[str, pd.DataFrame]:
    """
    逐股票用getDayData单独获取日K线数据，避免批量接口缺陷。
    """
    result = {}
    for code in stock_list:
        try:
            df = hbdl.getDayData(stock_code=code, start_date=start_date, end_date=end_date, is_download=need_download, dividend_type=dividend_type)
            result[code] = df
        except Exception as e:
            print(f"getDayData fail: {code} {e}")
    return result


def fetch_single_daily_bar(stock_code: str, start_date: str, end_date: str, dividend_type: str = 'front', is_download: int = 0) -> pd.DataFrame:
    """
    拉取单只股票的日K线行情
    """
    return hbdl.getDayData(stock_code=stock_code,
                          start_date=start_date, end_date=end_date,
                          is_download=is_download, dividend_type=dividend_type)

# xtdata_fetcher.py 负责行情数据K线获取，为@说明.md量价过滤部分数据入口
# fetch_daily_bars批量请求保证各自数据独立处理，配合“涨停判定”“均线”等策略。参数说明见函数内注释。