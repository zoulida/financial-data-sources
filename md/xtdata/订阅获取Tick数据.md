## Tick 数据订阅指南

本指南基于 `订阅获取Tick数据.py`，总结如何通过 `xtquant.xtdata` 订阅实时 Tick 行情。

### 1. 核心流程

1. **定义回调**：`on_tick_data(datas)` 会在每次推送时收到一个 `stock_code -> tick_data` 的字典，可在回调里解析 `lastPrice`、`lastClose` 等字段并做自定义处理。
2. **创建订阅管理类**：`SubscribeTickData` 维护一个 `subscription_id`，负责订阅和取消订阅，避免重复订阅导致的资源占用。
3. **订阅**：调用 `xtdata.subscribe_whole_quote(code_list, callback)`，传入股票代码列表和回调函数，返回的订阅 ID 被保存以便后续取消。
4. **取消订阅**：使用 `xtdata.unsubscribe_quote(subscription_id)` 释放订阅，防止遗留后台推送。

### 2. 关键代码片段

```25:63:source/实盘/xuntou/datadownload/订阅获取Tick数据.py
class SubscribeTickData:
    def __init__(self):
        self.subscription_id = None
    def subscribe_stock_quotes(self, stock_codes, callback=on_tick_data):
        if self.subscription_id is not None:
            xtdata.unsubscribe_quote(self.subscription_id)
        self.subscription_id = xtdata.subscribe_whole_quote(
            code_list=stock_codes,
            callback=callback
        )
```

```65:77:source/实盘/xuntou/datadownload/订阅获取Tick数据.py
    def unsubscribe_stock_quotes(self):
        if self.subscription_id is not None:
            xtdata.unsubscribe_quote(self.subscription_id)
            self.subscription_id = None
```

### 3. 快速开始

1. 确保 `xtquant` 环境配置完毕，可正常连接券商行情源。
2. 在脚本入口处创建实例并传入待订阅的证券代码：
   ```python
   subscribe_tick_data = SubscribeTickData()
   subscribe_tick_data.subscribe_stock_quotes(["600519.SH"])
   time.sleep(10)  # 保持订阅一段时间以接收推送
   subscribe_tick_data.unsubscribe_stock_quotes()
   ```
3. 根据需要修改回调函数，将 Tick 数据写入日志、数据库或驱动交易策略。

### 4. 使用建议

- 若需要多实例并行订阅，考虑封装成单例或使用股票池拆分订阅，避免重复订阅同一标的。
- 回调中需加异常保护，防止单次异常导致订阅崩溃。
- 长时间运行时建议增加心跳与重订阅策略，确保网络抖动后能自动恢复。

通过上述流程即可快速集成 Tick 行情订阅，为实盘交易或实时监控提供数据支撑。

