# TdxClient 使用指南

> 面向刚接触本库的量化开发者，覆盖 TdxClient 的全部接口和常见使用姿势。

## 一、快速开始

```python
from opentdx.tdxClient import TdxClient
from opentdx.const import MARKET, PERIOD, ADJUST, SORT_TYPE, CATEGORY, BOARD_TYPE

# 推荐：上下文管理器（自动连接/登录/断开）
with TdxClient() as client:
    kline = client.stock_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=10)

# 手动管理
client = TdxClient()
client.quotation_client.connect().login()
client.ex_quotation_client.connect().login()
data = client.stock_count(MARKET.SZ)
client.quotation_client.disconnect()
client.ex_quotation_client.disconnect()
```

TdxClient 内部持有两个客户端，自动覆盖 A 股和扩展市场（港股/美股/期货）：

| 属性 | 类型 | 用途 |
|---|---|---|
| `client.quotation_client` | MacStandardClient | A 股行情 + MAC 板块/K线/分时 |
| `client.ex_quotation_client` | MacExtendedClient | 扩展市场 + MAC 协议 |

---

## 二、A 股行情

### 2.1 市场概况

```python
# 股票总数
n = client.stock_count(MARKET.SZ)

# 股票列表（code / name / vol / pre_close）
stocks = client.stock_list(MARKET.SZ)               # 全量
stocks = client.stock_list(MARKET.SZ, start=0, count=100)

# 排行榜（涨幅/跌幅/振幅/涨速/跌速/量比/委比/换手）
board = client.stock_top_board(CATEGORY.A)
print(board['increase'][:5])    # 涨幅前 5
print(board['turnover'][:5])    # 换手前 5
```

### 2.2 行情报价

```python
from opentdx.const import FILTER_TYPE

# 简略报价（1 档盘口）— 三种调用方式
client.stock_quotes(MARKET.SZ, '000001')                             # 单只
client.stock_quotes((MARKET.SZ, '000001'))                           # 元组
client.stock_quotes([(MARKET.SZ, '000001'), (MARKET.SH, '600000')])  # 批量

# 详细报价（5 档盘口）
client.stock_quotes_detail(MARKET.SZ, '000001')

# 行情列表（支持排序 + 过滤）
client.stock_quotes_list(
    CATEGORY.A,
    count=200,
    sort_type=SORT_TYPE.CHANGE_PCT,   # 按涨幅排序
    reverse=False,                     # 降序
    filter=[FILTER_TYPE.ST]           # 排除 ST
)

# MAC 协议行情（自定义返回字段）
from opentdx.utils.bitmap import PresetField
client.stock_quotes_fields(
    [(MARKET.SZ, '000001')],
    fields=PresetField.ENHANCED
)
```

### 2.3 K 线

```python
# 日线
client.stock_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=100)

# 30 分钟线
client.stock_kline(MARKET.SH, '999999', PERIOD.MIN_30, count=240)

# 10 分钟线（多周期 + times）
client.stock_kline(MARKET.SH, '999999', PERIOD.MINS, times=10, count=50)

# 前复权周线
client.stock_kline(MARKET.SZ, '000001', PERIOD.WEEKLY, adjust=ADJUST.QFQ)

# K 线结构: datetime, open, high, low, close, vol, amount, float_shares, turnover
```

**周期速查**：`MIN_1 / MIN_5 / MIN_15 / MIN_30 / MIN_60 / DAILY / WEEKLY / MONTHLY / QUARTERLY / YEARLY`
**多周期**：`MINS / DAYS / SECONDS`（需配合 `times` 参数）

### 2.4 分时 / 成交 / 竞价

```python
from datetime import date

# 实时分时
ticks = client.stock_tick_chart(MARKET.SZ, '000001')
# → [{time, price, avg, vol, momentum}, ...]

# 历史分时
history = client.stock_tick_chart(MARKET.SZ, '000001', date=date(2026, 3, 16))

# 分时缩略（240 个采样点价格）
samples = client.stock_chart_sampling(MARKET.SZ, '000001')

# 逐笔成交（实时）
trades = client.stock_transaction(MARKET.SZ, '000001')
# → [{time, price, vol, trade_count, bs_flag}, ...]
# bs_flag: 0=买入 / 1=卖出 / 2=中性 / 5=盘后

# 历史成交
trades = client.stock_transaction(MARKET.SZ, '000001', date=date(2026, 3, 3))

# 集合竞价（9:15-9:25）
auction = client.stock_auction(MARKET.SZ, '300308')
# → [{time, price, matched, unmatched}, ...]

# 历史委托分布
orders = client.stock_history_orders(MARKET.SZ, '000001', date(2026, 1, 7))
```

