# 网格交易策略 v3.0

基于 vnpy 框架的网格交易策略，支持 QMT 实盘交易和历史 tick 数据模拟回放。

## 模块架构

```
网格实盘3.0/
├── __init__.py          # 包初始化
├── config.py            # 配置常量、状态码映射、默认参数
├── models.py            # 数据模型 (GridSpec, PositionEntry, Trade)
├── utils.py             # 工具函数 (交易所判断、交易时段判断)
├── grid_engine.py       # 网格引擎 (层级管理、价格映射、越界检测)
├── position_book.py     # 仓位簿 (CRUD、CSV持久化、线程安全、审计日志)
├── order_manager.py     # 订单管理 (挂单状态、券商同步、涨跌停检查、去重)
├── broker.py            # 券商网关 (QMT下单、查询、成交回调)
├── trader.py            # QMT交易器构建 (BaseTrader工厂)
├── tick_converter.py    # Tick数据转换 (xtdata → vnpy TickData)
├── reporter.py          # 交易报告 (配对逻辑、日终CSV输出)
├── grid_strategy.py     # 策略核心 (网格初始化、tick处理、买卖决策)
├── strategy_manager.py  # 策略管理器 (生命周期、行情订阅、回调路由)
├── mock_replayer.py     # 模拟回放器 (历史tick数据回放)
└── run.py               # 统一启动入口
```

## 模块职责

| 模块 | 职责 | 行数 |
|------|------|------|
| `config.py` | 集中管理所有魔法数字和常量 | ~100 |
| `models.py` | 定义数据结构，无业务逻辑 | ~180 |
| `utils.py` | 纯函数工具，无状态 | ~80 |
| `grid_engine.py` | 价格↔层级映射，越界检测 | ~130 |
| `position_book.py` | 仓位CRUD + CSV持久化 | ~280 |
| `order_manager.py` | 订单全生命周期管理 | ~350 |
| `broker.py` | 券商交互封装 | ~280 |
| `grid_strategy.py` | 交易决策（从原1870行精简） | ~550 |
| `strategy_manager.py` | 策略编排（从原767行精简） | ~250 |

## 仓位状态流转

```
pending (买单已下，未成交)
    ↓ 券商确认成交 / sync_buy_order_status
BuyFilled (买单已成交，等待挂卖单)
    ↓ place_sell_for_pending_positions
hanging (卖单已挂出)
    ↓ 卖单成交            ↓ 卖单撤销
filled (完成一轮)      cancelled (已撤销)
    ↓ 清理删除               ↓ 重新挂卖单
  (移除记录)              hanging
```

## 快速开始

### 实盘模式

```bash
python run.py --symbol 162411.SZ --step 0.001 --baseline 1.076 --up_grids 50 --down_grids 100
```

### 模拟回放模式

```bash
python run.py --symbol 162411.SZ --simulate --simulate-date 20260304 --speed-factor 2.0
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--symbol` | 162411.SZ | 股票代码 |
| `--step` | 0.001 | 网格步长 |
| `--up_grids` | 50 | 向上网格数 |
| `--down_grids` | 100 | 向下网格数 |
| `--lot_per_grid` | 1 | 每格手数 |
| `--hand_size` | 100 | 每手股数 |
| `--baseline` | 1.076 | 基准价格 |
| `--simulate` | False | 启用模拟回放 |
| `--simulate-date` | 20260304 | 模拟日期 |
| `--speed-factor` | 1.0 | 回放速度因子 |

## 相比 v2 (网格实盘新) 的改进

1. **模块拆分**：原 `grid_strategy.py` 1870行 → 拆分为 6 个模块，每个 < 350 行
2. **常量集中**：所有魔法数字（订单状态码、超时值等）集中到 `config.py`
3. **职责清晰**：订单管理、券商交互、仓位管理各有独立模块
4. **中文注释**：每个模块、每个类、每个关键方法均有详细注释
5. **数据模型**：`models.py` 统一定义所有数据结构
6. **线程安全**：`PositionBook` 使用 RLock 保护所有操作
7. **审计日志**：删除仓位自动记录到 `removed_positions.csv`（含调用栈）

## 依赖

- vnpy / vnpy_ctastrategy
- xtquant (xtdata + QMT交易)
- pandas
