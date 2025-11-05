# 网格选股综合评分系统

## 功能概述

批量计算1800+只基金的网格适用性综合评分，基于以下算法：

**总分 = 0.7 × VolScore + 0.3 × HLScore**

### VolScore（波动率得分，0-100分）

综合评估标的的波动特征，包括：

1. **历史波动率得分（40%）**
   - 计算30日收盘-收盘年化波动率（%）
   - 映射规则：10% → 0分，50% → 100分（线性插值）
   - <10%或>50% 一律取边界值

2. **波动稳定性得分（35%）**
   - 跳空比率：mean(|开盘涨跌幅|) / mean(ATR/前收)
   - 收益率偏度：252日收益率的偏度
   - 跳空魔鬼（GapRatio>0.5）直接0分
   - 偏度惩罚：左偏(<-0.5)或右偏(>0.5)都扣分

3. **近期波动衰减得分（25%）**
   - 计算30日波动率 / 252日波动率
   - 比值 ≥1 得100分，≤0.3 得0分（线性插值）
   - 防止"过去很肥、现在萎了"的标的

**合成公式：**
```
VolScore = 0.4×历史波动率得分 + 0.35×稳定性得分 + 0.25×衰减得分
```

### HLScore（半衰期得分，0-100分）

基于OLS离散回归计算均值回归速度：

1. **计算步骤**
   - 取252个交易日对数价序列 ln(P)
   - OLS回归：Δy_t = α + β·y_{t-1} + ε_t
   - 计算半衰期：HL = ln(2) / θ，其中 θ = -ln(1+β)
   - 滚动63天重复计算，得到HL序列

2. **打分公式**
   - 自身历史分位（60%）：1 - percentile(HL_current, HL_history)
   - 跨品种相对分位（40%）：1 - percentile(HL_current, 全市场HL)
   - HL越小（均值回归越快）得分越高

**合成公式：**
```
HLScore = 0.6×自身分位得分 + 0.4×跨品种分位得分
```

## 模块结构

```
网格选股/
├── data_fetcher.py                      # 数据获取模块（独立）
├── fetch_all_public_funds_final.py     # 基金列表获取
├── grid_stock_scoring.py               # 主评分脚本
├── AllPublicFunds_Ashare.csv           # 基金列表缓存
├── result.csv                           # 输出结果
└── README.md                            # 本文档
```

### 1. 数据获取模块（data_fetcher.py）

独立的数据获取模块，使用**合并下载数据模块**的 `getDayData` 获取后复权日线数据。

**主要功能：**
- `get_single_stock_data(code)` - 获取单只标的数据
- `get_batch_stock_data(code_list)` - 批量获取多只标的数据
- `validate_data(df)` - 数据验证
- `get_data_info(df)` - 获取数据信息
- `get_day_data_with_timeout()` - 带超时和重试机制的数据获取

**核心特性：**
- ✅ 使用成熟的合并下载数据模块
- ✅ 支持本地CSV缓存，避免重复下载
- ✅ 带超时机制（默认5秒）
- ✅ 自动重试（默认3次）
- ✅ 异常静默处理

**示例：**
```python
from data_fetcher import DataFetcher

# 初始化
fetcher = DataFetcher(start_date="20241101", end_date="20251102")

# 获取单只标的数据
df = fetcher.get_single_stock_data("159001.SZ")

# 批量获取
results = fetcher.get_batch_stock_data(["159001.SZ", "510300.SH"])
```

### 2. 主评分脚本（grid_stock_scoring.py）

完整的评分系统，调用数据获取模块并计算综合得分。

**主要类：**
- `GridStockScorer` - 评分器类

**核心方法：**
- `calculate_vol_score(df)` - 计算VolScore
- `calculate_hl_score(df)` - 计算HLScore
- `calculate_cross_hl_score(hl_values_dict)` - 计算跨品种HLScore
- `process_all_funds(fund_df)` - 异步批量处理

## 安装依赖

```bash
pip install pandas numpy statsmodels tqdm scipy xtquant
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

## 使用方法

### 方式1：直接运行

```bash
python grid_stock_scoring.py
```

### 方式2：在代码中调用

```python
from grid_stock_scoring import GridStockScorer
import asyncio

# 初始化评分器
scorer = GridStockScorer(start_date="20241101")

# 运行评分
asyncio.run(scorer.run())
```

### 方式3：自定义日期范围

```python
from grid_stock_scoring import GridStockScorer
import asyncio

# 使用自定义日期
scorer = GridStockScorer(
    start_date="20240101",
    end_date="20241231"
)

