# -*- coding: utf-8 -*-
"""板块炒作阶段预测模块。

数据来源：
- 行情：仅使用 Qlib 全市场日线数据（``md/qlib数据/qlib_data/cn_data``）。
- 板块/概念成分：仅使用 XtQuant ``xtdata.get_sector_list`` /
  ``xtdata.get_stock_list_in_sector``。

输出：每日每个板块一行四分类预测：
- 预备炒作 / 正在炒作 / 炒作末期 / 冷门板块。
"""
