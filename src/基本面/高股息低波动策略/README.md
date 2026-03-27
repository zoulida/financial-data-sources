# 高股息低波动股票筛选系统

## 📋 项目简介

本系统实现了一套专业的"高股息低波动"股票筛选策略，适用于稳健型投资者构建红利低波组合。系统采用机构级别的筛选标准，通过6条硬门槛和双因子评分体系，从全市场约3,500只股票中精选出30-50只优质标的。

## 🎯 策略逻辑

### 一、选股宇宙（约3,500只）

1. **获取基础池**: 沪深主板A股
2. **剔除异常股**: ST、*ST、退市整理股
3. **上市年限**: 剔除上市不足3年（保证有3个完整会计年度分红记录）
4. **流动性**: 剔除最近1年日均成交额全市场后20%

### 二、6条硬门槛（剩余80-120只）

| 指标 | 阈值 | 目的 |
|------|------|------|
| ① 连续分红年限 | ≥3年 | 杜绝"偶发性高分红" |
| ② 最近年度股息率 | ≥4% | 高于10年期国债1.6%两倍有余 |
| ③ 过去3年平均股息支付率 | 30%-70% | 太低=没诚意，太高=不可持续 |
| ④ 最近年报扣非ROE | ≥8% | 盈利质量差的不考虑 |
| ⑤ 最近一期资产负债率 | 低于行业中位数 | 防高杠杆陷阱（行业中性） |
| ⑥ 过去52周年化波动率 | 全市场最低30% | 真正"低波" |

### 三、双因子打分（前30-50只）

**红利因子得分** = 0.6 × 股息率排名分 + 0.4 × 股息稳定性排名分
- 股息率排名分: 最高=100分，线性递减
- 股息稳定性: 3年股息支付率标准差倒数排名，越稳越高

**低波因子得分** = 100 - 波动率百分位 × 100

**综合得分** = 0.5 × 红利因子 + 0.5 × 低波因子

取前30-50只，可选等权或股息率加权。

## 🏗️ 项目结构

```
src/高股息低波动/
├── __init__.py                 # 模块初始化
├── config.py                   # 配置文件（可调整参数）
├── wind_data_fetcher.py        # Wind数据获取（财务数据）
├── market_data_fetcher.py      # XtQuant数据获取（行情数据）
├── stock_filter.py             # 6条硬门槛筛选
├── scoring.py                  # 双因子打分
├── main.py                     # 主程序入口
├── README.md                   # 本文档
└── data/                       # 输出数据目录
    ├── stock_universe.txt      # 选股宇宙
    ├── dividend_data_*.csv     # 分红数据
    ├── financial_data_*.csv    # 财务数据
    ├── filtered_stocks_*.csv   # 筛选结果
    ├── full_ranking_*.csv      # 完整排名
    ├── top_30_stocks_*.csv     # 前30只股票
    └── portfolio_summary_*.csv # 组合摘要
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Wind API（需要授权）
- XtQuant（需要Token）

### 依赖安装

```bash
pip install pandas numpy tqdm WindPy
```

### 基本使用

```bash
# 使用默认参数（选取前30只）
cd src/高股息低波动
python main.py

# 指定选取数量
python main.py --top-n 50

# 指定输出目录
python main.py --output-dir "D:/results"
```

### Python代码调用

```python
from pathlib import Path
from src.高股息低波动.main import HighDividendLowVolatilitySelector

# 初始化选择器
selector = HighDividendLowVolatilitySelector(
    output_dir=Path("./data"),
    top_n=30
)

# 运行筛选
top_stocks = selector.run()

# 查看结果
print(top_stocks)
```

## ⚡ 智能缓存功能

系统内置智能缓存，大幅提升运行效率：

| 场景 | 耗时 | 说明 |
|------|------|------|
| 首次运行 | 15-30分钟 | 获取所有数据 |
| 第二次运行 | 1-2分钟 | 使用缓存 ⚡ |
| 提升幅度 | **93%+** | 显著提升 |

**缓存策略**:
- ✅ 所有数据获取函数按天缓存
- ✅ 每天首次运行自动更新数据
- ✅ 支持手动清空缓存强制更新

**查看缓存状态**:
```python
from src.common.shelve_tool import get_cache_info
print(get_cache_info())
```

**详细说明**: 参考 `CACHE_GUIDE.md`

## 📊 数据源说明

### Wind API（财务数据）

- **股票列表**: `w.wset("sectorconstituent", ...)`
- **上市日期**: `ipo_date`
- **股息率**: `dividendyield2`
- **股息支付率**: `s_fa_dividentbt`
- **连续分红年限**: `continuousdividendyears`
- **扣非ROE**: `roe_deducted`
- **资产负债率**: `debttoassets`
- **行业分类**: `industry_sw`

参考文档: `md/winds/Wind数据获取完整指南.md`

### XtQuant（行情数据）

- **日K线数据**: 开盘、收盘、最高、最低、成交量、成交额
- **波动率计算**: 基于收盘价日收益率
- **流动性数据**: 日均成交额

参考文档: `md/合并下载数据/合并下载数据.md`

## ⚙️ 配置说明

所有参数都可以在 `config.py` 中调整：

```python
from src.高股息低波动.config import Config

