# OpenTDX 测试与使用说明

## 一、项目定位

`opentdx` 是一个 Python 版通达信 TDX 行情数据客户端，提供 A 股、指数、板块、港股、美股、期货等行情接口。

它适合用作当前项目中的辅助数据源，重点用于：

- **实时行情**：A 股、指数、港股、美股报价。
- **K 线数据**：日线、分钟线、周线等。
- **分时与逐笔**：个股分时图、逐笔成交、集合竞价。
- **市场异动**：涨停、跌停、拉升、封单等异动信息。
- **板块数据**：行业板块、概念板块、地区板块、板块成分股行情。
- **资金流向**：个股当日和 5 日主力/散户资金流入流出。
- **主力监控**：通达信 MAC 协议增强版市场监控数据。

## 二、环境检查

本次测试环境：

| 项目 | 结果 |
|---|---|
| Python | `3.12.6` |
| pandas | `2.3.3` |
| numpy | `2.3.3` |
| click | `8.3.0` |
| 项目版本 | `opentdx 0.2.4` |
| Python 要求 | `>=3.12` |

依赖来自 `pyproject.toml`：

```text
pandas
numpy
click
```

## 三、功能测试结论

测试时间：2026-05-23 07:34 左右。

测试方式：直接在 `md/通达信/opentdx-main` 目录内使用源码运行，不安装到全局环境。

测试结果文件：

```text
opentdx_功能测试结果.json
```

核心结论：**17 项核心功能全部测试成功**。

| 功能 | 测试结果 | 返回数量 | 样例字段 |
|---|---:|---:|---|
| 服务器信息 | 成功 | 15 | `today`, `sessions_1`, `last_trading_day` |
| 深市股票数量 | 成功 | - | 返回整数 |
| 深市股票列表 | 成功 | 5 | `code`, `name`, `vol`, `pre_close` |
| A 股实时报价 | 成功 | 2 | `market`, `code`, `close`, `open`, `high`, `low`, `amount` |
| A 股日 K 线 | 成功 | 5 | `datetime`, `open`, `high`, `low`, `close`, `vol`, `amount` |
| 指数信息 | 成功 | 2 | `market`, `code`, `close`, `up_count`, `down_count` |
| 个股分时 | 成功 | 5 | `time`, `price`, `avg`, `vol`, `momentum` |
| 逐笔成交 | 成功 | 5 | `time`, `price`, `vol`, `trade_count`, `bs_flag` |
| 集合竞价 | 成功 | 5 | `time`, `price`, `matched`, `unmatched` |
| 市场异动 | 成功 | 5 | `code`, `time`, `desc`, `value`, `unusual_type` |
| 概念板块列表 | 成功 | 5 | `code`, `name`, `price`, `rise_speed` |
| 板块成分行情 | 成功 | 5 | `code`, `name`, `close`, `vol`, `amount`, `turnover_rate` |
| 个股所属板块 | 成功 | 3 | `data`, `query_info`, `ext` |
| 个股资金流向 | 成功 | 3 | `data`, `query_info`, `ext` |
| 主力监控 | 成功 | 5 | `code`, `time`, `desc`, `value`, `unusual_type` |
| 美股 K 线 | 成功 | 3 | `datetime`, `open`, `high`, `low`, `close`, `vol` |
| 港美股报价 | 成功 | 2 | `market`, `code`, `close`, `open`, `high`, `low`, `vol` |

## 四、命令行使用方式

在项目目录执行：

```powershell
python -m opentdx.cli --help
```

常用命令示例：

```powershell
python -m opentdx.cli kline SZ 000001 --period DAILY --count 10
python -m opentdx.cli quote "SZ 000001, SH 600519" --json
python -m opentdx.cli index "SH 999999, SZ 399001" --json
python -m opentdx.cli stock-list SZ --count 20
python -m opentdx.cli unusual SZ --count 20
python -m opentdx.cli transaction SZ 000001 --count 50
python -m opentdx.cli tick SZ 000001
python -m opentdx.cli auction SZ 000001
```

板块和主力监控：

```powershell
python -m opentdx.cli board GN --count 10
python -m opentdx.cli board HY --count 10
python -m opentdx.cli board-members 881001 --count 20
python -m opentdx.cli monitor SZ --count 20
```

