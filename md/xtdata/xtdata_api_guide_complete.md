# XtQuant.XtData 行情模块 API 完整指南

## 📋 概述

`xtdata` 是 `xtquant` 库中提供行情相关数据的核心模块，专为量化交易者设计，提供精简直接的数据需求。作为 Python 库，`xtdata` 可灵活集成到各种策略脚本中。

> **📌 重要提示**: 本指南基于迅投知识库的XtQuant.XtData行情模块API文档转换而来。如需查找更详细的字段信息或最新更新，请参考官方文档：[http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc](http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc)

### 主要功能
- **行情数据**：历史和实时的 K 线和分笔数据
- **财务数据**：完整的财务报表数据
- **合约基础信息**：股票、期货、期权等合约信息
- **板块和行业分类**：行业板块分类信息

## 🚀 快速开始

### 环境准备
```python
from xtquant import xtdata
import pandas as pd
import numpy as np
```

### 基本使用流程
1. **初始化**：设置 Token，初始化行情模块
2. **订阅数据**：订阅实时行情或下载历史数据
3. **获取数据**：通过接口获取所需数据
4. **数据处理**：转换为 DataFrame 进行后续分析

## 📊 核心接口说明

### 1. 行情数据接口

#### 1.1 订阅单股行情
```python
xtdata.subscribe_quote(stock_code, period='1d', start_time='', end_time='', count=0, callback=None)
```

**参数说明**：
- `stock_code` (str): 合约代码，如 `'000001.SZ'`
- `period` (str): 数据周期，支持 `1m`、`5m`、`1d`、`tick`、`10m`、`15m`、`30m`、`1h`、`1w`
- `start_time` (str): 开始时间
- `end_time` (str): 结束时间
- `count` (int): 订阅的数量
- `callback` (func): 回调函数

**示例**：
```python
# 订阅平安银行日K线数据
xtdata.subscribe_quote('000001.SZ', '1d', count=100)
```

#### 1.2 订阅全推行情
```python
xtdata.subscribe_whole_quote(code_list, callback=None)
```

**参数说明**：
- `code_list` (list): 代码列表，支持市场代码或合约代码
  - 市场代码：`['SH', 'SZ']` 表示订阅全市场
  - 合约代码：`['600000.SH', '000001.SZ']` 表示订阅指定合约

#### 1.3 反订阅行情数据
```python
xtdata.unsubscribe_quote(seq)
```

**参数说明**：
- `seq` (int): 订阅序列号

#### 1.4 获取行情数据
```python
xtdata.get_market_data(field_list=[], stock_list=[], period='1d', start_time='', end_time='', count=-1, dividend_type='none', fill_data=True)
```

**参数说明**：
- `field_list` (list): 数据字段列表，传空则为全部字段
- `stock_list` (list): 合约代码列表
- `period` (str): 周期
- `start_time` (str): 开始时间
- `end_time` (str): 结束时间
- `count` (int): 数据个数
- `dividend_type` (str): 除权方式
- `fill_data` (bool): 是否向后填充空缺数据

**返回值**：
- 当 `period` 为 `1m`、`5m`、`1d` 等K线周期时，返回 `dict { field1 : value1, field2 : value2, ... }`
- 当 `period` 为 `tick` 分笔周期时，返回 `dict { stock1 : value1, stock2 : value2, ... }`

#### 1.5 获取本地行情数据
```python
xtdata.get_local_data(field_list=[], stock_list=[], period='1d', start_time='', end_time='', count=-1, dividend_type='none', fill_data=True, data_dir=data_dir)
```

**参数说明**：
- `data_dir` (str): MiniQmt配套路径的userdata_mini路径，用于直接读取数据文件

#### 1.6 获取全推数据
```python
xtdata.get_full_tick(code_list)
```

**参数说明**：
- `code_list` (list): 代码列表，支持市场代码或合约代码

#### 1.7 获取除权数据
```python
xtdata.get_divid_factors(stock_code, start_time='', end_time='')
```

**参数说明**：
- `stock_code` (str): 合约代码
- `start_time` (str): 开始时间
- `end_time` (str): 结束时间

**返回值**：
- `pd.DataFrame`: 除权数据

### 2. 数据下载接口

#### 2.1 下载历史行情数据
```python
xtdata.download_history_data(stock_code, period, start_time='', end_time='', incrementally=None)
```

**参数说明**：
- `stock_code` (str): 合约代码
- `period` (str): 周期
- `start_time` (str): 开始时间
- `end_time` (str): 结束时间
- `incrementally` (bool/None): 是否增量下载

#### 2.2 批量下载历史行情数据
```python
xtdata.download_history_data2(stock_list, period, start_time='', end_time='', callback=None, incrementally=None)
```

