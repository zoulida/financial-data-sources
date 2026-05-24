# OpenTDX 多因子 Workflow Web 回测计划

本计划将在 `src/opentdx多因子` 下实现一套参考 `workflow_v2.py` 架构的 OpenTDX 多因子回测系统，包含命令行运行、内置 Flask Web 控制台、实时日志和结果摘要。

## 1. 目标与边界

- **目标目录**：`d:\pythonProject\数据源\src\opentdx多因子`
- **OpenTDX 来源**：`d:\pythonProject\数据源\md\通达信\opentdx-main`
- **数据源约束**：股票列表、报价、K 线、市值、板块、资金流、异动等全部来自 OpenTDX。
- **股票池过滤**：最新价 `<15元`，总市值 `<120亿`，剔除 ST、停牌、无成交、无有效价格标的。
- **第一版因子**：基础版多因子，不复刻完整 Alpha158。
- **Web 形态**：参考 `workflow_v2.py`，采用单文件 Flask 控制台模式。

## 2. 参考 `workflow_v2.py` 的框架设计

计划新增：

```text
src/opentdx多因子/
    OpenTDX_多因子Workflow回测计划.md
    workflow_opentdx.py
    workflow_opentdx_config.json
    opentdx_loader.py
    README.md
    cache/
    outputs/
```

`workflow_opentdx.py` 参考 `workflow_v2.py`：配置类、配置持久化、Workflow 主类、耗时统计、缓存机制、CLI/Web 双入口、后台运行状态、Web API 和内嵌 HTML 控制台。

## 3. Workflow 主流程步骤

1. 初始化 OpenTDX。
2. 加载股票列表与报价。
3. 执行 `<15元`、`<120亿` 股票池过滤。
4. 加载历史 K 线并构造面板。
5. 构造未来收益。
6. 计算基础因子。
7. 横截面标准化。
8. 单因子评价。
9. 构造综合信号。
10. 组合回测。
11. 保存结果。
12. 生成图表。

## 4. Web 交互界面

第一版页面包含参数表单、启动回测、清空缓存、实时日志、结果摘要、因子评价 Top 表、最近一次调仓持仓和图表路径。

## 5. 验收标准

- `python workflow_opentdx.py` 能启动 Web 控制台。
- `python workflow_opentdx.py --cli` 能直接运行回测。
- Web 能设置参数、启动任务、查看实时日志和结果摘要。
- 全流程数据来源仅为 OpenTDX。
- 股票池严格执行 `<15元`、`<120亿`。
- 能生成完整结果目录、CSV、图表和 README。
