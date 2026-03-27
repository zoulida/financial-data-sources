# 竞价监控程序

## 功能说明
在开盘日9:15-9:20期间，每10秒获取A股tick数据，记录竞价最大金额并保存到CSV文件。

## 使用方法

### 1. 直接运行
```bash
python auction_monitor.py
```

### 2. 定时运行（推荐）
在竞价时间前启动程序，会自动监控9:15-9:20的竞价数据。

## 输出文件
- `data/auction_max_amounts.csv`：竞价最大金额记录
  - date: 日期
  - total_max_amount: 当日竞价最大金额总和
  - stock_count: 统计股票数量
  - timestamp: 记录时间

## 依赖
- xtquant
- pandas
- tools.tradeCal（交易日历）

## 注意事项
- 确保在竞价时间（9:15-9:20）运行
- 需要网络连接获取实时数据
- 首次运行可能需要更新板块数据
