# Backtrader 实盘交易系统

基于 Backtrader 和 XtQuant 实现的实盘交易系统。

## 功能特点

- ✅ 基于 Backtrader 框架，支持策略开发
- ✅ 集成 XtQuant 交易接口，支持实盘交易
- ✅ 支持成交回调，策略可以实时接收成交通知
- ✅ 自动处理订单状态更新
- ✅ 支持限价单和市价单

## 项目结构

```
backtrader实盘交易/
├── main.py                  # 主程序入口
├── xtquant_broker.py        # XtQuant Broker 实现
├── simple_buy_strategy.py   # 简单买入策略示例
├── xttrader_base.py         # XtQuant 交易基础类
└── README.md                # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
# 方式1：使用项目 requirements.txt
pip install -r requirements.txt

# 方式2：手动安装
pip install backtrader>=1.9.78
pip install xtquant
```

### 2. 配置参数

编辑 `main.py`，修改以下配置：

```python
# 交易账号配置
ACCOUNT_ID = "8886063599"  # 您的账号
ACCOUNT_TYPE = "STOCK"  # 账号类型
QMT_PATH = r"D:\国金证券QMT交易端\userdata_mini"  # QMT 路径

# 策略参数
STOCK_CODE = "159100.SZ"  # 目标股票
BUY_VOLUME = 100  # 买入数量（1手=100股）
```

### 3. 运行策略

```bash
python main.py
```

## 策略说明

### SimpleBuyStrategy

简单买入策略，功能：
- 买入指定股票（默认：159100.SZ）
- 买入数量：1手=100股
- 买入后持有，不卖出
- 实时接收成交回调并打印成交信息

### 策略参数

- `stock_code`: 股票代码，默认 '159100.SZ'
- `buy_volume`: 买入数量，默认 100 股

## Broker 说明

### XtQuantBroker

XtQuant Broker 实现了 Backtrader 的 Broker 接口，主要功能：

1. **订单提交**：将 Backtrader 的订单转换为 XtQuant 的委托
2. **订单管理**：维护订单映射关系
3. **成交回调**：接收 XtQuant 的成交回调，转换为策略事件
4. **资金查询**：实时查询可用资金和总资产
5. **持仓查询**：查询当前持仓信息

### Broker 参数

- `account_id`: 交易账号
- `account_type`: 账号类型（STOCK/CREDIT/FUTURES）
- `path`: QMT 客户端路径
- `session`: 会话ID（0表示自动生成）
- `commission`: 佣金费率，默认 0.0003 (0.03%)
- `slippage`: 滑点，默认 0.0

## 成交回调机制

策略通过以下方式接收成交通知：

1. **Broker 接收回调**：XtQuant 的成交回调被 `XtQuantBroker._on_trade_callback` 接收
2. **事件队列**：成交信息被放入 `_trade_queue` 队列
3. **策略处理**：策略在 `next()` 方法中调用 `broker.get_trade_events()` 获取成交事件
4. **打印成交**：策略的 `_on_trade()` 方法处理成交事件并打印

### 成交事件格式

```python
{
    'order': backtrader_order,      # Backtrader 订单对象
    'trade': xt_trade,              # XtTrade 对象
    'stock_code': '159100.SZ',      # 股票代码
    'price': 1.23,                  # 成交价格
    'volume': 100,                  # 成交数量
    'time': '20250101 093000'       # 成交时间
}
```

## 使用示例

### 基本使用

```python
from xtquant_broker import XtQuantBroker
from simple_buy_strategy import SimpleBuyStrategy
import backtrader as bt

# 创建 Cerebro
cerebro = bt.Cerebro()

# 创建 Broker
broker = XtQuantBroker(
    account_id="8886063599",
    account_type="STOCK",
    path=r"D:\国金证券QMT交易端\userdata_mini"
)
cerebro.setbroker(broker)

# 添加数据源
data = create_data_feed("159100.SZ")
cerebro.adddata(data)

# 添加策略
cerebro.addstrategy(SimpleBuyStrategy, stock_code="159100.SZ", buy_volume=100)

# 运行策略
cerebro.run()
```

### 自定义策略

```python
class MyStrategy(bt.Strategy):
    def __init__(self):
        self.order = None
    
    def next(self):
        # 检查成交事件
        broker = self.broker
        if hasattr(broker, 'get_trade_events'):
            trade_events = broker.get_trade_events()
            for event in trade_events:
                self._on_trade(event)
        
        # 策略逻辑
        if not self.position:
            self.order = self.buy(size=100)
    
    def _on_trade(self, trade_event):
        """处理成交事件"""
        print(f"成交: {trade_event['stock_code']}, "
              f"价格: {trade_event['price']}, "
              f"数量: {trade_event['volume']}")
```

## 注意事项

1. **QMT 客户端**：运行前请确保 QMT 客户端已启动并登录
2. **账号配置**：请根据实际情况修改账号信息
3. **数据获取**：策略需要历史数据，确保 XtQuant 可以获取到数据
4. **订单数量**：A股最小交易单位为100股（1手），系统会自动调整
5. **成交回调**：成交回调是异步的，策略需要在 `next()` 中主动检查

## 故障排除

### 连接失败

- 检查 QMT 客户端是否已启动并登录
- 检查 `QMT_PATH` 路径是否正确
- 检查账号信息是否正确

### 数据获取失败

- 检查股票代码格式是否正确（例如：159100.SZ）
- 检查网络连接
- 检查 XtQuant 是否正常初始化

### 订单提交失败

- 检查可用资金是否充足
- 检查股票代码是否正确
- 检查交易时间（非交易时间无法下单）

## 参考文档

- [Backtrader 官方文档](https://www.backtrader.com/)
- [XtQuant 官方文档](http://dict.thinktrader.net/nativeApi/xtdata.html?id=nOY9mc)

## 许可证

本项目仅供学习和研究使用。

