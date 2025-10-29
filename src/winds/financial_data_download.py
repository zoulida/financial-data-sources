# 现在可以直接导入 firstBan 模块，无需额外配置路径
# from firstban import your_module  # 取消注释并替换为实际的模块名

from xtquant.xtdata import download_financial_data2, get_financial_data

# 1. 下载股本表（一次性即可，更新频率≈季度）
download_financial_data2(stock_list=['600519.SH'],          # 可换成自己的股票池
                       table_list=['Capital'])             # 对应 CAPITALSTRUCTURE

# 2. 读取最新一条股本数据
df = get_financial_data(stock_list=['600519.SH'],
                       #table='Capital',                     # 关键：写 'Capital'
                       table_list=['total_capital',             # 总股本
                              'circulating_capital',        # 已上市流通A股
                              'restrict_circulating_capital',# 限售流通股份
                              'm_timetag',                  # 报告截止日
                              'm_anntime'])                 # 公告日
print(df)      # tail(1) 看最近一次变动