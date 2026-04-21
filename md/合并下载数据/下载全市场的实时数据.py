__author__ = 'zoulida'

import pandas as pd
from xtquant import xtdata

# 获取全市场股票列表
#from source.实盘.xuntou.datadownload.下载全市场收盘数据 import get_stock_list_in_sector

def get_full_tick(stock_list ):#= get_stock_list_in_sector()
    #stock_list = get_stock_list_in_sector()
    res = xtdata.get_full_tick(stock_list)
    df = pd.DataFrame(res).T
    return df
    #print(df)   
    # Index(['timetag', 'lastPrice', 'open', 'high', 'low', 'lastClose', 'amount',       'volume', 'pvolume', 'stockStatus', 'openInt', 'settlementPrice',       'lastSettlementPrice', 'askPrice', 'bidPrice', 'askVol', 'bidVol'],      dtype='object')

if __name__ == "__main__":
    print(get_full_tick(['600387.SH']))
'''
                     timetag lastPrice  ...                               askVol                               bidVol
600000.SH  20250526 15:00:02     12.05  ...            [433, 435, 823, 416, 706]          [1187, 294, 393, 588, 1818]
600004.SH  20250526 15:00:01      9.48  ...        [1778, 5430, 3292, 2836, 426]           [368, 473, 404, 8335, 203]
600006.SH  20250526 15:00:02      7.74  ...       [3335, 2349, 5020, 1032, 2672]          [2936, 1706, 577, 531, 742]
600007.SH  20250526 15:00:02     21.53  ...               [40, 50, 62, 243, 162]              [158, 355, 386, 15, 57]
600008.SH  20250526 15:00:01      3.14  ...  [18764, 59046, 44874, 27737, 42202]  [54657, 79314, 27744, 18404, 10532]
'''