### 2.5 多日分时（一次获取多天）

```python
# 获取最近 5 个交易日的分时图
data = client.stock_tick_charts(MARKET.SZ, '000001', days=5)
for day in data['charts']:
    print(day['date'], day['pre_close'], len(day['ticks']))
```

### 2.6 指数

```python
# 指数概况（三种调用方式）
client.index_info(MARKET.SH, '999999')
client.index_info([(MARKET.SH, '999999'), (MARKET.SZ, '399001')])
# → [{open, high, low, close, pre_close, diff, vol, amount, up_count, down_count}]

# 指数动量
momentum = client.index_momentum(MARKET.SZ, '399001')
```

### 2.7 个股特征

```python
# 简要特征（现价/内外盘/换手/均价等）
info = client.stock_symbol_info(MARKET.SZ, '000001')
# → {market, code, name, time, pre_close, open, high, low, close,
#     vol, amount, inside_volume, outside_volume, turnover, avg}

# 成交分布（各价位买卖档位 + 3 档盘口）
profile = client.stock_vol_profile(MARKET.SZ, '000001')
# → vol_profile: [{price, vol, buy, sell}, ...]

# F10 公司资料
f10 = client.stock_f10(MARKET.SZ, '000001')
# → [{name: '公司概况'/'财务指标'/'除权分红'/'财报', content: ...}]

# 除权分红数据
xdxr = [item for item in f10 if item['name'] == '除权分红'][0]
```

### 2.8 异动监控

```python
# 主力监控精灵（MAC 增强版）
unusual = client.stock_market_monitor(MARKET.SZ, count=50)
# → [{market, code, name, time, desc, value, unusual_type}, ...]

# 原始异动数据
unusual = client.stock_unusual(MARKET.SZ)
```

---

## 三、板块数据

```python
from opentdx.const import BOARD_TYPE, SORT_TYPE, SORT_ORDER

# 板块列表
boards = client.stock_board_list(BOARD_TYPE.ALL)
boards = client.stock_board_list(BOARD_TYPE.GN, count=200)  # 概念板块

# 板块成分报价（按涨幅排序）
members = client.stock_board_members(
    "881001",                          # 板块代码
    count=50,
    sort_type=SORT_TYPE.CHANGE_PCT,
    sort_order=SORT_ORDER.DESC,
)

# 板块活跃度最高成员
top = client.stock_board_top_members("881001", count=20)

# 查询个股所属板块
df = client.stock_belong_board(MARKET.SZ, '000001')
print(df[['board_symbol_name', 'close', '涨停数']])

# 资金流向（当日 + 5 日）
df = client.stock_capital_flow(MARKET.SZ, '000001')
print(df[['今日主力净流入', '5日主力净流入']])

# 板块文件（板块→成分股对照表）
from opentdx.const import BLOCK_FILE_TYPE
blocks = client.stock_block(BLOCK_FILE_TYPE.GN)
# → [{block_name, stocks: [code, ...]}, ...]
```

### 板块类型速查

| BOARD_TYPE | 说明 | 数量 |
|---|---|---|
| `ALL` | 全部板块 | 559 |
| `HY` | 行业一级 | 127 |
| `HY2` | 行业二级 | 344 |
| `GN` | 概念 | 269 |
| `FG` | 风格 | 158 |
| `DQ` | 地区 | 32 |
| `YJ_LEVEL1/2/3` | 研究板 | 30/127/344 |

---

## 四、扩展市场（期货 / 港股 / 美股）

```python
from opentdx.const import EX_MARKET

# 商品总数 / 分类 / 列表
client.goods_count()
client.goods_category_list()
client.goods_list(count=100)

# 品种列表（期货合约品种，MAC 协议）
varieties = client.goods_varieties(30)  # 市场代码 30=上海期货

# 行情报价（三种调用方式一致）
client.goods_quotes(EX_MARKET.US_STOCK, 'TSLA')
client.goods_quotes([(EX_MARKET.US_STOCK, 'TSLA'),
                     (EX_MARKET.HK_MAIN_BOARD, '09988')])

# 行情列表（支持排序）
client.goods_quotes_list(EX_MARKET.US_STOCK, count=100,
                         sortType=SORT_TYPE.TOTAL_AMOUNT)

# K 线
client.goods_kline(EX_MARKET.US_STOCK, 'TSLA', PERIOD.DAILY, count=100)
client.goods_kline(EX_MARKET.HK_MAIN_BOARD, '00700', PERIOD.MIN_30, count=240)

# 分时图
client.goods_tick_chart(EX_MARKET.US_STOCK, 'TSLA')                       # 实时
client.goods_tick_chart(EX_MARKET.US_STOCK, 'TSLA', date=date(2026, 3, 3)) # 历史
client.goods_chart_sampling(EX_MARKET.US_STOCK, 'TSLA')                    # 缩略

# 历史成交
client.goods_history_transaction(EX_MARKET.US_STOCK, 'TSLA', date(2026, 3, 3))
```

