#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wind API 工具函数库
提供常用的Wind API操作函数，便于复用
"""

import pandas as pd
from WindPy import w
from datetime import datetime
import time
import sys
import os

# 添加shelveTool模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from tools.shelveTool import shelve_me_week

def init_wind_api():
    """
    初始化Wind API
    
    Returns:
        bool: 初始化是否成功
    """
    print("初始化Wind API...")
    try:
        w.start()
        print("✓ Wind API 初始化成功")
        return True
    except Exception as e:
        print(f"✗ Wind API 初始化失败: {e}")
        return False

def close_wind_api():
    """
    关闭Wind API
    """
    print("关闭Wind API...")
    try:
        w.stop()
        print("✓ Wind API 已关闭")
    except:
        pass

@shelve_me_week
def get_index_constituents(index_code, date=None):
    """
    获取指数成分股（周级缓存）
    
    Args:
        index_code (str): 指数代码，如 "000985.CSI"
        date (str, optional): 日期，格式 "YYYY-MM-DD"，默认获取最新
    
    Returns:
        pd.DataFrame or None: 成分股数据，失败返回None
    """
    print(f"获取指数成分股: {index_code}")
    
    try:
        # 构建参数
        if date:
            params = f"windcode={index_code};date={date}"
        else:
            params = f"windcode={index_code}"
        
        # 获取指数成分股
        data = w.wset("indexconstituent", params)
        
        if data.ErrorCode != 0:
            print(f"   ✗ 获取失败，错误代码: {data.ErrorCode}")
            print(f"   错误信息: {data.Data}")
            return None
        
        if not data.Data or len(data.Data) == 0:
            print(f"   ⚠ 未获取到数据")
            return None
        
        # 转换为DataFrame
        df_constituents = pd.DataFrame(data.Data).T
        df_constituents.columns = data.Fields
        
        # 确保wind_code列存在
        if 'wind_code' not in df_constituents.columns and 'code' in df_constituents.columns:
            df_constituents.rename(columns={'code': 'wind_code'}, inplace=True)
        
        print(f"   ✓ 获取到 {len(df_constituents)} 只成分股")
        return df_constituents
        
    except Exception as e:
        print(f"   ✗ 获取成分股失败: {e}")
        import traceback
        traceback.print_exc()
        return None

@shelve_me_week
def get_stock_basic_info(stock_codes, fields=None, batch_size=50):
    """
    批量获取股票基本信息（周级缓存）
    
    Args:
        stock_codes (list): 股票代码列表
        fields (str, optional): 字段列表，默认获取基本信息
        batch_size (int): 批处理大小，默认50
    
    Returns:
        pd.DataFrame or None: 股票信息数据，失败返回None
    """
    if fields is None:
        fields = "sec_name,ipo_date,delist_date,sec_status,mkt,windcode"
    
    print(f"获取股票基本信息，共 {len(stock_codes)} 只股票...")
    
    all_info = []
    
    for i in range(0, len(stock_codes), batch_size):
        batch = stock_codes[i:i+batch_size]
        print(f"   正在处理第 {i//batch_size + 1} 批 ({len(batch)} 只股票)...")
        
        try:
            # 获取股票基本信息
            data = w.wss(batch, fields)
            
            if data.ErrorCode == 0:
                # 创建DataFrame
                temp_df = pd.DataFrame(data.Data).T
                temp_df.columns = data.Fields
                
                # 添加股票代码作为列
                temp_df['wind_code'] = data.Codes
                
                all_info.append(temp_df)
            else:
                print(f"   ⚠ 错误代码: {data.ErrorCode}")
            
            # 延迟以避免API限制
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ⚠ 批量获取失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if not all_info:
        print("   ✗ 未获取到任何股票信息")
        return None
    
    # 合并所有信息
    df_info = pd.concat(all_info, axis=0, ignore_index=True)
    
    print(f"   ✓ 获取到 {len(df_info)} 只股票的基本信息")
    print(f"   字段: {list(df_info.columns)}")
    
    if 'wind_code' not in df_info.columns:
        print("   ⚠ 未找到 wind_code 列")
        return None
    
    return df_info

def get_stock_quotes(stock_codes, fields=None, trade_date=None):
    """
    获取股票行情数据（使用迅投XTQuant接口）
    
    Args:
        stock_codes (list): 股票代码列表，格式如["000001.SZ", "000002.SZ"]
        fields (list, optional): 字段列表，默认获取基本行情
        trade_date (str, optional): 交易日期，格式 "YYYYMMDD"，默认最新
    
    Returns:
        pd.DataFrame or None: 行情数据，失败返回None
    """
    if fields is None:
        fields = ['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose']
    
    print(f"获取股票行情数据，共 {len(stock_codes)} 只股票...")
    
    try:
        # 导入迅投xtdata模块
        from xtquant import xtdata
        
        # 设置默认日期
        if not trade_date:
            from datetime import datetime
            trade_date = datetime.now().strftime('%Y%m%d')
        
        # 使用迅投接口获取行情数据
        data = xtdata.get_market_data_ex(
            field_list=fields,
            stock_list=stock_codes,
            period='1d',
            start_time=trade_date,
            end_time=trade_date,
            count=1,
            dividend_type='none',
            fill_data=True
        )
        
        if data and len(data) > 0:
            # 转换为DataFrame
            df_quotes = pd.DataFrame()
            for field in fields:
                if field in data and not data[field].empty:
                    df_quotes[field] = data[field].iloc[-1]  # 取最后一行（最新数据）
            
            if not df_quotes.empty:
                df_quotes.index = stock_codes
                df_quotes.index.name = 'wind_code'
                print(f"   ✓ 获取到 {len(df_quotes)} 只股票的行情数据")
                return df_quotes
            else:
                print(f"   ✗ 未获取到有效数据")
                return None
        else:
            print(f"   ✗ 未获取到数据")
            return None
        
    except ImportError as e:
        print(f"   ✗ 导入迅投xtdata模块失败: {e}")
        print("   请确保已安装xtquant库")
        return None
    except Exception as e:
        print(f"   ✗ 获取行情数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

@shelve_me_week(-1)
def get_stock_turnover_data(stock_codes, start_date=None, end_date=None):
    """
    获取股票成交金额数据（使用Wind API）
    
    Args:
        stock_codes (list): 股票代码列表
        start_date (str, optional): 开始日期，格式 "YYYYMMDD"
        end_date (str, optional): 结束日期，格式 "YYYYMMDD"
    
    Returns:
        pd.DataFrame or None: 成交金额数据，失败返回None
    """
    print(f"获取股票成交金额数据，共 {len(stock_codes)} 只股票...")
    
    try:
        # 设置默认日期（最近一年）
        if not end_date:
            from datetime import datetime
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            from datetime import datetime, timedelta
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        # 获取成交金额数据 - 使用年成交额字段
        data = w.wss(stock_codes, 
                    "yq_amount",  # 年成交额
                    f"tradeDate={end_date}")
        
        if data.ErrorCode != 0:
            print(f"   ✗ 获取失败，错误代码: {data.ErrorCode}")
            return None
        
        # 转换为DataFrame
        df_turnover = pd.DataFrame(data.Data).T
        df_turnover.columns = data.Fields
        df_turnover.index = data.Codes
        df_turnover.index.name = 'wind_code'
        
        # 计算日均成交金额（年成交额 / 250个交易日）
        df_turnover['AMT_AVG_1Y'] = df_turnover['YQ_AMOUNT'] / 250
        
        print(f"   ✓ 获取到 {len(df_turnover)} 只股票的成交金额数据")
        return df_turnover[['AMT_AVG_1Y']]
        
    except Exception as e:
        print(f"   ✗ 获取成交金额数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_realtime_quotes(stock_codes, fields=None):
    """
    获取股票实时行情数据（使用迅投XTQuant接口）
    
    Args:
        stock_codes (list): 股票代码列表，格式如["000001.SZ", "000002.SZ"]
        fields (list, optional): 字段列表，默认获取基本行情
    
    Returns:
        pd.DataFrame or None: 实时行情数据，失败返回None
    """
    if fields is None:
        fields = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount', 'preClose', 'lastPrice']
    
    print(f"获取股票实时行情数据，共 {len(stock_codes)} 只股票...")
    
    try:
        # 导入迅投xtdata模块
        from xtquant import xtdata
        
        # 先订阅实时数据
        xtdata.subscribe_quote(stock_codes, '1d', 1)
        
        # 获取实时行情数据
        data = xtdata.get_market_data_ex(
            field_list=fields,
            stock_list=stock_codes,
            period='1d',
            count=1,
            dividend_type='none',
            fill_data=True
        )
        
        if data and len(data) > 0:
            # 转换为DataFrame
            df_quotes = pd.DataFrame()
            for field in fields:
                if field in data and not data[field].empty:
                    df_quotes[field] = data[field].iloc[-1]  # 取最后一行（最新数据）
            
            if not df_quotes.empty:
                df_quotes.index = stock_codes
                df_quotes.index.name = 'wind_code'
                print(f"   ✓ 获取到 {len(df_quotes)} 只股票的实时行情数据")
                return df_quotes
            else:
                print(f"   ✗ 未获取到有效数据")
                return None
        else:
            print(f"   ✗ 未获取到数据")
            return None
        
    except ImportError as e:
        print(f"   ✗ 导入迅投xtdata模块失败: {e}")
        print("   请确保已安装xtquant库")
        return None
    except Exception as e:
        print(f"   ✗ 获取实时行情数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_stock_history_quotes(stock_code, start_date=None, end_date=None, dividend_type='front'):
    """
    获取单只股票历史行情数据（使用迅投XTQuant接口）
    
    Args:
        stock_code (str): 股票代码，格式如"600519.SH"
        start_date (str, optional): 开始日期，格式 "YYYYMMDD"
        end_date (str, optional): 结束日期，格式 "YYYYMMDD"
        dividend_type (str): 复权类型，'none'/'front'/'back'，默认'front'
    
    Returns:
        pd.DataFrame or None: 历史行情数据，失败返回None
    """
    print(f"获取股票历史行情: {stock_code}")
    
    try:
        # 导入迅投数据下载模块
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
        from source.实盘.xuntou.datadownload.合并下载数据 import getDayData
        
        # 设置默认日期
        if not start_date:
            from datetime import datetime, timedelta
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        if not end_date:
            from datetime import datetime
            end_date = datetime.now().strftime('%Y%m%d')
        
        # 使用迅投接口获取数据
        df_history = getDayData(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            is_download=0,  # 优先从缓存读取
            dividend_type=dividend_type
        )
        
        if df_history is not None and not df_history.empty:
            print(f"   ✓ 获取到 {len(df_history)} 条历史记录")
            return df_history
        else:
            print(f"   ✗ 未获取到数据")
            return None
        
    except ImportError as e:
        print(f"   ✗ 导入迅投数据模块失败: {e}")
        print("   请确保迅投数据下载模块路径正确")
        return None
    except Exception as e:
        print(f"   ✗ 获取历史行情失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_batch_stock_history_quotes(stock_codes, start_date=None, end_date=None, dividend_type='front'):
    """
    批量获取多只股票历史行情数据（使用迅投XTQuant接口）
    
    Args:
        stock_codes (list): 股票代码列表，格式如["600519.SH", "000001.SZ"]
        start_date (str, optional): 开始日期，格式 "YYYYMMDD"
        end_date (str, optional): 结束日期，格式 "YYYYMMDD"
        dividend_type (str): 复权类型，'none'/'front'/'back'，默认'front'
    
    Returns:
        dict: 以股票代码为键，DataFrame为值的字典
    """
    print(f"批量获取股票历史行情，共 {len(stock_codes)} 只股票...")
    
    try:
        # 导入迅投数据下载模块
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
        from source.实盘.xuntou.datadownload.合并下载数据 import batchDownloadDayData
        
        # 设置默认日期
        if not start_date:
            from datetime import datetime, timedelta
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        if not end_date:
            from datetime import datetime
            end_date = datetime.now().strftime('%Y%m%d')
        
        # 使用迅投接口批量获取数据
        data_dict = batchDownloadDayData(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            dividend_type=dividend_type,
            need_download=0,  # 优先从缓存读取
            batchNum=1
        )
        
        if data_dict:
            print(f"   ✓ 成功获取 {len(data_dict)} 只股票的历史数据")
            return data_dict
        else:
            print(f"   ✗ 未获取到任何数据")
            return {}
        
    except ImportError as e:
        print(f"   ✗ 导入迅投数据模块失败: {e}")
        print("   请确保迅投数据下载模块路径正确")
        return {}
    except Exception as e:
        print(f"   ✗ 批量获取历史行情失败: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_tick_data(stock_codes, fields=None, count=100):
    """
    获取股票tick数据（使用迅投XTQuant接口）
    
    Args:
        stock_codes (list): 股票代码列表，格式如["000001.SZ", "000002.SZ"]
        fields (list, optional): 字段列表，默认获取基本tick数据
        count (int): 获取的tick数量，默认100
    
    Returns:
        dict: 以股票代码为键，DataFrame为值的字典
    """
    if fields is None:
        fields = ['time', 'stime', 'lastPrice', 'volume', 'amount', 'bidPrice1', 'askPrice1', 'bidVol1', 'askVol1']
    
    print(f"获取股票tick数据，共 {len(stock_codes)} 只股票...")
    
    try:
        # 导入迅投xtdata模块
        from xtquant import xtdata
        
        # 先订阅tick数据
        xtdata.subscribe_quote(stock_codes, 'tick', count)
        
        # 获取tick数据
        data = xtdata.get_market_data_ex(
            field_list=fields,
            stock_list=stock_codes,
            period='tick',
            count=count,
            dividend_type='none',
            fill_data=True
        )
        
        if data and len(data) > 0:
            # 转换为DataFrame字典
            tick_dict = {}
            for stock_code in stock_codes:
                if stock_code in data:
                    tick_data = data[stock_code]
                    if len(tick_data) > 0:
                        # 将numpy数组转换为DataFrame
                        df_tick = pd.DataFrame(tick_data)
                        if len(df_tick.columns) == len(fields):
                            df_tick.columns = fields
                        tick_dict[stock_code] = df_tick
            
            if tick_dict:
                print(f"   ✓ 获取到 {len(tick_dict)} 只股票的tick数据")
                return tick_dict
            else:
                print(f"   ✗ 未获取到有效tick数据")
                return {}
        else:
            print(f"   ✗ 未获取到tick数据")
            return {}
        
    except ImportError as e:
        print(f"   ✗ 导入迅投xtdata模块失败: {e}")
        print("   请确保已安装xtquant库")
        return {}
    except Exception as e:
        print(f"   ✗ 获取tick数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {}

def test_wind_connection():
    """
    测试Wind API连接
    
    Returns:
        bool: 连接是否成功
    """
    print("测试Wind API连接...")
    
    try:
        # 初始化
        if not init_wind_api():
            return False
        
        # 测试简单查询
        data = w.wss(["000001.SZ"], "sec_name")
        
        if data.ErrorCode == 0:
            print("✓ Wind API 连接测试成功")
            close_wind_api()
            return True
        else:
            print(f"✗ Wind API 连接测试失败，错误代码: {data.ErrorCode}")
            close_wind_api()
            return False
            
    except Exception as e:
        print(f"✗ Wind API 连接测试失败: {e}")
        try:
            close_wind_api()
        except:
            pass
        return False

if __name__ == "__main__":
    # 测试连接
    test_wind_connection()
