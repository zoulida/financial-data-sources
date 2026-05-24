# OpenTDX 多因子 Workflow 回测

这是一个只使用 `md/通达信/opentdx-main` 数据接口的 OpenTDX 多因子回测框架，结构参考 `src/主升浪/qlib传统多因子2.0/workflow_v2.py`。

## 功能

- **数据源**：全部来自 OpenTDX。
- **股票池**：默认过滤 `价格 < 15元`、`总市值 < 120亿` 的小盘低价股。
- **基础因子**：动量、波动率、成交额、换手、价格强度、资金流、异动强度。
- **回测方式**：TopN 选股、周调仓、等权持仓、下一交易日执行。
- **交互界面**：内置 Flask Web 控制台，支持参数配置、启动任务、实时日志和结果摘要。

## 启动 Web 控制台

```powershell
python workflow_opentdx.py
```

默认地址：

```text
http://127.0.0.1:7788/
```

如果端口冲突：

```powershell
python workflow_opentdx.py --port 7789
```

## 命令行运行

```powershell
python workflow_opentdx.py --cli
```

小样本调试：

```powershell
python workflow_opentdx.py --cli --debug-max-codes 30
```

强制刷新缓存：

```powershell
python workflow_opentdx.py --cli --force-refresh-cache
```

## 配置文件

默认配置：

```text
workflow_opentdx_config.json
```

关键参数：

- **`opentdx_path`**：OpenTDX 项目路径。
- **`max_price`**：股价上限，默认 `15.0`。
- **`max_market_cap_yi`**：市值上限，默认 `120.0` 亿元。
- **`topn`**：每次调仓持仓数量，默认 `30`。
- **`rebalance_freq`**：调仓频率，默认 `W-FRI`。
- **`debug_max_codes`**：调试限制股票数量，`0` 表示不限制。
- **`enable_data_cache`**：是否启用缓存。

## 输出目录

每次运行输出到：

```text
outputs/YYYYMMDD_HHMMSS/
```

主要文件：

- **`config.json`**：本次运行配置。
- **`universe.csv`**：过滤后的股票池。
- **`stock_pool_report.csv`**：股票池过滤报告。
- **`price_panel_close.csv`**：收盘价矩阵。
- **`factor_values/`**：单因子矩阵。
- **`factor_evaluation.csv`**：因子评价。
- **`factor_scores.csv`**：综合得分。
- **`selection.csv`**：调仓日选股。
- **`target_weights.csv`**：目标权重。
- **`holdings_by_rebalance.csv`**：每次调仓持仓。
- **`equity_curve.csv`**：净值曲线。
- **`drawdown.csv`**：回撤序列。
- **`performance.csv`**：绩效摘要。
- **`equity_curve.png`**：净值图。
- **`drawdown.png`**：回撤图。

## 注意事项

- OpenTDX 全市场逐只拉取 K 线较慢，建议先用 `debug_max_codes=30` 跑通。
- 市值字段依赖 OpenTDX 返回字段，若字段不可用会尝试用价格和股本估算。
- 该框架用于研究回测，不直接下单交易。
