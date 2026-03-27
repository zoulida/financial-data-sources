# 快速开始指南

## 5分钟上手

### 1. 环境准备（2分钟）

```bash
# 进入项目目录
cd src/高股息低波动

# 安装依赖
pip install -r requirements.txt
```

**前置条件:**
- ✅ Python 3.8+
- ✅ Wind终端（需要登录）
- ✅ XtQuant配置（参考 `md/合并下载数据/合并下载数据.md`）

### 2. 运行程序（1分钟）

#### Windows用户
双击运行 `run.bat`

#### 命令行运行
```bash
# 默认设置（选取前30只）
python main.py

# 自定义数量
python main.py --top-n 50

# 指定输出目录
python main.py --output-dir "D:/results"
```

#### 交互式运行
```bash
python run.py
```

### 3. 查看结果（2分钟）

**⚡ 缓存提示**: 
- 首次运行: 15-30分钟（获取数据）
- 第二次运行: 1-2分钟（使用缓存）
- 每天首次运行会自动更新数据

结果保存在 `data/` 目录：

```
data/
├── top_30_stocks_YYYYMMDD_HHMMSS.csv    ← 最终组合（重点关注）
├── portfolio_summary_YYYYMMDD_HHMMSS.csv ← 组合摘要
└── full_ranking_YYYYMMDD_HHMMSS.csv      ← 完整排名
```

**关键字段说明:**

| 字段 | 说明 |
|------|------|
| `stock_code` | 股票代码 |
| `stock_name` | 股票名称 |
| `dividend_yield` | 股息率(%) |
| `roe_deducted` | 扣非ROE(%) |
| `volatility_annual` | 年化波动率 |
| `composite_score` | 综合得分(0-100) |
| `rank` | 排名 |

---

## 常用场景

### 场景1: 更激进的选择（提高ROE要求）

```python
from main import HighDividendLowVolatilitySelector
from stock_filter import StockFilter

selector = HighDividendLowVolatilitySelector(top_n=30)
selector.filter_engine = StockFilter(
    min_dividend_years=3,
    min_dividend_yield=4.0,
    payout_ratio_range=(30.0, 70.0),
    min_roe=12.0,  # 提高到12%
    volatility_percentile=0.3
)
result = selector.run()
```

### 场景2: 更防御的选择（更高股息率）

```python
selector = HighDividendLowVolatilitySelector(top_n=30)
selector.filter_engine = StockFilter(
    min_dividend_years=5,  # 5年连续分红
    min_dividend_yield=5.0,  # 5%股息率
    payout_ratio_range=(30.0, 60.0),
    min_roe=8.0,
    volatility_percentile=0.2  # 更低波动率
)
result = selector.run()
```

### 场景3: 分步运行（逐步检查）

```python
selector = HighDividendLowVolatilitySelector(top_n=30)

# 第一步：构建股票池
stocks = selector.step1_build_universe()
print(f"股票池: {len(stocks)} 只")

# 第二步：获取数据
div_df, fin_df, pay_df, vol_df = selector.step2_fetch_data(stocks)
print(f"数据获取完成")

# 第三步：筛选
filtered = selector.step3_apply_filters(div_df, fin_df, pay_df, vol_df)
print(f"筛选后: {len(filtered)} 只")

# 第四步：打分
top_stocks, full_rank = selector.step4_score_and_rank(filtered)
print(f"最终: {len(top_stocks)} 只")
```

---

## 故障排查

### ❌ Wind连接失败

```python
from WindPy import w
w.start()
if w.isconnected():
    print("✓ Wind已连接")
else:
    print("✗ Wind未连接，请启动Wind终端并登录")
```

### ❌ XtQuant导入失败

检查路径配置：
```python
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]
print(f"项目根目录: {project_root}")
print(f"合并下载数据路径: {project_root / 'md' / '合并下载数据'}")
```

### ❌ 筛选结果为空

降低部分阈值：
```python
selector.filter_engine = StockFilter(
    min_dividend_years=2,  # 降低到2年
    min_dividend_yield=3.0,  # 降低到3%
    # ... 其他参数
)
```

### ❌ 数据下载超时

分批处理或使用缓存：
```python
# 在 market_data_fetcher.py 中设置
# is_download=0 表示优先使用缓存
```

---

## 输出文件详解

### 1. top_30_stocks_*.csv（最终组合）
**用途**: 直接用于投资决策

**关键列**:
- `rank`: 综合排名
- `stock_code`, `stock_name`: 股票信息
- `dividend_yield`: 股息率（决定收益）
- `volatility_annual`: 波动率（决定风险）
- `roe_deducted`: 盈利能力
- `composite_score`: 综合得分

### 2. portfolio_summary_*.csv（组合摘要）
**用途**: 快速了解组合整体特征

**指标**:
- 股票数量
- 平均股息率
- 平均ROE
- 平均波动率
- 平均综合得分

### 3. full_ranking_*.csv（完整排名）
**用途**: 查看所有通过筛选的股票

**用法**: 
- 可作为备选池
- 如top 30某只股票出现问题，从这里选择替补

---

## 下一步

1. **阅读完整文档**: `README.md`
2. **查看使用示例**: `example_usage.py`
3. **自定义配置**: `config.py`
4. **了解更新**: `CHANGELOG.md`

---

## 快速参考

### 默认参数一览

```
【选股宇宙】
- 上市年限 ≥ 3年
- 流动性：剔除后20%

【硬门槛】
- 连续分红 ≥ 3年
- 股息率 ≥ 4%
- 股息支付率：30%-70%
- 扣非ROE ≥ 8%
- 资产负债率：行业中性
- 波动率：最低30%

【评分】
- 红利因子权重：50%
  - 股息率：60%
  - 稳定性：40%
- 低波因子权重：50%

【输出】
- 最终选取：30只
```

### 命令速查

```bash
# 基本运行
python main.py

# 选50只
python main.py --top-n 50

# 指定输出
python main.py --output-dir ./results

# 交互式
python run.py

# 查看示例
python example_usage.py
```

---

**提示**: 第一次运行会下载大量数据，耗时约10-30分钟（取决于网络和数据量）。后续运行可使用缓存加速。

