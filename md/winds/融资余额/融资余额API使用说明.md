# Wind API - 融资余额数据获取指南

## 概述

本文档介绍如何使用Wind API获取融资融券交易数据，包括融资余额、买入额、偿还额等关键指标。

## API接口

### 接口名称
`w.wset("margintradingsizeanalys(value)", parameters)`

### 接口说明
获取融资融券交易规模分析数据，支持按日、周、月频率查询历史数据。

## 参数说明

### 必选参数

| 参数名 | 说明 | 可选值 | 示例 |
|--------|------|--------|------|
| exchange | 交易所 | `all` - 全部 ⚠️ **仅支持all** | `all` |
| startdate | 开始日期 | 日期格式：YYYY-MM-DD | `2025-07-20` |
| enddate | 结束日期 | 日期格式：YYYY-MM-DD | `2025-10-20` |
| frequency | 数据频率 | `day` - 日<br>`week` - 周<br>`month` - 月 | `day` |
| sort | 排序方式 | `asc` - 升序<br>`desc` - 降序 | `asc` |

⚠️ **重要提示**: 根据实际测试，`exchange` 参数目前只支持 `all`（全市场），设置为 `sse`（上交所）或 `szse`（深交所）时返回空数据。

### 参数组合示例

```python
# 获取全市场的日度数据
parameters = "exchange=all;startdate=2025-07-20;enddate=2025-10-20;frequency=day;sort=asc"

# 获取全市场的周度数据
parameters = "exchange=all;startdate=2025-01-01;enddate=2025-10-20;frequency=week;sort=desc"

# 获取全市场的月度数据
parameters = "exchange=all;startdate=2024-01-01;enddate=2025-10-20;frequency=month;sort=asc"
```

## 返回字段说明

| 中文字段名 | Wind API返回字段名 | 说明 | 单位 |
|-----------|-------------------|------|------|
| 日期 | end_date | 交易日期 | - |
| 融资余额 | margin_balance | 融资余额 | 元 |
| 融资余额占流通市值(%) | margin_balance_ratio_negmktcap | 融资余额占流通市值比例 | % |
| 融资余量 | margin_amount | 融资余量（股数） | 股 |
| 期间买入额 | period_bought_amount | 期间融资买入金额 | 元 |
| 买入额占A股成交额(%) | total_amount_ratio_a-share_amount | 买入额占A股成交额比例 | % |
| 期间偿还额 | period_paid_amount | 期间融资偿还金额 | 元 |
| 期间净买入额 | period_net_purchases | 期间净买入额（买入额-偿还额） | 元 |
| 期间融资买入个股数 | buy_count | 期间融资买入个股数量 | 只 |
| 占融资标的比(%) | margin_trading_underlying | 占融资标的股票总数比例 | % |

**注意**: 示例代码会自动将Wind API返回的英文字段名转换为中文字段名，方便使用。

## 代码示例

### 基础示例

```python
from WindPy import w
import pandas as pd
from datetime import datetime, timedelta

# 初始化Wind API
w.start()

# 获取最近3个月的融资余额数据
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

# 调用API
data = w.wset(
    "margintradingsizeanalys(value)",
    f"exchange=all;startdate={start_date};enddate={end_date};frequency=day;sort=asc"
)

# 检查返回状态
if data.ErrorCode != 0:
    print(f"错误代码: {data.ErrorCode}")
    print(f"错误信息: {data.Data}")
else:
    # 转换为DataFrame
    df = pd.DataFrame(data.Data, index=data.Fields).T
    df.columns = data.Fields
    
    # 显示数据
    print(df.head())
    print(f"\n数据形状: {df.shape}")
    
# 关闭连接
w.close()
```

### 完整示例（带数据处理）