**参数说明**：
- `stock_list` (list): 合约列表
- `callback` (func): 回调函数，参数为进度信息dict
  - `total`: 总下载个数
  - `finished`: 已完成个数
  - `stockcode`: 本地下载完成的合约代码
  - `message`: 本次信息

#### 2.3 下载财务数据
```python
xtdata.download_financial_data(stock_list, table_list=[])
```

**参数说明**：
- `stock_list` (list): 合约列表
- `table_list` (list): 报表列表

#### 2.4 下载过期（退市）合约信息
```python
xtdata.download_history_contracts()
```

### 3. 合约信息接口

#### 3.1 获取合约信息
```python
xtdata.get_instrument_detail(stock_code, iscomplete)
```

**参数说明**：
- `stock_code` (str): 合约代码
- `iscomplete` (bool): 是否完整信息

**返回值**：
- `dict`: 合约详细信息

#### 3.2 获取合约类型
```python
xtdata.get_instrument_type(stock_code)
```

**参数说明**：
- `stock_code` (str): 合约代码

**返回值**：
- `dict`: 合约类型信息
  - `'index'`: 指数
  - `'stock'`: 股票
  - `'fund'`: 基金
  - `'etf'`: ETF

#### 3.3 获取交易日历
```python
xtdata.get_trading_dates(market, start_time='', end_time='', count=-1)
```

**参数说明**：
- `market` (str): 市场代码
- `start_time` (str): 开始时间
- `end_time` (str): 结束时间
- `count` (int): 数据个数

**返回值**：
- `list`: 时间戳列表

#### 3.4 获取节假日数据
```python
xtdata.get_holidays()
```

**返回值**：
- `list`: 8位的日期字符串格式

### 4. 板块管理接口

#### 4.1 获取板块列表
```python
xtdata.get_sector_list()
```

**返回值**：
- `list`: 板块列表

#### 4.2 获取板块成分股列表
```python
xtdata.get_stock_list_in_sector(sector_name)
```

**参数说明**：
- `sector_name` (str): 板块名称

**返回值**：
- `list`: 成分股列表

#### 4.3 下载板块分类信息
```python
xtdata.download_sector_data()
```

#### 4.4 创建板块目录节点
```python
xtdata.create_sector_folder(parent_node, folder_name, overwrite)
```

**参数说明**：
- `parent_node` (str): 父节点，`''` 为 '我的' （默认目录）
- `folder_name` (str): 要创建的板块目录名称
- `overwrite` (bool): 是否覆盖

#### 4.5 创建板块
```python
xtdata.create_sector(parent_node, sector_name, overwrite)
```

#### 4.6 添加自定义板块
```python
xtdata.add_sector(sector_name, stock_list)
```

**参数说明**：
- `sector_name` (str): 板块名称
- `stock_list` (list): 成分股列表

#### 4.7 移除板块成分股
```python
xtdata.remove_stock_from_sector(sector_name, stock_list)
```

#### 4.8 移除自定义板块
```python
xtdata.remove_sector(sector_name)
```

#### 4.9 重置板块
```python
xtdata.reset_sector(sector_name, stock_list)
```

### 5. 指数相关接口

#### 5.1 获取指数成分权重信息
```python
xtdata.get_index_weight(index_code)
```

**参数说明**：
- `index_code` (str): 指数代码

**返回值**：
- `dict`: 成分权重信息

#### 5.2 下载指数成分权重信息
```python
xtdata.download_index_weight()
```

### 6. 公式相关接口

#### 6.1 订阅公式
```python
xtdata.subscribe_formula(formula_name, stock_code, period, start_time='', end_time='', count=-1, dividend_type=None, extend_param={}, callback=None)
```

#### 6.2 反订阅公式
```python
xtdata.unsubscribe_formula(subID)
```

#### 6.3 调用公式
```python
xtdata.call_formula(formula_name, stock_code, period, start_time="", end_time="", count=-1, dividend_type="none", extend_param={})
```

#### 6.4 批量调用公式
```python
xtdata.call_formula_batch(formula_names, stock_codes, period, start_time="", end_time="", count=-1, dividend_type="none", extend_params=[])
```

#### 6.5 生成指数数据
```python
xtdata.generate_index_data(formula_name, formula_param={}, stock_list=[], period='1d', dividend_type='none', start_time='', end_time='', fill_mode='fixed', fill_value=float('nan'), result_path=None)
```

## 📋 数据字段说明

### 行情数据字段

