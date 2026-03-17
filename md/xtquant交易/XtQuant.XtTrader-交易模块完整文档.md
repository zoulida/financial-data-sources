# XtQuant.XtTrader 交易模块完整文档

## 概述

XtQuant封装了策略交易所需要的Python API接口，可以和MiniQMT客户端交互进行报单、撤单、查询资产、查询委托、查询成交、查询持仓以及收到资金、委托、成交和持仓等变动的主推消息。

## 完整示例代码

```python
#coding=utf-8
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant

class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        """ 连接断开 :return: """
        print("connection lost")

    def on_stock_order(self, order):
        """ 委托回报推送 :param order: XtOrder对象 :return: """
        print("on order callback:")
        print(order.stock_code, order.order_status, order.order_sysid)

    def on_stock_trade(self, trade):
        """ 成交变动推送 :param trade: XtTrade对象 :return: """
        print("on trade callback")
        print(trade.account_id, trade.stock_code, trade.order_id)

    def on_order_error(self, order_error):
        """ 委托失败推送 :param order_error:XtOrderError 对象 :return: """
        print("on order_error callback")
        print(order_error.order_id, order_error.error_id, order_error.error_msg)

    def on_cancel_error(self, cancel_error):
        """ 撤单失败推送 :param cancel_error: XtCancelError 对象 :return: """
        print("on cancel_error callback")
        print(cancel_error.order_id, cancel_error.error_id, cancel_error.error_msg)

    def on_order_stock_async_response(self, response):
        """ 异步下单回报推送 :param response: XtOrderResponse 对象 :return: """
        print("on_order_stock_async_response")
        print(response.account_id, response.order_id, response.seq)

    def on_account_status(self, status):
        """ :param response: XtAccountStatus 对象 :return: """
        print("on_account_status")
        print(status.account_id, status.account_type, status.status)

if __name__ == "__main__":
    print("demo test")
    
    # path为mini qmt客户端安装目录下userdata_mini路径
    path = 'D:\\迅投极速交易终端 睿智融科版\\userdata_mini'
    
    # session_id为会话编号，策略使用方对于不同的Python策略需要使用不同的会话编号
    session_id = 123456
    xt_trader = XtQuantTrader(path, session_id)
    
    # 创建资金账号为1000000365的证券账号对象
    acc = StockAccount('1000000365')
    
    # StockAccount可以用第二个参数指定账号类型，如沪港通传'HUGANGTONG'，深港通传'SHENGANGTONG'
    # acc = StockAccount('1000000365','STOCK')
    
    # 创建交易回调类对象，并声明接收回调
    callback = MyXtQuantTraderCallback()
    xt_trader.register_callback(callback)
    
    # 启动交易线程
    xt_trader.start()
    
    # 建立交易连接，返回0表示连接成功
    connect_result = xt_trader.connect()
    print(connect_result)
    
    # 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
    subscribe_result = xt_trader.subscribe(acc)
    print(subscribe_result)
    
    stock_code = '600000.SH'
    
    # 使用指定价下单，接口返回订单编号，后续可以用于撤单操作以及查询委托状态
    print("order using the fix price:")
    fix_result_order_id = xt_trader.order_stock(acc, stock_code, xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5, 'strategy_name', 'remark')
    print(fix_result_order_id)
    
    # 使用订单编号撤单
    print("cancel order:")
    cancel_order_result = xt_trader.cancel_order_stock(acc, fix_result_order_id)
    print(cancel_order_result)
    
    # 使用异步下单接口，接口返回下单请求序号seq，seq可以和on_order_stock_async_response的委托反馈response对应起来
    print("order using async api:")
    async_seq = xt_trader.order_stock_async(acc, stock_code, xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5, 'strategy_name', 'remark')
    print(async_seq)
    
    # 查询证券资产
    print("query asset:")
    asset = xt_trader.query_stock_asset(acc)
    if asset:
        print("asset:")
        print("cash {0}".format(asset.cash))
    
    # 根据订单编号查询委托
    print("query order:")
    order = xt_trader.query_stock_order(acc, fix_result_order_id)
    if order:
        print("order:")
        print("order {0}".format(order.order_id))
    
    # 查询当日所有的委托
    print("query orders:")
    orders = xt_trader.query_stock_orders(acc)
    print("orders:", len(orders))
    if len(orders) != 0:
        print("last order:")
        print("{0} {1} {2}".format(orders[-1].stock_code, orders[-1].order_volume, orders[-1].price))
    
    # 查询当日所有的成交
    print("query trade:")
    trades = xt_trader.query_stock_trades(acc)
    print("trades:", len(trades))
    if len(trades) != 0:
        print("last trade:")
        print("{0} {1} {2}".format(trades[-1].stock_code, trades[-1].traded_volume, trades[-1].traded_price))
    
    # 查询当日所有的持仓
    print("query positions:")
    positions = xt_trader.query_stock_positions(acc)
    print("positions:", len(positions))
    if len(positions) != 0:
        print("last position:")
        print("{0} {1} {2}".format(positions[-1].account_id, positions[-1].stock_code, positions[-1].volume))
    
    # 根据股票代码查询对应持仓
    print("query position:")
    position = xt_trader.query_stock_position(acc, stock_code)
    if position:
        print("position:")
        print("{0} {1} {2}".format(position.account_id, position.stock_code, position.volume))
    
    # 阻塞线程，接收交易推送
    xt_trader.run_forever()
```

