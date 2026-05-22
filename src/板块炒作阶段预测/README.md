# 板块炒作阶段预测

基于 Qlib 全市场日线行情 + XtQuant 板块/概念成分，生成每日每个板块的四阶段分类预测：

- **预备炒作**：当前刚开始放量/扩散，未来明显走强
- **正在炒作**：过去强势、当前活跃，未来仍能延续
- **炒作末期**：过去明显上涨且当前拥挤，未来超额收益转弱或回撤扩大
- **冷门板块**：过去与未来都缺乏超额收益和成交活跃度

## 数据边界

- **行情**：仅使用 Qlib 全市场数据 `md/qlib数据/qlib_data/cn_data`
- **板块成分**：仅使用 XtQuant `xtdata.get_sector_list` / `xtdata.get_stock_list_in_sector`
- 不依赖 Wind、akshare、tushare 等外部数据源

## 模块结构

- `code_utils.py`：XtQuant ↔ Qlib 代码格式转换、A 股代码过滤
- `sector_constituents.py`：板块列表、成分股拉取与缓存
- `qlib_market_loader.py`：Qlib provider_uri 自动定位、行情宽表读取
- `feature_builder.py`：板块级特征工程（收益、活跃度、扩散度、拥挤度）
- `label_builder.py`：未来窗口四阶段标签构造
- `model_pipeline.py`：LightGBM 多分类（兜底 sklearn HGB）+ 时间切分评估
- `run_sector_stage.py`：CLI 入口

## 标签量化口径

所有阈值均为 **横截面分位**（每个交易日所有板块内部排名 0~1）。

| 阶段 | 过去强度 | 当前活跃度 | 未来表现 | 备注 |
| --- | --- | --- | --- | --- |
| **炒作末期** | `past_excess_long_rank ≥ 0.85` | `amount_share_rank ≥ 0.75` | `future_excess_main_rank ≤ 0.5` 或 `future_drawdown_main ≤ -10%` | 优先级最高 |
| **正在炒作** | `past_excess_main_rank ≥ 0.75` | `amount_share_rank ≥ 0.75` | `future_excess_short > 0` 且 `future_excess_main_rank ≥ 0.5` | |
| **预备炒作** | `past_excess_main_rank < 0.75` 且 `past_excess_long_rank < 0.85` | `amount_share_short_rank ≥ 0.6` | `future_excess_main_rank ≥ 0.85` | 抓"启动初期" |
| **冷门板块** | `past_excess_main_rank ≤ 0.5` | `amount_share_rank ≤ 0.4` | `future_excess_main_rank ≤ 0.5` | 兜底 |

未匹配上述任一规则的样本在默认配置下并入"冷门板块"（`merge_neutral_to_cold=True`），也可保留为"中性板块"做 5 分类。

## 模型

- 默认 LightGBM 多分类 (`objective=multiclass`)
- 启用 `class_weight` 自动平衡四类样本
- 严格按时间切分 train (60%) / valid (20%) / test (20%)
- 输出：测试集分类报告、特征重要性、最新交易日板块阶段概率榜单

## 使用方法

```bash
# 第一次使用建议先更新本地板块数据
python -m src.板块炒作阶段预测.run_sector_stage \
    --start-date 2024-01-01 \
    --end-date 2026-05-22 \
    --update-sectors \
    --output-dir src/板块炒作阶段预测/results

# 后续日常运行（板块缓存 24h 内复用）
python -m src.板块炒作阶段预测.run_sector_stage \
    --start-date 2024-01-01 \
    --end-date 2026-05-22

# 在没有 LightGBM 的环境降级到 sklearn
python -m src.板块炒作阶段预测.run_sector_stage --model hgb

# 只跑指定板块（用于冒烟）
python -m src.板块炒作阶段预测.run_sector_stage \
    --sectors 半导体 锂电池 光伏 人工智能
```

## 输出产物

`output_dir` 默认指向 `src/板块炒作阶段预测/results/`：

- `latest_predictions_<date>.csv`：最新一日板块阶段概率与主分类
- `full_predictions.csv`：训练区间全部样本的预测
- `test_predictions.csv`：测试集预测（含真实标签）
- `feature_importance.csv`：LightGBM 特征重要性（gain）
- `model_info.json`：训练时间切分、混淆矩阵、macro F1、balanced acc 等
- `run_info.json`：本次运行的全部参数

## 注意事项

- **板块成分历史不可回溯**：XtQuant 当前接口返回当前成分，会引入幸存者偏差。第一版在训练区间整体使用同一份成分；建议每天保存 `--snapshot` 快照，逐步累积成分历史。
- **Qlib 数据日期**：预测最新可达 Qlib 本地日历最新日，若数据未更新则预测会滞后。
- **板块高度重叠**：概念板块成分重复度高，最新榜单可能出现强相关板块，业务侧可在使用时人工合并或基于成分 Jaccard 去重。
- **冷门样本占比偏高**：默认把"中性"并入冷门，类别会偏向冷门；模型通过 `class_weight` 自动平衡，最终评估关注 macro F1 与 balanced accuracy。
