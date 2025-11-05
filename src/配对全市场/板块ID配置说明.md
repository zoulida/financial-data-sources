# Wind板块ID配置说明

## 更新时间
2025-11-03 (最后更新)

## 当前配置

### Wind板块ID汇总

| 资产类型 | 板块ID | 接口 | 状态 |
|---------|--------|------|------|
| A股股票 | `a001010100000000` | w.wset("sectorconstituent") | ✅ 已确认 |
| 基金 | `1000052032000000` | w.wset("sectorconstituent") | ✅ 已确认 |
| 可转债 | `1000073208000000` | w.wset("sectorconstituent") | ✅ 已确认 |

## ✅ 板块ID已确认

**三类资产使用不同的板块ID，配置明确**

## 代码实现

### 股票获取 ✅
```python
data = w.wset("sectorconstituent", f"date={today};sectorid=a001010100000000")
```

### 基金获取 ✅
```python
data = w.wset("sectorconstituent", f"date={today};sectorid=1000052032000000")
```

### 可转债获取 ✅
```python
data = w.wset("sectorconstituent", f"date={today};sectorid=1000073208000000")
```

## 数据结构

### sectorconstituent 返回格式
```python
data.Data[0]  # 序号或日期
data.Data[1]  # 代码
data.Data[2]  # 名称
```

## 板块ID常量定义

建议在配置文件中定义：

```python
# Wind板块ID配置
SECTOR_IDS = {
    'stock': 'a001010100000000',      # A股股票
    'fund': '1000052032000000',       # 基金
    'bond': '1000073208000000'        # 可转债
}
```

## 测试示例

测试获取各类资产：

```python
from WindPy import w
from datetime import datetime

w.start()
today = datetime.now().strftime('%Y-%m-%d')

# 测试股票
stock_data = w.wset("sectorconstituent", f"date={today};sectorid=a001010100000000")
print(f"股票数量: {len(stock_data.Data[1])}")

# 测试基金
fund_data = w.wset("sectorconstituent", f"date={today};sectorid=1000052032000000")
print(f"基金数量: {len(fund_data.Data[1])}")

# 测试可转债
bond_data = w.wset("sectorconstituent", f"date={today};sectorid=1000073208000000")
print(f"可转债数量: {len(bond_data.Data[1])}")
```

## 装饰器提醒

❗ **重要**: `@shelve_me_week` 装饰器不接受参数！

**错误用法**：
```python
@shelve_me_week(0)   # ❌ 错误
@shelve_me_week(-1)  # ❌ 错误
```

**正确用法**：
```python
@shelve_me_week  # ✅ 正确
```

---

## 总结

✅ **板块ID配置已确认并应用到代码中**

- 股票：`a001010100000000`
- 基金：`1000052032000000`
- 可转债：`1000073208000000`

所有数据获取函数已更新并使用正确的板块ID。

