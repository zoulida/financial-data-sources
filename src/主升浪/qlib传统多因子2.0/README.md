# QLib 传统多因子 2.0

在 1.0 单文件 workflow 的基础上扩展，支持：

1. **任选因子库目录**：`_root` / `alpha101` / `alpha158` / `alpha191`，可多选。
2. **股票池二级过滤**：按"市值"（akshare 实时市值快照）+ "股价"区间静态过滤股票池。
3. **三种未来收益口径**：T+N 持有期 close、T+1~T+N 区间 max(high)、T+1~T+N 区间 max(close)。
4. **三种因子过滤策略**：`none`、`threshold`（IC 阈值 + 相关性去重）、`topk`（按 |Rank IC IR| 降序选 K 个）。
5. **传统打分回测** 与 **ML 信号回测**：等权 / IC 加权 / 规则 三种打分；LightGBM / Ridge / Lasso 三种 ML 模型。

## 目录结构

```
qlib传统多因子2.0/
├── README.md                    # 本文件
├── workflow_v2_config.json      # Web 持久化默认参数（首次运行后生成）
├── _cache_market_cap.csv        # akshare 市值快照缓存（首次运行后生成）
├── workflow_v2.py               # 主入口 + Flask Web 控制台
├── factor_loader.py             # 因子库自动扫描与统一调用
├── stock_pool_filter.py         # 股票池过滤（akshare 市值 + 股价区间）
├── return_builder.py            # 三种未来收益构造
├── factor_filter.py             # 三种过滤策略
├── ml_pipeline.py               # LightGBM / Ridge / Lasso 训练与预测
├── _smoke_test.py               # 端到端冒烟测试（traditional 链路）
├── _smoke_test_ml.py            # 端到端冒烟测试（ML 链路）
└── results/                     # 结果输出目录（运行后生成）
```

## 快速开始

### 启动 Web 控制台（推荐）

```powershell
cd d:\pythonProject\sdufe-qlib\source\qlib传统多因子2.0
python workflow_v2.py
```

控制台默认监听 `http://127.0.0.1:7778/`。表单上选好参数后点击"运行"，右侧会实时刷新日志和结果表。

### 命令行直跑

```powershell
python workflow_v2.py --cli
```

会读取 `workflow_v2_config.json` 中的参数（不存在则用默认值）直接运行一次。

### 冒烟测试

```powershell
python _smoke_test.py     # traditional 链路（用 _root 因子库）
python _smoke_test_ml.py  # ML 链路（用 _root + ridge）
```

## 关键参数说明

参考类 `WorkflowConfigV2`（在 `workflow_v2.py` 中定义）。

### 数据 / 股票池

| 参数 | 默认值 | 说明 |
|---|---|---|
| `provider_uri` | `d:/pythonProject/sdufe-qlib/source/qlib-data数据下载/cn_data` | QLib 数据目录 |
| `market` | `csi300` | 股票池 |
| `benchmark` | `SH000300` | 基准指数 |
| `start_time` / `end_time` | `2024-11-01` / `2026-04-30` | 行情起止 |

### 股票池过滤（市值 + 股价）

读取股票池行情后、构造未来收益前，可按"总市值/流通市值"和"股价"做静态二级过滤。

| 参数 | 默认值 | 说明 |
|---|---|---|
| `enable_market_cap_filter` | `True` | 是否启用市值过滤 |
| `min_market_cap_yi` / `max_market_cap_yi` | `20` / `150` | 市值区间（亿元） |
| `market_cap_kind` | `total` | `total` 总市值 / `float` 流通市值 |
| `market_cap_cache_max_age_days` | `30` | 市值快照缓存有效期 |
| `force_refresh_market_cap_cache` | `False` | 强制重新拉取（首次或想取最新值时勾选） |
| `enable_price_filter` | `True` | 是否启用股价过滤 |
| `min_close_price` / `max_close_price` | `2.0` / `15.0` | 股价区间（元） |
| `price_filter_mode` | `last` | `last` 末日价 / `mean` 全期均值 / `median` 全期中位数 |

实现要点：

- **市值数据来源**：QLib `cn_data` 不含市值字段，运行时通过 `akshare` 实时拉取全 A 股市值快照（5500+ 只），缓存到 `_cache_market_cap.csv`，30 天内复用。仅首次或缓存过期时联网。
- **静态过滤**：市值/股价均按"快照"剔除整支股票，而非按日动态剔除。优点是简洁、不引入幸存者偏差以外的复杂性；缺点是回测期内股价/市值漂移大的股票需要通过 `mean`/`median` 模式平滑。
- **股票代码自动转换**：akshare 返回的 `600000`/`000001` 自动转为 QLib 风格 `SH600000`/`SZ000001`/`BJ8xxxxx`。

> ⚠️ **csi300 成分股几乎都是大盘股（市值 200 亿+）**。如要在 csi300 上启用 `[20, 150]` 亿区间，过滤后股票数量可能为 0 而报错。要么放宽上限，要么改用 `market=csi500` / `csi1000` / `all`。

### 因子库（多选）

`factor_libraries: List[str]`，从下列 4 个值中任选若干：

