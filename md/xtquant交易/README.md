# XtQuant 基础交易类

基于迅投XtQuant API文档创建的统一交易接口，提供便捷的股票交易功能。

## 文件说明

- `base_trader.py` - 基础交易类，封装了常用的交易接口
- `demo.py` - 使用示例，演示各种交易功能
- `README.md` - 说明文档

## 快速开始

### 1. 创建交易实例

```python
from base_trader import BaseTrader, BaseTraderCallback

# 创建交易实例
trader = BaseTrader(
    path=r'D:\国金证券QMT交易端\userdata_mini',
    account='8886063599',
    session_id=123456
)
```

### 2. 连接和订阅

```python
# 连接交易系统
if trader.connect() == 0:
    print("连接成功")
    
    # 注册回调
    callback = BaseTraderCallback()
    trader.register_callback(callback)
    
    # 订阅账号信息
    trader.subscribe()
```

### 3. 交易操作

```python
# 买入股票
order_id = trader.buy('512710.SH', 100, 0.661)

# 卖出股票
order_id = trader.sell('512710.SH', 100, 0.670)

# 撤销委托
trader.cancel_order(order_id)
```

### 4. 查询操作

```python
# 查询资产
asset = trader.get_asset()
print(f"可用资金: {asset['cash']}")

# 查询持仓
positions = trader.get_positions()

# 查询委托
orders = trader.get_orders()

# 查询成交
trades = trader.get_trades()
```

## 主要功能

### 交易功能
- **买入股票** - `buy()` 同步买入
- **卖出股票** - `sell()` 同步卖出  
- **异步下单** - `buy_async()` 异步买入
- **撤销委托** - `cancel_order()` 撤单

### 查询功能
- **查询资产** - `get_asset()` 获取资金信息
- **查询持仓** - `get_positions()` 获取所有持仓
- **查询单只持仓** - `get_position()` 获取指定股票持仓
- **查询委托** - `get_orders()` 获取当日委托
- **查询单笔委托** - `get_order()` 获取指定委托信息
- **查询成交** - `get_trades()` 获取当日成交

### 回调功能
- **连接状态** - `on_disconnected()` 连接断开
- **委托推送** - `on_stock_order()` 委托状态变化
- **成交推送** - `on_stock_trade()` 成交回报
- **错误推送** - `on_order_error()` 委托失败
- **撤单失败** - `on_cancel_error()` 撤单失败

## 运行示例

```bash
# 运行demo
python demo.py
```

demo提供4种演示模式：
1. 完整功能演示 - 展示所有功能
2. 简单交易演示 - 基础交易操作
3. 持仓管理演示 - 持仓查询和管理
4. 委托管理演示 - 委托查询和管理

## 注意事项

1. **参数配置** - 请确保path和account参数正确
2. **会话ID** - 不同策略使用不同的session_id
3. **交易风险** - demo中的交易代码已注释，避免误操作
4. **连接管理** - 程序结束时调用`stop()`停止交易线程
5. **错误处理** - 所有接口都有错误检查和日志输出

## API参考

### BaseTrader 类

#### 初始化
```python
BaseTrader(path, account, session_id=123456)
```

#### 连接相关
- `connect()` - 连接交易系统
- `subscribe()` - 订阅账号信息
- `register_callback()` - 注册回调
- `stop()` - 停止交易
- `run_forever()` - 阻塞接收推送

#### 交易相关
- `buy(stock_code, volume, price)` - 买入
- `sell(stock_code, volume, price)` - 卖出
- `buy_async(stock_code, volume, price)` - 异步买入
- `cancel_order(order_id)` - 撤单

#### 查询相关
- `get_asset()` - 查询资产
- `get_positions()` - 查询持仓
- `get_position(stock_code)` - 查询单只持仓
- `get_orders()` - 查询委托
- `get_order(order_id)` - 查询单笔委托
- `get_trades()` - 查询成交

### BaseTraderCallback 类

#### 回调方法
- `on_disconnected()` - 连接断开
- `on_stock_order(order)` - 委托推送
- `on_stock_trade(trade)` - 成交推送
- `on_order_error(order_error)` - 委托失败
- `on_cancel_error(cancel_error)` - 撤单失败
- `on_order_stock_async_response(response)` - 异步下单回报
- `on_account_status(status)` - 账号状态

## 常量说明

使用 `xtconstant` 模块中的常量：

- `xtconstant.STOCK_BUY` - 买入
- `xtconstant.STOCK_SELL` - 卖出
- `xtconstant.FIX_PRICE` - 限价
- 其他价格类型请参考XtQuant文档

## 错误码

- 连接/订阅/交易返回 0 表示成功
- 买入/卖出返回 >0 表示订单ID，-1 表示失败
- 撤单返回 0 表示成功

## 许可证

本项目基于迅投XtQuant API开发，请遵守相关使用条款。