### 常用市场代码

| EX_MARKET | 说明 |
|---|---|
| `HK_MAIN_BOARD` | 香港主板 |
| `HK_GEM` | 香港创业板 |
| `HK_STOCK_GGT` | 港股通 |
| `US_STOCK` | 美股 |
| `SH_FUTURES` | 上海期货 |
| `DL_FUTURES` | 大连商品 |
| `ZZ_FUTURES` | 郑州商品 |
| `CFFEX_FUTURES` | 中金所期货 |

---

## 五、服务器与文件

```python
# 服务器交易日时段
info = client.server_info()
print(info['today'], info['last_trading_day'], info['sessions_1'])
# 可判断当前是否在交易时段

# K 线可用记录数
offset = client.stock_kline_offset(count=128000)
print(offset['total'])

# MAC 协议文件下载（板块文件等）
data = client.download_file('block_gn.dat')
text = data.decode('gbk', errors='replace')
```

---

## 六、批量请求与性能

### 6.1 批量行情

```python
# 一次请求多只股票（比循环快 10-100 倍）
codes = [(MARKET.SZ, '000001'), (MARKET.SZ, '000002'),
         (MARKET.SH, '600000'), (MARKET.SH, '600036')]
quotes = client.stock_quotes(codes)
```

### 6.2 大批量 K 线（自动分页）

```python
# TdxClient 内置自动分页，直接传大 count 即可
kline = client.stock_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=5000)
```

### 6.3 板块全量成分获取

```python
# 一次获取板块全部成分股行情
all_members = client.stock_board_members("881001", count=100000)
```

### 6.4 连接复用

```python
# 上下文管理器内，所有请求复用同一连接
with TdxClient() as client:
    for code in code_list:
        quotes = client.stock_quotes(MARKET.SZ, code)  # 复用连接
```

---

## 七、返回数据单位约定

| 字段 | 单位 | 示例 |
|---|---|---|
| 价格 (open/high/low/close/pre_close) | 元 (float) | `11.36` = 11.36 元/股 |
| 成交量 (vol) | 股 (int) | `121638752` = 约 1.22 亿股 |
| 成交额 (amount) | 元 (float) | `1380730880.0` = 约 13.8 亿 |
| 换手率 (turnover) | % (float) | `5.23` = 5.23% |
| 涨跌幅 | % (float) | `2.15` = 上涨 2.15% |
| 时间 (time/datetime) | time / datetime | 非字符串，可直接计算 |

---

## 八、与 pandas 配合

```python
import pandas as pd

with TdxClient() as client:
    # K 线转 DataFrame
    df = pd.DataFrame(client.stock_kline(MARKET.SZ, '000001', PERIOD.DAILY))
    df.set_index('datetime', inplace=True)

    # 分时转 DataFrame
    ticks = pd.DataFrame(client.stock_tick_chart(MARKET.SZ, '000001'))

    # 板块成分批量获取
    members = pd.DataFrame(client.stock_board_members("881001", count=200))

    # 资金流向自动返回 DataFrame
    flow = client.stock_capital_flow(MARKET.SZ, '000001')

    # 所属板块自动返回 DataFrame
    boards = client.stock_belong_board(MARKET.SZ, '000001')
```

---

## 九、常见问题

**Q: 连接断开怎么办？**
TdxClient 内置自动重连机制，`q_client()` 和 `eq_client()` 在每次调用时检查连接状态，断开自动重连并登录。

**Q: 如何选择服务器？**
默认使用 MAC 行情主站。如需切换，手动设置：
```python
client = TdxClient()
client.quotation_client._t.hosts = [("自定义", "ip", 7709)]
```

**Q: 扩展市场支持哪些品种？**
期货、港股、美股、外汇、国际指数、基金等，完整列表见 `EX_MARKET` 枚举。
