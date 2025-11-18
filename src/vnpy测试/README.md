# vnpy 金叉死叉策略示例

这个目录包含了vnpy策略开发的完整示例，包括数据导入和策略回测。

## 文件说明

### 1. `generate_random_bars.py` - 随机K线数据生成器

**功能**：生成随机K线数据并导入到vnpy数据库

**使用方法**：
```bash
python generate_random_bars.py
```

**主要功能**：
- 生成指定天数的随机K线数据（OHLCV）
- 支持自定义合约代码、交易所、基础价格、波动率等参数
- 自动导入数据到vnpy的SQLite数据库
- 显示数据生成和导入的详细信息

**配置参数**（可在代码中修改）：
- `symbol`: 合约代码（默认：`rb2405`）
- `exchange`: 交易所（默认：`Exchange.SHFE`）
- `start_date`: 起始日期（默认：`2023-01-01`）
- `days`: 生成天数（默认：`365`）
- `base_price`: 基础价格（默认：`3500.0`）
- `volatility`: 日波动率（默认：`0.015`，即1.5%）

### 2. `golden_cross_demo.py` - 金叉死叉策略回测

**功能**：基于移动平均线交叉的CTA策略回测

**策略逻辑**：
- **金叉**：当快线（5日均线）向上穿越慢线（20日均线）时做多
- **死叉**：当快线向下穿越慢线时做空

**使用方法**：
```bash
python golden_cross_demo.py
```

**策略参数**（可在代码中修改）：
- `fast_window`: 快线周期（默认：`5`）
- `slow_window`: 慢线周期（默认：`20`）
- `fixed_size`: 每次交易数量（默认：`1`）

**回测参数**（可在代码中修改）：
- `vt_symbol`: 合约代码（默认：`rb2405.SHFE`）
- `start`: 回测起始日期（默认：`datetime(2023, 1, 1)`）
- `end`: 回测结束日期（默认：`datetime(2024, 12, 31)`）
- `capital`: 初始资金（默认：`1,000,000`）
- `rate`: 手续费率（默认：`1/10000`）
- `slippage`: 滑点（默认：`1`）

## 使用流程

### 第一步：生成并导入测试数据

```bash
python generate_random_bars.py
```

输出示例：
```
============================================================
随机K线数据生成和导入示例
============================================================

配置参数:
  合约代码: rb2405
  交易所: SHFE
  起始日期: 2023-01-01
  生成天数: 365
  基础价格: 3500.0
  波动率: 1.50%

正在生成随机K线数据...
✓ 成功生成 365 条K线数据

正在导入 365 条K线数据到数据库...
✓ 成功导入 365 条数据
```

### 第二步：运行策略回测

```bash
python golden_cross_demo.py
```

输出示例：
```
正在加载历史数据...
[成功] 成功加载 361 条历史数据

开始运行回测...

计算回测统计指标...

============================================================
回测统计结果:
============================================================
  total_return            :      0.53%
  annual_return           :      0.35%
  max_ddpercent           :     -0.89%
  total_trade_count       :     27.00
  sharpe_ratio            :     53.56%
  total_net_pnl           :   5270.15
```

## 数据导入原理

### vnpy数据库结构

vnpy使用SQLite数据库存储K线数据，通过`vnpy.trader.database`模块访问。

### 导入步骤

1. **获取数据库实例**：
   ```python
   from vnpy.trader.database import get_database
   database = get_database()
   ```

2. **创建BarData对象**：
   ```python
   from vnpy_ctastrategy import BarData
   from vnpy.trader.constant import Interval, Exchange
   
   bar = BarData(
       symbol="rb2405",
       exchange=Exchange.SHFE,
       datetime=datetime(2023, 1, 1, 15, 0, 0),
       interval=Interval.DAILY,
       volume=10000,
       open_price=3500.0,
       high_price=3520.0,
       low_price=3480.0,
       close_price=3510.0,
       turnover=35100000.0,
       open_interest=0,
       gateway_name="DEMO",
   )
   ```

3. **保存到数据库**：
   ```python
   database.save_bar_data([bar1, bar2, ...])
   ```

## 注意事项

1. **数据格式要求**：
   - `datetime`必须是交易日的收盘时间（通常为15:00）
   - `high_price >= max(open_price, close_price)`
   - `low_price <= min(open_price, close_price)`
   - `volume`和`turnover`必须为正数

2. **合约代码格式**：
   - 数据库中使用格式：`symbol.exchange`（如：`rb2405.SHFE`）
   - 回测时使用`vt_symbol`参数

3. **数据覆盖**：
   - 如果数据库中已存在相同合约、相同日期的数据，新数据会覆盖旧数据

4. **性能考虑**：
   - 批量导入数据时，建议一次性导入所有数据，而不是逐条导入

## 扩展使用

### 从其他数据源导入

如果你有来自其他数据源（如XtQuant、Wind等）的数据，可以：

1. 将数据转换为`BarData`对象列表
2. 使用`database.save_bar_data()`导入

示例：
```python
# 假设你从XtQuant获取了数据
import pandas as pd
from xtquant import xtdata

# 获取数据
data = xtdata.get_market_data_ex(...)
df = pd.DataFrame(data['close'].T)

# 转换为BarData
bars = []
for date, row in df.iterrows():
    bar = BarData(
        symbol="000001.SZ",
        exchange=Exchange.SZSE,
        datetime=date,
        interval=Interval.DAILY,
        # ... 其他字段
    )
    bars.append(bar)

# 导入数据库
database.save_bar_data(bars)
```

## 故障排除

### 问题1：数据库中没有数据

**解决方案**：
- 先运行`generate_random_bars.py`生成测试数据
- 检查`vt_symbol`格式是否正确（如：`rb2405.SHFE`）
- 检查日期范围是否匹配

### 问题2：回测结果为空

**可能原因**：
- 数据量不足（策略需要至少`slow_window + 50`条数据）
- 策略参数设置不当
- 数据时间范围问题

**解决方案**：
- 增加生成数据的天数
- 调整策略参数（如减小`slow_window`）
- 检查数据的时间范围

### 问题3：导入数据失败

**可能原因**：
- 数据库连接问题
- 数据格式不正确

**解决方案**：
- 检查是否安装了`vnpy-sqlite`
- 验证`BarData`对象的字段是否完整和正确

## 相关资源

- [vnpy官方文档](https://www.vnpy.com/)
- [vnpy_ctastrategy文档](https://github.com/vnpy/vnpy_ctastrategy)