## 市场类型常量

### 交易所市场
- **上交所** - `xtconstant.SH_MARKET`
- **深交所** - `xtconstant.SZ_MARKET`
- **北交所** - `xtconstant.MARKET_ENUM_BEIJING`
- **沪港通** - `xtconstant.MARKET_ENUM_SHANGHAI_HONGKONG_STOCK`
- **深港通** - `xtconstant.MARKET_ENUM_SHENZHEN_HONGKONG_STOCK`

### 期货交易所
- **上期所** - `xtconstant.MARKET_ENUM_SHANGHAI_FUTURE`
- **大商所** - `xtconstant.MARKET_ENUM_DALIANG_FUTURE`
- **郑商所** - `xtconstant.MARKET_ENUM_ZHENGZHOU_FUTURE`
- **中金所** - `xtconstant.MARKET_ENUM_INDEX_FUTURE`
- **能源中心** - `xtconstant.MARKET_ENUM_INTL_ENERGY_FUTURE`
- **广期所** - `xtconstant.MARKET_ENUM_GUANGZHOU_FUTURE`

### 期权市场
- **上海期权** - `xtconstant.MARKET_ENUM_SHANGHAI_STOCK_OPTION`
- **深证期权** - `xtconstant.MARKET_ENUM_SHENZHEN_STOCK_OPTION`

## 账户类型常量

- **期货** - `xtconstant.FUTURE_ACCOUNT`
- **股票** - `xtconstant.SECURITY_ACCOUNT`
- **信用** - `xtconstant.CREDIT_ACCOUNT`
- **期货期权** - `xtconstant.FUTURE_OPTION_ACCOUNT`
- **股票期权** - `xtconstant.STOCK_OPTION_ACCOUNT`
- **沪港通** - `xtconstant.HUGANGTONG_ACCOUNT`
- **深港通** - `xtconstant.SHENGANGTONG_ACCOUNT`

## 报价类型常量

### 基础报价类型
- **最新价** - `xtconstant.LATEST_PRICE`
- **指定价** - `xtconstant.FIX_PRICE`

### 市价类型（仅在实盘环境生效）
- **郑商所期货 市价最优价** - `xtconstant.MARKET_BEST`
- **市价最优价** - `xtconstant.MARKET_BEST`

### 大商所期货市价类型
- **市价即成剩撤** - `xtconstant.MARKET_CANCEL`
- **市价全额成交或撤** - `xtconstant.MARKET_CANCEL_ALL`

### 中金所期货市价类型
- **市价最优一档即成剩撤** - `xtconstant.MARKET_CANCEL_1`
- **市价最优五档即成剩撤** - `xtconstant.MARKET_CANCEL_5`
- **市价最优一档即成剩转** - `xtconstant.MARKET_CONVERT_1`
- **市价最优五档即成剩转** - `xtconstant.MARKET_CONVERT_5`

