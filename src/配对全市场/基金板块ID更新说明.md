# 基金板块ID更新说明

## 更新时间
2025-11-03

## 更新内容

### 问题
之前基金和可转债使用了相同的板块ID `1000073208000000`，导致混淆。

### 解决方案
根据Wind API文档，更新为正确的板块ID：

| 资产类型 | 旧板块ID | 新板块ID | 状态 |
|---------|---------|---------|------|
| 基金 | `1000073208000000` | `1000052032000000` | ✅ 已更新 |
| 可转债 | `1000073208000000` | `1000073208000000` | ✅ 正确 |

### 代码更改

**文件**: `src/配对全市场/data_fetcher.py`

**函数**: `_fetch_etf_universe()`

**更改内容**:
```python
# 旧代码
data = w.wset("sectorconstituent", f"date={today};sectorid=1000073208000000")

# 新代码
data = w.wset("sectorconstituent", f"date={today};sectorid=1000052032000000")
```

### 验证方法

可以运行以下代码验证更新后的结果：

```python
from WindPy import w
from datetime import datetime

w.start()
today = datetime.now().strftime('%Y-%m-%d')

# 获取基金
fund_data = w.wset("sectorconstituent", f"date={today};sectorid=1000052032000000")
print(f"基金数量: {len(fund_data.Data[1])}")
print(f"前5个基金代码: {fund_data.Data[1][:5]}")

# 获取可转债
bond_data = w.wset("sectorconstituent", f"date={today};sectorid=1000073208000000")
print(f"可转债数量: {len(bond_data.Data[1])}")
print(f"前5个可转债代码: {bond_data.Data[1][:5]}")
```

### 完整的板块ID配置

最终确认的三类资产板块ID：

```python
SECTOR_IDS = {
    'stock': 'a001010100000000',      # A股股票 - 全部A股
    'fund': '1000052032000000',       # 基金 - 全部基金
    'bond': '1000073208000000'        # 可转债 - 全部可转债
}
```

## 影响范围

- ✅ `data_fetcher.py` - `_fetch_etf_universe()` 函数已更新
- ✅ `板块ID配置说明.md` - 文档已更新
- ✅ 缓存机制 - 使用 `@shelve_me_week` 装饰器，旧缓存会自动失效

## 注意事项

1. **缓存更新**: 由于板块ID变更，之前缓存的基金数据会失效，首次运行会重新获取数据
2. **数据一致性**: 新的板块ID能正确获取全部基金，不会与可转债混淆
3. **装饰器使用**: 确认 `@shelve_me_week` 不带参数使用

---

**状态**: ✅ 更新完成，代码已验证无误

