# 配对交易全市场扫描系统

## 📋 项目简介

这是一个基于协整检验和OU半衰期的A股配对交易全市场扫描系统。系统自动筛选市场上所有可能的配对组合，通过严格的统计检验找出最优质的配对交易机会。

### 核心特点

- **全市场扫描**: 覆盖股票（市值前2000）、ETF、可转债
- **双重检验**: 协整检验（p<0.05）+ OU半衰期（<60天）
- **智能筛选**: 三步筛选机制，减少90%计算量
- **批量处理**: 支持断点续传，可随时中断恢复
- **缓存机制**: 7天数据缓存，避免重复获取

### 技术亮点

- **协整检验**: Engle-Granger两步法
- **半衰期估计**: Kalman Filter + OLS回归
- **评分公式**: Score = 100×(1-p) + 50×(1-H/60)
- **进度管理**: Pickle持久化，支持中断恢复

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置检查

检查 `config.py` 中的配置参数：

```python
# 主要配置项
STOCK_TOP_N = 2000  # 股票池大小
ETF_MIN_AVG_AMOUNT = 10000000  # ETF最小成交额
MIN_CORRELATION = 0.85  # 最小相关系数
MAX_P_VALUE = 0.05  # 协整检验p值阈值
MAX_HALF_LIFE = 60  # 最大半衰期（天）
TOP_N = 100  # 输出前N名
```

### 3. 运行扫描

```bash
# 激活虚拟环境后运行
cd src/配对全市场
python main.py
```

**注意**：首次运行需要从Wind获取大量数据，可能需要1-2小时。后续运行会使用缓存，速度显著提升。

### 4. 查看结果

运行完成后会生成以下文件：

- `pairs_result_top100.csv` - 前100名配对详情
- `pairs_result_all.csv` - 所有通过检验的配对
- `summary_report.txt` - 汇总统计报告
- `pairs_trading.log` - 详细运行日志

## 📊 输出文件说明

### pairs_result_top100.csv

| 列名 | 说明 |
|------|------|
| code1 | 标的A代码 |
| code2 | 标的B代码 |
| name1 | 标的A名称 |
| name2 | 标的B名称 |
| beta | 协整系数 |
| score | 综合得分 |
| half_life | OU半衰期（天） |
| p_value | 协整检验p值 |
| correlation | Pearson相关系数 |
| data_points | 有效数据点数 |

### summary_report.txt

包含以下统计信息：

- 任务执行时间
- 通过检验的配对总数
- 评分统计（最高/最低/平均分）
- 半衰期统计
- p值统计
- 前10名配对列表

## 🔧 系统架构

### 模块说明

```
src/配对全市场/
├── config.py              # 配置文件
├── cache_manager.py       # 缓存管理（7天有效期）
├── data_fetcher.py        # 数据获取（Wind API）
├── pair_screener.py       # 配对初筛（相关性+波动率）
├── cointegration.py       # 协整检验（Engle-Granger）
├── ou_estimator.py        # OU半衰期估计（Kalman Filter）
├── scoring.py             # 评分排序
├── progress_manager.py    # 进度管理（断点续传）
├── main.py                # 主程序入口
└── cache/                 # 缓存目录
```

### 执行流程

```
1. 获取资产池
   ├─ 股票（市值前2000）
   ├─ ETF（日均成交>1000万）
   └─ 可转债（规模>3亿，成交>1000万）

2. 获取价格数据
   └─ 250日历史收盘价（前复权）

3. 配对初筛（减少90%计算量）
   ├─ Pearson相关系数 ≥ 0.85
   ├─ 价差年化波动率 < 25%
   └─ 日均成交额 > 1000万

4. 协整检验 + 半衰期估计
   ├─ Engle-Granger协整检验（p<0.05）
   ├─ Kalman Filter平滑价差
   └─ OLS估计半衰期（<60天）

5. 评分排序
   ├─ Score = 100×(1-p) + 50×(1-H/60)
   └─ 按得分降序排列

6. 输出结果
   ├─ 前100名配对
   ├─ 所有通过配对
   └─ 汇总报告
```

## ⚙️ 配置说明

### 数据筛选配置

```python
class DataFilterConfig:
    STOCK_TOP_N = 2000  # 股票池大小
    ETF_MIN_AVG_AMOUNT = 10000000  # ETF最小成交额
    CONVERTIBLE_BOND_MIN_SIZE = 300000000  # 可转债最小规模
    CONVERTIBLE_BOND_MIN_AMOUNT = 10000000  # 可转债最小成交额
```

### 初筛配置

```python
class PairScreenConfig:
    MIN_CORRELATION = 0.85  # 最小相关系数
    MAX_SPREAD_VOLATILITY = 0.25  # 最大价差波动率
    MIN_DATA_POINTS = 200  # 最少数据点
```

