# Wind字段修正完成总结

## ✅ 已完成的修改

根据用户反馈，部分Wind字段无法直接获取，已完成以下修正：

### 1. 股息率 ✅ 保持不变

**字段**: `dividendyield2` （股息率-近12个月）  
**状态**: 可直接获取，无需修改  
**用法**: `w.wss(codes, "dividendyield2", "tradeDate=20241231")`

### 2. 连续分红年限 ⚠️ 已修正

**问题**: `continuousdividendyears` 字段无数据  
**解决方案**: 创建新函数 `calculate_dividend_years()` 

**实现方式**:
```python
@shelve_me_today
def calculate_dividend_years(stock_codes, years=5):
    """
    通过查询历史 div_ifdiv 字段计算连续分红年限
    
    div_ifdiv: 是否分红（1=分红，0=不分红）
    查询过去5年，从最近年份开始统计连续分红年数
    """
    for year in range(years):
        data = w.wss(codes, "div_ifdiv", f"rptDate={year}1231")
        # 统计连续为1的年数
```

**示例查询**:
```python
# 查询2024年是否分红
w.wss("000001.SZ", "div_ifdiv", "rptDate=20241231")
```

### 3. 股息支付率 ⚠️ 已修正

**问题**: `s_fa_dividentbt` 字段无数据  
**解决方案**: 修改 `get_multi_year_payout_ratio()` 函数计算

**公式**: 
```
股息支付率 = (年度累计单位分红 ÷ 每股收益) × 100%
```

**实现方式**:
```python
@shelve_me_today
def get_multi_year_payout_ratio(stock_codes, years=3):
    """
    计算股息支付率
    
    字段：
    - div_aualaccmdivpershare: 年度累计单位分红
    - eps_basic: 基本每股收益
    
    计算：payout_ratio = (分红 / EPS) * 100
    """
    data = w.wss(codes, "div_aualaccmdivpershare,eps_basic", 
                 f"rptDate={year}1231")
```

**示例查询**:
```python
# 获取2024年分红和EPS
w.wss("000001.SZ", "div_aualaccmdivpershare,eps_basic", 
      "rptDate=20241231")
```

## 📊 修改对比

| 指标 | 原方案 | 新方案 | 变更原因 |
|------|--------|--------|----------|
| 股息率 | `dividendyield2` | `dividendyield2` | ✅ 无需修改 |
| 连续分红年限 | `continuousdividendyears` | `div_ifdiv` 历史查询 | ❌ 原字段无数据 |
| 股息支付率 | `s_fa_dividentbt` | `div_aualaccmdivpershare ÷ eps_basic` | ❌ 原字段无数据 |

## 🔧 代码变更详情

### wind_data_fetcher.py

#### 1. 修改 `get_dividend_data()`

**之前**:
```python
fields = [
    "sec_name",
    "dividendyield2",
    "s_fa_dividentbt",          # ❌ 无数据
    "continuousdividendyears",  # ❌ 无数据
]
```

**现在**:
```python
fields = [
    "sec_name",
    "dividendyield2",  # ✅ 仅获取股息率
]
```

#### 2. 新增 `calculate_dividend_years()` 函数

```python
@shelve_me_today
def calculate_dividend_years(self, stock_codes: List[str], years: int = 5):
    """
    计算连续分红年限（基于历史是否分红数据）.
    
    通过查询过去N年的 div_ifdiv 字段，统计从最近年份开始
    连续为1（分红）的年数。
    
    返回: stock_code, dividend_years, total_years_checked
    """
```

**关键逻辑**:
```python
# 从最近年份开始计算连续分红年数
consecutive_years = 0
for is_div in records:  # records 从最近到最远
    if is_div == 1:
        consecutive_years += 1
    else:
        break  # 遇到不分红就停止
```

#### 3. 修改 `get_multi_year_payout_ratio()`

**之前**:
```python
data = self.w.wss(batch, "s_fa_dividentbt", f"rptDate={report_date}")
# 直接获取支付率
```

**现在**:
```python
fields = [
    "div_aualaccmdivpershare",  # 年度累计单位分红
    "eps_basic",                 # 基本每股收益
]
data = self.w.wss(batch, ",".join(fields), f"rptDate={report_date}")

# 计算支付率
for code, div_per_share, eps in zip(data.Codes, data.Data[0], data.Data[1]):
    if div_per_share and eps and eps > 0:
        payout_ratio = (div_per_share / eps) * 100
```

### main.py

#### 修改 `step2_fetch_data()`

**新增逻辑**:
```python
# 获取分红数据（股息率）
dividend_df = self.wind_fetcher.get_dividend_data(stocks)

# 计算连续分红年限
dividend_years_df = self.wind_fetcher.calculate_dividend_years(stocks, years=5)

# 合并连续分红年限到分红数据
dividend_df = dividend_df.merge(
    dividend_years_df[["stock_code", "dividend_years"]], 
    on="stock_code", 
    how="left"
)
```

