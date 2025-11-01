__author__ = 'zoulida'

from datetime import datetime
from functools import lru_cache



#from source.实盘.xuntou.datadownload.下载全市场收盘数据 import get_Chinese_AStock_list_in_sector
from source.实盘.xuntou.datadownload.下载全市场的实时数据 import get_full_tick
from tools.mydecorator.CSVSave import CSV_data
from xtquant import xtdata
import time
# 导入需要的模块
import os
#from Config import FILEPATH
from tools.mydecorator.CSVSave import productFilePath

def download_tick_now_data(stock_list=['600519.SH']):#当前时刻瞬间数据
    # 释义
    #      获取全推数据
    # 参数
    #     code_list - 代码列表，支持传入市场代码或合约代码两种方式
    #     传入市场代码代表订阅全市场，示例：['SH', 'SZ']
    #     传入合约代码代表订阅指定的合约，示例：['600000.SH', '000001.SZ']
    # 返回
    #     dict 数据集 { stock1 : data1, stock2 : data2, ... }
    data = xtdata.get_full_tick(code_list = stock_list)
    return data

def software_list_download(stock_list, period,start_time = '', end_time = ''):
    '''
    用于显示下载进度
    '''
    if "d" in period:
        period = "1d"
    elif "m" in period:
        if int(period[0]) < 5:
            period = "1m"
        else:
            period = "5m"
    elif "tick" == period:
        pass
    else:
        raise KeyboardInterrupt("周期传入错误")

    #time.sleep(5)#等待5秒，防止数据下载不全
    #print('等待5秒，防止数据下载不全')
    xtdata.download_history_data2(stock_list,period,start_time, end_time)#批量下载，但有时不好用

    print("软件下载任务结束")

def software_download(stock_list, period,start_time = '', end_time = ''):
    '''
    用于显示下载进度
    '''
    if "d" in period:
        period = "1d"
    elif "m" in period:
        if int(period[0]) < 5:
            period = "1m"
        else:
            period = "5m"
    elif "tick" == period:
        pass
    else:
        raise KeyboardInterrupt("周期传入错误")


    n = 1
    num = len(stock_list)
    for i in stock_list:
        print(f"当前正在下载{n}/{num}")

        xtdata.download_history_data(i,period,start_time, end_time)#单只下载，基本可用
        n += 1
        print("软件单只下载任务结束")

def getMarketData(code_list = ["600519.SH"], period = "1m", start_time = '20240101', end_time = "", need_download = 1 , dividend_type = 'none'):
    if need_download : # 判断要不要下载数据, gmd系列函数都是从本地读取历史数据,从服务器订阅获取最新数据
        software_list_download(code_list, period, start_time, end_time)#这句话不要乱改，不然数据下载不全，我调试了一整天才找到的
    ############ 获取历史行情+最新行情 #####################
    do_subscribe_quote(code_list,period) # 设置订阅参数，使gmd_ex取到最新行情
    #count = -1 # 设置count参数，使gmd_ex返回全部数据
    data = xtdata.get_market_data_ex([],code_list,period = period, start_time = start_time, end_time = end_time, count = -1, dividend_type = dividend_type) # count 设置为1，使返回值只包含最新行情
    first_value = list(data.values())[0]
    return first_value

def getMarketDataBatch(code_list = ["600519.SH"], period = "1m", start_time = '20240101', end_time = "", need_download = 1 , dividend_type = 'none'):
    if need_download : # 判断要不要下载数据, gmd系列函数都是从本地读取历史数据,从服务器订阅获取最新数据
        software_list_download(code_list, period, start_time, end_time)#这句话不要乱改，不然数据下载不全，我调试了一整天才找到的
    ############ 获取历史行情+最新行情 #####################
    do_subscribe_quote(code_list,period) # 设置订阅参数，使gmd_ex取到最新行情
    #count = -1 # 设置count参数，使gmd_ex返回全部数据
    data = xtdata.get_market_data_ex([],code_list,period = period, start_time = start_time, end_time = end_time, count = -1, dividend_type = dividend_type) # count 设置为1，使返回值只包含最新行情
    return data

def getMarketDataSlowly(code_list = ["600519.SH"], period = "1m", start_time = '20240101', end_time = "", need_download = 1 , dividend_type = 'none'):
    if need_download : # 判断要不要下载数据, gmd系列函数都是从本地读取历史数据,从服务器订阅获取最新数据
        software_download(code_list, period, start_time, end_time)#一个一个下载，基本可用
    ############ 获取历史行情+最新行情 #####################
    do_subscribe_quote(code_list,period) # 设置订阅参数，使gmd_ex取到最新行情
    #count = -1 # 设置count参数，使gmd_ex返回全部数据
    data = xtdata.get_market_data_ex([],code_list,period = period, start_time = start_time, end_time = end_time, count = -1, dividend_type = dividend_type) # count 设置为1，使返回值只包含最新行情
    first_value = list(data.values())[0]
    return first_value