asyncio.run(scorer.run())
```

## 输出结果

### result.csv 格式

| 列名 | 说明 | 示例 |
|-----|------|------|
| code | 基金代码 | 159001.SZ |
| name | 基金名称 | 货币ETF |
| hist30 | 30日年化波动率(%) | 25.43 |
| hl | 当前半衰期(天) | 15.2 |
| vol_score | VolScore得分 | 78.5 |
| hl_score | HLScore得分 | 65.3 |
| total | 综合总分 | 74.5 |

**注意：** 结果按 `total` 列降序排序。

## 性能优化

1. **异步协程加速**
   - 使用 `asyncio` + `ThreadPoolExecutor` 实现并发
   - 10个线程同时处理，大幅提升速度

2. **进度条显示**
   - 使用 `tqdm` 显示实时进度
   - 支持总进度和百分比显示

3. **异常捕获不中断**
   - 单只标的失败不影响其他标的
   - 缺失数据自动丢弃
   - 静默失败，不打印冗余错误

4. **数据验证**
   - 自动过滤数据不足252天的标的
   - 自动删除缺失值
   - 自动验证数据完整性

## 日期范围说明

脚本会自动调用 `get_date_range.py` 获取日期范围：

- **start_date**: 固定为 `20241101`
- **end_date**: 自动计算
  - 交易日 + 21点后：当天日期
  - 交易日 + 21点前：上一交易日
  - 非交易日：上一交易日

也可以手动指定日期范围（格式：YYYYMMDD）。

## 数据源说明

- **基金列表**: 使用 Wind API 获取（板块ID: 1000019786000000）
- **行情数据**: 使用**合并下载数据模块** (`getDayData`) 获取
  - 数据源：XtQuant
  - 缓存机制：支持本地CSV缓存，避免重复下载
  - 超时控制：5秒超时，3次重试
- **复权方式**: 后复权（`dividend_type='back'`）
- **数据周期**: 日线
- **数据字段**: date, open, high, low, close, volume, amount

## 注意事项

1. **数据要求**
   - 至少需要252个交易日的数据
   - 数据不足的标的会自动跳过
   - 建议数据区间至少覆盖1年

2. **计算时间**
   - 1800只标的约需15-30分钟
   - 取决于网络速度和机器性能

3. **依赖服务**
   - 需要**合并下载数据模块**正常工作（位于 `source.实盘.xuntou.datadownload.合并下载数据`）
   - 需要 XtQuant 账号和授权
   - 需要 Wind 终端登录（获取基金列表）
   - 网络连接正常

4. **异常处理**
   - 数据获取失败自动跳过
   - 计算异常自动返回0分
   - 不会中断整体流程

## 评分解读

### 高分标的特征（Total > 70）

- **高波动**: 30日波动率在20%-50%之间
- **稳定跳空**: 跳空比率低，收益率分布对称
- **持续波动**: 近期波动未明显衰减
- **快速回归**: 半衰期较短，均值回归快

### 低分标的特征（Total < 30）

- **低波动**: 30日波动率 < 15%
- **魔鬼跳空**: 跳空比率 > 0.5
- **单边趋势**: 收益率严重偏斜
- **慢速回归**: 半衰期很长或无均值回归

## 常见问题

### Q1: 为什么有些基金没有得分？

**A:** 可能原因：
- 数据不足252个交易日
- 数据获取失败
- 计算过程异常（如除零错误）

### Q2: VolScore 和 HLScore 哪个更重要？

**A:** 
- VolScore占70%：决定网格利润空间（肥不肥）
- HLScore占30%：决定网格交易频率（快不快）
- 两者缺一不可

### Q3: 如何筛选适合网格的标的？

**A:** 建议标准：
1. Total > 60分（综合评分及格）
2. hist30 > 20%（波动率足够）
3. hl < 30天（均值回归够快）
4. vol_score > 50（波动特征合格）

### Q4: 数据获取太慢怎么办？

**A:** 优化建议：
- 增加线程数（修改 `max_workers=10` → `20`）
- 使用本地缓存数据
- 缩短日期范围
- 过滤掉不活跃的标的

## 更新日志

### v1.0.0 (2025-11-02)
- ✅ 完整实现 70%Vol + 30%HL 评分体系
- ✅ 独立数据获取模块
- ✅ 异步协程加速
- ✅ 进度条显示
- ✅ 异常捕获不中断
- ✅ 结果降序排序导出

## 技术支持

如有问题，请检查：
1. 依赖包是否完整安装
2. XtQuant 是否正常登录
3. Wind 终端是否启动
4. 网络连接是否正常

## 许可证

MIT License

