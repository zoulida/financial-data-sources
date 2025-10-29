# 窄基前60名指数成分股变动分析

## 项目说明

本项目分析窄基前60名指数的成分股变动，统计新纳入股票在数据截止日和生效日前后5个交易日的表现。

## 文件说明

### 数据文件
- `zhaiji_top_indices_list.csv` - 窄基前60名指数列表（指数代码、名称、基金规模）

### 程序文件
- `download_changes.py` - 下载指数变动数据
- `analyze_performance.py` - 分析新纳入股票表现

## 使用步骤

### 1. 下载变动数据

```bash
cd "D:\pythonProject\数据源\src\窄基调整\窄基前60名"
python download_changes.py
```

**功能说明:**
- 读取 `zhaiji_top_indices_list.csv` 中的指数列表
- 使用Wind API下载每个指数的成分股变动数据
- 自动跳过已下载的数据
- 生成 `download_summary.csv` 汇总报告

**输出文件:**
- `{指数名称}_{指数代码}_changes.csv` - 各指数的变动数据
- `download_summary.csv` - 下载汇总报告

### 2. 分析股票表现

```bash
python analyze_performance.py
```

**功能说明:**
- 读取所有 `*_changes.csv` 变动数据文件
- 计算每个指数的数据截止日和生效日
- 获取新纳入股票在关键日期的前后5个交易日表现
- 分析涨跌幅、胜率、成交量变化等指标

**输出文件:**
- `zhaiji_stocks_performance.csv` - 详细股票表现数据
- `zhaiji_summary.csv` - 按指数汇总统计

## 分析方法

### 关键日期计算

1. **生效日**: 指数调整生效的日期（从变动数据中获取）
2. **数据截止日**: 生效日前第二个自然月的最后一个自然日
   - 例如：生效日为 2025-06-16
   - 前第二个自然月为 2025-04
   - 数据截止日为 2025-04-30

### 观察窗口

- **数据截止日窗口**: 数据截止日前5个交易日 + 当日 + 后5个交易日（共11个交易日）
- **生效日窗口**: 生效日前5个交易日 + 当日 + 后5个交易日（共11个交易日）

### 分析指标

对每只新纳入的股票，计算以下指标：

1. **涨跌幅**
   - 平均日涨跌幅
   - 累计涨跌幅
   - 最大/最小日涨跌幅
   - 波动率

2. **胜率**
   - 上涨天数占比

3. **成交量变化**
   - 成交量变化率

## 数据源

### 数据源

程序使用以下数据源：
1. **Wind API** - 获取指数成分股变动历史（`w.wset("indexhistory")`）
2. **项目数据下载模块** - 获取股票日线行情数据（`getDayData`）
   - 模块路径：`source.实盘.xuntou.datadownload.合并下载数据`
   - 使用迅投(XTQuant)数据接口
   - 支持缓存机制，避免重复下载

### 数据时间范围

- 默认开始日期: 2023-01-01
- 结束日期: 当前日期

## 指数列表

`zhaiji_top_indices_list.csv` 包含60个窄基指数，按基金规模排序：

前10名指数：
1. 证券公司 (399975.SZ) - 968.41亿元
2. 国证芯片 (980017.CNI) - 491.03亿元
3. 中证医疗 (399989.SZ) - 402.06亿元
4. 中证白酒 (399997.SZ) - 397.00亿元
5. 红利低波 (h30269.CSI) - 384.45亿元
6. CS人工智能 (930713.CSI) - 373.18亿元
7. 中证银行 (399986.SZ) - 347.65亿元
8. 中证军工 (399967.SZ) - 340.46亿元
9. 机器人 (h30590.CSI) - 304.30亿元
10. 中证红利 (000922.CSI) - 275.64亿元

完整列表共60个指数，均排除了：
- 港股通相关指数
- 综合指数（如沪深300、中证500等）
- 全指、全市场类指数

## 快速检查API

在运行分析前，建议先检查API是否可用：

```bash
python check_api.py
```
或双击运行 `check_api.bat`

**检查内容:**
- XtQuant API 可用性
- Wind API 可用性
- 测试查询是否成功

## 注意事项

1. **API访问**
   - 下载变动数据：需要Wind API（运行 `download_changes.py` 时）
   - 分析股票表现：使用项目的数据下载模块（运行 `analyze_performance.py` 时）
   - **重要**: 
     - 运行下载变动数据前，请确保 Wind 终端已启动
     - 分析股票表现时，使用项目的数据缓存，无需Wind终端

2. **常见问题**
   - 如果遇到 `name 'USE_WIND' is not defined` 错误
     - 确保 Wind 终端已启动
     - 运行 `python check_api.py` 检查API状态
     - 重启Wind终端后重试

3. **运行时间**
   - 下载60个指数数据约需10-20分钟
   - 分析过程需要获取大量股票数据，可能需要较长时间

4. **数据存储**
   - 变动数据文件保存在当前目录
   - 建议定期备份数据

5. **错误处理**
   - 程序会自动重试失败的API调用
   - 下载失败的指数会记录在输出中

## 快速开始

```bash
# 进入目录
cd "D:\pythonProject\数据源\src\窄基调整\窄基前60名"

# 步骤0: 检查API是否可用（推荐）
python check_api.py

# 步骤1: 下载变动数据
python download_changes.py

# 步骤2: 分析股票表现
python analyze_performance.py
```

或者使用批处理文件：
1. 先运行 `check_api.bat` 检查API
2. 再运行 `run_download.bat` 下载数据
3. 最后运行 `run_analysis.bat` 进行分析

## 输出文件说明

### 变动数据文件格式

**文件名:** `{指数名称}_{指数代码}_changes.csv`

**字段说明:**
- `tradedate` - 交易日期（生效日）
- `tradecode` - 股票代码
- `tradename` - 股票名称
- `windhy` - 行业分类
- `mv` - 市值
- `weight` - 权重
- `tradestatus` - 交易状态（纳入/剔除）
- `changepctbefore` - 调整前涨跌幅
- `changepctafter` - 调整后涨跌幅

### 分析结果文件格式

**详细结果:** `zhaiji_stocks_performance.csv`
- `index_name` - 指数名称
- `index_code` - 指数代码
- `stock_code` - 股票代码
- `center_date` - 观察中心日期
- `window_type` - 窗口类型（cutoff_date/effective_date）
- `cumulative_return` - 累计涨跌幅
- `win_rate` - 胜率
- `volatility` - 波动率
- 等...

**汇总报告:** `zhaiji_summary.csv`
- 按指数汇总的统计指标
- 平均累计涨跌幅、胜率等

## 后续分析

可以根据生成的结果进行进一步分析：
- 比较不同指数的纳入效应
- 分析数据截止日和生效日的表现差异
- 研究不同行业的纳入效应