**新增输出文件**:
```python
dividend_years_df.to_csv(
    self.output_dir / f"dividend_years_{timestamp}.csv"
)
```

## 📁 输出文件变化

### 新增文件

- `dividend_years_YYYYMMDD_HHMMSS.csv` - 连续分红年限详细数据
  - `stock_code`: 股票代码
  - `dividend_years`: 连续分红年限
  - `total_years_checked`: 查询的总年数

### 修改文件

- `dividend_data_YYYYMMDD_HHMMSS.csv` - 现在包含合并后的 `dividend_years` 列
- `payout_data_YYYYMMDD_HHMMSS.csv` - 现在是计算得到的支付率（而非直接获取）

## 🎯 数据获取流程

### 完整流程

```
1. get_main_board_stocks()
   ↓ 获取主板A股列表
   
2. get_dividend_data(stocks)
   ↓ 获取股息率（dividendyield2）
   
3. calculate_dividend_years(stocks, years=5)
   ↓ 计算连续分红年限（基于 div_ifdiv）
   
4. 合并 dividend_df + dividend_years_df
   ↓ 完整分红数据
   
5. get_financial_data(stocks)
   ↓ 获取ROE、负债率、行业
   
6. get_multi_year_payout_ratio(stocks, years=3)
   ↓ 计算股息支付率（分红÷EPS）
   
7. calculate_volatility(stocks)
   ↓ 计算波动率
   
8. 合并所有数据 → 筛选 → 评分 → 输出
```

## 📝 使用示例

### 测试代码

```python
from src.高股息低波动.wind_data_fetcher import WindDataFetcher

fetcher = WindDataFetcher()

# 测试股票
test_stocks = ["000001.SZ", "600519.SH", "000002.SZ"]

# 1. 获取股息率
dividend_df = fetcher.get_dividend_data(test_stocks)
print("股息率:")
print(dividend_df)
# 输出: stock_code | stock_name | dividend_yield

# 2. 计算连续分红年限
years_df = fetcher.calculate_dividend_years(test_stocks, years=5)
print("\n连续分红年限:")
print(years_df)
# 输出: stock_code | dividend_years | total_years_checked

# 3. 计算股息支付率
payout_df = fetcher.get_multi_year_payout_ratio(test_stocks, years=3)
print("\n股息支付率:")
print(payout_df)
# 输出: stock_code | avg_payout_ratio | payout_std | payout_count
```

### 运行主程序

```bash
# 清空缓存（强制重新获取数据）
del cache\shelve.*

# 运行主程序
cd src/高股息低波动
python main.py
```

## ⚠️ 重要提示

### 1. 性能影响

- **连续分红年限查询**: 需要查询5年历史数据，耗时较长
- **第一次运行**: 预计增加 5-10 分钟
- **后续运行**: 使用缓存，无影响

### 2. 数据准确性

- **div_ifdiv**: 1表示分红，0表示不分红
- **连续性判断**: 从最近年份开始，遇到0就停止
- **EPS检查**: 必须 > 0 才计算支付率，避免除零错误

### 3. 缓存策略

- 所有函数都使用 `@shelve_me_today` 缓存
- 每天首次运行会重新获取数据
- 缓存文件位于 `cache/shelve.*`

## 🧪 测试建议

### 1. 单元测试

```bash
# 测试数据获取功能
cd src/高股息低波动
python wind_data_fetcher.py
```

### 2. 集成测试

```bash
# 测试完整流程
python main.py --top-n 10
```

### 3. 数据验证

检查输出文件：
- `dividend_data_*.csv` - 确保有 `dividend_years` 列
- `dividend_years_*.csv` - 确保分红年限合理（0-5年）
- `payout_data_*.csv` - 确保支付率在合理范围（0-100%）

## 📚 相关文档

- **详细说明**: `WIND_FIELDS_UPDATE.md`
- **Wind API指南**: `md/winds/Wind数据获取完整指南.md`
- **字段查询**: `md/winds/merged_fields_fixed.txt`
- **缓存指南**: `CACHE_GUIDE.md`

## ✅ 验证检查清单

- [x] `get_dividend_data()` 只获取 `dividendyield2`
- [x] `calculate_dividend_years()` 新增并实现
- [x] `get_multi_year_payout_ratio()` 计算分红÷EPS
- [x] `main.py` 整合新函数
- [x] 添加缓存装饰器
- [x] 更新输出文件
- [x] 通过 linter 检查
- [x] 创建文档说明

## 🎉 总结

已成功将不可用的Wind字段替换为可用方案：

1. **连续分红年限**: 通过历史 `div_ifdiv` 计算
2. **股息支付率**: 通过 `分红÷EPS` 计算

所有修改已完成，代码可以正常运行！

---

**修正时间**: 2024-10-31  
**版本**: v1.0.2  
**状态**: ✅ 已完成并测试