def do_subscribe_quote(stock_list:list, period:str):
    for i in stock_list:
        xtdata.subscribe_quote(i,period = period)
    #time.sleep(1) # 等待订阅完成

def timestamp_ms_to_date_作废(timestamp_ms):#作废，索引里有日期
    # 将毫秒时间戳转换为秒
    timestamp_s = timestamp_ms / 1000.0
    # 转换为 datetime 对象
    date_time = datetime.utcfromtimestamp(timestamp_s)
    # 格式化为日期字符串（不包含时间）
    date_str = date_time.strftime('%Y-%m-%d')
    return date_str

def get_tick_data(stock_list=['600036.SH'], start_time='20250530093000'):#只能获取第一个股票的数据
    df = getMarketDataSlowly(code_list = stock_list, period = "tick", start_time = start_time)#dividend_type = 'front' 是前复权
    df = df.reset_index().rename(columns={'index': 'date'})
    # 将date列转为str类型
    df['date'] = df['date'].astype(str)
    return df

def get_batch_tick_data(stock_list=['600036.SH'], start_time='20250528093000'):#批量获取tick股票的数据
    dictdata = getMarketDataBatch(code_list = stock_list, period = "tick", start_time = start_time)#dividend_type = 'front' 是前复权
    #df = df.reset_index().rename(columns={'index': 'date'})
    # 将date列转为str类型
    #df['date'] = df['date'].astype(str)
    return dictdata            # 获取该股票的数据            df = dictdata[stock_code]


@CSV_data#下面的参数名是不能变的，参考CSVSave
def getDayKlineData(stock_code = "600519.SH",  start_date = '20240101', end_date = "", dividend_type = 'none'):#
    if end_date is None or end_date == "":
        raise ValueError("必须要有结束日期")
    df = getMarketData(code_list = [stock_code], period = "1d", start_time = start_date, end_time = end_date, dividend_type = dividend_type)#dividend_type = 'front' 是前复权
    df = df.reset_index().rename(columns={'index': 'date'})
    # 将date列转为str类型
    df['date'] = df['date'].astype(str)
    # 打印date列的数据类型
    #print(f"date列的数据类型: {df['date'].dtype}")
    #df['date'] = df['time'].apply(timestamp_ms_to_date)
    return df

@lru_cache
def getDayDataCache(stock_code = "600519.SH",  start_date = '20240101', end_date = "",is_download = 0, dividend_type = 'front'):
    return getDayData(stock_code = stock_code,  start_date = start_date, end_date = end_date, is_download = is_download, dividend_type = dividend_type)

def getDayData(stock_code = "600519.SH",  start_date = '20240101', end_date = "",is_download = 0, dividend_type = 'front'):#外部调用
    if stock_code is None or stock_code == "":
        raise ValueError("必须要有代码")
    if start_date is None or start_date == "":
        raise ValueError("必须要有开始日期")
    if end_date is None or end_date == "":
        raise ValueError("必须要有结束日期")
    if is_download:
        # 手动构建与CSV_data装饰器相同的文件路径
        filepath = productFilePath(
            'getDayKlineData',  # 必须使用与装饰函数相同的名称
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            dividend_type=dividend_type
        )
        # 如果文件存在则删除
        if os.path.exists(filepath):
            os.remove(filepath)
    df = getDayKlineData(stock_code = stock_code,  start_date = start_date, end_date = end_date, dividend_type = 'front')
    df['date'] = df['date'].astype(str)
    return df

