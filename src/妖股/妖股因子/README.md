# 妖股因子量化系统

## 📋 概述

将"妖股"拆解为可计算、可回测、可落地的数字指标。通过四个生命周期阶段的核心因子，合成"妖股概率分"。

### 生命周期阶段

1. **潜伏期（T-20～T-2）**：资金潜伏、筹码松动
2. **启动期（T-1～T+0）**：涨停强度、量价爆破  
3. **加速期（T+1～T+N）**：连板强度、情绪共振
4. **分歧期（高位巨量断板）**：筹码博弈、技术背离

## 🚀 快速开始

### 安装依赖

```bash
pip install pandas numpy scikit-learn matplotlib seaborn
```

### 基本使用

```python
from src.妖股.妖股因子 import MonsterStockQuantSystem

# 创建系统实例
system = MonsterStockQuantSystem(use_mock_data=True)

# 运行分析
results = system.run_analysis(
    stock_code='000001.SZ',
    start_date='20240101',
    end_date='20241231',
    probability_threshold=0.5
)

# 查看结果
print(results['final_factors']['monster_probability'].describe())
```

### 命令行使用

```bash
# 使用模拟数据
python -m src.妖股.妖股因子.main --stock 000001.SZ --start 20240101 --end 20241231 --mock-data

# 使用Wind API
python -m src.妖股.妖股因子.main --stock 000001.SZ --start 20240101 --end 20241231 --wind-token YOUR_TOKEN

# 使用XtQuant API
python -m src.妖股.妖股因子.main --stock 000001.SZ --start 20240101 --end 20241231 --xtquant-token YOUR_TOKEN
```

## 📊 系统架构

### 核心模块

1. **数据获取模块** (`data_fetcher.py`)
   - 集成Wind API和XtQuant API
   - 支持模拟数据生成
   - 自动数据源切换

2. **因子计算模块** (`factor_calculator.py`)
   - 潜伏期因子：龙虎榜净买占比、大单净流入斜率等
   - 启动期因子：封单额占比、量比等
   - 加速期因子：连板数、隔日溢价等
   - 分歧期因子：浮动筹码、技术背离等

3. **数据预处理模块** (`data_processor.py`)
   - 去极值：Winsorize双侧2.5%
   - 中性化：对市值、行业、β做回归取残差
   - 标准化：横截面z-score

4. **概率分合成模块** (`probability_synthesizer.py`)
   - 动态加权logistic回归
   - 滚动训练更新
   - L1正则化

5. **回测框架** (`backtester.py`)
   - 因子有效性分析
   - 策略回测
   - 风险指标计算
   - 绩效评估

## 🔧 详细使用

### 1. 分步骤使用

```python
from src.妖股.妖股因子 import *

# 1. 数据获取
data_fetcher = MonsterStockDataFetcher(use_mock_data=True)
stock_data = data_fetcher.fetch_stock_data('000001.SZ', '20240101', '20241231')

# 2. 因子计算
calculator = MonsterStockFactorCalculator()
raw_factors = calculator.calculate_all_factors(stock_data)

# 3. 数据预处理
processor = DataProcessor()
processed_factors = processor.process_factors(raw_factors)

# 4. 概率分合成
synthesizer = MonsterStockProbabilitySynthesizer()
final_factors = synthesizer.calculate_monster_probability(processed_factors)

# 5. 回测验证
backtester = MonsterStockBacktester()
backtest_results = backtester.run_backtest(final_factors, stock_data)
```

### 2. 多股票分析

```python
stock_codes = ['000001.SZ', '000002.SZ', '600000.SH']
results = {}

for stock_code in stock_codes:
    result = system.run_analysis(stock_code, '20240101', '20241231')
    results[stock_code] = result
```

### 3. 参数调优

```python
thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
results = {}

for threshold in thresholds:
    result = system.run_analysis('000001.SZ', '20240101', '20241231', threshold)
    results[threshold] = result['backtest_results']['performance_metrics']
```

## 📈 因子说明

### 潜伏期因子

| 因子名称 | 计算方法 | 阈值 |
|---------|---------|------|
| 龙虎榜净买占比 | sum(机构+游资净买额)/流通市值 | >2% |
| 大单净流入5日斜率 | linear regression β | >0且p<0.05 |
| 股东户数环比增速 | 环比增长率 | >15% |
| 换手率20日均值分位 | 过去250日前20%区间 | 前20% |

### 启动期因子

| 因子名称 | 计算方法 | 阈值 |
|---------|---------|------|
| 封单额/流通市值 | 封单金额/流通市值 | >5%(主板)或>3%(20cm) |
| 封板耗时 | 首次封板时间 | 10:00前完成 |
| 量比 | 当日成交量/60日均量 | >3且破2倍 |
| 实体阳线占比 | 近5日阳线比例 | ≥80% |

