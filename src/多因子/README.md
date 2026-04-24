# 多因子回测框架

本目录提供一版面向 A 股小盘股波段场景的轻量多因子回测骨架。

## 设计原则

- 股票池统一走 `src/基础筛选/filterStocks.py` 中的 `get_universe_with_basics()`
- 日线行情统一走 `md/合并下载数据/合并下载数据.py`
- 时间范围统一走 `md/获取enddate/get_date_range.py`
- 第一版使用 `vectorbt` 做组合回测

## 当前内置因子

- `momentum_20`: 20日动量
- `risk_adjusted_momentum_20`: 20日风险调整动量

## 主入口

```python
from src.多因子.main import run_strategy

summary = run_strategy()
print(summary["results"]["stats"])
```

## 输出文件

默认输出到 `src/多因子/outputs/`：

- `selection_matrix.csv`
- `score_matrix.csv`
- `selected_stocks.csv`
- `portfolio_stats.csv`
- `equity_curve.csv`
- `returns.csv`
- `positions.csv`

## 说明

当前版本是第一版骨架，已完成：

- 基础股票池获取
- 日期范围自动获取（起始日期参考统一规则，固定从 `20241101` 开始）
- 日线行情对齐
- 两个技术因子
- 因子打分与等权选股
- VectorBT 组合回测

后续建议继续补充：

- 停牌 / 涨跌停过滤
- 上市天数过滤
- Wind 辅助基本面过滤
- 更丰富的回测报告

