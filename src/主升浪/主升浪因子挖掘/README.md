# 主升浪因子挖掘

专门用于"在主升浪起爆前夜识别潜伏标的"的因子挖掘与评估子项目。

## 目录结构

```
src/主升浪因子挖掘/
├── config.py                  # 主升浪事件阈值、Top-K、缓存目录
├── events.py                  # 主升浪事件标注（is_blastoff / forward_max_return / forward_drawdown / time_to_peak）
├── factors/
│   ├── _base.py               # 共享算子（rolling_zscore / linreg_slope ...）
│   ├── vol_shrink_20.py       # 缩量盘整：log(volume) 的 20 日斜率取负
│   ├── range_squeeze_20.py    # 布林带宽度收窄
│   ├── higher_lows_20.py      # 低点抬升斜率
│   ├── amount_anomaly_5.py    # 5 日成交额相对前 20 日均值的 z-score
│   └── ma_alignment.py        # 5/10/20/60 日均线粘合度
├── factor_registry.py         # 自动发现 factors/ 下因子，注册名为 blastoff.<name>
├── blastoff_evaluation.py     # 主升浪 KPI：Precision@K / Recall@K / 平均最大涨幅 / 起爆速度 / 盈亏比
├── report.py                  # CSV + PNG 输出
├── dialogs.py                 # Tkinter 运行参数对话框
├── main.py                    # 入口
├── outputs/                   # 评估结果（首次运行自动生成）
├── factor_cache/              # 因子缓存（暂未使用，预留）
└── event_cache/               # 事件标注缓存
```

## 主升浪事件定义

对每只股票每个交易日 t（以 t 日收盘价作为买入价）：
- `forward_max_return[t]` = max( close[t+1..t+N] ) / close[t] - 1
- `forward_drawdown[t]` = 在到达上述峰值之前的最大回撤（≤ 0）
- `time_to_peak[t]` = 达到峰值用了多少个交易日（1..N）
- `is_blastoff[t]` = `forward_max_return >= 涨幅阈值` 且 `forward_drawdown >= -最大回撤限制`

默认参数（可在对话框中修改）：
- `N = 20` 个交易日
- 涨幅阈值 = 30%
- 最大回撤限制 = 8%

## 评估指标

- **Precision@K**：每日因子排名前 K 中，未来 N 日触发主升浪事件的占比（按时间均值）
- **Recall@K**：所有主升浪事件中被排进前 K 的占比
- **平均/中位最大涨幅**：TopK 内 `forward_max_return` 的均值/中位数
- **平均最大回撤**：TopK 内 `forward_drawdown` 的均值
- **平均起爆速度**：TopK 内 `time_to_peak` 的均值（越小越好）
- **盈亏比** = 平均最大涨幅 / |平均最大回撤|
- **IC / RankIC（参考列）**：复用 `src/多因子/factor_evaluation`

## 运行

在项目根目录（`d:/pythonProject/数据源`）执行：

```bash
python -m src.主升浪因子挖掘.main
```

弹出对话框 → 选日期范围、事件参数、Top-K 列表、勾选因子 → 点"运行" → 控制台打印各因子 KPI，文件写入 `outputs/<run_id>/<factor>/`。

## 输出结构

```
outputs/<run_id>/
├── overall_summary.csv               # 所有因子的最高 K 档汇总
└── <factor_name>/
    ├── metrics.csv                   # 各档 Top-K 的 KPI
    ├── ic_reference.csv              # IC / RankIC 参考列
    ├── events_summary.csv            # 事件总览
    ├── precision_at_k.png            # Precision@K 柱状图
    ├── max_return_at_k.png           # 平均最大涨幅柱状图
    └── top_K_picks_<snapshot>.csv    # 末期 Top-K 个股清单（可作盘前参考）
```

## 复用 src/多因子 的模块

- `data_loader.build_data_bundle`：股票池 + 日线行情 + 基准（含批量数据缓存与 xtquant 懒加载）
- `universe.build_tradable_mask`：可交易掩码
- `scoring.mask_factor`：因子值掩码
- `backtest_vectorbt.build_rebalance_mask`：调仓日掩码（仅用于 IC 计算口径）
- `factor_evaluation.calc_ic_series / calc_rank_ic_series`：参考指标

本子项目**不修改**任何 `src/多因子` 文件。

## 后续扩展点

- 增加更多起爆前夜因子（建议方向：换手加速、跳空次数、底部成交量分位、量价背离等）
- 接入 `src/多因子/backtest_vectorbt` 做组合层回测，加入动态止盈止损
- 把"事件总览"扩成行业分布、市值分布、起爆速度直方图