### 加速期因子

| 因子名称 | 计算方法 | 阈值 |
|---------|---------|------|
| 连板数 | barssince(涨停) | ≥3 |
| 隔日溢价 | 高开幅度×是否回封 | >3%且30min内回封 |
| 概念板块涨停占比 | 所属概念涨停数/总数 | >30% |
| 全A涨停数 | 市场涨停股票数 | 20日高位 |

### 分歧期因子

| 因子名称 | 计算方法 | 阈值 |
|---------|---------|------|
| WINNER(C)浮动筹码 | 获利盘比例 | >70%且换手>25% |
| 价格中枢偏离度 | (C-MA13)/MA13 | >15% |
| CCI背离 | CCI突破+200后3日回落 | 背离信号=1 |
| MACD背离 | 15min顶背离 | 背离信号=1 |

## 📊 输出结果

### 因子数据

- `raw_factors`: 原始因子数据
- `processed_factors`: 预处理后因子数据
- `final_factors`: 最终因子数据（包含妖股概率分）

### 回测结果

- `strategy_returns`: 策略收益率序列
- `benchmark_returns`: 基准收益率序列
- `performance_metrics`: 绩效指标
- `risk_metrics`: 风险指标
- `trading_summary`: 交易摘要

### 关键指标

- **妖股概率分**: 0-1之间的概率值
- **妖股评分**: 0-100分的评分
- **IC信息比率**: 因子有效性指标
- **夏普比率**: 风险调整后收益
- **最大回撤**: 最大亏损幅度

## ⚙️ 配置参数

### 数据获取参数

```python
# Wind API配置
wind_token = "YOUR_WIND_TOKEN"

# XtQuant API配置  
xtquant_token = "YOUR_XTQUANT_TOKEN"

# 强制使用模拟数据
use_mock_data = True
```

### 因子计算参数

```python
# 回看期参数
lookback_days = 250  # 换手率分位计算回看期
volume_ma_days = 60  # 量比计算均线期
```

### 预处理参数

```python
# 去极值参数
winsorize_limits = (0.025, 0.975)  # 2.5%双侧去极值

# 中性化参数
neutralize_factors = ['market_cap', 'industry', 'beta']

# 标准化方法
standardize_method = 'zscore'  # 'zscore'或'minmax'
```

### 概率分合成参数

```python
# 妖股定义
min_boards = 4  # 最少连板数

# 训练参数
lookback_years = 2  # 回看年数
retrain_frequency = 'W'  # 重训练频率
regularization = 0.01  # L1正则化参数
```

### 回测参数

```python
# 交易参数
hold_days = 5  # 持仓天数
transaction_cost = 0.001  # 交易成本（单边）

# 概率阈值
probability_threshold = 0.5  # 买入概率阈值
```

## 📁 文件结构

```
src/妖股/妖股因子/
├── __init__.py              # 模块初始化
├── main.py                  # 主程序
├── factor_calculator.py     # 因子计算器
├── data_processor.py        # 数据预处理器
├── probability_synthesizer.py # 概率分合成器
├── data_fetcher.py          # 数据获取器
├── backtester.py            # 回测框架
├── example_usage.py         # 使用示例
└── README.md               # 说明文档
```

## 🔍 示例代码

### 完整示例

```python
# 运行完整示例
python -m src.妖股.妖股因子.example_usage
```

### 自定义分析

```python
from src.妖股.妖股因子 import MonsterStockQuantSystem

# 创建系统
system = MonsterStockQuantSystem(use_mock_data=True)

# 运行分析
results = system.run_analysis(
    stock_code='000001.SZ',
    start_date='20240101', 
    end_date='20241231',
    probability_threshold=0.6
)

# 查看结果
print("妖股概率分统计:")
print(results['final_factors']['monster_probability'].describe())

# 绘制图表
system.plot_results()

# 打印回测摘要
system.backtester.print_summary()
```

## ⚠️ 注意事项

1. **数据权限**: 使用Wind API或XtQuant API需要相应的数据权限
2. **模拟数据**: 当API不可用时，系统会自动使用模拟数据
3. **参数调优**: 建议根据实际市场情况调整概率阈值等参数
4. **风险控制**: 本系统仅用于研究，实际投资需谨慎
5. **数据质量**: 确保输入数据的完整性和准确性

## 📞 技术支持

如有问题，请检查：

1. 依赖包是否正确安装
2. API token是否有效
3. 数据格式是否正确
4. 参数设置是否合理

## 📄 许可证

本项目仅供学习和研究使用，请勿用于商业用途。