港股、美股、期货等扩展市场：

```powershell
python -m opentdx.cli g-kline US_STOCK TSLA --period DAILY --count 10
python -m opentdx.cli g-kline HK_MAIN_BOARD 00700 --period DAILY --count 10
python -m opentdx.cli g-quote "US_STOCK TSLA, HK_MAIN_BOARD 00700" --json
```

如果通过 `pip install -e .` 安装为可编辑包，也可以直接使用：

```powershell
opentdx kline SZ 000001 --period DAILY --count 10
opentdx quote "SZ 000001, SH 600519"
```

## 五、Python 调用示例

推荐使用统一入口 `TdxClient`。

```python
import pandas as pd
from opentdx.tdxClient import TdxClient
from opentdx.const import MARKET, PERIOD, ADJUST, BOARD_TYPE, EX_MARKET

with TdxClient() as client:
    kline = client.stock_kline(MARKET.SZ, "000001", PERIOD.DAILY, count=20, adjust=ADJUST.NONE)
    quotes = client.stock_quotes([(MARKET.SZ, "000001"), (MARKET.SH, "600519")])
    boards = client.stock_board_list(BOARD_TYPE.GN, count=20)
    members = client.stock_board_members("881001", count=50)
    flow = client.stock_capital_flow(MARKET.SZ, "000001")
    monitor = client.stock_market_monitor(MARKET.SZ, count=20)
    us_kline = client.goods_kline(EX_MARKET.US_STOCK, "TSLA", PERIOD.DAILY, count=10)

print(pd.DataFrame(kline).head())
print(pd.DataFrame(quotes).head())
```

## 六、重要接口清单

### 1. A 股行情

| 方法 | 用途 |
|---|---|
| `stock_count(MARKET.SZ)` | 获取市场股票数量 |
| `stock_list(MARKET.SZ, count=20)` | 获取股票列表 |
| `stock_quotes(...)` | 获取 A 股实时报价 |
| `stock_quotes_detail(...)` | 获取详细报价和盘口 |
| `stock_kline(...)` | 获取 K 线 |
| `index_info(...)` | 获取指数信息 |

### 2. 分时、逐笔、竞价

| 方法 | 用途 |
|---|---|
| `stock_tick_chart(...)` | 个股分时图 |
| `stock_tick_charts(...)` | 多日分时图 |
| `stock_transaction(...)` | 逐笔成交 |
| `stock_auction(...)` | 集合竞价 |
| `stock_history_orders(...)` | 历史委托分布 |

### 3. 异动、板块、资金流

| 方法 | 用途 |
|---|---|
| `stock_unusual(...)` | 市场异动数据 |
| `stock_board_list(...)` | 板块列表 |
| `stock_board_members(...)` | 板块成分股行情 |
| `stock_board_top_members(...)` | 板块活跃成分股 |
| `stock_belong_board(...)` | 查询个股所属板块 |
| `stock_capital_flow(...)` | 个股资金流向 |
| `stock_market_monitor(...)` | 主力监控 |

### 4. 扩展市场

| 方法 | 用途 |
|---|---|
| `goods_count()` | 扩展市场商品数量 |
| `goods_category_list()` | 商品分类列表 |
| `goods_list()` | 商品列表 |
| `goods_varieties(...)` | 期货/期权合约品种 |
| `goods_quotes(...)` | 港股、美股、期货报价 |
| `goods_kline(...)` | 港股、美股、期货 K 线 |
| `goods_tick_chart(...)` | 扩展市场分时 |

## 七、适合接入当前项目的方向

### 1. 热门板块和概念炒作阶段识别

可用数据：

- `stock_board_list(BOARD_TYPE.GN)`：概念板块列表。
- `stock_board_list(BOARD_TYPE.HY)`：行业板块列表。
- `stock_board_members(board_symbol)`：板块成分股行情。
- `stock_market_monitor(MARKET.SZ/SH/BJ)`：市场异动。
- `stock_capital_flow(market, code)`：资金流向。
- `stock_belong_board(market, code)`：个股所属板块。

可构造特征：

- 板块涨幅。
- 板块涨速。
- 板块成交额。
- 板块内涨停数量。
- 板块内异动数量。
- 龙头股涨幅。
- 主力资金净流入。
- 成分股同步上涨比例。

