# Wind API 使用说明和修复记录

## 🔧 已修复的问题

### 问题描述
程序运行时出现错误：`module 'WindPy' has no attribute 'start'`

### 原因分析
Wind API 的导入方式错误：
```python
# ❌ 错误的导入方式
import WindPy as w
w.start()
```

### 解决方案
正确的 Wind API 导入方式：
```python
# ✅ 正确的导入方式
from WindPy import w
w.start()
```

## 📊 Wind API 数据获取方法

### 1. 融资余额数据

#### 正确的获取方式（使用 wset 接口）⭐ 推荐

```python
from WindPy import w
import pandas as pd
from datetime import datetime, timedelta

# 启动Wind API
w.start()

# 设置时间范围
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

# 使用 wset 接口获取融资融券交易规模数据
# 这是获取融资余额数据的标准方法
params = (
    f"exchange=all;"  # 全市场数据
    f"startdate={start_date};"
    f"enddate={end_date};"
    f"frequency=day;"  # 日度数据
    f"sort=desc"  # 降序排列，最新数据在前
)

data = w.wset("margintradingsizeanalys(value)", params)

if data.ErrorCode == 0 and data.Data:
    # 转换为DataFrame
    df = pd.DataFrame(data.Data, index=data.Fields).T
    df.columns = data.Fields
    
    # 获取期间净买入额（period_net_purchases）
    if 'period_net_purchases' in df.columns:
        net_buy_values = df['period_net_purchases'].head(3).tolist()
        net_buy_values = [float(v) for v in net_buy_values if v is not None]
        
        print(f"最近3日融资净买入额:")
        for i, v in enumerate(net_buy_values):
            print(f"  第{i+1}日: {v/100000000:.2f} 亿元")
    else:
        print("未找到期间净买入额字段")
else:
    print(f"错误码: {data.ErrorCode}")

# 关闭Wind API
w.stop()
```

#### 旧方法（不推荐）

```python
# ❌ 此方法可能不稳定，不推荐使用
# data = w.wsd("881001.WI", "margin_netbuyamt", start_date, end_date, "")
```

#### wset 接口返回字段说明（推荐使用）

| Wind字段 | 中文名称 | 说明 |
|---------|---------|------|
| `end_date` | 日期 | 交易日期 |
| `margin_balance` | 融资余额 | 当日融资余额总额 |
| `period_net_purchases` | 期间净买入额 | ⭐ 融资买入额 - 融资偿还额 |
| `period_bought_amount` | 期间买入额 | 期间融资买入金额 |
| `period_paid_amount` | 期间偿还额 | 期间融资偿还金额 |
| `margin_balance_ratio_negmktcap` | 融资余额占流通市值比 | 融资余额占流通市值的百分比 |
| `buy_count` | 期间融资买入个股数 | 融资买入的股票数量 |

**重要**: 使用 `w.wset("margintradingsizeanalys(value)")` 接口获取数据

### 2. 开户数数据

```python
from WindPy import w
from datetime import datetime, timedelta

w.start()

# 获取新增投资者数（月度数据）
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

# M0001780: 新增A股账户数（月度）
data = w.edb("M0001780", start_date, end_date, "")

if data.ErrorCode == 0 and len(data.Data[0]) >= 2:
    recent_two = data.Data[0][-2:]  # 最近两个月
    last_month = recent_two[-1]
    prev_month = recent_two[-2]
    
    change_rate = (last_month - prev_month) / prev_month * 100
    print(f"环比变化: {change_rate:+.1f}%")

w.stop()
```

#### 常用经济数据库代码

| 代码 | 名称 | 频率 |
|------|-----|------|
| `M0001780` | 新增A股账户数 | 月度 |
| `M0001781` | 期末A股账户数 | 月度 |
| `M0001782` | 有效A股账户数 | 月度 |

### 3. 上证指数行情数据

```python
from WindPy import w

w.start()

# 获取上证指数最近5日行情
data = w.wsd("000001.SH", "close,volume", "-5TD", "TD", "")

if data.ErrorCode == 0:
    closes = data.Data[0]
    volumes = data.Data[1]
    print(f"收盘价: {closes}")
    print(f"成交量: {volumes}")

w.stop()
```

