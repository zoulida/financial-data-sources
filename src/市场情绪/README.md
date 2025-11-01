# 市场情绪监控程序

## 📋 概述

本程序用于获取和分析内地市场的涨跌家数统计，包括上涨、平盘、下跌、涨停、跌停家数等关键市场情绪指标。

## 🚀 功能特性

### 核心功能
- **数据获取**: 使用Wind API获取内地市场涨跌家数统计
- **指标计算**: 自动计算市场强度、情绪指标等衍生指标
- **数据分析**: 提供市场情绪分析和统计信息
- **数据保存**: 支持CSV格式数据保存
- **可视化**: 提供多种图表展示市场情绪变化

### 支持的指标
- 内地-上涨家数
- 内地-平盘家数  
- 内地-下跌家数
- 内地-涨停家数
- 内地-跌停家数

### 计算的衍生指标
- 总股票数
- 上涨/下跌/平盘比例
- 涨停/跌停比例
- 涨跌比
- 涨跌停比
- 市场强度指标
- 综合情绪指标

## 📁 文件结构

```
src/市场情绪/
├── market_sentiment_monitor.py  # 主程序模块
├── visualization.py             # 可视化模块
├── example_usage.py            # 使用示例
├── field.txt                   # 字段映射文件
└── README.md                   # 说明文档
```

## 🛠️ 安装依赖

```bash
pip install pandas numpy matplotlib seaborn WindPy
```

## 📖 使用方法

### 基本使用

```python
from src.市场情绪.market_sentiment_monitor import MarketSentimentMonitor

# 创建监控器
monitor = MarketSentimentMonitor()

# 获取最近5天的数据
df = monitor.get_latest_data(days=5)

# 计算情绪指标
df_with_indicators = monitor.calculate_sentiment_indicators(df)

# 分析市场情绪
analysis = monitor.analyze_market_sentiment(df_with_indicators)

# 保存数据
monitor.save_data(df_with_indicators)

# 关闭Wind接口
monitor.close()
```

### 自定义日期范围

```python
# 获取指定日期范围的数据
df = monitor.get_market_sentiment_data("2025-01-20", "2025-01-29")
```

### 可视化

```python
from src.市场情绪.visualization import MarketSentimentVisualizer

# 创建可视化器
visualizer = MarketSentimentVisualizer()

# 生成概览图
visualizer.plot_sentiment_overview(df)

# 生成热力图
visualizer.plot_sentiment_heatmap(df)

# 生成分布图
visualizer.plot_sentiment_distribution(df)

# 生成趋势图
visualizer.plot_sentiment_trend(df)

# 创建完整仪表板
visualizer.create_dashboard(df, "charts")
```

## 🎯 运行示例

### 运行基本示例
```bash
python src/市场情绪/example_usage.py
```

### 运行主程序
```bash
python src/市场情绪/market_sentiment_monitor.py
```

## 📊 输出说明

### 数据文件
- **CSV格式**: 包含原始数据和计算指标
- **保存位置**: `data/market_sentiment_YYYYMMDD_HHMMSS.csv`

### 图表文件
- **概览图**: 涨跌家数对比、涨跌停家数、市场强度、情绪指标
- **热力图**: 各指标的时间序列热力图
- **分布图**: 各指标的分布直方图
- **趋势图**: 市场情绪趋势分析图

### 日志文件
- **位置**: `logs/market_sentiment_YYYYMMDD.log`
- **内容**: 程序运行日志和错误信息

## 🔧 配置说明

### Wind API配置
程序使用Wind API获取数据，需要：
1. 安装WindPy库
2. 确保有Wind数据权限
3. 程序会自动初始化Wind接口

### 模拟数据模式
如果Wind API不可用，程序会自动切换到模拟数据模式，用于测试和演示。

## 📈 指标说明

### 基础指标
- **上涨家数**: 当日上涨的股票数量
- **下跌家数**: 当日下跌的股票数量
- **平盘家数**: 当日平盘的股票数量
- **涨停家数**: 当日涨停的股票数量
- **跌停家数**: 当日跌停的股票数量

### 衍生指标
- **市场强度**: (上涨比例 - 下跌比例) × 100
- **情绪指标**: 综合涨跌比例和涨跌停比例的情绪指标
- **涨跌比**: 上涨家数 / 下跌家数
- **涨跌停比**: 涨停家数 / 跌停家数

### 情绪判断标准
- **极度乐观**: 情绪指标 > 20
- **乐观**: 情绪指标 10-20
- **中性**: 情绪指标 -10 到 10
- **悲观**: 情绪指标 -20 到 -10
- **极度悲观**: 情绪指标 < -20

## ⚠️ 注意事项

1. **数据权限**: 确保有Wind API的数据权限
2. **网络连接**: 需要稳定的网络连接
3. **日期格式**: 使用'YYYY-MM-DD'格式
4. **资源管理**: 使用完毕后调用`close()`方法关闭Wind接口
5. **错误处理**: 程序包含完整的错误处理和日志记录

## 🔍 故障排除

### 常见问题
1. **WindPy导入失败**: 检查是否安装了WindPy库
2. **数据获取失败**: 检查Wind API权限和网络连接
3. **图表显示问题**: 检查matplotlib中文字体配置

### 日志查看
查看`logs/market_sentiment_YYYYMMDD.log`文件获取详细错误信息。

## 📞 技术支持

如遇到问题，请检查：
1. 依赖库是否正确安装
2. Wind API是否正常工作
3. 网络连接是否正常
4. 查看日志文件获取详细错误信息

## 📝 更新日志

### v1.0.0 (2025-01-29)
- 初始版本发布
- 支持内地市场涨跌家数统计
- 提供完整的可视化功能
- 包含错误处理和日志记录
