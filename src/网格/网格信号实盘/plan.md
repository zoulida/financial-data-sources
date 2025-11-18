<!-- 9d64e5bb-dd8e-44b1-b13e-82d4a6355d1b 8c5edc23-b0a2-4490-a2e9-37a953f4df7b -->
# 网格信号生成器（512710.SH）实现计划

## 目标

构建一个可运行的“信号+本地模拟成交”网格策略：

- 标的：`512710.SH`
- 网格步长：0.001 元；上方10格、下方20格（共31价位）
- 每格仓位：10手（假设1手=100份，可配置）
- 触发规则：价格到达某网格价位
  - 若该价位持仓=0 → 生成买入并模拟成交；随即在上一个网格挂出卖单
  - 若该价位已有持仓 → 生成卖出并模拟成交；随即在下一个网格挂出买单
- 突破最上/最下网格：停止交易并告警，直到价格回到网格内
- 启动时基准价：当日9:30开盘价（从快照字段`open`获取）；若未到9:30则等待
- 盘中时段：9:30-11:30与13:00-15:01；时段外仅记录/等待，不产生新单
- 行情数据：使用`md/tdx/xtdata_quote.py`的`fetch_quotes_basic_auto_switch`
- 每日收盘后输出CSV：仓位、成交配对盈亏、成交记录、持仓盈亏

## 目录与主要文件

- 新增：`src/网格/网格信号/grid_engine.py`
  - 网格构建与价格到格位判定、越界停止逻辑
- 新增：`src/网格/网格信号/order_sim.py`
  - 本地撮合/成交回报、挂单簿（上/下一个格）
- 新增：`src/网格/网格信号/position_book.py`
  - 每格持仓、加减仓、成本核算、未实现盈亏
- 新增：`src/网格/网格信号/reporter.py`
  - 日内记录与收盘汇总：成交明细、成交对、仓位、持仓盈亏，落地CSV
- 新增：`src/网格/网格信号/runtime.py`
  - 交易时段控制、首次9:30基准获取、订阅并循环处理tick、策略主循环
- 新增：`scripts/run_grid_512710.py`
  - 运行入口（可传参：手数、步长、上下格数、输出目录等）

## 关键实现要点

- 基准与网格：
  - 等待交易日且时间≥09:30，取快照`open`作为`baseline`
  - 生成价位集合：`levels = [baseline + k*0.001 for k in range(-20, 11)]`（含两端）
  - 保留两端边界以做越界检查
- 价格到达判定：
  - 取快照字段`price`为最新成交价（若为空，可后退用`bid1/ask1`中点）
  - 以上一个价格`last_price`与当前`price`确定“跨越的格位列表”，逐一执行
- 订单与撮合：
  - 网格级别只允许0/持有（10手），到达价位：若持仓=0则买入成交，若持仓>0则卖出成交
  - 成交后立即在相邻格位生成对向挂单；越过边界则忽略该挂单
  - 撮合为价到即成（模拟即时成交），不维护盘口深度
- 越界与恢复：
  - 当`price > max(levels)`或`price < min(levels)`：进入`halted`，仅监控不下单；当价格回到区间内自动解除
- 交易时段：
  - 仅在时段内执行策略逻辑；时段外不触发新成交
- 报表：
  - 成交明细：时间、方向、价位、数量、关联格位
  - 成交对盈亏：按买-卖配对逐笔统计，含持仓周期
  - 收盘仓位：逐格位数量、持仓成本、未实现盈亏；汇总总持仓与总盈亏
  - 路径：`data/grid/512710/YYYYMMDD/` 下生成 `trades.csv`, `pairs.csv`, `positions.csv`, `pnl.csv`

## 与现有代码的衔接

- 引用数据源：`from md.tdx.xtdata_quote import QuoteSubscriber` 或轮询 `fetch_quotes_basic_auto_switch(["512710.SH"])`
  - 采用轮询简化：每1.9s取一次，复用已有容错与IP切换
- 读取字段优先级：`price`→`(bid1+ask1)/2`→前价回退

## 配置项（入口脚本参数）

- `--symbol 512710.SH`
- `--step 0.001`
- `--up_grids 10 --down_grids 20`
- `--lot_per_grid 10`（手）与`--hand_size 100`
- `--out_dir data/grid/512710`
- `--tick_interval 1.9`

## 简要伪代码片段

- 价格跨格处理（简化）：
```python
levels = make_levels(baseline, step, -down, up)
while in_trading_session(now()):
    px = get_last_price()
    for level in crossed_levels(last_px, px, levels):
        if halted: break
        if pos[level] == 0:
            fill_buy(level, qty)
            place_sell(level+1)
        else:
            fill_sell(level, qty)
            place_buy(level-1)
    last_px = px
```


## 验证与告警

- 启动时打印：基准价、网格上下边界
- 越界进入/退出时打印并写入日志
- 异常字段空值/断流：回退、跳过并记录

## 输出示例字段

- trades.csv：`ts,side,price,qty,level_idx`
- pairs.csv：`buy_ts,buy_px,sell_ts,sell_px,qty,pnl`
- positions.csv：`level_px,qty,avg_cost,unrealized_pnl`
- pnl.csv：`total_realized,total_unrealized,net`

### To-dos

- [ ] 创建 runtime 主循环，接入快照轮询与时间窗控制
- [ ] 实现网格生成、到达与跨越判定、越界停止与恢复逻辑
- [ ] 实现本地撮合引擎：买成即挂上格卖、卖成即挂下格买
- [ ] 实现逐格位持仓与成本、未实现盈亏计算
- [ ] 实现成交、配对盈亏、持仓与汇总 CSV 输出
- [ ] 创建运行脚本 run_grid_512710.py 支持命令行配置