### 上交所/北交所股票市价类型
- **最优五档即时成交剩余撤销** - `xtconstant.MARKET_SH_CONVERT_5_CANCEL`
- **最优五档即时成交剩转限价** - `xtconstant.MARKET_SH_CONVERT_5_LIMIT`
- **对手方最优价格委托** - `xtconstant.MARKET_PEER_PRICE_FIRST`
- **本方最优价格委托** - `xtconstant.MARKET_MINE_PRICE_FIRST`

### 深交所股票期权市价类型
- **对手方最优价格委托** - `xtconstant.MARKET_PEER_PRICE_FIRST`
- **本方最优价格委托** - `xtconstant.MARKET_MINE_PRICE_FIRST`
- **即时成交剩余撤销委托** - `xtconstant.MARKET_SZ_INSTBUSI_RESTCANCEL`
- **最优五档即时成交剩余撤销** - `xtconstant.MARKET_SZ_CONVERT_5_CANCEL`
- **全额成交或撤销委托** - `xtconstant.MARKET_SZ_FULL_OR_CANCEL`

## 核心API接口

### 1. 创建API实例

```python
XtQuantTrader(path, session_id)
```

**释义**: 创建XtQuant API的实例

**参数**:
- `path` - str: MiniQMT客户端userdata_mini的完整路径
- `session_id` - int: 与MiniQMT通信的会话ID，不同的会话要保证不重复

**返回**: XtQuant API实例对象

**示例**:
```python
path = 'D:\\迅投极速交易终端 睿智融科版\\userdata_mini'
session_id = 123456
xt_trader = XtQuantTrader(path, session_id)
```

### 2. 注册回调类

```python
register_callback(callback)
```

**释义**: 将回调类实例对象注册到API实例中，用以消息回调和主推

**参数**:
- `callback` - XtQuantTraderCallback: 回调类实例对象

**示例**:
```python
class MyXtQuantTraderCallback(XtQuantTraderCallback):
    pass

callback = MyXtQuantTraderCallback()
xt_trader.register_callback(callback)
```

### 3. 准备API环境

```python
start()
```

**释义**: 启动交易线程，准备交易所需的环境

**示例**:
```python
xt_trader.start()
```

### 4. 创建连接

```python
connect()
```

**释义**: 连接MiniQMT

**返回**: 连接结果信息，连接成功返回0，失败返回非0

**备注**: 该连接为一次性连接，断开连接后不会重连，需要再次主动调用

**示例**:
```python
connect_result = xt_trader.connect()
print(connect_result)
```

### 5. 停止运行

```python
stop()
```

**释义**: 停止API接口

**示例**:
```python
xt_trader.stop()
```

### 6. 阻塞当前线程进入等待状态

```python
run_forever()
```

**释义**: 阻塞当前线程，进入等待状态，直到stop函数被调用结束阻塞

**示例**:
```python
xt_trader.run_forever()
```

### 7. 订阅账号信息

```python
subscribe(account)
```

**释义**: 订阅账号信息，包括资金账号、委托信息、成交信息、持仓信息

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 订阅结果信息，订阅成功返回0，订阅失败返回-1

**示例**:
```python
account = StockAccount('1000000365')
subscribe_result = xt_trader.subscribe(account)
```

### 8. 反订阅账号信息

```python
unsubscribe(account)
```

**释义**: 反订阅账号信息

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 反订阅结果信息，订阅成功返回0，订阅失败返回-1

**示例**:
```python
account = StockAccount('1000000365')
unsubscribe_result = xt_trader.unsubscribe(account)
```

### 9. 股票同步报单

```python
order_stock(account, stock_code, order_type, order_volume, price_type, price, strategy_name, remark)
```

**释义**: 股票同步报单

**参数**:
- `account` - StockAccount: 资金账号
- `stock_code` - str: 股票代码
- `order_type` - int: 委托类型，见数据字典委托类型(order_type)字段说明
- `order_volume` - int: 委托数量
- `price_type` - int: 报价类型，见数据字典报价类型(price_type)字段说明
- `price` - float: 委托价格，如果price_type为非指定价类型，此参数无效
- `strategy_name` - str: 策略名称
- `remark` - str: 备注