| 库名 | 因子数（实际可用） | 备注 |
|---|---|---|
| `_root` | 2 | 顶层散件 `momentum.py` / `risk_adjusted_momentum.py` |
| `alpha101` | 101 | WorldQuant 101 alphas，**部分因子计算量大，全量加载需 4-5 分钟** |
| `alpha158` | 78 | 简化版 158，多为 ratio / rank 类，秒级 |
| `alpha191` | 189 | 国泰君安 191，2 个未实现因子（`#030` `#143`）已被自动跳过 |

`alpha101` / `alpha191` 中部分因子使用了大量 `rolling correlation` / `ts_rank` 等 O(N²) 操作，单个因子可能耗时 5-15 秒。慢因子会有 `⚠️ 慢因子 ... 耗时 ...s` 的提示。

### 未来收益

| 参数 | 取值 | 说明 |
|---|---|---|
| `future_return_mode` | `holding_close` | T+N 收盘价 / T 收盘价 - 1 |
|  | `max_high` | 未来 N 日内最高价（high）/ T 收盘价 - 1 |
|  | `max_close` | 未来 N 日内最高收盘价 / T 收盘价 - 1 |
| `holding_period` | 1 | 持有期 N |

> **重要**：`max_high` / `max_close` 仅用于 **因子评价** 与 **ML 标签**；**回测净值** 一律按 close-to-close 计算（最高价通常无法实际成交，避免失真）。

### 因子过滤

| 参数 | 取值 | 说明 |
|---|---|---|
| `filter_method` | `none` | 不过滤 |
|  | `threshold` | `|RankIC mean| > rank_ic_min` 且 `|RankIC IR| > rank_ic_ir_min`，再剔除 `|相关性| > corr_max` 的高相关因子（保留 IR 更高者） |
|  | `topk` | 按 `|RankIC IR|` 降序选前 K 个 |
| `filter_rank_ic_min` | 0.02 | 阈值参数 |
| `filter_rank_ic_ir_min` | 0.3 | 阈值参数 |
| `filter_corr_max` | 0.7 | 相关性阈值 |
| `filter_topk` | 20 | TopK 参数 |

### 信号 / ML

| 参数 | 取值 | 说明 |
|---|---|---|
| `signal_mode` | `traditional` | 等权 / IC 加权 / 规则 三种打分 |
|  | `ml` | 单一 ML 模型预测信号 |
| `ml_model` | `lightgbm` | 默认；超参与 `qlib官方/official_workflow_demo.py` 一致 |
|  | `ridge` | sklearn Ridge（最快，对照基线） |
|  | `lasso` | sklearn Lasso |
| `train_end_time` | `2025-06-30` | 训练集终点 |
| `valid_end_time` | `2025-09-30` | 验证集终点（仅 LightGBM 用作 early stopping） |
| `test_start_time` | `2025-10-01` | 测试集起点（即回测段起点） |

## 与 1.0 的差异

| 维度 | 1.0 (`qlib传统多因子/`) | 2.0 (本目录) |
|---|---|---|
| 因子来源 | 硬编码 10 个因子 | 任选 4 个目录的全部因子 |
| 数据结构 | MultiIndex(datetime, instrument) Series | 全程宽表 DataFrame |
| 未来收益 | 仅 T+1 次日收益 | 三种口径，N 可配置 |
| 因子过滤 | 无 | 三种策略 |
| ML 训练 | 无 | LightGBM / Ridge / Lasso |
| Web 端口 | 7777 | 7778（错开） |
| 主体文件 | 单文件 ~880 行 | 6 个模块拆分 |

## 常见问题

### Q1: 为什么 `alpha101` 加载这么慢？

部分因子（如 `alpha017` / `alpha026` / `alpha035`）使用了 `ts_rank` + `rolling correlation` 嵌套，时间复杂度高。这是因子库自身的实现问题，与 workflow 无关。**建议**：

- 默认只用 `_root` 或 `alpha158` 快速验证
- 需要用 `alpha101` / `alpha191` 时耐心等待，或先 cache 因子值

### Q2: 在 Windows 中文目录下卡死？

QLib 默认用 `joblib_backend='multiprocessing'`，在 Windows + 中文路径下子进程 spawn 会因路径乱码失败、反复重试。`workflow_v2.py` 已强制 `joblib_backend='threading'` + `kernels=1` 规避。

如果你在自己的脚本中复用 workflow，请用 `if __name__ == "__main__":` 守卫包住主体代码。

### Q3: `factor_libraries=['alpha101', 'alpha191']` 后内存暴涨？

每个因子是一份和 close 同形状的宽表，全部加载后会占用 `n_days × n_codes × 290 × 8 bytes`。对于 2 年 csi300 数据约 `500 × 300 × 290 × 8 ≈ 350 MB`，可控。如果内存紧张，建议先用 `topk` 做粗筛、再用 `threshold` 做精筛。

### Q4: ML 模式下基准选择？

ML 模式下，`train_end_time / valid_end_time / test_start_time` 必须落在 `start_time` 与 `end_time` 之间。建议 `train ≈ 70%` / `valid ≈ 15%` / `test ≈ 15%`。
