# 日期范围获取工具

## 功能说明

这个工具用于自动计算数据获取的日期范围，特别适用于金融数据的定期获取场景。

### 日期计算规则

- **start_date**: 固定为 `20241101`
- **end_date**: 根据以下规则动态计算
  1. **如果当天是交易日**：
     - 21:00 之后 → 使用当天日期
     - 21:00 之前 → 使用上一个交易日
  2. **如果当天不是交易日**：
     - 使用上一个交易日

## 安装依赖

程序依赖于外部交易日历工具，路径：`D:\pythonworkspace\zldtools\tools\tradeCal.py`

需要安装的Python包：
```bash
pip install exchange-calendars akshare pandas
```

## 使用方法

### 方式1：直接运行查看结果

```bash
python get_date_range.py
```

输出示例：
```
============================================================
日期范围计算工具
============================================================
当前时间: 2025-11-02 18:05:47
当前日期: 20251102
是否交易日: 否
------------------------------------------------------------
计算原因: 今天不是交易日
start_date: 20241101
end_date:   20251031
------------------------------------------------------------
带横杠格式:
start_date: 2024-11-01
end_date:   2025-10-31
============================================================
```

### 方式2：在代码中导入使用

#### 示例1：获取基本格式（YYYYMMDD）

```python
from get_date_range import get_date_range

start_date, end_date, reason = get_date_range()
print(f"start_date: {start_date}")  # '20241101'
print(f"end_date: {end_date}")      # '20251031'
print(f"原因: {reason}")             # '今天不是交易日'
```

#### 示例2：获取带横杠格式（YYYY-MM-DD）

```python
from get_date_range import get_date_range_formatted

start_date, end_date, reason = get_date_range_formatted(with_dash=True)
print(f"start_date: {start_date}")  # '2024-11-01'
print(f"end_date: {end_date}")      # '2025-10-31'
```

#### 示例3：在数据获取中使用

```python
from get_date_range import get_date_range
import WindPy as w

# 获取日期范围
start_date, end_date, reason = get_date_range()
print(f"数据获取区间: {start_date} 至 {end_date} ({reason})")

# 使用Wind API获取数据
w.start()
data = w.wsd(
    "000001.SZ",
    "close,volume",
    start_date,
    end_date
)
```

#### 示例4：在XtQuant中使用

```python
from get_date_range import get_date_range_formatted
from xtquant import xtdata

# 获取带横杠格式的日期
start_date, end_date, reason = get_date_range_formatted(with_dash=True)
print(f"数据获取区间: {start_date} 至 {end_date} ({reason})")

# 使用XtQuant获取行情数据
data = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume'],
    stock_list=['000001.SZ'],
    start_time=start_date,
    end_time=end_date,
    period='1d'
)
```

## API 文档

### `get_date_range()`

获取日期范围（基本格式）

**返回值：**
- `tuple`: (start_date, end_date, reason)
  - start_date (str): 起始日期，格式 "YYYYMMDD"
  - end_date (str): 结束日期，格式 "YYYYMMDD"
  - reason (str): 计算原因说明

**示例：**
```python
start, end, reason = get_date_range()
# ('20241101', '20251031', '今天不是交易日')
```

### `get_date_range_formatted(with_dash=False)`

获取格式化的日期范围

**参数：**
- `with_dash` (bool): 是否使用带横杠的格式，默认 False

**返回值：**
- `tuple`: (start_date, end_date, reason)
  - 如果 with_dash=False: 格式为 "YYYYMMDD"
  - 如果 with_dash=True: 格式为 "YYYY-MM-DD"

**示例：**
```python
# 基本格式
start, end, reason = get_date_range_formatted(with_dash=False)
# ('20241101', '20251031', '今天不是交易日')

# 带横杠格式
start, end, reason = get_date_range_formatted(with_dash=True)
# ('2024-11-01', '2025-10-31', '今天不是交易日')
```

### `format_date_with_dash(date_str)`

将日期格式从 YYYYMMDD 转换为 YYYY-MM-DD

**参数：**
- `date_str` (str): 格式为 "YYYYMMDD" 的日期字符串

**返回值：**
- `str`: 格式为 "YYYY-MM-DD" 的日期字符串

**示例：**
```python
date = format_date_with_dash("20251101")
# '2025-11-01'
```

### `print_date_info()`

打印当前日期信息和计算结果（用于调试）

**示例：**
```python
print_date_info()
# 输出详细的日期计算信息
```

## 场景说明

### 场景1：交易日早上运行（8:00）
- 当前：2025-11-03 08:00（假设是交易日）
- 结果：end_date = 2025-11-01（上一个交易日）
- 原因：今天是交易日但未到21点

### 场景2：交易日晚上运行（22:00）
- 当前：2025-11-03 22:00（假设是交易日）
- 结果：end_date = 2025-11-03（当天）
- 原因：今天是交易日且已过21点

### 场景3：周末运行
- 当前：2025-11-02 18:05（周六）
- 结果：end_date = 2025-10-31（上周五）
- 原因：今天不是交易日

## 注意事项

1. 确保 `D:\pythonworkspace\zldtools\tools\tradeCal.py` 路径正确
2. 需要安装 `exchange-calendars` 库用于交易日历查询
3. 首次运行会下载交易日历数据，可能需要几秒钟
4. 交易日历数据会被缓存，后续运行会更快

## 文件结构

```
md/获取enddate/
├── get_date_range.py   # 主程序
└── README.md          # 使用说明（本文件）
```

## 依赖的外部函数

来自 `tradeCal.py`：
- `is_open_day(date)`: 判断指定日期是否为交易日
- `getLastOpenDay(date)`: 获取指定日期的上一个交易日

## 更新日志

### 2025-11-02
- 初始版本发布
- 实现基本的日期范围计算功能
- 支持多种日期格式输出