### 2. 短线情绪监控

可用数据：

- `stock_unusual`：异动事件。
- `stock_market_monitor`：主力监控。
- `stock_quotes`：实时报价。
- `stock_tick_chart`：分时走势。
- `stock_auction`：集合竞价。

适合做：

- 涨停/跌停监控。
- 拉升/跳水监控。
- 封单监控。
- 板块联动监控。
- 竞价强弱监控。

### 3. 多因子和主升浪辅助因子

可补充因子：

- 资金流入强度。
- 异动频率。
- 板块热度。
- 所属概念数量。
- 分时动量。
- 涨速。
- 成交活跃度。

## 八、注意事项

### 1. 项目成熟度

`pyproject.toml` 标记为：

```text
Development Status :: 3 - Alpha
```

说明项目仍处于早期阶段，接口和字段可能变化。

### 2. 数据稳定性

通达信协议类数据源通常依赖外部服务器，可能出现：

- 连接超时。
- 服务器限流。
- 个别接口临时失效。
- 字段含义变化。
- 非交易时段返回数据不完整。

### 3. 回测数据建议

不建议把 `opentdx` 作为严肃历史回测的唯一数据源。更合适的定位是：

- 实时监控。
- 辅助行情。
- 板块/概念补充。
- 资金流和异动信号。
- 策略过滤条件。

历史回测仍建议以 Qlib、本地标准化行情、Wind 或其他稳定数据源为主。

### 4. 字段返回格式

部分接口返回 `dict`，其中真正的数据在 `data` 字段里，例如：

- `stock_belong_board`
- `stock_capital_flow`

使用时需要先查看返回结构，再做统一封装。

## 九、建议封装方式

建议不要在策略代码里直接大量调用 `opentdx` 原始接口，而是在当前项目中建立一层适配器，例如：

```text
src/数据源/opentdx_adapter.py
```

适配器负责：

- 统一市场代码。
- 统一字段名称。
- 处理连接失败。
- 控制请求频率。
- 缓存板块成分。
- 将返回值转换为 `DataFrame`。
- 与 Qlib / XtQuant / Wind 的代码体系对齐。

## 十、本次测试执行的核心代码逻辑

测试脚本主要调用：

```python
from opentdx.tdxClient import TdxClient
from opentdx.const import MARKET, PERIOD, ADJUST, BOARD_TYPE, EX_MARKET

with TdxClient() as c:
    c.server_info()
    c.stock_count(MARKET.SZ)
    c.stock_list(MARKET.SZ, count=5)
    c.stock_quotes([(MARKET.SZ, "000001"), (MARKET.SH, "600519")])
    c.stock_kline(MARKET.SZ, "000001", PERIOD.DAILY, count=5, adjust=ADJUST.NONE)
    c.index_info([(MARKET.SH, "999999"), (MARKET.SZ, "399001")])
    c.stock_tick_chart(MARKET.SZ, "000001")[:5]
    c.stock_transaction(MARKET.SZ, "000001")[:5]
    c.stock_auction(MARKET.SZ, "000001")[:5]
    c.stock_unusual(MARKET.SZ, count=5)
    c.stock_board_list(BOARD_TYPE.GN, count=5)
    c.stock_board_members("881001", count=5)
    c.stock_belong_board(MARKET.SZ, "000001")
    c.stock_capital_flow(MARKET.SZ, "000001")
    c.stock_market_monitor(MARKET.SZ, count=5)
    c.goods_kline(EX_MARKET.US_STOCK, "TSLA", PERIOD.DAILY, count=3)
    c.goods_quotes([(EX_MARKET.US_STOCK, "TSLA"), (EX_MARKET.HK_MAIN_BOARD, "00700")])
```

## 十一、结论

`opentdx` 在当前环境下可以正常运行，核心行情、K 线、分时、逐笔、竞价、异动、板块、资金流向、主力监控、港美股扩展市场等功能均通过测试。

对当前项目而言，它最适合作为 **通达信特色实时数据源** 使用，尤其适合补充：

- 热门概念/行业板块识别。
- 短线情绪监控。
- 主力资金流向。
- 市场异动事件。
- 竞价和分时辅助信号。