**返回**: 返回订单编号，如果为-1表示委托失败

**示例**:
```python
account = StockAccount('1000000365')
order_id = xt_trader.order_stock(account, '600000.SH', xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5, 'strategy_name', 'remark')
```

### 10. 股票异步报单

```python
order_stock_async(account, stock_code, order_type, order_volume, price_type, price, strategy_name, remark)
```

**释义**: 股票异步报单

**参数**: 同order_stock

**返回**: 返回下单请求序号，成功委托后的序号为大于0的正整数，如果为-1表示委托失败

**备注**: 如果失败，则通过委托失败主推接口返回委托失败信息

### 11. 股票同步撤单

```python
cancel_order_stock(account, order_id)
```

**释义**: 根据订单编号对委托进行撤单操作

**参数**:
- `account` - StockAccount: 资金账号
- `order_id` - int: 同步下单接口返回的订单编号，对于期货来说，是order结构中的order_sysid字段

**返回**: 返回是否成功发出撤单指令，0: 成功, -1: 表示撤单失败

**示例**:
```python
account = StockAccount('1000000365')
order_id = 100
cancel_result = xt_trader.cancel_order_stock(account, order_id)
```

### 12. 股票同步撤单（根据合同编号）

```python
cancel_order_stock_sysid(account, market, order_sysid)
```

**释义**: 根据券商柜台返回的合同编号对委托进行撤单操作

**参数**:
- `account` - StockAccount: 资金账号
- `market` - int: 交易市场
- `order_sysid` - str: 券商柜台的合同编号

**返回**: 返回是否成功发出撤单指令，0: 成功， -1: 表示撤单失败

**示例**:
```python
account = StockAccount('1000000365')
market = xtconstant.SH_MARKET
order_sysid = "100"
cancel_result = xt_trader.cancel_order_stock_sysid(account, market, order_sysid)
```

### 13. 股票异步撤单

```python
cancel_order_stock_async(account, order_id)
```

**释义**: 根据订单编号对委托进行异步撤单操作

**参数**:
- `account` - StockAccount: 资金账号
- `order_id` - int: 下单接口返回的订单编号，对于期货来说，是order结构中的order_sysid

**返回**: 返回撤单请求序号，成功委托后的撤单请求序号为大于0的正整数，如果为-1表示委托失败

**备注**: 如果失败，则通过撤单失败主推接口返回撤单失败信息

### 14. 股票异步撤单（根据合同编号）

```python
cancel_order_stock_sysid_async(account, market, order_sysid)
```

**释义**: 根据券商柜台返回的合同编号对委托进行异步撤单操作

**参数**:
- `account` - StockAccount: 资金账号
- `market` - int: 交易市场
- `order_sysid` - str: 券商柜台的合同编号

**返回**: 返回撤单请求序号，成功委托后的撤单请求序号为大于0的正整数，如果为-1表示委托失败

**备注**: 如果失败，则通过撤单失败主推接口返回撤单失败信息

### 15. 资金划拨

```python
fund_transfer(account, transfer_direction, price)
```

**释义**: 资金划拨

**参数**:
- `account` - StockAccount: 资金账号
- `transfer_direction` - int: 划拨方向，见数据字典划拨方向(transfer_direction)字段说明
- `price` - float: 划拨金额

**返回**: (success, msg)
- `success` - bool: 划拨操作是否成功
- `msg` - str: 反馈信息

### 16. 外部交易数据录入

```python
sync_transaction_from_external(operation, data_type, account, deal_list)
```

**释义**: 通用数据导出

**参数**:
- `operation` - str: 操作类型，有"UPDATE","REPLACE","ADD","DELETE"
- `data_type` - str: 数据类型，有"DEAL"
- `account` - StockAccount: 资金账号
- `deal_list` - list: 成交列表，每一项是Deal成交对象的参数字典，键名参考官网数据字典，大小写保持一致

**返回**: result - dict: 结果反馈信息