```python
from WindPy import w
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class MarginTradingAnalyzer:
    """融资融券数据分析器"""
    
    def __init__(self):
        """初始化"""
        w.start()
        
    def get_margin_data(self, start_date, end_date, exchange='all', frequency='day'):
        """
        获取融资融券数据
        
        参数:
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'
            exchange: 交易所，'all'/'sse'/'szse'
            frequency: 数据频率，'day'/'week'/'month'
            
        返回:
            DataFrame: 融资融券数据
        """
        params = (
            f"exchange={exchange};"
            f"startdate={start_date};"
            f"enddate={end_date};"
            f"frequency={frequency};"
            f"sort=asc"
        )
        
        data = w.wset("margintradingsizeanalys(value)", params)
        
        if data.ErrorCode != 0:
            raise Exception(f"数据获取失败: {data.Data}")
            
        # 转换为DataFrame
        df = pd.DataFrame(data.Data, index=data.Fields).T
        
        # 设置列名（中文）
        column_mapping = {
            'date': '日期',
            'exchange': '交易所',
            'rzye': '融资余额',
            'rzyezb': '融资余额占流通市值(%)',
            'rzyl': '融资余量',
            'qjmre': '期间买入额',
            'mrezb': '买入额占A股成交额(%)',
            'qjche': '期间偿还额',
            'qjjmre': '期间净买入额',
            'rzggsl': '期间融资买入个股数',
            'rzbdzb': '占融资标的比(%)'
        }
        
        df.columns = [column_mapping.get(col, col) for col in data.Fields]
        
        # 数据类型转换
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'])
            
        # 数值列转换为float
        numeric_columns = [
            '融资余额', '融资余额占流通市值(%)', '融资余量',
            '期间买入额', '买入额占A股成交额(%)', '期间偿还额',
            '期间净买入额', '期间融资买入个股数', '占融资标的比(%)'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        return df
    
    def calculate_metrics(self, df):
        """
        计算衍生指标
        
        参数:
            df: 原始数据DataFrame
            
        返回:
            DataFrame: 添加了衍生指标的数据
        """
        df = df.copy()
        
        # 计算日变化
        df['融资余额日变化'] = df['融资余额'].diff()
        df['融资余额变化率(%)'] = df['融资余额'].pct_change() * 100
        
        # 计算移动平均
        df['融资余额_5日均'] = df['融资余额'].rolling(window=5).mean()
        df['融资余额_20日均'] = df['融资余额'].rolling(window=20).mean()
        
        # 计算净买入占比
        df['净买入占买入比(%)'] = (df['期间净买入额'] / df['期间买入额'] * 100)
        
        return df
    
    def get_exchange_comparison(self, start_date, end_date):
        """
        获取交易所对比数据
        
        参数:
            start_date: 开始日期
            end_date: 结束日期
            
        返回:
            DataFrame: 两个交易所的对比数据
        """
        # 获取上交所数据
        df_sse = self.get_margin_data(start_date, end_date, exchange='sse')
        df_sse['交易所'] = '上交所'
        
        # 获取深交所数据
        df_szse = self.get_margin_data(start_date, end_date, exchange='szse')
        df_szse['交易所'] = '深交所'
        
        # 合并数据
        df_combined = pd.concat([df_sse, df_szse], ignore_index=True)
        
        return df_combined
    
    def close(self):
        """关闭Wind连接"""
        w.close()


# 使用示例
if __name__ == '__main__':
    # 创建分析器实例
    analyzer = MarginTradingAnalyzer()
    
    try:
        # 设置日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # 1. 获取全市场数据
        print("=" * 60)
        print("1. 获取全市场融资融券数据")
        print("=" * 60)
        df_all = analyzer.get_margin_data(start_date, end_date, exchange='all')
        print(f"\n数据范围: {df_all['日期'].min()} 至 {df_all['日期'].max()}")
        print(f"数据条数: {len(df_all)}")
        print("\n最新数据:")
        print(df_all.tail(5).to_string(index=False))
        
        # 2. 计算衍生指标
        print("\n" + "=" * 60)
        print("2. 计算衍生指标")
        print("=" * 60)
        df_metrics = analyzer.calculate_metrics(df_all)
        print("\n最新数据（含衍生指标）:")
        print(df_metrics[['日期', '融资余额', '融资余额日变化', 
                         '融资余额变化率(%)', '净买入占买入比(%)']].tail(5).to_string(index=False))
        
        # 3. 获取交易所对比数据
        print("\n" + "=" * 60)
        print("3. 交易所对比分析")
        print("=" * 60)
        df_comparison = analyzer.get_exchange_comparison(start_date, end_date)
        
        # 按日期分组，显示两个交易所的对比
        latest_date = df_comparison['日期'].max()
        df_latest = df_comparison[df_comparison['日期'] == latest_date]
        print(f"\n最新日期 {latest_date} 的对比数据:")
        print(df_latest[['交易所', '融资余额', '期间买入额', 
                        '期间净买入额', '融资余额占流通市值(%)']].to_string(index=False))
        
        # 4. 统计摘要
        print("\n" + "=" * 60)
        print("4. 统计摘要")
        print("=" * 60)
        print("\n融资余额统计:")
        print(f"  平均值: {df_all['融资余额'].mean():,.2f} 元")
        print(f"  最大值: {df_all['融资余额'].max():,.2f} 元")
        print(f"  最小值: {df_all['融资余额'].min():,.2f} 元")
        print(f"  标准差: {df_all['融资余额'].std():,.2f} 元")
        
        print("\n期间净买入额统计:")
        print(f"  平均值: {df_all['期间净买入额'].mean():,.2f} 元")
        print(f"  最大值: {df_all['期间净买入额'].max():,.2f} 元")
        print(f"  最小值: {df_all['期间净买入额'].min():,.2f} 元")
        
        # 5. 保存数据
        output_file = 'margin_trading_data.csv'
        df_metrics.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n数据已保存到: {output_file}")
        
    except Exception as e:
        print(f"错误: {str(e)}")
        
    finally:
        # 关闭连接
        analyzer.close()
        print("\nWind连接已关闭")
```