#### tick - 分笔数据
- `time`: 时间戳
- `lastPrice`: 最新价
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `lastClose`: 前收盘价
- `amount`: 成交总金额
- `volume`: 成交总数量
- `pvolume`: 原始成交总数量
- `stockStatus`: 证券状态
- `openInt`: 持仓量
- `lastSettlementPrice`: 前结算
- `askPrice`: 委卖价
- `bidPrice`: 委买价
- `askVol`: 委卖量
- `bidVol`: 委买量
- `transactionNum`: 成交笔数

#### 1m / 5m / 1d - K线数据
- `time`: 时间戳
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量
- `amount`: 成交额
- `settelementPrice`: 今结算
- `openInterest`: 持仓量
- `preClose`: 前收价
- `suspendFlag`: 停牌标记 (0-正常, 1-停牌, -1-当日起复牌)

#### 除权数据
- `time`: 时间戳
- `dividend`: 分红
- `splitRatio`: 拆股比例
- `dividendRatio`: 分红比例
- `splitPrice`: 拆股价格
- `dividendPrice`: 分红价格

### Level2数据字段

#### l2quote - level2实时行情快照
- `time`: 时间戳
- `lastPrice`: 最新价
- `askPrice1-10`: 卖1-10价
- `bidPrice1-10`: 买1-10价
- `askVol1-10`: 卖1-10量
- `bidVol1-10`: 买1-10量
- `totalAskVol`: 总卖量
- `totalBidVol`: 总买量

#### l2order - level2逐笔委托
- `time`: 时间戳
- `orderType`: 委托类型
- `orderDirection`: 委托方向
- `price`: 委托价格
- `volume`: 委托数量
- `orderID`: 委托编号

#### l2transaction - level2逐笔成交
- `time`: 时间戳
- `transactionType`: 成交类型
- `transactionDirection`: 成交方向
- `price`: 成交价格
- `volume`: 成交数量
- `transactionID`: 成交编号

### 财务数据字段

#### Balance - 资产负债表
- `totalAssets`: 总资产
- `totalLiabilities`: 总负债
- `totalEquity`: 总股本
- `currentAssets`: 流动资产
- `currentLiabilities`: 流动负债
- `fixedAssets`: 固定资产
- `longTermDebt`: 长期负债

#### Income - 利润表
- `totalRevenue`: 营业收入
- `operatingProfit`: 营业利润
- `netProfit`: 净利润
- `grossProfit`: 毛利润
- `operatingExpenses`: 营业费用

#### CashFlow - 现金流量表
- `operatingCashFlow`: 经营活动现金流
- `investingCashFlow`: 投资活动现金流
- `financingCashFlow`: 筹资活动现金流
- `netCashFlow`: 净现金流

#### PershareIndex - 主要指标
- `eps`: 每股收益
- `bps`: 每股净资产
- `roe`: 净资产收益率
- `roa`: 总资产收益率
- `pe`: 市盈率
- `pb`: 市净率

#### Capital - 股本表
- `totalShares`: 总股本
- `tradableShares`: 流通股本
- `nonTradableShares`: 非流通股本

#### Top10holder/Top10flowholder - 十大股东/十大流通股东
- `holderName`: 股东名称
- `holdAmount`: 持股数量
- `holdRatio`: 持股比例
- `holdChange`: 持股变化

#### Holdernum - 股东数
- `holderNum`: 股东数量
- `avgHoldAmount`: 平均持股数量

### 合约信息字段