# 自定义配置
config = Config()
config.filter.min_dividend_years = 5  # 调整最少分红年限
config.filter.min_dividend_yield = 5.0  # 调整最低股息率
config.output.top_n = 50  # 调整选取数量

# 查看配置
config.print_config()
```

## 📈 输出文件说明

### 1. 中间数据文件

| 文件名 | 说明 | 主要字段 |
|--------|------|----------|
| `stock_universe.txt` | 初始股票池 | 股票代码列表 |
| `dividend_data_*.csv` | 分红数据 | stock_code, dividend_yield, dividend_years |
| `financial_data_*.csv` | 财务数据 | stock_code, roe_deducted, debt_ratio, industry |
| `payout_data_*.csv` | 支付率数据 | stock_code, avg_payout_ratio, payout_std |
| `volatility_data_*.csv` | 波动率数据 | stock_code, volatility_annual |

### 2. 最终结果文件

| 文件名 | 说明 | 主要字段 |
|--------|------|----------|
| `filtered_stocks_*.csv` | 通过6条硬门槛的股票 | 所有筛选字段 |
| `full_ranking_*.csv` | 完整排名（含得分） | rank, composite_score, 各因子得分 |
| `top_30_stocks_*.csv` | 前30只股票 | 最终组合成分股 |
| `portfolio_summary_*.csv` | 组合摘要统计 | 平均股息率、ROE、波动率等 |

## 💡 使用建议

### 1. 数据更新频率

- **季度更新**: 每季度财报发布后运行一次
- **年度更新**: 每年年报发布后（4-5月）重点运行
- **实时监控**: 关注成分股的重大事件

### 2. 组合管理

- **等权配置**: 每只股票配置相同权重（适合小资金）
- **股息率加权**: 按股息率加权配置（强化红利属性）
- **行业分散**: 关注行业集中度，避免单一行业过重

### 3. 风险控制

- **定期复查**: 每季度检查成分股是否仍符合标准
- **止损机制**: 若出现ST、业绩大幅下滑等情况及时剔除
- **再平衡**: 每年调整一次组合，卖出不符合标准的，买入新入选的

### 4. 参数调整

根据市场环境调整参数：
- **牛市**: 可适当降低股息率要求，提高ROE要求
- **熊市**: 可提高股息率要求，加强防御性
- **震荡市**: 保持默认参数即可

## 🔧 常见问题

### 1. Wind连接失败

```python
# 检查Wind是否启动
from WindPy import w
w.start()
if w.isconnected():
    print("Wind连接成功")
else:
    print("Wind连接失败，请检查客户端")
```

### 2. XtQuant数据下载失败

- 检查Token是否有效
- 确保网络连接正常
- 查看 `md/合并下载数据/合并下载数据.py` 中的配置

### 3. 筛选结果过少

- 适当降低某些阈值（如股息率从4%降至3%）
- 扩大股息支付率范围
- 增加波动率百分位阈值

### 4. 数据不完整

- 某些新股可能缺少历史数据，会被自动过滤
- 部分财务指标可能未披露，可在筛选前先清洗数据

## 📚 参考文档

- **Wind API指南**: `md/winds/Wind数据获取完整指南.md`
- **Wind字段映射**: `md/winds/merged_fields_fixed.txt`
- **XtQuant API**: `md/xtdata/xtdata_api_guide.md`
- **数据下载模块**: `md/合并下载数据/合并下载数据.md`

## 📄 代码规范

本项目遵循以下规范：
- **格式化**: Black代码格式化
- **文档**: 函数级docstring
- **类型标注**: 全部函数参数和返回值
- **进度条**: 使用tqdm显示进度

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📜 许可证

本项目仅供学习和研究使用，不构成投资建议。

---

**免责声明**: 
- 本系统基于历史数据和量化模型，不保证未来收益
- 投资有风险，入市需谨慎
- 使用本系统进行投资决策，风险自负