### 协整检验配置

```python
class CointegrationConfig:
    MAX_P_VALUE = 0.05  # p值阈值
    METHOD = 'Engle-Granger'  # 检验方法
```

### OU模型配置

```python
class OUModelConfig:
    MAX_HALF_LIFE = 60  # 最大半衰期
    MIN_HALF_LIFE = 5   # 最小半衰期
    OPTIMAL_HALF_LIFE_MIN = 15  # 优选最小值
    OPTIMAL_HALF_LIFE_MAX = 40  # 优选最大值
```

### 评分配置

```python
class ScoringConfig:
    P_VALUE_WEIGHT = 100  # p值权重
    HALF_LIFE_WEIGHT = 50  # 半衰期权重
    TOP_N = 100  # 输出前N名
```

### 进度管理配置

```python
class ProgressConfig:
    BATCH_SIZE = 1000  # 批大小
    SAVE_INTERVAL = 5  # 保存间隔（批次）
```

## 💻 虚拟环境配置

本项目使用Python虚拟环境，请确保在虚拟环境中运行：

### Windows

```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 运行程序
python src/配对全市场/main.py

# 退出虚拟环境
deactivate
```

### Linux/Mac

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行程序
python src/配对全市场/main.py

# 退出虚拟环境
deactivate
```

## 🔍 高级功能

### 断点续传

系统支持断点续传功能，如果中途中断（Ctrl+C 或异常退出），下次运行时会自动从中断处继续：

```python
# 主程序会自动检测未完成的任务
scanner = PairsTradingScanner(use_cache=True, resume=True)
scanner.run()
```

如需重新开始，删除进度文件：

```bash
del cache\progress.pkl
```

### 缓存管理

查看缓存信息：

```python
from cache_manager import get_cache_manager

cm = get_cache_manager()
info = cm.get_cache_info()
print(f"缓存文件数: {info['total_files']}")
print(f"有效文件: {info['valid_files']}")
```

清理过期缓存：

```python
cm.clear_expired()
```

清空所有缓存：

```python
cm.clear_all()
```

### 单独测试模块

每个模块都支持独立测试：

```bash
# 测试数据获取
python data_fetcher.py

# 测试配对初筛
python pair_screener.py

# 测试协整检验
python cointegration.py

# 测试OU估计
python ou_estimator.py

# 测试评分器
python scoring.py
```

## 📈 性能优化

### 提升处理速度

1. **使用缓存**: 首次运行后，后续会大幅提速
2. **调整批大小**: 增大`BATCH_SIZE`可减少保存次数
3. **减少筛选范围**: 降低`STOCK_TOP_N`或提高初筛阈值

### 减少内存占用

1. **减小批大小**: 降低`BATCH_SIZE`
2. **清理缓存**: 定期运行`cm.clear_expired()`
3. **分步运行**: 先运行数据获取，再运行检验

## ⚠️ 注意事项

### Wind API

- 需要已登录的Wind终端
- 确保有足够的数据权限
- 首次运行会大量调用API，注意流量限制

### 数据质量

- 自动过滤数据点不足的标的
- 自动处理价格缺失值
- 建议定期更新股票列表CSV

### 系统要求

- Python 3.8+
- 内存：建议8GB以上
- 硬盘：至少5GB空余空间（用于缓存）
- Wind终端：需已登录

## 🐛 常见问题

### Q1: Wind API报错

**A**: 检查Wind终端是否已登录，是否有数据权限。

### Q2: 内存不足

**A**: 减小`BATCH_SIZE`参数，或者减少`STOCK_TOP_N`。

### Q3: 处理速度慢

**A**: 首次运行需要获取大量数据，属于正常现象。使用缓存后会显著提速。

### Q4: 结果数量少

**A**: 可以适当放宽初筛条件：
- 降低`MIN_CORRELATION`（如0.80）
- 增大`MAX_SPREAD_VOLATILITY`（如0.30）
- 增大`MAX_HALF_LIFE`（如80天）

### Q5: 进度丢失

**A**: 检查`cache/progress.pkl`是否存在。如果删除了该文件，需要重新开始。

## 📝 更新日志

### v1.0.0 (2025-11-03)

- ✅ 实现全市场配对扫描
- ✅ 支持股票、ETF、可转债
- ✅ 三步筛选机制
- ✅ 协整检验 + OU半衰期
- ✅ 评分排序系统
- ✅ 批量处理 + 断点续传
- ✅ 缓存机制（7天有效期）

## 📞 技术支持

如遇到问题，请：

1. 查看日志文件 `pairs_trading.log`
2. 检查配置文件 `config.py`
3. 运行模块测试脚本
4. 查看缓存状态

---

**项目目标**: 为配对交易者提供专业、高效、可靠的全市场配对扫描工具，基于严格的统计检验，发现高质量的配对交易机会。