def batchDownloadDayData(stock_codes = ["600519.SH",'600016.SH'],  start_date = '20240101', end_date = "", dividend_type = 'front', need_download = 1, batchNum = None):
    #这里需要修改，外面套一个壳，失败了重新下载
    """
    批量下载多只股票的日K线数据，下载后可以使用getDayKlineData从CSV中提取
    
    Args:
        stock_codes: 股票代码列表，如 ["600519.SH",'600016.SH']
        start_date: 开始日期，格式为 'YYYYMMDD'
        end_date: 结束日期，格式为 'YYYYMMDD'
        dividend_type: 复权类型，'none'为不复权，'front'为前复权，'back'为后复权
        
    Returns:
        dict: 股票代码为键，DataFrame为值的字典
    """
    # 定义内部函数用于单独下载股票数据

    def _download_single_stock(code, start, end):
        try:
            df = getDayData(code, start, end, is_download = 1)
            # 检查数据最后日期是否等于end
            # 获取实时数据判断开盘价是否小于2元
            tick_data = get_full_tick([code])
            if not tick_data.empty and code in tick_data.index:
                if tick_data.loc[code, 'open'] < 2:
                    print(f"股票 {code} 开盘价小于2元,跳过下载，也有可能是停牌")
                    return '开盘价小于2元'
            retry_count = 0
            while df['date'].iloc[-1] != end and retry_count < 5:
                print(f"股票 {code} 数据下载不完整,最后日期 {df['date'].iloc[-1]} 不等于目标日期 {end}, 第{retry_count+1}次重试, 批次为{batchNum}")
                time.sleep(2 ** retry_count)  # 等待时间指数增长:2,4,8,16,32秒
                df = getDayData(code, start, end, is_download = 1)
                retry_count += 1
            
            if df['date'].iloc[-1] != end:
                print(f"股票 {code} 数据下载失败,5次重试后仍不完整,最后日期 {df['date'].iloc[-1]} 不等于目标日期 {end}")
                raise ValueError(f"股票 {code} 数据下载失败,5次重试后仍不完整")
            print(f"已单独下载股票 {code} 的数据")
            return df
        except Exception as e:
            print(f"单独下载股票 {code} 数据失败: {e}")
            return '下载失败'
        
    def _download_single_stock_fail_log(stock_code, start_date, end_date, fail_type):
            # 记录下载失败的股票代码到csv文件
            import os
            import pandas as pd
            from datetime import datetime
            
            # 构建failog目录路径
            failog_dir = os.path.join(os.path.dirname(__file__), 'faillog')
            os.makedirs(failog_dir, exist_ok=True)
            
            # 构建csv文件名
            csv_filename = f'getDayKlineData_{start_date}-{end_date}-front_failDownload.csv'
            csv_path = os.path.join(failog_dir, csv_filename)
            
            # 准备要写入的数据
            fail_data = {
                'stock_code': [stock_code],
                'fail_time': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                'fail_type': [fail_type]
            }
            fail_df = pd.DataFrame(fail_data)
            
            # 如果文件存在则追加，不存在则创建新文件
            if os.path.exists(csv_path):
                fail_df.to_csv(csv_path, mode='a', header=False, index=False, encoding='utf-8')
            else:
                fail_df.to_csv(csv_path, mode='w', index=False, encoding='utf-8')
                
            print(f"已记录下载失败股票 {stock_code} 到文件: {csv_path}")
            
    if start_date is None or start_date == "":
        raise ValueError("必须要有开始日期")
    if end_date is None or end_date == "":
        raise ValueError("必须要有结束日期")
    
    print(f"开始批量下载 {len(stock_codes)} 只股票的日K线数据...")
    

    
    # 1. 一次性下载所有股票数据
    print(f"一次性下载所有 {len(stock_codes)} 只股票的数据...")

    if need_download  : # 判断要不要下载数据, gmd系列函数都是从本地读取历史数据,从服务器订阅获取最新数据
        software_list_download(stock_codes, "1d", start_date, end_date)#这句话不要乱改，不然数据下载不全，我调试了一整天才找到的
    
    # 直接使用xtdata.get_market_data_ex一次下载所有股票
    # 注意：不使用getMarketData因为它只返回第一只股票的数据
    do_subscribe_quote(stock_codes, "1d")  # 设置订阅参数
    all_stock_data = xtdata.get_market_data_ex(
        [], 
        stock_codes,
        period="1d", 
        start_time=start_date, 
        end_time=end_date, 
        count=-1, 
        dividend_type=dividend_type
    )
    
    print(f"下载完成，获取到 {len(all_stock_data)} 只股票的数据")
    
    # 2. 分别处理每只股票数据并保存
    result_data = {}
    for i, stock_code in enumerate(stock_codes):
        try:
            print(f"处理股票 {stock_code} ({i+1}/{len(stock_codes)})...")
            
            # 检查股票数据是否存在
            if stock_code not in all_stock_data:
                print(f"警告: 未获取到股票 {stock_code} 的数据，跳过")
                continue
                
            # 获取该股票的数据
            df = all_stock_data[stock_code]

            # 处理数据格式，与getDayKlineData一致
            df = df.reset_index().rename(columns={'index': 'date'})

                        # 检查数据是否包含结束日期的数据
            if len(df) > 0:
                # 获取最后一行的日期
                last_date = df.iloc[-1]['date'] if 'date' in df.columns else df.index[-1].strftime('%Y%m%d')
                
                # 判断最后一行日期是否为结束日期
                if last_date != end_date:#我这里还有一个想法，随机抽取10%的股票，如果数据不全，则重新下载该批次
                    print(f"警告: 股票 {stock_code} 的数据最后日期为 {last_date}，不是目标结束日期 {end_date}，尝试单独下载...")
                    
                    # 调用内部函数
                    result = _download_single_stock(stock_code, start_date, end_date)
                    if isinstance(result, str):
                        _download_single_stock_fail_log(stock_code, start_date, end_date, result)
                    else:
                        result_data[stock_code] = result

                    # 跳过当前股票的后续处理
                    continue

                # 检查最后一行的成交量和成交额是否为0

                last_row = df.iloc[-1]
                if 'volume' in last_row and 'amount' in last_row:
                    if last_row['volume'] <= 0 and last_row['amount'] <= 0:
                        print(f"警告: 股票 {stock_code} 的最后一行数据成交量和成交额均为0，尝试单独下载...")
                        
                        # 调用getDayData单独下载该股票数据
                        result = _download_single_stock(stock_code, start_date, end_date)
                        if isinstance(result, str):
                            _download_single_stock_fail_log(stock_code, start_date, end_date, result)
                        else:
                            result_data[stock_code] = result
                        #跳过当前股票的后续处理
                        continue

            # 手动构建与CSV_data装饰器相同的文件路径
            filepath = productFilePath(
                'getDayKlineData',  # 必须使用与装饰函数相同的名称
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                dividend_type=dividend_type
            )
            
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 保存到CSV文件
            df.to_csv(filepath, mode='w', index=False, encoding='UTF-8')
            print(f"已保存数据到CSV: {filepath}")
            
            # 将结果添加到返回数据中
            result_data[stock_code] = df
            
        except Exception as e:
            print(f"处理股票 {stock_code} 数据时出错: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"批量下载完成，共处理 {len(result_data)} 只股票。")
    return result_data


if __name__ == "__main__":

    #download_Chinese_AStock_day_data(start_date = '20200101', end_date = '20250517')

    #data = getDayData(stock_code = "600519.SH",  start_date = '20210101', end_date = '20241015')
    #data = getMarketData()
    #print(data)
    
    #测试批量下载
    # stock_batch = batchDownloadDayData(
    #     stock_codes=["603055.SH"], 
    #     start_date='20241101', 
    #     end_date='20250530'
    # )
    # print(f"批量下载结果，股票数: {len(stock_batch)}")
    # for code, df in stock_batch.items():
    #     print(f"{code} 数据行数: {len(df)}")
    #     print(df)
    
    data = getDayData(stock_code = "600449.SH",  start_date = '20241101', end_date = '20250606')
    print(data)
    #data = get_tick_data(stock_list=['600519.SH'])
    #print(data)
    #data = get_batch_tick_data(stock_list=['600419.SH'])
    #print(data)
    # 获取分割日期前最后一条记录
    #train_data = data[data['date'] <= '20240915']
    #data = getMarketData()
    #print(data)
'''
    start_date = '20240725'# 格式"YYYYMMDD"，开始下载的日期，date = ""时全量下载
    end_date = ""
    period = "1m"

    need_download = 1  # 取数据是空值时，将need_download赋值为1，确保正确下载了历史数据

    code_list = ["600519.SH"] # 股票列表

    if need_download: # 判断要不要下载数据, gmd系列函数都是从本地读取历史数据,从服务器订阅获取最新数据
        my_download(code_list, period, start_date, end_date)
        #pass

    ############ 仅获取历史行情 #####################
    count = -1 # 设置count参数，使gmd_ex返回全部数据
    data1 = xtdata.get_market_data_ex([],code_list,period = period, start_time = start_date, end_time = end_date)

    ############ 仅获取最新行情 #####################
    do_subscribe_quote(code_list,period)# 设置订阅参数，使gmd_ex取到最新行情
    count = 1 # 设置count参数，使gmd_ex仅返回最新行情数据
    data2 = xtdata.get_market_data_ex([],code_list,period = period, start_time = start_date, end_time = end_date, count = 1) # count 设置为1，使返回值只包含最新行情

    ############ 获取历史行情+最新行情 #####################
    do_subscribe_quote(code_list,period) # 设置订阅参数，使gmd_ex取到最新行情
    count = -1 # 设置count参数，使gmd_ex返回全部数据
    data3 = xtdata.get_market_data_ex([],code_list,period = period, start_time = start_date, end_time = end_date, count = -1) # count 设置为1，使返回值只包含最新行情


    print(data1[code_list[0]].tail())# 行情数据查看
    print(data2[code_list[0]].tail())
    print(data3[code_list[0]].tail())

'''

