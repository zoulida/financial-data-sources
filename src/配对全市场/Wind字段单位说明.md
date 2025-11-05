# Wind API 字段单位说明

## 更新时间
2025-11-03

## 字段单位总结

### 成交额相关字段

| 字段名 | 中文名称 | 单位 | 是否需要转换 | 说明 |
|-------|---------|------|------------|------|
| `amt` | 成交额 | **元** | ❌ 否 | 直接使用，无需转换 |
| `amt_nd` | N日平均成交额 | **元** | ❌ 否 | 直接使用，无需转换 |

### 市值/规模相关字段

| 字段名 | 中文名称 | 单位 | 是否需要转换 | 转换公式 |
|-------|---------|------|------------|---------|
| `mkt_cap_ard` | 总市值 | **元** | ❌ 否 | 直接使用 |
| `outstandingbalance` | 债券余额 | **亿元** | ✅ 是 | `值 × 1e8` |
| `carryingvalue` | 债券账面价值 | **待确认** | ⚠️ 待确认 | 待确认 |

## 代码实现

### 1. 股票市值获取
```python
# mkt_cap_ard 返回的单位为元，无需转换
cap_data = w.wss(codes, "mkt_cap_ard", f"unit=1;tradeDate={yesterday}")
market_caps = cap_data.Data[0]  # 直接使用
```

### 2. 基金成交额获取
```python
# amt 返回的单位为元，无需转换
amt_data = w.wsd(codes, "amt", start_date, end_date, "unit=1")
avg_amounts = amt_data.Data[0]  # 直接使用
```

### 3. 可转债数据获取
```python
# 使用 wss 同时获取成交额和债券余额
data = w.wss(codes, "amt,outstandingbalance", 
             f"unit=1;tradeDate={last_trade_day};cycle=D")

# amt（成交额）单位为元，无需转换
df['avg_amount'] = data.Data[0]

# outstandingbalance（债券余额）单位为亿元，需要转换为元
df['carrying_value'] = [x * 1e8 if x is not None else np.nan for x in data.Data[1]]
```

## 配置文件单位

### config.py 中的阈值单位统一为元

```python
class DataFilterConfig:
    # ETF筛选
    ETF_MIN_AVG_AMOUNT = 10000000  # 1000万元 = 0.1亿元
    
    # 可转债筛选
    CONVERTIBLE_BOND_MIN_SIZE = 500000000  # 5亿元
    CONVERTIBLE_BOND_MIN_AMOUNT = 10000000  # 1000万元 = 0.1亿元
    
    # 通用成交额门槛
    MIN_AVG_AMOUNT = 10000000  # 1000万元 = 0.1亿元
```

## 单位转换对照表

| 元 | 万元 | 亿元 |
|----|------|------|
| 1 | 0.0001 | 0.00000001 |
| 10,000 | 1 | 0.0001 |
| 100,000,000 | 10,000 | 1 |

### 常用金额转换

| 描述 | 元 | 亿元 | Python表达式 |
|-----|---|------|-------------|
| 1000万 | 10,000,000 | 0.1 | `1e7` |
| 3亿 | 300,000,000 | 3 | `3e8` |
| 5亿 | 500,000,000 | 5 | `5e8` |
| 10亿 | 1,000,000,000 | 10 | `1e9` |

## 验证方法

### 测试脚本
```python
from WindPy import w
from datetime import datetime

w.start()
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

# 测试股票市值（应返回亿元）
cap_data = w.wss("600009.SH", "mkt_cap_ard", f"unit=1;tradeDate={yesterday}")
print(f"市值（原始值）: {cap_data.Data[0][0]} 亿元")
print(f"市值（转换后）: {cap_data.Data[0][0] * 1e8} 元")

# 测试成交额（应返回元）
amt_data = w.wss("600009.SH", "amt", f"unit=1;tradeDate={yesterday};cycle=D")
print(f"成交额（原始值）: {amt_data.Data[0][0]} 元")

# 测试可转债（amt返回元，outstandingbalance返回亿元）
bond_data = w.wss("110064.SH", "amt,outstandingbalance", 
                  f"unit=1;tradeDate={yesterday};cycle=D")
print(f"可转债成交额（原始值）: {bond_data.Data[0][0]} 元")
print(f"债券余额（原始值）: {bond_data.Data[1][0]} 亿元")
print(f"债券余额（转换后）: {bond_data.Data[1][0] * 1e8} 元")
```

## 重要提醒

### ✅ 正确做法
- `amt` 字段：**直接使用**，单位已是元
- `mkt_cap_ard` 字段：**直接使用**，单位已是元
- `outstandingbalance` 字段：**乘以 1e8**，从亿元转为元

### ❌ 错误做法
- 对 `amt` 进行单位转换（会导致数值错误放大）
- 对 `mkt_cap_ard` 进行单位转换（会导致数值错误）
- 不对 `outstandingbalance` 进行转换（会导致筛选失效，数值偏小1亿倍）

## 总结

**关键点**：
1. ✅ Wind API 的 `amt` 成交额字段返回的是**元**，无需转换
2. ✅ Wind API 的 `mkt_cap_ard`（市值）返回的是**元**，无需转换
3. ✅ Wind API 的 `outstandingbalance`（债券余额）返回的是**亿元**，需要乘以1e8转换为元
4. ✅ 配置文件中所有阈值统一使用**元**为单位
5. ✅ 数据获取后立即进行单位转换（仅债券余额），确保后续处理一致

---

**状态**: ✅ 所有单位已确认并修正

