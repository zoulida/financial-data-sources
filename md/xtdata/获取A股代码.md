使用 xtquant 获取全部 A 股代码只需两行核心代码：

from xtquant import xtdata
a_share_codes = xtdata.get_stock_list_in_sector("沪深A股")

以下为示例代码：
# -*- coding: utf-8 -*-
"""
功能：用 xtquant 获取全部 A 股代码列表
作者：you
日期：2025-xx-xx
"""

import os
import time
import pandas as pd
from xtquant.xtdata import get_stock_list_in_sector, download_sector_data

# 1. 更新本地板块数据（首次运行务必执行，否则可能返回空列表）
# download_sector_data()
pass

# 2. 获取“沪深A股”板块下全部代码
print('>>> 正在获取 A 股代码列表...')
a_share_codes = get_stock_list_in_sector('沪深A股')
print(f'>>> 共获取 {len(a_share_codes)} 只 A 股')

# 3. 简单清洗：去掉退市整理板、ST 等（可选）
#    这里仅演示把 688/689（北交所）和 83/87（退市整理）剔除
a_share_codes = [c for c in a_share_codes
                 if not (c.startswith(('688', '689', '83', '87')))]
print(f'>>> 剔除北交所/退市整理后剩余 {len(a_share_codes)} 只')

# 4. 保存为 CSV / TXT 两份文件
output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)

# CSV 带表头，方便 Excel 打开
df = pd.DataFrame({'code': a_share_codes})
df.to_csv(os.path.join(output_dir, 'a_share_codes.csv'),
          index=False, encoding='utf-8-sig')

# TXT 一行一个，方便程序读取
with open(os.path.join(output_dir, 'a_share_codes.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(a_share_codes))

print('>>> 已写入：')
print(f'    {os.path.abspath(output_dir)}/a_share_codes.csv')
print(f'    {os.path.abspath(output_dir)}/a_share_codes.txt')








下面给出“用 xtquant 获取 A 股最新总市值”的完整思路 + 代码。
xtquant 本身只提供行情/财务字段的“原始数据接口”，市值字段（totalValue / 总市值）需要到“财务专项”里去拿，或者自己用“最新价 × 总股本”算。两种办法都演示，你按场景二选一即可。
一、直接取财务字段（最简洁，推荐）
Python
复制
# -*- coding: utf-8 -*-
"""
功能：用 xtquant 取 A 股最新总市值（单位：亿元）
依赖：pip install xtquant
"""
from xtquant.xtdata import get_stock_list_in_sector, download_financial_data, get_financial_data

# 1. 先更新财务数据（每天第一次运行务必执行）
download_financial_data()

# 2. 拿到全部 A 股代码
codes = get_stock_list_in_sector('沪深A股')

# 3. 一次性拉取“总市值”字段
#    财务字段名：totalValue（单位：元）
field = 'totalValue'
df = get_financial_data(codes, [field])

# 4. 换算成“亿元”并排序
df['totalValue_yi'] = df['totalValue'] / 1e8
df = df.sort_values('totalValue_yi', ascending=False)

# 5. 保存结果
df[['code', 'totalValue_yi']].to_csv('a股市值排行榜.csv', index=False, encoding='utf-8-sig')
print('>>> 已生成 a股市值排行榜.csv，共', len(df), '条')
运行后 CSV 示例：
表格
复制
code	totalValue_yi
000858.SZ	6883.45
600519.SH	23564.21
…	…
二、自己算：最新价 × 总股本（无需财务权限）
如果本地财务数据没更新，可用实时行情字段“现价 * 总股本”秒算：
Python
复制
from xtquant.xtdata import get_stock_list_in_sector, get_local_data

codes = get_stock_list_in_sector('沪深A股')
# 取最新日线（返回 dict：{code: DataFrame})
price_df = get_local_data(field_list=['close', 'totalShares'], stock_list=codes)

mv_list = []
for code, df in price_df.items():
    if df.empty:
        continue
    close = df['close'].iloc[-1]        # 最新收盘价
    shares = df['totalShares'].iloc[-1] # 总股本（股）
    mv = close * shares / 1e8           # 亿元
    mv_list.append({'code': code, 'mv_yi': round(mv, 2)})

import pandas as pd
pd.DataFrame(mv_list).sort_values('mv_yi', ascending=False)\
                     .to_csv('a股市值_自算版.csv', index=False)
注意：totalShares 字段需提前在本地“数据管理”里勾选“股本数据”并下载，否则返回空。