**示例**:
```python
deal_list = [
    {'m_strExchangeID':'SF', 'm_strInstrumentID':'ag2407',
     'm_strTradeID':'123456', 'm_strOrderSysID':'1234566',
     'm_dPrice':7600, 'm_nVolume':1,
     'm_strTradeDate': '20240627'}
]
resp = xt_trader.sync_transaction_from_external('ADD', 'DEAL', acc, deal_list)
print(resp)
# 成功输出示例：{'msg': 'sync transaction from external success'}
# 失败输出示例：{'error': {'msg': '[0-0: invalid operation type: ADDD], '}}
```

## 查询接口

### 17. 资产查询

```python
query_stock_asset(account)
```

**释义**: 查询资金账号对应的资产

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 该账号对应的资产对象XtAsset或者None

**备注**: 返回None表示查询失败

**示例**:
```python
account = StockAccount('1000000365')
asset = xt_trader.query_stock_asset(account)
```

### 18. 委托查询

```python
query_stock_orders(account, cancelable_only = False)
```

**释义**: 查询资金账号对应的当日所有委托

**参数**:
- `account` - StockAccount: 资金账号
- `cancelable_only` - bool: 仅查询可撤委托

**返回**: 该账号对应的当日所有委托对象XtOrder组成的list或者None

**备注**: None表示查询失败或者当日委托列表为空

**示例**:
```python
account = StockAccount('1000000365')
orders = xt_trader.query_stock_orders(account, False)
```

### 19. 成交查询

```python
query_stock_trades(account)
```

**释义**: 查询资金账号对应的当日所有成交

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 该账号对应的当日所有成交对象XtTrade组成的list或者None

**备注**: None表示查询失败或者当日成交列表为空

**示例**:
```python
account = StockAccount('1000000365')
trades = xt_trader.query_stock_trades(account)
```

### 20. 持仓查询

```python
query_stock_positions(account)
```

**释义**: 查询资金账号对应的持仓

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 该账号对应的最新持仓对象XtPosition组成的list或者None

**备注**: None表示查询失败或者当日持仓列表为空

**示例**:
```python
account = StockAccount('1000000365')
positions = xt_trader.query_stock_positions(account)
```

### 21. 期货持仓统计查询

```python
query_position_statistics(account)
```

**释义**: 查询期货账号的持仓统计

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 该账号对应的最新持仓对象XtPositionStatistics组成的list或者None

**备注**: None表示查询失败或者当日持仓列表为空

**示例**:
```python
account = StockAccount('1000000365', 'FUTURE')
positions = xt_trader.query_position_statistics(account)
```

### 22. 信用资产查询

```python
query_credit_detail(account)
```

**释义**: 查询信用资金账号对应的资产

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 该信用账户对应的资产对象XtCreditDetail组成的list或者None

**备注**: 
- 返回None表示查询失败
- 通常情况下一个资金账号只有一个详细信息数据

**示例**:
```python
account = StockAccount('1208970161', 'CREDIT')
datas = xt_trader.query_credit_detail(account)
```

### 23. 负债合约查询

```python
query_stk_compacts(account)
```

**释义**: 查询资金账号对应的负债合约

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 该账户对应的负债合约对象StkCompacts组成的list或者None

**备注**: None表示查询失败或者负债合约列表为空

**示例**:
```python
account = StockAccount('1208970161', 'CREDIT')
datas = xt_trader.query_stk_compacts(account)
```

### 24. 融资融券标的查询

```python
query_credit_subjects(account)
```

**释义**: 查询资金账号对应的融资融券标的

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 该账户对应的融资融券标的对象CreditSubjects组成的list或者None

**备注**: None表示查询失败或者融资融券标的列表为空

**示例**:
```python
account = StockAccount('1208970161', 'CREDIT')
datas = xt_trader.query_credit_subjects(account)
```

### 25. 可融券数据查询

```python
query_credit_slo_code(account)
```

**释义**: 查询资金账号对应的可融券数据

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 该账户对应的可融券数据对象CreditSloCode组成的list或者None

**备注**: None表示查询失败或者可融券数据列表为空

