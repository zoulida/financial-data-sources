# AKShare 开户数据 API 使用说明

## 目录

1. [接口概述](#接口概述)
2. [数据字段说明](#数据字段说明)
3. [基础用法](#基础用法)
4. [进阶用法](#进阶用法)
5. [数据分析示例](#数据分析示例)
6. [常见问题](#常见问题)
7. [最佳实践](#最佳实践)

---

## 接口概述

### 接口名称

```python
akshare.stock_account_statistics_em()
```

### 接口说明

- **功能**: 获取中国证券市场投资者开户统计数据
- **数据来源**: 东方财富网 / 中国结算
- **数据类型**: 月度统计数据
- **历史范围**: 支持获取完整历史数据（通常从 2015 年开始）
- **返回格式**: pandas DataFrame

### 调用方式

```python
import akshare as ak

# 无需参数，一次性获取全部历史数据
df = ak.stock_account_statistics_em()
```

### 数据更新节奏

- **官方发布**: 中国结算每月中旬公布上月完整数据
- **AKShare 同步**: 通常在官方公布后 1-2 天内更新
- **⚠️ 实际情况**: 经测试，该接口最新数据截至 **2023年8月**，后续数据暂未更新
- **数据范围**: 约2016年1月 - 2023年8月（共100+条记录）

---

## 数据字段说明

### 返回字段（2023-08 实测）

| 序号 | 字段名 | 数据类型 | 说明 | 示例 |
|------|--------|----------|------|------|
| 1 | 数据日期 | object/str | 统计月份，格式 YYYY-MM | "2023-08" |
| 2 | 新增投资者-数量 | float | 当月新增投资者数量（万户） | 99.59 |
| 3 | 新增投资者-环比 | float | 新增数量环比增长率（%） | 9.40 |
| 4 | 新增投资者-同比 | float | 新增数量同比增长率（%） | -20.07 |
| 5 | 期末投资者-总量 | float | 截至月末累计投资者总数（万户） | 22141.58 |
| 6 | 期末投资者-A股账户 | float | A股账户数量（万户） | 22082.23 |
| 7 | 期末投资者-B股账户 | float | B股账户数量（万户） | 238.81 |
| 8 | 沪深总市值 | float | 沪深两市总市值（亿元） | 808664.77 |
| 9 | 沪深户均市值 | float | 户均市值（万元） | 36.62 |
| 10 | 上证指数-收盘 | float | 该月最后一个交易日上证指数收盘点位 | 3119.88 |
| 11 | 上证指数-涨跌幅 | float | 该月上证指数涨跌幅（%） | -5.20 |

### 字段详细说明

#### 1. 数据日期

- **格式**: "YYYY-MM"（字符串）
- **含义**: 统计月份
- **示例**: "2025-07" 表示 2025 年 7 月的统计数据
- **注意**: 字符串类型，需要转换为日期类型用于时间序列分析

#### 2. 新增投资者-数量

- **单位**: 万户
- **含义**: 该月新增的投资者账户数量
- **特点**:
  - 反映当月市场活跃度
  - 存在季节性波动（年初较多）
  - 牛市期间通常激增
- **应用**: 判断散户入市热情，顶底信号

#### 3. 期末投资者-总量

- **单位**: 万户
- **含义**: 截至该月末的投资者账户累计总数
- **特点**:
  - 单调递增（不考虑销户）
  - 反映市场长期参与度
  - 增速变化更有参考价值
- **应用**: 长期趋势分析，市场规模评估

#### 4. 上证指数-收盘

- **单位**: 点
- **含义**: 该月最后一个交易日的上证指数收盘价
- **作用**: 方便对照行情，分析开户数与指数的关系
- **应用**: 开户-行情相关性分析

---

## 基础用法

### 1. 获取全部历史数据

```python
import akshare as ak
import pandas as pd

# 获取全部数据
df = ak.stock_account_statistics_em()

# 查看数据基本信息
print(f"数据行数: {len(df)}")
print(f"数据范围: {df['数据日期'].min()} 至 {df['数据日期'].max()}")
print("\n数据预览:")
print(df.head())
```

### 2. 查看最新数据

```python
import akshare as ak

# 获取数据
df = ak.stock_account_statistics_em()

# 查看最近 5 个月
print("最近 5 个月数据:")
print(df.tail())

# 获取最新一条记录
latest = df.sort_values('数据日期').iloc[-1]
print(f"\n最新数据:")
print(f"数据日期: {latest['数据日期']}")
print(f"新增开户: {latest['新增投资者-数量']} 万户")
print(f"期末总量: {latest['期末投资者-总量']} 万户")
print(f"上证指数: {latest['上证指数-收盘']} 点")
```

### 3. 基础数据处理

```python
import akshare as ak
import pandas as pd

# 获取数据
df = ak.stock_account_statistics_em()

# 转换日期类型
df['数据日期'] = pd.to_datetime(df['数据日期'])

# 按日期排序
df = df.sort_values('数据日期').reset_index(drop=True)

# 设置日期为索引
df.set_index('数据日期', inplace=True)

print(df.tail())
```

---

## 进阶用法

### 1. 时间范围筛选

```python
import akshare as ak
import pandas as pd

# 获取数据
df = ak.stock_account_statistics_em()
df['数据日期'] = pd.to_datetime(df['数据日期'])

# 获取最近一年的数据
one_year_ago = pd.Timestamp.now() - pd.DateOffset(years=1)
recent_df = df[df['数据日期'] >= one_year_ago]
print(f"最近一年数据: {len(recent_df)} 条")

# 获取特定年份的数据
df_2024 = df[df['数据日期'].dt.year == 2024]
print(f"2024 年数据: {len(df_2024)} 条")

# 获取特定月份范围
start_date = '2024-01'
end_date = '2024-12'
df_range = df[(df['数据日期'] >= start_date) & (df['数据日期'] <= end_date)]
print(f"{start_date} 至 {end_date}: {len(df_range)} 条")
```

### 2. 数据统计分析

```python
import akshare as ak
import pandas as pd

# 获取数据
df = ak.stock_account_statistics_em()
df['数据日期'] = pd.to_datetime(df['数据日期'])

# 新增开户数统计
print("新增开户数统计:")
print(f"平均值: {df['新增投资者-数量'].mean():.2f} 万户")
print(f"中位数: {df['新增投资者-数量'].median():.2f} 万户")
print(f"最大值: {df['新增投资者-数量'].max():.2f} 万户")
print(f"最小值: {df['新增投资者-数量'].min():.2f} 万户")
print(f"标准差: {df['新增投资者-数量'].std():.2f} 万户")

# 找出开户最多的月份
max_idx = df['新增投资者-数量'].idxmax()
print(f"\n开户最多月份: {df.loc[max_idx, '数据日期'].strftime('%Y-%m')}")
print(f"新增数量: {df.loc[max_idx, '新增投资者-数量']:.2f} 万户")
print(f"当月上证指数: {df.loc[max_idx, '上证指数-收盘']:.2f} 点")
```

### 3. 计算衍生指标

```python
import akshare as ak
import pandas as pd

# 获取数据
df = ak.stock_account_statistics_em()
df['数据日期'] = pd.to_datetime(df['数据日期'])
df = df.sort_values('数据日期').reset_index(drop=True)

# 计算同比增长率
df['新增开户_同比'] = df['新增投资者-数量'].pct_change(12) * 100

# 计算环比增长率
df['新增开户_环比'] = df['新增投资者-数量'].pct_change(1) * 100

# 计算移动平均
df['新增开户_MA3'] = df['新增投资者-数量'].rolling(window=3).mean()
df['新增开户_MA6'] = df['新增投资者-数量'].rolling(window=6).mean()

# 计算上证指数变化
df['指数_环比涨跌'] = df['上证指数-收盘'].pct_change(1) * 100

# 查看结果
print(df[['数据日期', '新增投资者-数量', '新增开户_环比', 
          '新增开户_MA3', '上证指数-收盘', '指数_环比涨跌']].tail(10))
```

### 4. 异常值检测

```python
import akshare as ak
import pandas as pd
import numpy as np

# 获取数据
df = ak.stock_account_statistics_em()
df['数据日期'] = pd.to_datetime(df['数据日期'])

# 使用 3-sigma 方法检测异常值
mean_val = df['新增投资者-数量'].mean()
std_val = df['新增投资者-数量'].std()

# 定义异常阈值
upper_bound = mean_val + 3 * std_val
lower_bound = mean_val - 3 * std_val

# 找出异常值
outliers = df[(df['新增投资者-数量'] > upper_bound) | 
              (df['新增投资者-数量'] < lower_bound)]

print(f"检测到 {len(outliers)} 个异常值:")
print(outliers[['数据日期', '新增投资者-数量', '上证指数-收盘']])
```

---

## 数据分析示例

### 1. 开户数与指数相关性分析

```python
import akshare as ak
import pandas as pd

# 获取数据
df = ak.stock_account_statistics_em()
df['数据日期'] = pd.to_datetime(df['数据日期'])

# 计算相关系数
correlation = df['新增投资者-数量'].corr(df['上证指数-收盘'])
print(f"新增开户数与上证指数相关系数: {correlation:.4f}")

# 计算滞后相关性（开户数领先/滞后指数）
for lag in range(-6, 7):
    if lag == 0:
        continue
    corr = df['新增投资者-数量'].corr(df['上证指数-收盘'].shift(lag))
    direction = "开户领先" if lag > 0 else "开户滞后"
    print(f"{direction} {abs(lag)} 个月相关系数: {corr:.4f}")
```

### 2. 季节性分析

```python
import akshare as ak
import pandas as pd

# 获取数据
df = ak.stock_account_statistics_em()
df['数据日期'] = pd.to_datetime(df['数据日期'])
df['月份'] = df['数据日期'].dt.month

# 按月份统计平均开户数
monthly_avg = df.groupby('月份')['新增投资者-数量'].agg(['mean', 'std', 'count'])
monthly_avg.columns = ['平均开户数', '标准差', '样本数']
print("各月份平均开户数:")
print(monthly_avg)

# 找出开户最多的月份
peak_month = monthly_avg['平均开户数'].idxmax()
print(f"\n历史上开户最活跃月份: {peak_month} 月")
```

### 3. 市场周期判断

```python
import akshare as ak
import pandas as pd
import numpy as np

# 获取数据
df = ak.stock_account_statistics_em()
df['数据日期'] = pd.to_datetime(df['数据日期'])
df = df.sort_values('数据日期').reset_index(drop=True)

# 计算开户数的分位数
df['开户_分位数'] = df['新增投资者-数量'].rank(pct=True)

# 判断市场阶段
def judge_market_phase(percentile):
    if percentile >= 0.8:
        return '过热（顶部风险）'
    elif percentile >= 0.6:
        return '活跃（谨慎乐观）'
    elif percentile >= 0.4:
        return '正常'
    elif percentile >= 0.2:
        return '冷淡'
    else:
        return '冰冷（底部机会）'

df['市场阶段'] = df['开户_分位数'].apply(judge_market_phase)

# 查看最近一年的市场阶段
recent = df.tail(12)[['数据日期', '新增投资者-数量', '开户_分位数', '市场阶段', '上证指数-收盘']]
print("最近一年市场阶段:")
print(recent)
```

### 4. 同比、环比分析

```python
import akshare as ak
import pandas as pd

# 获取数据
df = ak.stock_account_statistics_em()
df['数据日期'] = pd.to_datetime(df['数据日期'])
df = df.sort_values('数据日期').reset_index(drop=True)

# 计算同比、环比
df['新增_同比增长'] = df['新增投资者-数量'].pct_change(12) * 100
df['新增_环比增长'] = df['新增投资者-数量'].pct_change(1) * 100
df['总量_同比增长'] = df['期末投资者-总量'].pct_change(12) * 100

# 查看最近数据
recent = df.tail(12)[['数据日期', '新增投资者-数量', '新增_环比增长', '新增_同比增长']]
print("最近一年同比环比变化:")
print(recent)

# 统计分析
print(f"\n环比增长统计:")
print(f"平均: {df['新增_环比增长'].mean():.2f}%")
print(f"中位数: {df['新增_环比增长'].median():.2f}%")
print(f"最大: {df['新增_环比增长'].max():.2f}%")
print(f"最小: {df['新增_环比增长'].min():.2f}%")
```

---

## 常见问题

### Q1: 为什么数据只到2023年8月？

**A**: 经实测，AKShare 的 `stock_account_statistics_em()` 接口目前最新数据只更新到2023年8月，之后的数据暂未同步。

**可能原因**:
1. 东方财富网数据源调整或接口变更
2. AKShare 该接口停止维护
3. 需要使用其他接口获取最新数据

**获取最新开户数据的替代方案**:
1. **中国结算官网**: http://www.chinaclear.cn/ （手动下载月报）
2. **Wind数据库**: 使用 Wind API 获取开户数据（需要订阅）
3. **同花顺iFinD**: 金融终端数据
4. **东方财富Choice**: 金融终端数据

### Q2: 数据多久更新一次？

**A**: 理论上中国结算每月中旬（通常 10-15 号）公布上月数据，AKShare 会在 1-2 天内同步。但该接口目前停留在2023年8月。

### Q3: 为什么拉取的数据不包含本月？

**A**: 因为本月尚未结束，官方还未公布数据。通常能获取到的最新数据是上个月的。注：当前接口最新数据为2023年8月。

### Q4: 数据日期是字符串还是日期类型？

**A**: 原始数据返回的是字符串类型（object），需要使用 `pd.to_datetime()` 转换为日期类型后才能进行时间序列分析。

```python
df['数据日期'] = pd.to_datetime(df['数据日期'])
```

### Q5: 新增开户数为什么会有负值？

**A**: 正常情况下不会出现负值。如果出现，可能是：
- 数据源异常
- 账户销户调整
- 统计口径变化

建议检查原始数据或剔除异常值。

### Q6: 如何判断开户数是高还是低？

**A**: 可以采用以下方法：
1. **历史分位数法**: 计算当前值在历史数据中的分位数
2. **均值比较法**: 与历史平均值或移动平均比较
3. **同比比较法**: 与去年同期比较
4. **标准差法**: 计算偏离均值的标准差倍数

### Q7: 开户数能预测股市涨跌吗？

**A**: 开户数是一个**情绪指标**，不能单独用于预测：
- **滞后性**: 通常在牛市中后期才激增
- **逆向指标**: 开户数暴增往往是顶部信号
- **需配合**: 应结合估值、资金面、政策等多维度分析

### Q8: 数据获取失败怎么办？

**A**: 可能的原因和解决方案：
1. **网络问题**: 检查网络连接
2. **数据源维护**: 等待数据源恢复
3. **AKShare 版本**: 更新到最新版本
   ```bash
   pip install --upgrade akshare
   ```
4. **接口变更**: 查看 AKShare 官方文档确认接口是否调整
5. **数据更新停滞**: 如果需要最新数据，请使用替代方案（见Q1）

### Q9: 如何保存数据到本地？

**A**: 可以保存为多种格式：

```python
import akshare as ak

df = ak.stock_account_statistics_em()

# 保存为 CSV
df.to_csv('开户数据.csv', index=False, encoding='utf-8-sig')

# 保存为 Excel
df.to_excel('开户数据.xlsx', index=False)

# 保存为 Parquet（推荐，速度快、占用小）
df.to_parquet('开户数据.parquet', index=False)
```

---

## 最佳实践

### 1. 数据获取与缓存

```python
import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

def get_account_data(use_cache=True, cache_hours=24):
    """
    获取开户数据，支持本地缓存
    
    Args:
        use_cache: 是否使用缓存
        cache_hours: 缓存有效期（小时）
    
    Returns:
        pd.DataFrame: 开户数据
    """
    cache_file = Path('cache/account_data.parquet')
    
    # 检查缓存
    if use_cache and cache_file.exists():
        cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - cache_time < timedelta(hours=cache_hours):
            print(f"使用缓存数据（更新于 {cache_time.strftime('%Y-%m-%d %H:%M:%S')}）")
            return pd.read_parquet(cache_file)
    
    # 获取最新数据
    print("从 AKShare 获取最新数据...")
    df = ak.stock_account_statistics_em()
    
    # 数据预处理
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 保存缓存
    cache_file.parent.mkdir(exist_ok=True)
    df.to_parquet(cache_file, index=False)
    print(f"数据已缓存到 {cache_file}")
    
    return df
```

### 2. 异常处理与重试

```python
import akshare as ak
import time

def get_account_data_safe(max_retries=3, retry_delay=5):
    """
    安全获取开户数据，支持重试
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
    
    Returns:
        pd.DataFrame or None: 开户数据或 None
    """
    for attempt in range(max_retries):
        try:
            df = ak.stock_account_statistics_em()
            
            # 数据验证
            if df is None or len(df) == 0:
                raise ValueError("返回数据为空")
            
            required_cols = ['数据日期', '新增投资者-数量', '期末投资者-总量', '上证指数-收盘']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"缺少必要字段，当前字段: {df.columns.tolist()}")
            
            print(f"数据获取成功，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            print(f"第 {attempt + 1} 次尝试失败: {str(e)}")
            if attempt < max_retries - 1:
                print(f"{retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print("达到最大重试次数，获取失败")
                return None
```

### 3. 完整的数据处理流程

```python
import akshare as ak
import pandas as pd
import numpy as np

def process_account_data(df):
    """
    完整的数据处理流程
    
    Args:
        df: 原始数据
    
    Returns:
        pd.DataFrame: 处理后的数据
    """
    # 1. 数据类型转换
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    
    # 2. 排序
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 3. 计算衍生指标
    df['新增_环比'] = df['新增投资者-数量'].pct_change(1) * 100
    df['新增_同比'] = df['新增投资者-数量'].pct_change(12) * 100
    df['新增_MA3'] = df['新增投资者-数量'].rolling(window=3).mean()
    df['新增_MA6'] = df['新增投资者-数量'].rolling(window=6).mean()
    df['新增_MA12'] = df['新增投资者-数量'].rolling(window=12).mean()
    
    # 4. 计算分位数
    df['新增_分位数'] = df['新增投资者-数量'].rank(pct=True)
    
    # 5. 市场阶段判断
    conditions = [
        (df['新增_分位数'] >= 0.8),
        (df['新增_分位数'] >= 0.6),
        (df['新增_分位数'] >= 0.4),
        (df['新增_分位数'] >= 0.2)
    ]
    choices = ['过热', '活跃', '正常', '冷淡']
    df['市场阶段'] = np.select(conditions, choices, default='冰冷')
    
    # 6. 计算指数变化
    df['指数_环比'] = df['上证指数-收盘'].pct_change(1) * 100
    df['指数_同比'] = df['上证指数-收盘'].pct_change(12) * 100
    
    return df

# 使用示例
df = ak.stock_account_statistics_em()
df_processed = process_account_data(df)
print(df_processed.tail())
```

### 4. 监控与告警

```python
import akshare as ak
import pandas as pd

def check_account_alert(threshold_percentile=0.8):
    """
    检查开户数是否超过警戒线
    
    Args:
        threshold_percentile: 警戒分位数
    
    Returns:
        dict: 告警信息
    """
    # 获取数据
    df = ak.stock_account_statistics_em()
    df['数据日期'] = pd.to_datetime(df['数据日期'])
    df = df.sort_values('数据日期').reset_index(drop=True)
    
    # 获取最新数据
    latest = df.iloc[-1]
    
    # 计算分位数
    percentile = (df['新增投资者-数量'] <= latest['新增投资者-数量']).sum() / len(df)
    
    # 判断是否告警
    alert = percentile >= threshold_percentile
    
    result = {
        '数据日期': latest['数据日期'].strftime('%Y-%m'),
        '新增开户': f"{latest['新增投资者-数量']:.2f} 万户",
        '历史分位数': f"{percentile:.2%}",
        '上证指数': f"{latest['上证指数-收盘']:.2f} 点",
        '是否告警': alert,
        '告警信息': f"⚠️ 开户数处于历史 {percentile:.0%} 分位，市场可能过热" if alert else "✅ 开户数正常"
    }
    
    return result

# 使用示例
alert_info = check_account_alert(threshold_percentile=0.8)
for key, value in alert_info.items():
    print(f"{key}: {value}")
```

---

## 总结

AKShare 的 `stock_account_statistics_em()` 接口提供了便捷的投资者开户数据获取功能，结合适当的数据处理和分析方法，可以有效辅助市场情绪判断和投资决策。

**核心要点**:
1. 月度数据，更新延迟约 1 个月
2. 新增开户数是重要的情绪指标
3. 开户暴增往往是市场顶部信号（逆向指标）
4. 需要结合其他指标综合判断
5. 建议使用缓存机制减少重复请求

**参考资料**:
- [AKShare 官方文档](https://akshare.akfamily.xyz/)
- [中国结算官网](http://www.chinaclear.cn/)
- 示例代码见 `示例代码.py`

