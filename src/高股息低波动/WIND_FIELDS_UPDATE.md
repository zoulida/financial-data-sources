# Wind字段更新说明

## 📋 问题与解决方案

根据实际测试，部分Wind字段无法直接获取，需要通过计算或查询历史数据得到。

### 1. 股息率 ✅ 直接可用

**字段**: `dividendyield2`  
**说明**: 股息率（近12个月）  
**用法**:
```python
data = w.wss("000001.SZ", "dividendyield2", "tradeDate=20241231")
```

### 2. 连续分红年限 ⚠️ 需要计算

**原字段**: `continuousdividendyears` ❌ 无数据  
**解决方案**: 使用 `div_ifdiv` 按年度查询

**字段**: `div_ifdiv`  
**说明**: 是否分红（1=分红，0=不分红）  
**用法**:
```python
# 查询2024年是否分红
data = w.wss("000001.SZ", "div_ifdiv", "rptDate=20241231")

# 查询多年连续分红
for year in range(2020, 2025):
    data = w.wss(codes, "div_ifdiv", f"rptDate={year}1231")
    # 从最近年份开始，连续为1的年数即为连续分红年限
```

**实现函数**: `calculate_dividend_years()`

### 3. 股息支付率 ⚠️ 需要计算

**原字段**: `s_fa_dividentbt` ❌ 无数据  
**解决方案**: 手动计算

**公式**:
```
股息支付率 = 年度累计单位分红 ÷ 每股收益（EPS）× 100%
```

**所需字段**:
- `div_aualaccmdivpershare` - 年度累计单位分红
- `eps_basic` - 基本每股收益

**用法**:
```python
data = w.wss(
    "000001.SZ", 
    "div_aualaccmdivpershare,eps_basic", 
    "rptDate=20241231"
)

div_per_share = data.Data[0][0]  # 年度累计分红
eps = data.Data[1][0]             # 每股收益
payout_ratio = (div_per_share / eps) * 100  # 股息支付率（%）
```

**实现函数**: `get_multi_year_payout_ratio()` 已更新

## 📊 更新后的数据获取流程

### 步骤1: 获取股息率
```python
dividend_df = fetcher.get_dividend_data(stocks)
# 返回: stock_code, stock_name, dividend_yield
```

### 步骤2: 计算连续分红年限
```python
dividend_years_df = fetcher.calculate_dividend_years(stocks, years=5)
# 返回: stock_code, dividend_years, total_years_checked
```

### 步骤3: 计算股息支付率
```python
payout_df = fetcher.get_multi_year_payout_ratio(stocks, years=3)
# 返回: stock_code, avg_payout_ratio, payout_std, payout_count
```

## 🔄 代码变更总结

### wind_data_fetcher.py

#### 修改的函数

1. **get_dividend_data()**
   - **之前**: 获取 `dividendyield2`, `s_fa_dividentbt`, `continuousdividendyears`
   - **现在**: 只获取 `dividendyield2`（股息率）
   - **原因**: 后两个字段无数据

2. **get_multi_year_payout_ratio()**
   - **之前**: 获取 `s_fa_dividentbt`
   - **现在**: 获取 `div_aualaccmdivpershare` 和 `eps_basic`，计算支付率
   - **原因**: 原字段无数据，需要手动计算

#### 新增的函数

3. **calculate_dividend_years()** ⭐ 新增
   - **功能**: 计算连续分红年限
   - **方法**: 查询历史N年的 `div_ifdiv`，统计连续分红年数
   - **参数**: `years=5` 查询过去5年

### main.py

#### 修改的流程

**step2_fetch_data()** 更新：
```python
# 之前
dividend_df = fetcher.get_dividend_data(stocks)

# 现在
dividend_df = fetcher.get_dividend_data(stocks)  # 只获取股息率
dividend_years_df = fetcher.calculate_dividend_years(stocks, years=5)  # 计算分红年限
dividend_df = dividend_df.merge(dividend_years_df, on="stock_code")  # 合并
```

## 📁 输出文件变化

新增文件：
- `dividend_years_TIMESTAMP.csv` - 连续分红年限数据

修改文件：
- `dividend_data_TIMESTAMP.csv` - 现在包含合并后的分红年限
- `payout_data_TIMESTAMP.csv` - 现在是计算得到的支付率

## 🎯 字段映射对照表

| 需求 | 原计划字段 | 状态 | 实际方案 |
|------|-----------|------|----------|
| 股息率 | `dividendyield2` | ✅ 可用 | 直接获取 |
| 连续分红年限 | `continuousdividendyears` | ❌ 无数据 | 用 `div_ifdiv` 计算 |
| 股息支付率 | `s_fa_dividentbt` | ❌ 无数据 | 用 `div_aualaccmdivpershare ÷ eps_basic` |

## 📝 使用示例

### 完整测试代码

```python
from src.高股息低波动.wind_data_fetcher import WindDataFetcher

fetcher = WindDataFetcher()

# 测试股票列表
test_stocks = ["000001.SZ", "600519.SH", "000002.SZ"]

# 1. 获取股息率
print("=" * 80)
print("获取股息率")
dividend_df = fetcher.get_dividend_data(test_stocks)
print(dividend_df)
# 输出: stock_code, stock_name, dividend_yield

# 2. 计算连续分红年限
print("\n" + "=" * 80)
print("计算连续分红年限")
years_df = fetcher.calculate_dividend_years(test_stocks, years=5)
print(years_df)
# 输出: stock_code, dividend_years, total_years_checked

# 3. 计算股息支付率
print("\n" + "=" * 80)
print("计算股息支付率")
payout_df = fetcher.get_multi_year_payout_ratio(test_stocks, years=3)
print(payout_df)
# 输出: stock_code, avg_payout_ratio, payout_std, payout_count

# 4. 合并所有数据
print("\n" + "=" * 80)
print("合并数据")
result = dividend_df.merge(years_df, on="stock_code", how="left")
result = result.merge(payout_df, on="stock_code", how="left")
print(result)
```

## ⚠️ 注意事项

1. **连续分红年限计算**
   - 查询过去5年历史数据
   - 从最近年份开始，连续为1（分红）的年数
   - 如果某年不分红，则年限到此为止

2. **股息支付率计算**
   - 需要 EPS > 0 才计算
   - 结果转换为百分比（%）
   - 计算多年平均值和标准差

3. **数据时效性**
   - 建议使用前一年的年报数据
   - `rptDate` 通常设置为 `YYYY1231`

4. **性能考虑**
   - 连续分红年限需要查询多年数据，耗时较长
   - 建议使用缓存功能（已集成 `@shelve_me_today`）
   - 第二次运行会使用缓存，速度快

## 🔄 迁移建议

### 对于现有代码

1. 清空缓存（强制重新获取数据）
```bash
del cache\shelve.*
```

2. 重新运行程序
```bash
python main.py
```

3. 检查新生成的数据文件
```
data/
├── dividend_data_*.csv      # 现在包含 dividend_years
├── dividend_years_*.csv     # 新增：分红年限详细数据
├── payout_data_*.csv        # 现在是计算得到的支付率
```

## 📞 技术支持

如有问题，请参考：
- Wind API文档: `md/winds/Wind数据获取完整指南.md`
- 字段查询: `md/winds/merged_fields_fixed.txt`

---

**更新时间**: 2024-10-31  
**版本**: v1.0.1  
**状态**: ✅ 已验证可用

