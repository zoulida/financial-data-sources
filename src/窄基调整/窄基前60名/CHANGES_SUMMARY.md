# 修改总结

## 主要修改

### 1. `analyze_performance.py` - 使用项目的数据下载模块

**修改内容:**
- 删除了 Wind API 和 XtQuant API 的导入
- 改为使用项目的 `source.实盘.xuntou.datadownload.合并下载数据` 模块
- 使用 `getDayData` 函数获取股票K线数据

**优势:**
- 使用项目统一的缓存机制
- 无需启动 Wind 终端即可分析股票表现
- 数据格式统一，减少转换工作

### 2. 数据获取逻辑

**原来:**
```python
# 使用 Wind API
data = w.wsd(stock_code, "close,volume", start_date, end_date, "PriceAdj=F")
```

**现在:**
```python
# 使用项目数据下载模块
df = getDayData(
    stock_code=stock_code,
    start_date=start_str,
    end_date=end_str,
    is_download=0,  # 从缓存读取
    dividend_type='front'  # 前复权
)
```

### 3. 更新了 `check_api.py`

现在检查两个模块：
1. Wind API - 用于 `download_changes.py`（下载指数变动数据）
2. 项目数据下载模块 - 用于 `analyze_performance.py`（分析股票表现）

### 4. 更新了文档

在 `README.md` 中说明了：
- 两种不同的数据源使用场景
- Wind API 仅用于下载变动数据
- 项目数据下载模块用于分析股票表现

## 使用流程

### 步骤1: 下载变动数据（需要 Wind API）
```bash
python download_changes.py
```
或双击运行 `run_download.bat`

### 步骤2: 分析股票表现（使用项目数据模块）
```bash
python analyze_performance.py
```
或双击运行 `run_analysis.bat`

### 快速检查
```bash
python check_api.py
```
或双击运行 `check_api.bat`

## 数据流

```
指数变动数据 (Wind API)
    ↓
download_changes.py
    ↓
*_changes.csv 文件
    ↓
analyze_performance.py
    ↓
getDayData() 获取股票K线
    ↓
分析结果 CSV 文件
```

## 注意事项

1. **下载变动数据** 需要 Wind 终端启动
2. **分析股票表现** 不需要 Wind 终端，使用项目数据缓存
3. 如果第一次分析，股票数据可能还未缓存，会自动下载
4. 项目数据下载模块使用迅投(XTQuant)数据接口

## 文件说明

- `download_changes.py` - 使用 Wind API 下载指数变动数据
- `analyze_performance.py` - 使用项目数据模块分析股票表现
- `check_api.py` - 检查两个模块是否可用
- `README.md` - 完整的使用说明