**示例**:
```python
account = StockAccount('1208970161', 'CREDIT')
datas = xt_trader.query_credit_slo_code(account)
```

### 26. 标的担保品查询

```python
query_credit_assure(account)
```

**释义**: 查询资金账号对应的标的担保品

**参数**:
- `account` - StockAccount: 资金账号

**返回**: 该账户对应的标的担保品对象CreditAssure组成的list或者None

**备注**: None表示查询失败或者标的担保品列表为空

**示例**:
```python
account = StockAccount('1208970161', 'CREDIT')
datas = xt_trader.query_credit_assure(account)
```

### 27. 新股申购额度查询

```python
query_new_purchase_limit(account)
```

**释义**: 查询资金账号对应的新股新债申购额度信息

**参数**:
- `account` - StockAccount: 资金账号

**返回**: dict: 新股新债信息数据集
- { stock1: info1, stock2: info2, ... }
- `stock` - str: 品种代码，例如 '301208.SZ'
- `info` - dict: 新股信息
  - `name` - str: 品种名称
  - `type` - str: 品种类型 STOCK - 股票，BOND - 债券
  - `minPurchaseNum` / `maxPurchaseNum` - int: 最小 / 最大申购额度 单位为股（股票）/ 张（债券）
  - `purchaseDate` - str: 申购日期
  - `issuePrice` - float: 发行价

**返回值示例**:
```python
{
    '754810.SH': {
        'name': '丰山发债', 
        'type': 'BOND', 
        'maxPurchaseNum': 10000, 
        'minPurchaseNum': 10, 
        'purchaseDate': '20220627', 
        'issuePrice': 100.0
    }, 
    '301208.SZ': {
        'name': '中亦科技', 
        'type': 'STOCK', 
        'maxPurchaseNum': 16500, 
        'minPurchaseNum': 500, 
        'purchaseDate': '20220627', 
        'issuePrice': 46.06
    }
}
```

### 28. 账号信息查询

```python
query_account_infos()
```

**释义**: 查询所有资金账号

**参数**: 无

**返回**: list: 账号信息列表 [XtAccountInfo]

### 29. 账号状态查询

```python
query_account_status()
```

**释义**: 查询所有账号状态

**参数**: 无

**返回**: list: 账号状态列表 [XtAccountStatus]

### 30. 普通柜台资金查询

```python
query_com_fund(account)
```

**释义**: 划拨业务查询普通柜台的资金

**参数**:
- `account` - StockAccount: 资金账号

**返回**: result - dict: 资金信息，包含以下字段
- `success` - bool
- `error` - str
- `currentBalance` - double: 当前余额
- `enableBalance` - double: 可用余额
- `fetchBalance` - double: 可取金额
- `interest` - double: 待入账利息
- `assetBalance` - double: 总资产
- `fetchCash` - double: 可取现金
- `marketValue` - double: 市值
- `debt` - double: 负债

### 31. 普通柜台持仓查询

```python
query_com_position(account)
```

**释义**: 划拨业务查询普通柜台的持仓

**参数**:
- `account` - StockAccount: 资金账号

**返回**: result - list: 持仓信息列表 [position1, position2, ...]
- `position` - dict: 持仓信息，包含以下字段
  - `success` - bool
  - `error` - str
  - `stockAccount` - str: 股东号
  - `exchangeType` - str: 交易市场
  - `stockCode` - str: 证券代码
  - `stockName` - str: 证券名称
  - `totalAmt` - float: 总量
  - `enableAmount` - float: 可用量
  - `lastPrice` - float: 最新价
  - `costPrice` - float: 成本价
  - `income` - float: 盈亏
  - `incomeRate` - float: 盈亏比例
  - `marketValue` - float: 市值
  - `costBalance` - float: 成本总额
  - `bsOnTheWayVol` - int: 买卖在途量
  - `prEnableVol` - int: 申赎可用量

### 32. 通用数据导出

```python
export_data(account, result_path, data_type, start_time = None, end_time = None, user_param = {})
```

**释义**: 通用数据导出