## 数据可视化示例

```python
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

def plot_margin_data(df):
    """
    绘制融资融券数据图表
    
    参数:
        df: 包含融资融券数据的DataFrame
    """
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # 1. 融资余额走势
    ax1 = axes[0]
    ax1.plot(df['日期'], df['融资余额'] / 1e8, 'b-', linewidth=2, label='融资余额')
    if '融资余额_5日均' in df.columns:
        ax1.plot(df['日期'], df['融资余额_5日均'] / 1e8, 'r--', 
                linewidth=1.5, label='5日均线', alpha=0.7)
    if '融资余额_20日均' in df.columns:
        ax1.plot(df['日期'], df['融资余额_20日均'] / 1e8, 'g--', 
                linewidth=1.5, label='20日均线', alpha=0.7)
    
    ax1.set_title('融资余额走势图', fontsize=14, fontweight='bold')
    ax1.set_ylabel('融资余额（亿元）', fontsize=12)
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    
    # 2. 期间净买入额
    ax2 = axes[1]
    colors = ['green' if x >= 0 else 'red' for x in df['期间净买入额']]
    ax2.bar(df['日期'], df['期间净买入额'] / 1e8, color=colors, alpha=0.6)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title('期间净买入额', fontsize=14, fontweight='bold')
    ax2.set_ylabel('净买入额（亿元）', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    
    # 3. 融资余额占流通市值比例
    ax3 = axes[2]
    ax3.plot(df['日期'], df['融资余额占流通市值(%)'], 'purple', linewidth=2)
    ax3.fill_between(df['日期'], df['融资余额占流通市值(%)'], alpha=0.3, color='purple')
    ax3.set_title('融资余额占流通市值比例', fontsize=14, fontweight='bold')
    ax3.set_ylabel('比例（%）', fontsize=12)
    ax3.set_xlabel('日期', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    
    # 调整布局
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    plt.savefig('margin_trading_analysis.png', dpi=300, bbox_inches='tight')
    print("图表已保存为: margin_trading_analysis.png")
    
    plt.show()

# 使用示例
if __name__ == '__main__':
    analyzer = MarginTradingAnalyzer()
    
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        df = analyzer.get_margin_data(start_date, end_date)
        df = analyzer.calculate_metrics(df)
        
        plot_margin_data(df)
        
    finally:
        analyzer.close()
```

## 常见问题

### 1. 错误代码处理

```python
# 检查错误代码
if data.ErrorCode != 0:
    error_messages = {
        -40520007: "没有可用数据",
        -40521009: "数据提取失败",
        -40520003: "无此指标",
        -40520001: "参数错误"
    }
    error_msg = error_messages.get(data.ErrorCode, f"未知错误: {data.ErrorCode}")
    print(f"错误: {error_msg}")
```

### 2. 日期格式处理

```python
from datetime import datetime, timedelta

# 获取最近N天的数据
def get_recent_days(days=30):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

# 获取指定年份的数据
def get_year_data(year):
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    return start_date, end_date
```

### 3. 数据缺失处理

```python
# 处理缺失值
df = df.fillna(method='ffill')  # 向前填充
df = df.fillna(0)  # 填充为0

# 删除缺失值
df = df.dropna()
```

## 最佳实践

1. **连接管理**: 使用后及时调用 `w.close()` 关闭连接
2. **错误处理**: 始终检查 `ErrorCode` 并处理异常情况
3. **数据验证**: 获取数据后检查数据的完整性和合理性
4. **性能优化**: 避免频繁调用API，建议本地缓存数据
5. **日期处理**: 注意交易日与自然日的区别，可能返回的数据条数少于预期

## 相关文档

- [Wind数据获取完整指南](../Wind数据获取完整指南.md)
- [Wind API官方文档](https://www.wind.com.cn/)
- [合并字段参考](../merged_fields_fixed.txt)

## 更新日志

- 2025-10-20: 初始版本创建

---

**注意事项**:
- 本API需要有效的Wind终端授权
- 数据更新时间通常为T+1
- 部分历史数据可能存在缺失
- 建议在交易时间段外进行大量数据查询