## 🚨 常见错误和解决方法

### 错误1: ImportError: No module named 'WindPy'

**原因**: 未安装 WindPy 包

**解决方法**:
```bash
# 1. 确保已安装 Wind 金融终端
# 2. 在 Wind 终端安装目录下找到 WindPy
# 3. 或者直接安装
pip install WindPy
```

### 错误2: Wind API 无法连接

**原因**: Wind 终端未启动或未登录

**解决方法**:
1. 启动 Wind 金融终端
2. 登录 Wind 账号
3. 确保终端保持运行状态
4. 再运行 Python 程序

### 错误3: ErrorCode != 0

**原因**: 数据请求失败

**常见错误码**:
- `-40520007`: 没有可用数据
- `-40520010`: 时间区间无数据
- `-40520020`: 数据正在加载中

**解决方法**:
1. 检查时间范围是否合理
2. 检查代码是否正确
3. 稍后重试

### 错误4: 数据返回 None

**原因**: 非交易日或数据未更新

**解决方法**:
```python
# 过滤 None 值
net_buy_values = [v for v in data.Data[0] if v is not None]
```

## 📝 最佳实践

### 1. 启动和关闭

```python
from WindPy import w

try:
    w.start()
    # 执行数据获取操作
    data = w.wsd(...)
    
    # 处理数据
    if data.ErrorCode == 0:
        # ...
    
finally:
    w.stop()  # 确保关闭连接
```

### 2. 错误处理

```python
from WindPy import w

try:
    w.start()
    data = w.wsd("000001.SH", "close", "-5TD", "TD", "")
    
    if data.ErrorCode != 0:
        print(f"Wind API 错误: {data.ErrorCode}")
        return None
    
    if not data.Data or len(data.Data[0]) == 0:
        print("未获取到数据")
        return None
    
    # 处理数据
    result = data.Data[0]
    
except Exception as e:
    print(f"异常: {e}")
    return None
    
finally:
    w.stop()
```

### 3. 时间处理

```python
from datetime import datetime, timedelta

# 使用交易日 (TD = Trading Day)
data = w.wsd("000001.SH", "close", "-5TD", "TD", "")

# 或使用具体日期
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
data = w.wsd("000001.SH", "close", start_date, end_date, "")
```

## 🔍 数据验证

### 测试 Wind API 是否可用

运行测试脚本：
```bash
python test_data_sources.py
```

或手动测试：
```python
from WindPy import w

w.start()
print(f"Wind API 是否已登录: {w.isconnected()}")

# 简单测试
data = w.wsd("000001.SH", "close", "-1TD", "TD", "")
print(f"错误码: {data.ErrorCode}")
if data.ErrorCode == 0:
    print(f"上证指数收盘价: {data.Data[0][0]}")

w.stop()
```

## 📚 更多资源

### Wind API 官方文档
- Wind 金融终端内置帮助文档
- API 函数说明: 在 Wind 终端中按 F1

### 常用函数

| 函数 | 用途 | 示例 |
|------|-----|------|
| `w.wsd()` | 时间序列数据 | `w.wsd("000001.SH", "close", "-5TD", "TD")` |
| `w.wss()` | 截面数据 | `w.wss("000001.SH,000002.SZ", "pe_ttm")` |
| `w.wsi()` | 分钟数据 | `w.wsi("000001.SH", "close", "09:30:00", "15:00:00")` |
| `w.edb()` | 经济数据库 | `w.edb("M0001780", "20240101", "20241231")` |

## ✅ 修复确认

运行程序后，应该看到：
```
[1/4] 正在获取融资余额数据...
  ✓ Wind数据：融资净买入情况正常，得分: 0.0
    最近3日数据: ['89.23亿', '102.45亿', '76.89亿']
```

而不是：
```
[1/4] 正在获取融资余额数据...
  ✗ Wind API获取失败: module 'WindPy' has no attribute 'start'
```

---

**修复日期**: 2025-10-20  
**修复内容**: Wind API 导入方式和数据获取逻辑  
**测试状态**: ✅ 已通过测试