**参数**:
- `account` - StockAccount: 资金账号
- `result_path` - str: 导出路径，包含文件名及.csv后缀，如'C:\Users\Desktop\test\deal.csv'
- `data_type` - str: 数据类型，如'deal'
- `start_time` - str: 开始时间（可缺省）
- `end_time` - str: 结束时间（可缺省）
- `user_param` - dict: 用户参数（可缺省）

**返回**: result - dict: 结果反馈信息

**示例**:
```python
resp = xt_trader.export_data(acc, 'C:\\Users\\Desktop\\test\\deal.csv', 'deal')
print(resp)
# 成功输出示例：{'msg': 'export success'}
# 失败输出示例：{'error': {'errorMsg': 'can not find account info, accountID:2000449 accountType:2'}}
```

### 33. 通用数据查询

```python
query_data(account, result_path, data_type, start_time = None, end_time = None, user_param = {})
```

**释义**: 通用数据查询，利用export_data接口导出数据后再读取其中的数据内容，读取完毕后删除导出的文件

**参数**: 同export_data

**返回**: result - dict: 数据信息

**示例**:
```python
data = xt_trader.query_data(acc, 'C:\\Users\\Desktop\\test\\deal.csv', 'deal')
print(data)
```

## 回调接口

### XtQuantTraderCallback 回调方法

#### 连接状态回调
```python
def on_disconnected(self):
    """ 连接断开 :return: """
    print("connection lost")
```

#### 账号状态信息推送
```python
def on_account_status(self, status):
    """ 账号状态信息变动推送 :param data: XtAccountStatus 对象 :return: """
    print("on_account_status")
    print(status.account_id, status.account_type, status.status)
```

#### 委托信息推送
```python
def on_stock_order(self, order):
    """ 委托信息变动推送，例如已成交数量，委托状态变化等 :param data: XtOrder 对象 :return: """
    print("on order callback:")
    print(order.stock_code, order.order_status, order.order_sysid)
```

#### 成交信息推送
```python
def on_stock_trade(self, trade):
    """ 成交信息变动推送 :param data: XtTrade 对象 :return: """
    print("on trade callback")
    print(trade.account_id, trade.stock_code, trade.order_id)
```

#### 下单失败信息推送
```python
def on_order_error(self, order_error):
    """ 下单失败信息推送 :param data: XtOrderError 对象 :return: """
    print("on order_error callback")
    print(order_error.order_id, order_error.error_id, order_error.error_msg)
```

#### 撤单失败信息推送
```python
def on_cancel_error(self, cancel_error):
    """ 撤单失败信息的推送 :param data: XtCancelError 对象 :return: """
    print("on cancel_error callback")
    print(cancel_error.order_id, cancel_error.error_id, cancel_error.error_msg)
```

#### 异步下单回报推送
```python
def on_order_stock_async_response(self, response):
    """ 异步下单回报推送 :param data: XtOrderResponse 对象 :return: """
    print("on_order_stock_async_response")
    print(response.account_id, response.order_id, response.seq)
```

#### 约券相关异步接口的回报推送
```python
def on_smt_appointment_async_response(self, response):
    """ :param response: XtAppointmentResponse 对象 :return: """
    print("on_smt_appointment_async_response")
    print(response.account_id, response.order_sysid, response.error_id, response.error_msg, response.seq)
```

## 注意事项

1. **市价类型限制**: 市价类型只在实盘环境中生效，模拟环境不支持市价方式报单
2. **会话ID管理**: 不同的Python策略需要使用不同的会话编号
3. **连接管理**: 该连接为一次性连接，断开连接后不会重连，需要再次主动调用
4. **异步查询**: 推荐在推送回调中使用查询接口的异步版本
5. **数据字典**: 详细的数据结构定义请参考官方数据字典

## 相关链接

- [数据字典](http://dict.thinktrader.net/nativeApi/xttrader.html)
- [枚举常量](https://dict.thinktrader.net/innerApi/enum_constants.html)
- [XtQuant.XtData 行情模块](http://dict.thinktrader.net/nativeApi/xttrader.html)

---
*文档基于XT交易API官方文档整理，请以最新API文档为准*