#### 基础信息
- `instrumentID`: 合约代码
- `instrumentName`: 合约名称
- `exchangeID`: 交易所代码
- `productID`: 品种代码
- `underlyingInstrID`: 标的合约代码
- `createDate`: 创建日期
- `openDate`: 上市日期
- `expireDate`: 到期日期
- `isTrading`: 是否交易
- `priceTick`: 最小变动价位
- `volumeMultiple`: 合约乘数
- `longMarginRatio`: 多头保证金率
- `shortMarginRatio`: 空头保证金率
- `maxLimitOrderVolume`: 最大限价单数量
- `maxMarketOrderVolume`: 最大市价单数量
- `minLimitOrderVolume`: 最小限价单数量
- `minMarketOrderVolume`: 最小市价单数量
- `limitUp`: 涨停价
- `limitDown`: 跌停价
- `preSettlementPrice`: 前结算价
- `preClosePrice`: 前收盘价
- `preOpenInterest`: 前持仓量
- `openPrice`: 开盘价
- `highestPrice`: 最高价
- `lowestPrice`: 最低价
- `closePrice`: 收盘价
- `settlementPrice`: 结算价
- `upperLimitPrice`: 涨停价
- `lowerLimitPrice`: 跌停价
- `preDelta`: 昨虚实度
- `currDelta`: 今虚实度
- `updateTime`: 更新时间
- `updateMillisec`: 更新毫秒
- `bidPrice1-5`: 买1-5价
- `askPrice1-5`: 卖1-5价
- `bidVolume1-5`: 买1-5量
- `askVolume1-5`: 卖1-5量
- `averagePrice`: 均价
- `actionDay`: 业务日期
- `tradingDay`: 交易日
- `instrumentStatus`: 合约状态
- `startDelivDate`: 开始交割日
- `endDelivDate`: 结束交割日
- `delivYear`: 交割年份
- `delivMonth`: 交割月份
- `maxOrderVolume`: 最大委托数量
- `volume`: 成交量
- `turnover`: 成交额
- `openInterest`: 持仓量
- `closePrice`: 收盘价
- `settlementPrice`: 结算价
- `upperLimitPrice`: 涨停价
- `lowerLimitPrice`: 跌停价
- `preDelta`: 昨虚实度
- `currDelta`: 今虚实度
- `updateTime`: 更新时间
- `updateMillisec`: 更新毫秒
- `bidPrice1-5`: 买1-5价
- `askPrice1-5`: 卖1-5价
- `bidVolume1-5`: 买1-5量
- `askVolume1-5`: 卖1-5量
- `averagePrice`: 均价
- `actionDay`: 业务日期
- `tradingDay`: 交易日
- `instrumentStatus`: 合约状态
- `startDelivDate`: 开始交割日
- `endDelivDate`: 结束交割日
- `delivYear`: 交割年份
- `delivMonth`: 交割月份
- `maxOrderVolume`: 最大委托数量
- `volume`: 成交量
- `turnover`: 成交额
- `openInterest`: 持仓量
- `closePrice`: 收盘价
- `settlementPrice`: 结算价
- `upperLimitPrice`: 涨停价
- `lowerLimitPrice`: 跌停价
- `preDelta`: 昨虚实度
- `currDelta`: 今虚实度
- `updateTime`: 更新时间
- `updateMillisec`: 更新毫秒
- `bidPrice1-5`: 买1-5价
- `askPrice1-5`: 卖1-5价
- `bidVolume1-5`: 买1-5量
- `askVolume1-5`: 卖1-5量
- `averagePrice`: 均价
- `actionDay`: 业务日期
- `tradingDay`: 交易日
- `instrumentStatus`: 合约状态
- `startDelivDate`: 开始交割日
- `endDelivDate`: 结束交割日
- `delivYear`: 交割年份
- `delivMonth`: 交割月份
- `maxOrderVolume`: 最大委托数量
- `volume`: 成交量
- `turnover`: 成交额
- `openInterest`: 持仓量

## 🔧 使用示例

### 基本使用示例

```python
from xtquant import xtdata
import pandas as pd

# 初始化
xtdata.set_token('your_token_here')

# 获取行情数据
data = xtdata.get_market_data(
    field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
    stock_list=['000001.SZ'],
    period='1d',
    count=100
)

# 转换为DataFrame
df = pd.DataFrame(data['close'].T)
df.index.name = 'Date'
print(df.head())
```

### 实时行情订阅示例

```python
def on_data(datas):
    for stock_code in datas:
        print(f"{stock_code}: {datas[stock_code]}")

# 订阅实时行情
xtdata.subscribe_quote('000001.SZ', '1d', callback=on_data)

# 运行
xtdata.run()
```

### 财务数据获取示例

```python
# 下载财务数据
xtdata.download_financial_data(['000001.SZ'], ['Balance', 'Income'])

# 获取财务数据
financial_data = xtdata.get_financial_data(
    stock_list=['000001.SZ'],
    table_list=['Balance'],
    start_time='20230101',
    end_time='20231231'
)
```

## 📝 注意事项

1. **数据权限**：获取level2数据时需要数据终端有level2数据权限
2. **时间范围**：时间范围为闭区间
3. **数据完整性**：建议定期下载历史数据以确保数据完整性
4. **错误处理**：使用接口时请检查返回的ErrorCode
5. **性能优化**：批量操作时建议使用批量接口

## 🔗 相关链接

- [XtQuant官方文档](http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc)
- [迅投知识库](http://dict.thinktrader.net/)
- [XtQuant GitHub](https://github.com/xtquant/xtquant)

## 📄 版本信息

- 2020-09-01: 初稿
- 2020-09-07: 添加获取除权数据接口，完善合约信息接口
- 2020-09-13: 添加财务数据接口，调整获取和下载财务数据接口说明
- 2020-11-23: 合约基础信息字段类型调整，添加数据字典部分
- 2021-07-20: 添加新版本下载数据接口
- 2021-12-30: 数据字典调整
- 2024-01-19: 支持获取本地数据接口

---

*本文档基于迅投知识库的XtQuant.XtData行情模块API文档转换而来，如有疑问请参考官方文档。*
