# GA 因子工作流 进化报告

种群=10, 代数=3, 交叉率=0.7, 变异率=0.2, 精英保留=2, 最大深度=3, 最大节点=24


说明：本文件逐代追加，可以在 GA 运行过程中随时查看。`operation` 含义：`random_init` 初始随机, `random_inject` 本代随机注入, `random_restart` 本代重启, `elite` 从上代直接保留, `crossover` 交叉, `mutate` 变异, `crossover+mutate` 先交叉后变异, `reproduction` 原样复制。


## 第 0 代  best=0.3485  mean=0.2958  n_valid=5  archive=2
- 本代有效个体操作分布：random_init=5

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0008 | random_init |  | 0.3485 | 0.1233 | 0.32 | 1 | 1 | `vwap` |
| 2 | ga_g000_0006 | random_init |  | 0.3383 | 0.1184 | 0.31 | 1 | 1 | `open` |
| 3 | ga_g000_0009 | random_init |  | 0.3168 | 0.1105 | 0.29 | 1 | 1 | `amount` |
| 4 | ga_g000_0005 | random_init |  | 0.2433 | -0.0280 | -0.07 | 1 | 1 | `returns` |
| 5 | ga_g000_0002 | random_init |  | 0.2320 | -0.0900 | -0.24 | 3 | 5 | `covariance[3](covariance[5](amount,open),high)` |


## 第 1 代  best=0.3485  mean=0.3015  n_valid=5  archive=3
- 本代有效个体操作分布：random_init=4 | random_inject=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g001_0000 | random_init |  | 0.3485 | 0.1233 | 0.32 | 1 | 1 | `vwap` |
| 2 | ga_g001_0004 | random_inject |  | 0.3453 | 0.1209 | 0.32 | 1 | 1 | `volume` |
| 3 | ga_g001_0001 | random_init |  | 0.3383 | 0.1184 | 0.31 | 1 | 1 | `open` |
| 4 | ga_g001_0003 | random_init |  | 0.2434 | -0.0280 | -0.07 | 1 | 1 | `returns` |
| 5 | ga_g001_0002 | random_init |  | 0.2320 | -0.0900 | -0.24 | 3 | 5 | `covariance[3](covariance[5](amount,open),high)` |


## 第 2 代  best=0.3576  mean=0.3227  n_valid=9  archive=4
- 本代有效个体操作分布：random_init=4 | random_inject=3 | crossover=1 | crossover+mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g002_0005 | crossover |  | 0.3576 | -0.0995 | -0.26 | 3 | 5 | `covariance[3](covariance[5](returns,open),high)` |
| 2 | ga_g002_0000 | random_init |  | 0.3411 | 0.1233 | 0.32 | 1 | 1 | `vwap` |
| 3 | ga_g002_0003 | crossover+mutate | field | 0.3390 | 0.1221 | 0.32 | 1 | 1 | `high` |
| 4 | ga_g002_0001 | random_inject |  | 0.3379 | 0.1209 | 0.32 | 1 | 1 | `volume` |
| 5 | ga_g002_0007 | random_inject |  | 0.3319 | 0.1190 | 0.31 | 1 | 1 | `low` |

- **#1 ga_g002_0005**  来源=`crossover`  变异点=`-`
  - parent[0] = `covariance[3](covariance[5](amount,open),high)`
  - parent[1] = `returns`
- **#3 ga_g002_0003**  来源=`crossover+mutate`  变异点=`field`
  - parent[0] = `volume`
  - parent[1] = `open`

---

## 🌳 最优 Top 10 因子血缘


**[1] ga_g002_0005**  fitness=`0.3576`  
  expr = `covariance[3](covariance[5](returns,open),high)`
```
    └─ gen=2 op=crossover parents=2
        parent[0] = covariance[3](covariance[5](amount,open),high)
        └─ gen=0 op=random_init (root)
        parent[1] = returns
        └─ gen=0 op=random_init (root)
```

**[2] ga_g000_0008**  fitness=`0.3485`  
  expr = `vwap`
```
    └─ gen=0 op=random_init (root)
```

**[3] ga_g001_0004**  fitness=`0.3453`  
  expr = `volume`
```
    └─ gen=1 op=random_inject (root)
```

**[4] ga_g000_0006**  fitness=`0.3383`  
  expr = `open`
```
    └─ gen=0 op=random_init (root)
```

## 第 0 代  best=1.0586  mean=0.6092  n_valid=22  archive=10
- 本代有效个体操作分布：random_init=22

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0037 | random_init |  | 1.0586 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 2 | ga_g000_0017 | random_init |  | 1.0398 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 3 | ga_g000_0004 | random_init |  | 1.0110 | 0.1236 | 1.55 | 3 | 3 | `ts_std[10](rank(returns))` |
| 4 | ga_g000_0048 | random_init |  | 0.9112 | -0.1231 | -1.90 | 2 | 2 | `ts_min[3](vwap)` |
| 5 | ga_g000_0013 | random_init |  | 0.9020 | -0.1217 | -1.88 | 1 | 1 | `low` |


## 第 1 代  best=1.0878  mean=0.6176  n_valid=30  archive=14
- 本代有效个体操作分布：random_init=18 | crossover=7 | random_inject=2 | crossover+mutate=2 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g001_0045 | random_inject |  | 1.0878 | 0.1203 | 1.87 | 2 | 3 | `sub(returns,open)` |
| 2 | ga_g001_0000 | random_init |  | 1.0579 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 3 | ga_g001_0030 | crossover+mutate | delay | 1.0425 | -0.1261 | -2.10 | 3 | 3 | `delay[5](delay[3](vwap))` |
| 4 | ga_g001_0001 | random_init |  | 1.0411 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 5 | ga_g001_0002 | random_init |  | 1.0109 | 0.1236 | 1.55 | 3 | 3 | `ts_std[10](rank(returns))` |

- **#3 ga_g001_0030**  来源=`crossover+mutate`  变异点=`delay`
  - parent[0] = `ts_std[10](rank(returns))`
  - parent[1] = `ts_rank[3](log_abs(low))`

## 第 2 代  best=1.1319  mean=0.6852  n_valid=38  archive=18
- 本代有效个体操作分布：crossover=16 | random_init=10 | mutate=5 | random_inject=4 | crossover+mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g002_0008 | crossover |  | 1.1319 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 2 | ga_g002_0007 | crossover |  | 1.1249 | 0.1490 | 1.96 | 4 | 6 | `sub(zscore_cs(covariance[30](amount,close)),open)` |
| 3 | ga_g002_0000 | random_inject |  | 1.0832 | 0.1203 | 1.87 | 2 | 3 | `sub(returns,open)` |
| 4 | ga_g002_0001 | random_init |  | 1.0535 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 5 | ga_g002_0003 | random_init |  | 1.0427 | 0.1511 | 1.51 | 1 | 1 | `volume` |

- **#1 ga_g002_0008**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_std[20](correlation[3](demean(open),open))`
  - parent[1] = `returns`
- **#2 ga_g002_0007**  来源=`crossover`  变异点=`-`
  - parent[0] = `sub(returns,open)`
  - parent[1] = `zscore_cs(covariance[30](amount,close))`

## 第 3 代  best=1.1451  mean=0.8045  n_valid=37  archive=21
- 本代有效个体操作分布：crossover=13 | random_inject=8 | random_init=8 | mutate=4 | crossover+mutate=4

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g003_0010 | mutate | sub | 1.1451 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 2 | ga_g003_0000 | crossover |  | 1.1305 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 3 | ga_g003_0001 | crossover |  | 1.1221 | 0.1490 | 1.96 | 4 | 6 | `sub(zscore_cs(covariance[30](amount,close)),open)` |
| 4 | ga_g003_0002 | random_inject |  | 1.0810 | 0.1203 | 1.87 | 2 | 3 | `sub(returns,open)` |
| 5 | ga_g003_0025 | crossover |  | 1.0621 | 0.1187 | 1.83 | 2 | 3 | `sub(returns,vwap)` |

- **#1 ga_g003_0010**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`
- **#2 ga_g003_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_std[20](correlation[3](demean(open),open))`
  - parent[1] = `returns`
- **#3 ga_g003_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `sub(returns,open)`
  - parent[1] = `zscore_cs(covariance[30](amount,close))`

## 第 4 代  best=1.2219  mean=0.9253  n_valid=33  archive=25
- 本代有效个体操作分布：crossover=21 | random_inject=4 | random_init=4 | mutate=2 | crossover+mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g004_0033 | crossover |  | 1.2219 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g004_0000 | mutate | sub | 1.1406 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 3 | ga_g004_0001 | crossover |  | 1.1351 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 4 | ga_g004_0009 | crossover |  | 1.1311 | 0.2108 | 1.65 | 4 | 4 | `abs(scale(ts_std[20](returns)))` |
| 5 | ga_g004_0017 | crossover |  | 1.1263 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |

- **#1 ga_g004_0033**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g004_0000**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`
- **#3 ga_g004_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_std[20](correlation[3](demean(open),open))`
  - parent[1] = `returns`

## 第 5 代  best=1.2233  mean=0.9378  n_valid=25  archive=27
- 本代有效个体操作分布：crossover=15 | random_init=5 | random_inject=3 | mutate=1 | crossover+mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g005_0000 | crossover |  | 1.2233 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g005_0001 | mutate | sub | 1.1421 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 3 | ga_g005_0002 | crossover |  | 1.1317 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 4 | ga_g005_0004 | crossover |  | 1.1277 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |
| 5 | ga_g005_0003 | crossover |  | 1.1277 | 0.2108 | 1.65 | 4 | 4 | `abs(scale(ts_std[20](returns)))` |

- **#1 ga_g005_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g005_0001**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`
- **#3 ga_g005_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_std[20](correlation[3](demean(open),open))`
  - parent[1] = `returns`

## 第 6 代  best=1.2246  mean=0.8927  n_valid=30  archive=29
- 本代有效个体操作分布：crossover=16 | random_init=6 | random_inject=4 | crossover+mutate=2 | mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g006_0000 | crossover |  | 1.2246 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g006_0028 | crossover+mutate | ts_min | 1.1898 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 3 | ga_g006_0001 | mutate | sub | 1.1433 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 4 | ga_g006_0002 | crossover |  | 1.1308 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 5 | ga_g006_0003 | crossover |  | 1.1290 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |

- **#1 ga_g006_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g006_0028**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`
- **#3 ga_g006_0001**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`

## 第 7 代  best=1.2231  mean=0.9074  n_valid=34  archive=32
- 本代有效个体操作分布：crossover=18 | random_init=7 | mutate=5 | crossover+mutate=3 | random_inject=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g007_0000 | crossover |  | 1.2231 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g007_0001 | crossover+mutate | ts_min | 1.1884 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 3 | ga_g007_0002 | mutate | sub | 1.1419 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 4 | ga_g007_0003 | crossover |  | 1.1302 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 5 | ga_g007_0004 | crossover |  | 1.1276 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |

- **#1 ga_g007_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g007_0001**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`
- **#3 ga_g007_0002**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`

## 第 8 代  best=1.2284  mean=0.8811  n_valid=29  archive=34
- 本代有效个体操作分布：crossover=16 | crossover+mutate=4 | random_inject=4 | mutate=3 | random_init=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g008_0000 | crossover |  | 1.2284 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g008_0001 | crossover+mutate | ts_min | 1.1932 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 3 | ga_g008_0002 | mutate | sub | 1.1474 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 4 | ga_g008_0004 | crossover |  | 1.1331 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |
| 5 | ga_g008_0003 | crossover |  | 1.1268 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |

- **#1 ga_g008_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g008_0001**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`
- **#3 ga_g008_0002**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`

## 第 9 代  best=1.2244  mean=0.9183  n_valid=32  archive=39
- 本代有效个体操作分布：crossover=15 | mutate=5 | random_init=5 | crossover+mutate=4 | random_inject=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g009_0000 | crossover |  | 1.2244 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g009_0001 | crossover+mutate | ts_min | 1.1898 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 3 | ga_g009_0013 | crossover |  | 1.1878 | -0.1578 | -2.41 | 3 | 3 | `abs(ts_min[60](open))` |
| 4 | ga_g009_0021 | mutate | ts_min | 1.1817 | -0.1571 | -2.40 | 2 | 2 | `ts_min[60](vwap)` |
| 5 | ga_g009_0026 | crossover |  | 1.1811 | -0.1578 | -2.41 | 4 | 6 | `sub(ts_min[60](open),sign(ts_min[5](2)))` |

- **#1 ga_g009_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g009_0001**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`
- **#3 ga_g009_0013**  来源=`crossover`  变异点=`-`
  - parent[0] = `abs(ts_std[20](safe_div(open,low)))`
  - parent[1] = `ts_min[60](open)`

## 第 10 代  best=1.3579  mean=0.9861  n_valid=35  archive=41
- 本代有效个体操作分布：crossover=21 | mutate=6 | crossover+mutate=5 | random_init=2 | random_inject=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g010_0007 | crossover |  | 1.3579 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 2 | ga_g010_0000 | crossover |  | 1.2258 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 3 | ga_g010_0001 | crossover+mutate | ts_min | 1.1897 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 4 | ga_g010_0002 | crossover |  | 1.1877 | -0.1578 | -2.41 | 3 | 3 | `abs(ts_min[60](open))` |
| 5 | ga_g010_0003 | mutate | ts_min | 1.1817 | -0.1571 | -2.40 | 2 | 2 | `ts_min[60](vwap)` |

- **#1 ga_g010_0007**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](vwap)`
  - parent[1] = `abs(ts_min[60](open))`
- **#2 ga_g010_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#3 ga_g010_0001**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`

## 第 11 代  best=1.3553  mean=0.9625  n_valid=37  archive=44
- 本代有效个体操作分布：crossover=21 | mutate=7 | crossover+mutate=4 | random_inject=3 | random_init=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g011_0000 | crossover |  | 1.3553 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 2 | ga_g011_0028 | mutate | ts_min | 1.3224 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |
| 3 | ga_g011_0001 | crossover |  | 1.2214 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 4 | ga_g011_0014 | mutate | delay | 1.1980 | 0.1316 | 2.22 | 4 | 5 | `delay[20](delay[3](sub(returns,vwap)))` |
| 5 | ga_g011_0002 | crossover+mutate | ts_min | 1.1864 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |

- **#1 ga_g011_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](vwap)`
  - parent[1] = `abs(ts_min[60](open))`
- **#2 ga_g011_0028**  来源=`mutate`  变异点=`ts_min`
  - parent[0] = `ts_min[60](abs(ts_min[60](open)))`
- **#3 ga_g011_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`

## 第 12 代  best=1.3620  mean=1.0677  n_valid=33  archive=47
- 本代有效个体操作分布：crossover=19 | mutate=5 | crossover+mutate=4 | random_init=3 | random_inject=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g012_0041 | crossover |  | 1.3620 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g012_0033 | crossover |  | 1.3620 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g012_0000 | crossover |  | 1.3511 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 4 | ga_g012_0001 | mutate | ts_min | 1.3181 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |
| 5 | ga_g012_0030 | crossover |  | 1.2644 | 0.1570 | 2.40 | 4 | 5 | `ts_min[3](sub(returns,ts_min[60](vwap)))` |

- **#1 ga_g012_0041**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g012_0033**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g012_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](vwap)`
  - parent[1] = `abs(ts_min[60](open))`

## 第 13 代  best=1.3637  mean=1.0364  n_valid=31  archive=49
- 本代有效个体操作分布：crossover=15 | mutate=5 | random_inject=4 | random_init=4 | crossover+mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g013_0000 | crossover |  | 1.3637 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g013_0022 | crossover |  | 1.3637 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 3 | ga_g013_0001 | crossover |  | 1.3637 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 4 | ga_g013_0002 | crossover |  | 1.3522 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g013_0003 | mutate | ts_min | 1.3193 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g013_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g013_0022**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`
- **#3 ga_g013_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`

## 第 14 代  best=1.3627  mean=0.9825  n_valid=22  archive=52
- 本代有效个体操作分布：crossover=9 | mutate=6 | crossover+mutate=3 | random_init=3 | random_inject=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g014_0000 | crossover |  | 1.3627 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g014_0002 | crossover |  | 1.3627 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g014_0001 | crossover |  | 1.3627 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g014_0003 | crossover |  | 1.3508 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g014_0004 | mutate | ts_min | 1.3178 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g014_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g014_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g014_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 15 代  best=1.3661  mean=0.9000  n_valid=31  archive=55
- 本代有效个体操作分布：crossover=14 | crossover+mutate=6 | mutate=5 | random_init=4 | random_inject=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g015_0000 | crossover |  | 1.3661 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g015_0001 | crossover |  | 1.3661 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g015_0002 | crossover |  | 1.3661 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g015_0003 | crossover |  | 1.3544 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g015_0004 | mutate | ts_min | 1.3215 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g015_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g015_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g015_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 16 代  best=1.3674  mean=0.9428  n_valid=24  archive=57
- 本代有效个体操作分布：crossover=10 | random_init=5 | mutate=4 | crossover+mutate=3 | random_inject=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g016_0000 | crossover |  | 1.3674 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g016_0001 | crossover |  | 1.3674 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g016_0002 | crossover |  | 1.3674 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g016_0003 | crossover |  | 1.3552 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g016_0004 | mutate | ts_min | 1.3222 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g016_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g016_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g016_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 17 代  best=1.3671  mean=0.8858  n_valid=28  archive=58
- 本代有效个体操作分布：crossover=10 | random_init=8 | random_inject=6 | mutate=2 | crossover+mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g017_0000 | crossover |  | 1.3671 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g017_0001 | crossover |  | 1.3671 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g017_0002 | crossover |  | 1.3671 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g017_0003 | crossover |  | 1.3552 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g017_0004 | mutate | ts_min | 1.3222 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g017_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g017_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g017_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 18 代  best=1.3654  mean=0.9653  n_valid=32  archive=61
- 本代有效个体操作分布：random_inject=10 | crossover=9 | random_init=7 | crossover+mutate=4 | mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g018_0000 | crossover |  | 1.3654 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g018_0001 | crossover |  | 1.3654 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g018_0002 | crossover |  | 1.3654 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g018_0025 | crossover |  | 1.3615 | -0.1679 | -2.97 | 4 | 4 | `ts_min[60](abs(ts_min[60](low)))` |
| 5 | ga_g018_0003 | crossover |  | 1.3538 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |

- **#1 ga_g018_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g018_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g018_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 19 代  best=1.3613  mean=1.0146  n_valid=30  archive=63
- 本代有效个体操作分布：crossover=10 | crossover+mutate=6 | random_inject=6 | mutate=5 | random_init=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g019_0000 | crossover |  | 1.3613 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g019_0001 | crossover |  | 1.3613 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g019_0002 | crossover |  | 1.3613 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g019_0003 | crossover |  | 1.3577 | -0.1679 | -2.97 | 4 | 4 | `ts_min[60](abs(ts_min[60](low)))` |
| 5 | ga_g019_0004 | crossover |  | 1.3500 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |

- **#1 ga_g019_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g019_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g019_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

---

## 🌳 最优 Top 10 因子血缘


**[1] ga_g016_0002**  fitness=`1.3674`  
  expr = `ts_min[60](ts_min[10](ts_min[60](open)))`
```
    └─ gen=13 op=crossover parents=2
        parent[0] = ts_min[60](open)
        └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
            parent[0] = abs(scale(ts_std[20](returns)))
            └─ gen=4 op=crossover parents=2
                parent[0] = abs(scale(high))
                └─ gen=2 op=crossover+mutate mutate=abs parents=2
                    parent[0] = abs(scale(open))
                    └─ gen=1 op=random_inject (root)
                    parent[1] = vwap
                    └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](returns)
                └─ gen=2 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](demean(open),open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = returns
                    └─ gen=0 op=random_init (root)
            parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
            └─ gen=5 op=crossover parents=2
                parent[0] = ts_std[20](correlation[3](open,open))
                └─ gen=1 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](demean(low),open))
                    └─ gen=0 op=random_init (root)
                    parent[1] = open
                    └─ gen=0 op=random_init (root)
                parent[1] = sub(returns,vwap)
                └─ gen=3 op=crossover parents=2
                    parent[0] = sub(returns,open)
                    └─ gen=1 op=random_inject (root)
                    parent[1] = vwap
                    └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](ts_min[60](open))
        └─ gen=9 op=crossover parents=2
            parent[0] = ts_min[10](volume)
            └─ gen=8 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[20](volume)
                └─ gen=6 op=crossover parents=2
                    parent[0] = ts_min[20](open)
                    └─ gen=0 op=random_init (root)
                    parent[1] = volume
                    └─ gen=0 op=random_init (root)
            parent[1] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
```

**[2] ga_g016_0000**  fitness=`1.3674`  
  expr = `ts_min[60](ts_min[60](ts_min[10](open)))`
```
    └─ gen=12 op=crossover parents=2
        parent[0] = ts_min[60](abs(ts_min[60](high)))
        └─ gen=11 op=mutate mutate=ts_min parents=1
            parent[0] = ts_min[60](abs(ts_min[60](open)))
            └─ gen=10 op=crossover parents=2
                parent[0] = ts_min[60](vwap)
                └─ gen=9 op=mutate mutate=ts_min parents=1
                    parent[0] = ts_min[60](open)
                    └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                        └─ gen=5 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](open,open))
                            parent[1] = sub(returns,vwap)
                parent[1] = abs(ts_min[60](open))
                └─ gen=9 op=crossover parents=2
                    parent[0] = abs(ts_std[20](safe_div(open,low)))
                    └─ gen=6 op=crossover parents=2
                        parent[0] = abs(ts_std[20](correlation[3](open,open)))
                        └─ gen=5 op=crossover parents=2
                            parent[0] = abs(scale(ts_std[20](returns)))
                            parent[1] = ts_std[20](correlation[3](open,open))
                        parent[1] = safe_div(open,low)
                        └─ gen=5 op=random_inject (root)
                    parent[1] = ts_min[60](open)
                    └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                        └─ gen=5 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](open,open))
                            parent[1] = sub(returns,vwap)
        parent[1] = ts_min[60](ts_min[10](open))
        └─ gen=11 op=crossover parents=2
            parent[0] = ts_min[60](vwap)
            └─ gen=9 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
            parent[1] = ts_min[10](open)
            └─ gen=10 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = ts_min[60](vwap)
                └─ gen=9 op=mutate mutate=ts_min parents=1
                    parent[0] = ts_min[60](open)
                    └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                        └─ gen=5 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](open,open))
                            parent[1] = sub(returns,vwap)
                parent[1] = ts_min[10](add(ts_min[60](open),ts_min[20](volume)))
                └─ gen=9 op=crossover parents=2
                    parent[0] = ts_min[10](volume)
                    └─ gen=8 op=mutate mutate=ts_min parents=1
                        parent[0] = ts_min[20](volume)
                        └─ gen=6 op=crossover parents=2
                            parent[0] = ts_min[20](open)
                            parent[1] = volume
                    parent[1] = add(ts_min[60](open),ts_min[20](volume))
                    └─ gen=8 op=crossover parents=2
                        parent[0] = add(ts_min[60](open),ts_min[30](low))
                        └─ gen=7 op=crossover parents=2
                            parent[0] = add(low,ts_min[30](low))
                            parent[1] = ts_min[60](open)
                        parent[1] = ts_min[20](volume)
                        └─ gen=6 op=crossover parents=2
                            parent[0] = ts_min[20](open)
                            parent[1] = volume
```

**[3] ga_g016_0001**  fitness=`1.3674`  
  expr = `ts_min[10](ts_min[60](ts_min[60](open)))`
```
    └─ gen=12 op=crossover parents=2
        parent[0] = ts_min[10](ts_min[60](open))
        └─ gen=9 op=crossover parents=2
            parent[0] = ts_min[10](volume)
            └─ gen=8 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[20](volume)
                └─ gen=6 op=crossover parents=2
                    parent[0] = ts_min[20](open)
                    └─ gen=0 op=random_init (root)
                    parent[1] = volume
                    └─ gen=0 op=random_init (root)
            parent[1] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[60](open)
        └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
            parent[0] = abs(scale(ts_std[20](returns)))
            └─ gen=4 op=crossover parents=2
                parent[0] = abs(scale(high))
                └─ gen=2 op=crossover+mutate mutate=abs parents=2
                    parent[0] = abs(scale(open))
                    └─ gen=1 op=random_inject (root)
                    parent[1] = vwap
                    └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](returns)
                └─ gen=2 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](demean(open),open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = returns
                    └─ gen=0 op=random_init (root)
            parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
            └─ gen=5 op=crossover parents=2
                parent[0] = ts_std[20](correlation[3](open,open))
                └─ gen=1 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](demean(low),open))
                    └─ gen=0 op=random_init (root)
                    parent[1] = open
                    └─ gen=0 op=random_init (root)
                parent[1] = sub(returns,vwap)
                └─ gen=3 op=crossover parents=2
                    parent[0] = sub(returns,open)
                    └─ gen=1 op=random_inject (root)
                    parent[1] = vwap
                    └─ gen=0 op=random_init (root)
```

**[4] ga_g018_0025**  fitness=`1.3615`  
  expr = `ts_min[60](abs(ts_min[60](low)))`
```
    └─ gen=18 op=crossover parents=2
        parent[0] = ts_min[60](abs(ts_min[60](open)))
        └─ gen=10 op=crossover parents=2
            parent[0] = ts_min[60](vwap)
            └─ gen=9 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
            parent[1] = abs(ts_min[60](open))
            └─ gen=9 op=crossover parents=2
                parent[0] = abs(ts_std[20](safe_div(open,low)))
                └─ gen=6 op=crossover parents=2
                    parent[0] = abs(ts_std[20](correlation[3](open,open)))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                    parent[1] = safe_div(open,low)
                    └─ gen=5 op=random_inject (root)
                parent[1] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
        parent[1] = low
        └─ gen=0 op=random_init (root)
```

**[5] ga_g010_0007**  fitness=`1.3579`  
  expr = `ts_min[60](abs(ts_min[60](open)))`
```
    └─ gen=10 op=crossover parents=2
        parent[0] = ts_min[60](vwap)
        └─ gen=9 op=mutate mutate=ts_min parents=1
            parent[0] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
        parent[1] = abs(ts_min[60](open))
        └─ gen=9 op=crossover parents=2
            parent[0] = abs(ts_std[20](safe_div(open,low)))
            └─ gen=6 op=crossover parents=2
                parent[0] = abs(ts_std[20](correlation[3](open,open)))
                └─ gen=5 op=crossover parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                parent[1] = safe_div(open,low)
                └─ gen=5 op=random_inject (root)
            parent[1] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
```

**[6] ga_g011_0028**  fitness=`1.3224`  
  expr = `ts_min[60](abs(ts_min[60](high)))`
```
    └─ gen=11 op=mutate mutate=ts_min parents=1
        parent[0] = ts_min[60](abs(ts_min[60](open)))
        └─ gen=10 op=crossover parents=2
            parent[0] = ts_min[60](vwap)
            └─ gen=9 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
            parent[1] = abs(ts_min[60](open))
            └─ gen=9 op=crossover parents=2
                parent[0] = abs(ts_std[20](safe_div(open,low)))
                └─ gen=6 op=crossover parents=2
                    parent[0] = abs(ts_std[20](correlation[3](open,open)))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                    parent[1] = safe_div(open,low)
                    └─ gen=5 op=random_inject (root)
                parent[1] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
```

**[7] ga_g013_0004**  fitness=`1.2653`  
  expr = `ts_min[3](sub(returns,ts_min[60](vwap)))`
```
    └─ gen=12 op=crossover parents=2
        parent[0] = ts_min[3](sub(returns,low))
        └─ gen=4 op=crossover parents=2
            parent[0] = ts_min[3](abs(scale(open)))
            └─ gen=2 op=crossover parents=2
                parent[0] = ts_min[3](vwap)
                └─ gen=0 op=random_init (root)
                parent[1] = abs(scale(open))
                └─ gen=1 op=random_inject (root)
            parent[1] = sub(returns,low)
            └─ gen=3 op=mutate mutate=sub parents=1
                parent[0] = sub(returns,open)
                └─ gen=1 op=random_inject (root)
        parent[1] = ts_min[60](vwap)
        └─ gen=9 op=mutate mutate=ts_min parents=1
            parent[0] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
```

**[8] ga_g008_0000**  fitness=`1.2284`  
  expr = `delay[5](delay[3](sub(returns,vwap)))`
```
    └─ gen=4 op=crossover parents=2
        parent[0] = delay[5](delay[3](vwap))
        └─ gen=1 op=crossover+mutate mutate=delay parents=2
            parent[0] = ts_std[10](rank(returns))
            └─ gen=0 op=random_init (root)
            parent[1] = ts_rank[3](log_abs(low))
            └─ gen=0 op=random_init (root)
        parent[1] = sub(returns,vwap)
        └─ gen=3 op=crossover parents=2
            parent[0] = sub(returns,open)
            └─ gen=1 op=random_inject (root)
            parent[1] = vwap
            └─ gen=0 op=random_init (root)
```

**[9] ga_g014_0017**  fitness=`1.2264`  
  expr = `delay[5](delay[30](sub(returns,vwap)))`
```
    └─ gen=14 op=mutate mutate=delay parents=1
        parent[0] = delay[5](delay[3](sub(returns,vwap)))
        └─ gen=4 op=crossover parents=2
            parent[0] = delay[5](delay[3](vwap))
            └─ gen=1 op=crossover+mutate mutate=delay parents=2
                parent[0] = ts_std[10](rank(returns))
                └─ gen=0 op=random_init (root)
                parent[1] = ts_rank[3](log_abs(low))
                └─ gen=0 op=random_init (root)
            parent[1] = sub(returns,vwap)
            └─ gen=3 op=crossover parents=2
                parent[0] = sub(returns,open)
                └─ gen=1 op=random_inject (root)
                parent[1] = vwap
                └─ gen=0 op=random_init (root)
```

**[10] ga_g011_0014**  fitness=`1.1980`  
  expr = `delay[20](delay[3](sub(returns,vwap)))`
```
    └─ gen=11 op=mutate mutate=delay parents=1
        parent[0] = delay[5](delay[3](sub(returns,vwap)))
        └─ gen=4 op=crossover parents=2
            parent[0] = delay[5](delay[3](vwap))
            └─ gen=1 op=crossover+mutate mutate=delay parents=2
                parent[0] = ts_std[10](rank(returns))
                └─ gen=0 op=random_init (root)
                parent[1] = ts_rank[3](log_abs(low))
                └─ gen=0 op=random_init (root)
            parent[1] = sub(returns,vwap)
            └─ gen=3 op=crossover parents=2
                parent[0] = sub(returns,open)
                └─ gen=1 op=random_inject (root)
                parent[1] = vwap
                └─ gen=0 op=random_init (root)
```

## 第 0 代  best=0.2782  mean=0.1474  n_valid=5  archive=2
- 本代有效个体操作分布：random_init=5

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0002 | random_init |  | 0.2782 | -0.1174 | -0.30 | 3 | 5 | `covariance[3](covariance[5](amount,open),high)` |
| 2 | ga_g000_0006 | random_init |  | 0.1718 | 0.0067 | 0.02 | 1 | 1 | `open` |
| 3 | ga_g000_0005 | random_init |  | 0.1191 | 0.0175 | 0.04 | 1 | 1 | `returns` |
| 4 | ga_g000_0009 | random_init |  | 0.0864 | 0.0140 | 0.03 | 1 | 1 | `amount` |
| 5 | ga_g000_0008 | random_init |  | 0.0814 | 0.0116 | 0.03 | 1 | 1 | `vwap` |


## 第 1 代  best=0.2771  mean=0.1470  n_valid=5  archive=2
- 本代有效个体操作分布：random_init=4 | random_inject=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g001_0000 | random_init |  | 0.2771 | -0.1174 | -0.30 | 3 | 5 | `covariance[3](covariance[5](amount,open),high)` |
| 2 | ga_g001_0001 | random_init |  | 0.1615 | 0.0067 | 0.02 | 1 | 1 | `open` |
| 3 | ga_g001_0004 | random_inject |  | 0.1492 | 0.0031 | 0.01 | 1 | 1 | `volume` |
| 4 | ga_g001_0003 | random_init |  | 0.0760 | 0.0140 | 0.03 | 1 | 1 | `amount` |
| 5 | ga_g001_0002 | random_init |  | 0.0711 | 0.0116 | 0.03 | 1 | 1 | `vwap` |


## 第 2 代  best=0.2771  mean=0.1463  n_valid=7  archive=3
- 本代有效个体操作分布：random_init=4 | crossover+mutate=2 | random_inject=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g002_0000 | random_init |  | 0.2771 | -0.1174 | -0.30 | 3 | 5 | `covariance[3](covariance[5](amount,open),high)` |
| 2 | ga_g002_0003 | crossover+mutate | field | 0.1605 | 0.0079 | 0.02 | 1 | 1 | `high` |
| 3 | ga_g002_0001 | random_init |  | 0.1581 | 0.0067 | 0.02 | 1 | 1 | `open` |
| 4 | ga_g002_0002 | random_inject |  | 0.1458 | 0.0031 | 0.01 | 1 | 1 | `volume` |
| 5 | ga_g002_0005 | crossover+mutate | field | 0.1422 | 0.0012 | 0.00 | 1 | 1 | `low` |

- **#2 ga_g002_0003**  来源=`crossover+mutate`  变异点=`field`
  - parent[0] = `open`
  - parent[1] = `volume`

---

## 🌳 最优 Top 10 因子血缘


**[1] ga_g000_0002**  fitness=`0.2782`  
  expr = `covariance[3](covariance[5](amount,open),high)`
```
    └─ gen=0 op=random_init (root)
```

**[2] ga_g000_0006**  fitness=`0.1718`  
  expr = `open`
```
    └─ gen=0 op=random_init (root)
```

**[3] ga_g002_0003**  fitness=`0.1605`  
  expr = `high`
```
    └─ gen=2 op=crossover+mutate mutate=field parents=2
        parent[0] = open
        └─ gen=0 op=random_init (root)
        parent[1] = volume
        └─ gen=1 op=random_inject (root)
```

## 第 0 代  best=1.0586  mean=0.6092  n_valid=22  archive=10
- 本代有效个体操作分布：random_init=22

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0037 | random_init |  | 1.0586 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 2 | ga_g000_0017 | random_init |  | 1.0398 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 3 | ga_g000_0004 | random_init |  | 1.0110 | 0.1236 | 1.55 | 3 | 3 | `ts_std[10](rank(returns))` |
| 4 | ga_g000_0048 | random_init |  | 0.9112 | -0.1231 | -1.90 | 2 | 2 | `ts_min[3](vwap)` |
| 5 | ga_g000_0013 | random_init |  | 0.9020 | -0.1217 | -1.88 | 1 | 1 | `low` |


## 第 1 代  best=1.0878  mean=0.6176  n_valid=30  archive=14
- 本代有效个体操作分布：random_init=18 | crossover=7 | random_inject=2 | crossover+mutate=2 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g001_0045 | random_inject |  | 1.0878 | 0.1203 | 1.87 | 2 | 3 | `sub(returns,open)` |
| 2 | ga_g001_0000 | random_init |  | 1.0579 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 3 | ga_g001_0030 | crossover+mutate | delay | 1.0425 | -0.1261 | -2.10 | 3 | 3 | `delay[5](delay[3](vwap))` |
| 4 | ga_g001_0001 | random_init |  | 1.0411 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 5 | ga_g001_0002 | random_init |  | 1.0109 | 0.1236 | 1.55 | 3 | 3 | `ts_std[10](rank(returns))` |

- **#3 ga_g001_0030**  来源=`crossover+mutate`  变异点=`delay`
  - parent[0] = `ts_std[10](rank(returns))`
  - parent[1] = `ts_rank[3](log_abs(low))`

## 第 2 代  best=1.1319  mean=0.6852  n_valid=38  archive=18
- 本代有效个体操作分布：crossover=16 | random_init=10 | mutate=5 | random_inject=4 | crossover+mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g002_0008 | crossover |  | 1.1319 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 2 | ga_g002_0007 | crossover |  | 1.1249 | 0.1490 | 1.96 | 4 | 6 | `sub(zscore_cs(covariance[30](amount,close)),open)` |
| 3 | ga_g002_0000 | random_inject |  | 1.0832 | 0.1203 | 1.87 | 2 | 3 | `sub(returns,open)` |
| 4 | ga_g002_0001 | random_init |  | 1.0535 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 5 | ga_g002_0003 | random_init |  | 1.0427 | 0.1511 | 1.51 | 1 | 1 | `volume` |

- **#1 ga_g002_0008**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_std[20](correlation[3](demean(open),open))`
  - parent[1] = `returns`
- **#2 ga_g002_0007**  来源=`crossover`  变异点=`-`
  - parent[0] = `sub(returns,open)`
  - parent[1] = `zscore_cs(covariance[30](amount,close))`

## 第 3 代  best=1.1451  mean=0.8045  n_valid=37  archive=21
- 本代有效个体操作分布：crossover=13 | random_inject=8 | random_init=8 | mutate=4 | crossover+mutate=4

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g003_0010 | mutate | sub | 1.1451 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 2 | ga_g003_0000 | crossover |  | 1.1305 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 3 | ga_g003_0001 | crossover |  | 1.1221 | 0.1490 | 1.96 | 4 | 6 | `sub(zscore_cs(covariance[30](amount,close)),open)` |
| 4 | ga_g003_0002 | random_inject |  | 1.0810 | 0.1203 | 1.87 | 2 | 3 | `sub(returns,open)` |
| 5 | ga_g003_0025 | crossover |  | 1.0621 | 0.1187 | 1.83 | 2 | 3 | `sub(returns,vwap)` |

- **#1 ga_g003_0010**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`
- **#2 ga_g003_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_std[20](correlation[3](demean(open),open))`
  - parent[1] = `returns`
- **#3 ga_g003_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `sub(returns,open)`
  - parent[1] = `zscore_cs(covariance[30](amount,close))`

## 第 4 代  best=1.2219  mean=0.9253  n_valid=33  archive=25
- 本代有效个体操作分布：crossover=21 | random_inject=4 | random_init=4 | mutate=2 | crossover+mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g004_0033 | crossover |  | 1.2219 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g004_0000 | mutate | sub | 1.1406 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 3 | ga_g004_0001 | crossover |  | 1.1351 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 4 | ga_g004_0009 | crossover |  | 1.1311 | 0.2108 | 1.65 | 4 | 4 | `abs(scale(ts_std[20](returns)))` |
| 5 | ga_g004_0017 | crossover |  | 1.1263 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |

- **#1 ga_g004_0033**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g004_0000**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`
- **#3 ga_g004_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_std[20](correlation[3](demean(open),open))`
  - parent[1] = `returns`

## 第 5 代  best=1.2233  mean=0.9378  n_valid=25  archive=27
- 本代有效个体操作分布：crossover=15 | random_init=5 | random_inject=3 | mutate=1 | crossover+mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g005_0000 | crossover |  | 1.2233 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g005_0001 | mutate | sub | 1.1421 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 3 | ga_g005_0002 | crossover |  | 1.1317 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 4 | ga_g005_0004 | crossover |  | 1.1277 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |
| 5 | ga_g005_0003 | crossover |  | 1.1277 | 0.2108 | 1.65 | 4 | 4 | `abs(scale(ts_std[20](returns)))` |

- **#1 ga_g005_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g005_0001**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`
- **#3 ga_g005_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_std[20](correlation[3](demean(open),open))`
  - parent[1] = `returns`

## 第 6 代  best=1.2246  mean=0.8927  n_valid=30  archive=29
- 本代有效个体操作分布：crossover=16 | random_init=6 | random_inject=4 | crossover+mutate=2 | mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g006_0000 | crossover |  | 1.2246 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g006_0028 | crossover+mutate | ts_min | 1.1898 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 3 | ga_g006_0001 | mutate | sub | 1.1433 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 4 | ga_g006_0002 | crossover |  | 1.1308 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 5 | ga_g006_0003 | crossover |  | 1.1290 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |

- **#1 ga_g006_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g006_0028**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`
- **#3 ga_g006_0001**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`

## 第 7 代  best=1.2231  mean=0.9074  n_valid=34  archive=32
- 本代有效个体操作分布：crossover=18 | random_init=7 | mutate=5 | crossover+mutate=3 | random_inject=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g007_0000 | crossover |  | 1.2231 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g007_0001 | crossover+mutate | ts_min | 1.1884 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 3 | ga_g007_0002 | mutate | sub | 1.1419 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 4 | ga_g007_0003 | crossover |  | 1.1302 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |
| 5 | ga_g007_0004 | crossover |  | 1.1276 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |

- **#1 ga_g007_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g007_0001**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`
- **#3 ga_g007_0002**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`

## 第 8 代  best=1.2284  mean=0.8811  n_valid=29  archive=34
- 本代有效个体操作分布：crossover=16 | crossover+mutate=4 | random_inject=4 | mutate=3 | random_init=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g008_0000 | crossover |  | 1.2284 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g008_0001 | crossover+mutate | ts_min | 1.1932 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 3 | ga_g008_0002 | mutate | sub | 1.1474 | 0.1226 | 1.90 | 2 | 3 | `sub(returns,low)` |
| 4 | ga_g008_0004 | crossover |  | 1.1331 | 0.1200 | 1.88 | 3 | 4 | `ts_min[3](sub(returns,low))` |
| 5 | ga_g008_0003 | crossover |  | 1.1268 | 0.2108 | 1.65 | 2 | 2 | `ts_std[20](returns)` |

- **#1 ga_g008_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g008_0001**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`
- **#3 ga_g008_0002**  来源=`mutate`  变异点=`sub`
  - parent[0] = `sub(returns,open)`

## 第 9 代  best=1.2244  mean=0.9183  n_valid=32  archive=39
- 本代有效个体操作分布：crossover=15 | mutate=5 | random_init=5 | crossover+mutate=4 | random_inject=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g009_0000 | crossover |  | 1.2244 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 2 | ga_g009_0001 | crossover+mutate | ts_min | 1.1898 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 3 | ga_g009_0013 | crossover |  | 1.1878 | -0.1578 | -2.41 | 3 | 3 | `abs(ts_min[60](open))` |
| 4 | ga_g009_0021 | mutate | ts_min | 1.1817 | -0.1571 | -2.40 | 2 | 2 | `ts_min[60](vwap)` |
| 5 | ga_g009_0026 | crossover |  | 1.1811 | -0.1578 | -2.41 | 4 | 6 | `sub(ts_min[60](open),sign(ts_min[5](2)))` |

- **#1 ga_g009_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#2 ga_g009_0001**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`
- **#3 ga_g009_0013**  来源=`crossover`  变异点=`-`
  - parent[0] = `abs(ts_std[20](safe_div(open,low)))`
  - parent[1] = `ts_min[60](open)`

## 第 10 代  best=1.3579  mean=0.9861  n_valid=35  archive=41
- 本代有效个体操作分布：crossover=21 | mutate=6 | crossover+mutate=5 | random_init=2 | random_inject=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g010_0007 | crossover |  | 1.3579 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 2 | ga_g010_0000 | crossover |  | 1.2258 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 3 | ga_g010_0001 | crossover+mutate | ts_min | 1.1897 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |
| 4 | ga_g010_0002 | crossover |  | 1.1877 | -0.1578 | -2.41 | 3 | 3 | `abs(ts_min[60](open))` |
| 5 | ga_g010_0003 | mutate | ts_min | 1.1817 | -0.1571 | -2.40 | 2 | 2 | `ts_min[60](vwap)` |

- **#1 ga_g010_0007**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](vwap)`
  - parent[1] = `abs(ts_min[60](open))`
- **#2 ga_g010_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`
- **#3 ga_g010_0001**  来源=`crossover+mutate`  变异点=`ts_min`
  - parent[0] = `abs(scale(ts_std[20](returns)))`
  - parent[1] = `ts_std[20](correlation[3](sub(returns,vwap),open))`

## 第 11 代  best=1.3553  mean=0.9625  n_valid=37  archive=44
- 本代有效个体操作分布：crossover=21 | mutate=7 | crossover+mutate=4 | random_inject=3 | random_init=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g011_0000 | crossover |  | 1.3553 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 2 | ga_g011_0028 | mutate | ts_min | 1.3224 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |
| 3 | ga_g011_0001 | crossover |  | 1.2214 | 0.1261 | 2.12 | 4 | 5 | `delay[5](delay[3](sub(returns,vwap)))` |
| 4 | ga_g011_0014 | mutate | delay | 1.1980 | 0.1316 | 2.22 | 4 | 5 | `delay[20](delay[3](sub(returns,vwap)))` |
| 5 | ga_g011_0002 | crossover+mutate | ts_min | 1.1864 | -0.1578 | -2.41 | 2 | 2 | `ts_min[60](open)` |

- **#1 ga_g011_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](vwap)`
  - parent[1] = `abs(ts_min[60](open))`
- **#2 ga_g011_0028**  来源=`mutate`  变异点=`ts_min`
  - parent[0] = `ts_min[60](abs(ts_min[60](open)))`
- **#3 ga_g011_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[5](delay[3](vwap))`
  - parent[1] = `sub(returns,vwap)`

## 第 12 代  best=1.3620  mean=1.0677  n_valid=33  archive=47
- 本代有效个体操作分布：crossover=19 | mutate=5 | crossover+mutate=4 | random_init=3 | random_inject=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g012_0041 | crossover |  | 1.3620 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g012_0033 | crossover |  | 1.3620 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g012_0000 | crossover |  | 1.3511 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 4 | ga_g012_0001 | mutate | ts_min | 1.3181 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |
| 5 | ga_g012_0030 | crossover |  | 1.2644 | 0.1570 | 2.40 | 4 | 5 | `ts_min[3](sub(returns,ts_min[60](vwap)))` |

- **#1 ga_g012_0041**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g012_0033**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g012_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](vwap)`
  - parent[1] = `abs(ts_min[60](open))`

## 第 13 代  best=1.3637  mean=1.0364  n_valid=31  archive=49
- 本代有效个体操作分布：crossover=15 | mutate=5 | random_inject=4 | random_init=4 | crossover+mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g013_0000 | crossover |  | 1.3637 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g013_0022 | crossover |  | 1.3637 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 3 | ga_g013_0001 | crossover |  | 1.3637 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 4 | ga_g013_0002 | crossover |  | 1.3522 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g013_0003 | mutate | ts_min | 1.3193 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g013_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g013_0022**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`
- **#3 ga_g013_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`

## 第 14 代  best=1.3627  mean=0.9825  n_valid=22  archive=52
- 本代有效个体操作分布：crossover=9 | mutate=6 | crossover+mutate=3 | random_init=3 | random_inject=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g014_0000 | crossover |  | 1.3627 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g014_0002 | crossover |  | 1.3627 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g014_0001 | crossover |  | 1.3627 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g014_0003 | crossover |  | 1.3508 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g014_0004 | mutate | ts_min | 1.3178 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g014_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g014_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g014_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 15 代  best=1.3661  mean=0.9000  n_valid=31  archive=55
- 本代有效个体操作分布：crossover=14 | crossover+mutate=6 | mutate=5 | random_init=4 | random_inject=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g015_0000 | crossover |  | 1.3661 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g015_0001 | crossover |  | 1.3661 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g015_0002 | crossover |  | 1.3661 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g015_0003 | crossover |  | 1.3544 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g015_0004 | mutate | ts_min | 1.3215 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g015_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g015_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g015_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 16 代  best=1.3674  mean=0.9428  n_valid=24  archive=57
- 本代有效个体操作分布：crossover=10 | random_init=5 | mutate=4 | crossover+mutate=3 | random_inject=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g016_0000 | crossover |  | 1.3674 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g016_0001 | crossover |  | 1.3674 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g016_0002 | crossover |  | 1.3674 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g016_0003 | crossover |  | 1.3552 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g016_0004 | mutate | ts_min | 1.3222 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g016_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g016_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g016_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 17 代  best=1.3671  mean=0.8858  n_valid=28  archive=58
- 本代有效个体操作分布：crossover=10 | random_init=8 | random_inject=6 | mutate=2 | crossover+mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g017_0000 | crossover |  | 1.3671 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g017_0001 | crossover |  | 1.3671 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g017_0002 | crossover |  | 1.3671 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g017_0003 | crossover |  | 1.3552 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |
| 5 | ga_g017_0004 | mutate | ts_min | 1.3222 | -0.1588 | -2.89 | 4 | 4 | `ts_min[60](abs(ts_min[60](high)))` |

- **#1 ga_g017_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g017_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g017_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 18 代  best=1.3654  mean=0.9653  n_valid=32  archive=61
- 本代有效个体操作分布：random_inject=10 | crossover=9 | random_init=7 | crossover+mutate=4 | mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g018_0000 | crossover |  | 1.3654 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g018_0001 | crossover |  | 1.3654 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g018_0002 | crossover |  | 1.3654 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g018_0025 | crossover |  | 1.3615 | -0.1679 | -2.97 | 4 | 4 | `ts_min[60](abs(ts_min[60](low)))` |
| 5 | ga_g018_0003 | crossover |  | 1.3538 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |

- **#1 ga_g018_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g018_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g018_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

## 第 19 代  best=1.3613  mean=1.0146  n_valid=30  archive=63
- 本代有效个体操作分布：crossover=10 | crossover+mutate=6 | random_inject=6 | mutate=5 | random_init=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g019_0000 | crossover |  | 1.3613 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[60](ts_min[10](open)))` |
| 2 | ga_g019_0001 | crossover |  | 1.3613 | -0.1606 | -2.99 | 4 | 4 | `ts_min[10](ts_min[60](ts_min[60](open)))` |
| 3 | ga_g019_0002 | crossover |  | 1.3613 | -0.1606 | -2.99 | 4 | 4 | `ts_min[60](ts_min[10](ts_min[60](open)))` |
| 4 | ga_g019_0003 | crossover |  | 1.3577 | -0.1679 | -2.97 | 4 | 4 | `ts_min[60](abs(ts_min[60](low)))` |
| 5 | ga_g019_0004 | crossover |  | 1.3500 | -0.1632 | -2.96 | 4 | 4 | `ts_min[60](abs(ts_min[60](open)))` |

- **#1 ga_g019_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](abs(ts_min[60](high)))`
  - parent[1] = `ts_min[60](ts_min[10](open))`
- **#2 ga_g019_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](ts_min[60](open))`
  - parent[1] = `ts_min[60](open)`
- **#3 ga_g019_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[60](open)`
  - parent[1] = `ts_min[10](ts_min[60](open))`

---

## 🌳 最优 Top 10 因子血缘


**[1] ga_g016_0002**  fitness=`1.3674`  
  expr = `ts_min[60](ts_min[10](ts_min[60](open)))`
```
    └─ gen=13 op=crossover parents=2
        parent[0] = ts_min[60](open)
        └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
            parent[0] = abs(scale(ts_std[20](returns)))
            └─ gen=4 op=crossover parents=2
                parent[0] = abs(scale(high))
                └─ gen=2 op=crossover+mutate mutate=abs parents=2
                    parent[0] = abs(scale(open))
                    └─ gen=1 op=random_inject (root)
                    parent[1] = vwap
                    └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](returns)
                └─ gen=2 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](demean(open),open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = returns
                    └─ gen=0 op=random_init (root)
            parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
            └─ gen=5 op=crossover parents=2
                parent[0] = ts_std[20](correlation[3](open,open))
                └─ gen=1 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](demean(low),open))
                    └─ gen=0 op=random_init (root)
                    parent[1] = open
                    └─ gen=0 op=random_init (root)
                parent[1] = sub(returns,vwap)
                └─ gen=3 op=crossover parents=2
                    parent[0] = sub(returns,open)
                    └─ gen=1 op=random_inject (root)
                    parent[1] = vwap
                    └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](ts_min[60](open))
        └─ gen=9 op=crossover parents=2
            parent[0] = ts_min[10](volume)
            └─ gen=8 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[20](volume)
                └─ gen=6 op=crossover parents=2
                    parent[0] = ts_min[20](open)
                    └─ gen=0 op=random_init (root)
                    parent[1] = volume
                    └─ gen=0 op=random_init (root)
            parent[1] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
```

**[2] ga_g016_0000**  fitness=`1.3674`  
  expr = `ts_min[60](ts_min[60](ts_min[10](open)))`
```
    └─ gen=12 op=crossover parents=2
        parent[0] = ts_min[60](abs(ts_min[60](high)))
        └─ gen=11 op=mutate mutate=ts_min parents=1
            parent[0] = ts_min[60](abs(ts_min[60](open)))
            └─ gen=10 op=crossover parents=2
                parent[0] = ts_min[60](vwap)
                └─ gen=9 op=mutate mutate=ts_min parents=1
                    parent[0] = ts_min[60](open)
                    └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                        └─ gen=5 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](open,open))
                            parent[1] = sub(returns,vwap)
                parent[1] = abs(ts_min[60](open))
                └─ gen=9 op=crossover parents=2
                    parent[0] = abs(ts_std[20](safe_div(open,low)))
                    └─ gen=6 op=crossover parents=2
                        parent[0] = abs(ts_std[20](correlation[3](open,open)))
                        └─ gen=5 op=crossover parents=2
                            parent[0] = abs(scale(ts_std[20](returns)))
                            parent[1] = ts_std[20](correlation[3](open,open))
                        parent[1] = safe_div(open,low)
                        └─ gen=5 op=random_inject (root)
                    parent[1] = ts_min[60](open)
                    └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                        └─ gen=5 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](open,open))
                            parent[1] = sub(returns,vwap)
        parent[1] = ts_min[60](ts_min[10](open))
        └─ gen=11 op=crossover parents=2
            parent[0] = ts_min[60](vwap)
            └─ gen=9 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
            parent[1] = ts_min[10](open)
            └─ gen=10 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = ts_min[60](vwap)
                └─ gen=9 op=mutate mutate=ts_min parents=1
                    parent[0] = ts_min[60](open)
                    └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                        └─ gen=5 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](open,open))
                            parent[1] = sub(returns,vwap)
                parent[1] = ts_min[10](add(ts_min[60](open),ts_min[20](volume)))
                └─ gen=9 op=crossover parents=2
                    parent[0] = ts_min[10](volume)
                    └─ gen=8 op=mutate mutate=ts_min parents=1
                        parent[0] = ts_min[20](volume)
                        └─ gen=6 op=crossover parents=2
                            parent[0] = ts_min[20](open)
                            parent[1] = volume
                    parent[1] = add(ts_min[60](open),ts_min[20](volume))
                    └─ gen=8 op=crossover parents=2
                        parent[0] = add(ts_min[60](open),ts_min[30](low))
                        └─ gen=7 op=crossover parents=2
                            parent[0] = add(low,ts_min[30](low))
                            parent[1] = ts_min[60](open)
                        parent[1] = ts_min[20](volume)
                        └─ gen=6 op=crossover parents=2
                            parent[0] = ts_min[20](open)
                            parent[1] = volume
```

**[3] ga_g016_0001**  fitness=`1.3674`  
  expr = `ts_min[10](ts_min[60](ts_min[60](open)))`
```
    └─ gen=12 op=crossover parents=2
        parent[0] = ts_min[10](ts_min[60](open))
        └─ gen=9 op=crossover parents=2
            parent[0] = ts_min[10](volume)
            └─ gen=8 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[20](volume)
                └─ gen=6 op=crossover parents=2
                    parent[0] = ts_min[20](open)
                    └─ gen=0 op=random_init (root)
                    parent[1] = volume
                    └─ gen=0 op=random_init (root)
            parent[1] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[60](open)
        └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
            parent[0] = abs(scale(ts_std[20](returns)))
            └─ gen=4 op=crossover parents=2
                parent[0] = abs(scale(high))
                └─ gen=2 op=crossover+mutate mutate=abs parents=2
                    parent[0] = abs(scale(open))
                    └─ gen=1 op=random_inject (root)
                    parent[1] = vwap
                    └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](returns)
                └─ gen=2 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](demean(open),open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = returns
                    └─ gen=0 op=random_init (root)
            parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
            └─ gen=5 op=crossover parents=2
                parent[0] = ts_std[20](correlation[3](open,open))
                └─ gen=1 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](demean(low),open))
                    └─ gen=0 op=random_init (root)
                    parent[1] = open
                    └─ gen=0 op=random_init (root)
                parent[1] = sub(returns,vwap)
                └─ gen=3 op=crossover parents=2
                    parent[0] = sub(returns,open)
                    └─ gen=1 op=random_inject (root)
                    parent[1] = vwap
                    └─ gen=0 op=random_init (root)
```

**[4] ga_g018_0025**  fitness=`1.3615`  
  expr = `ts_min[60](abs(ts_min[60](low)))`
```
    └─ gen=18 op=crossover parents=2
        parent[0] = ts_min[60](abs(ts_min[60](open)))
        └─ gen=10 op=crossover parents=2
            parent[0] = ts_min[60](vwap)
            └─ gen=9 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
            parent[1] = abs(ts_min[60](open))
            └─ gen=9 op=crossover parents=2
                parent[0] = abs(ts_std[20](safe_div(open,low)))
                └─ gen=6 op=crossover parents=2
                    parent[0] = abs(ts_std[20](correlation[3](open,open)))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                    parent[1] = safe_div(open,low)
                    └─ gen=5 op=random_inject (root)
                parent[1] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
        parent[1] = low
        └─ gen=0 op=random_init (root)
```

**[5] ga_g010_0007**  fitness=`1.3579`  
  expr = `ts_min[60](abs(ts_min[60](open)))`
```
    └─ gen=10 op=crossover parents=2
        parent[0] = ts_min[60](vwap)
        └─ gen=9 op=mutate mutate=ts_min parents=1
            parent[0] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
        parent[1] = abs(ts_min[60](open))
        └─ gen=9 op=crossover parents=2
            parent[0] = abs(ts_std[20](safe_div(open,low)))
            └─ gen=6 op=crossover parents=2
                parent[0] = abs(ts_std[20](correlation[3](open,open)))
                └─ gen=5 op=crossover parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                parent[1] = safe_div(open,low)
                └─ gen=5 op=random_inject (root)
            parent[1] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
```

**[6] ga_g011_0028**  fitness=`1.3224`  
  expr = `ts_min[60](abs(ts_min[60](high)))`
```
    └─ gen=11 op=mutate mutate=ts_min parents=1
        parent[0] = ts_min[60](abs(ts_min[60](open)))
        └─ gen=10 op=crossover parents=2
            parent[0] = ts_min[60](vwap)
            └─ gen=9 op=mutate mutate=ts_min parents=1
                parent[0] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
            parent[1] = abs(ts_min[60](open))
            └─ gen=9 op=crossover parents=2
                parent[0] = abs(ts_std[20](safe_div(open,low)))
                └─ gen=6 op=crossover parents=2
                    parent[0] = abs(ts_std[20](correlation[3](open,open)))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = abs(scale(ts_std[20](returns)))
                        └─ gen=4 op=crossover parents=2
                            parent[0] = abs(scale(high))
                            parent[1] = ts_std[20](returns)
                        parent[1] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                    parent[1] = safe_div(open,low)
                    └─ gen=5 op=random_inject (root)
                parent[1] = ts_min[60](open)
                └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                    parent[0] = abs(scale(ts_std[20](returns)))
                    └─ gen=4 op=crossover parents=2
                        parent[0] = abs(scale(high))
                        └─ gen=2 op=crossover+mutate mutate=abs parents=2
                            parent[0] = abs(scale(open))
                            parent[1] = vwap
                        parent[1] = ts_std[20](returns)
                        └─ gen=2 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(open),open))
                            parent[1] = returns
                    parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                    └─ gen=5 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](open,open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = sub(returns,vwap)
                        └─ gen=3 op=crossover parents=2
                            parent[0] = sub(returns,open)
                            parent[1] = vwap
```

**[7] ga_g013_0004**  fitness=`1.2653`  
  expr = `ts_min[3](sub(returns,ts_min[60](vwap)))`
```
    └─ gen=12 op=crossover parents=2
        parent[0] = ts_min[3](sub(returns,low))
        └─ gen=4 op=crossover parents=2
            parent[0] = ts_min[3](abs(scale(open)))
            └─ gen=2 op=crossover parents=2
                parent[0] = ts_min[3](vwap)
                └─ gen=0 op=random_init (root)
                parent[1] = abs(scale(open))
                └─ gen=1 op=random_inject (root)
            parent[1] = sub(returns,low)
            └─ gen=3 op=mutate mutate=sub parents=1
                parent[0] = sub(returns,open)
                └─ gen=1 op=random_inject (root)
        parent[1] = ts_min[60](vwap)
        └─ gen=9 op=mutate mutate=ts_min parents=1
            parent[0] = ts_min[60](open)
            └─ gen=6 op=crossover+mutate mutate=ts_min parents=2
                parent[0] = abs(scale(ts_std[20](returns)))
                └─ gen=4 op=crossover parents=2
                    parent[0] = abs(scale(high))
                    └─ gen=2 op=crossover+mutate mutate=abs parents=2
                        parent[0] = abs(scale(open))
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
                    parent[1] = ts_std[20](returns)
                    └─ gen=2 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(open),open))
                        └─ gen=1 op=crossover parents=2
                            parent[0] = ts_std[20](correlation[3](demean(low),open))
                            parent[1] = open
                        parent[1] = returns
                        └─ gen=0 op=random_init (root)
                parent[1] = ts_std[20](correlation[3](sub(returns,vwap),open))
                └─ gen=5 op=crossover parents=2
                    parent[0] = ts_std[20](correlation[3](open,open))
                    └─ gen=1 op=crossover parents=2
                        parent[0] = ts_std[20](correlation[3](demean(low),open))
                        └─ gen=0 op=random_init (root)
                        parent[1] = open
                        └─ gen=0 op=random_init (root)
                    parent[1] = sub(returns,vwap)
                    └─ gen=3 op=crossover parents=2
                        parent[0] = sub(returns,open)
                        └─ gen=1 op=random_inject (root)
                        parent[1] = vwap
                        └─ gen=0 op=random_init (root)
```

**[8] ga_g008_0000**  fitness=`1.2284`  
  expr = `delay[5](delay[3](sub(returns,vwap)))`
```
    └─ gen=4 op=crossover parents=2
        parent[0] = delay[5](delay[3](vwap))
        └─ gen=1 op=crossover+mutate mutate=delay parents=2
            parent[0] = ts_std[10](rank(returns))
            └─ gen=0 op=random_init (root)
            parent[1] = ts_rank[3](log_abs(low))
            └─ gen=0 op=random_init (root)
        parent[1] = sub(returns,vwap)
        └─ gen=3 op=crossover parents=2
            parent[0] = sub(returns,open)
            └─ gen=1 op=random_inject (root)
            parent[1] = vwap
            └─ gen=0 op=random_init (root)
```

**[9] ga_g014_0017**  fitness=`1.2264`  
  expr = `delay[5](delay[30](sub(returns,vwap)))`
```
    └─ gen=14 op=mutate mutate=delay parents=1
        parent[0] = delay[5](delay[3](sub(returns,vwap)))
        └─ gen=4 op=crossover parents=2
            parent[0] = delay[5](delay[3](vwap))
            └─ gen=1 op=crossover+mutate mutate=delay parents=2
                parent[0] = ts_std[10](rank(returns))
                └─ gen=0 op=random_init (root)
                parent[1] = ts_rank[3](log_abs(low))
                └─ gen=0 op=random_init (root)
            parent[1] = sub(returns,vwap)
            └─ gen=3 op=crossover parents=2
                parent[0] = sub(returns,open)
                └─ gen=1 op=random_inject (root)
                parent[1] = vwap
                └─ gen=0 op=random_init (root)
```

**[10] ga_g011_0014**  fitness=`1.1980`  
  expr = `delay[20](delay[3](sub(returns,vwap)))`
```
    └─ gen=11 op=mutate mutate=delay parents=1
        parent[0] = delay[5](delay[3](sub(returns,vwap)))
        └─ gen=4 op=crossover parents=2
            parent[0] = delay[5](delay[3](vwap))
            └─ gen=1 op=crossover+mutate mutate=delay parents=2
                parent[0] = ts_std[10](rank(returns))
                └─ gen=0 op=random_init (root)
                parent[1] = ts_rank[3](log_abs(low))
                └─ gen=0 op=random_init (root)
            parent[1] = sub(returns,vwap)
            └─ gen=3 op=crossover parents=2
                parent[0] = sub(returns,open)
                └─ gen=1 op=random_inject (root)
                parent[1] = vwap
                └─ gen=0 op=random_init (root)
```

## 第 0 代  best=1.0588  mean=0.6243  n_valid=34  archive=15
- 本代有效个体操作分布：random_init=34

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0037 | random_init |  | 1.0588 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 2 | ga_g000_0055 | random_init |  | 1.0572 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 3 | ga_g000_0017 | random_init |  | 1.0378 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 4 | ga_g000_0075 | random_init |  | 1.0237 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |
| 5 | ga_g000_0004 | random_init |  | 1.0096 | 0.1236 | 1.55 | 3 | 3 | `ts_std[10](rank(returns))` |


## 第 1 代  best=1.0858  mean=0.5912  n_valid=50  archive=18
- 本代有效个体操作分布：random_init=26 | crossover=11 | random_inject=6 | crossover+mutate=5 | mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g001_0051 | crossover |  | 1.0858 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |
| 2 | ga_g001_0000 | random_init |  | 1.0593 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 3 | ga_g001_0001 | random_init |  | 1.0576 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 4 | ga_g001_0002 | random_init |  | 1.0391 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 5 | ga_g001_0003 | random_init |  | 1.0246 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |

- **#1 ga_g001_0051**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](open)`
  - parent[1] = `ts_min[20](open)`

## 第 2 代  best=1.0863  mean=0.6313  n_valid=56  archive=24
- 本代有效个体操作分布：crossover=24 | random_init=14 | mutate=7 | random_inject=7 | crossover+mutate=4

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g002_0045 | crossover |  | 1.0863 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 2 | ga_g002_0000 | crossover |  | 1.0857 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |
| 3 | ga_g002_0001 | random_init |  | 1.0592 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 4 | ga_g002_0002 | random_init |  | 1.0576 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 5 | ga_g002_0039 | mutate | delay | 1.0511 | -0.1268 | -2.23 | 2 | 2 | `delay[20](high)` |

- **#1 ga_g002_0045**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(amount)`
  - parent[1] = `ts_min[10](ts_min[20](open))`
- **#2 ga_g002_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](open)`
  - parent[1] = `ts_min[20](open)`

## 第 3 代  best=1.2055  mean=0.7548  n_valid=57  archive=30
- 本代有效个体操作分布：crossover=31 | random_init=11 | random_inject=9 | crossover+mutate=3 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g003_0064 | crossover |  | 1.2055 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g003_0057 | crossover |  | 1.1163 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 3 | ga_g003_0046 | crossover |  | 1.1157 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 4 | ga_g003_0000 | crossover |  | 1.0820 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 5 | ga_g003_0001 | crossover |  | 1.0811 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |

- **#1 ga_g003_0064**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g003_0057**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`
- **#3 ga_g003_0046**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](ts_mean[3](log_abs(volume)))`
  - parent[1] = `ts_min[3](vwap)`

## 第 4 代  best=1.2024  mean=0.7887  n_valid=46  archive=33
- 本代有效个体操作分布：crossover=23 | random_init=11 | crossover+mutate=5 | random_inject=4 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g004_0000 | crossover |  | 1.2024 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g004_0001 | crossover |  | 1.1127 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 3 | ga_g004_0002 | crossover |  | 1.1122 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 4 | ga_g004_0003 | crossover |  | 1.0784 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 5 | ga_g004_0004 | crossover |  | 1.0775 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |

- **#1 ga_g004_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g004_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`
- **#3 ga_g004_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](ts_mean[3](log_abs(volume)))`
  - parent[1] = `ts_min[3](vwap)`

## 第 5 代  best=1.2009  mean=0.8578  n_valid=45  archive=38
- 本代有效个体操作分布：crossover=23 | random_init=9 | crossover+mutate=8 | random_inject=4 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g005_0000 | crossover |  | 1.2009 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g005_0059 | mutate | delay | 1.1212 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 3 | ga_g005_0001 | crossover |  | 1.1101 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 4 | ga_g005_0002 | crossover |  | 1.1092 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 5 | ga_g005_0003 | crossover |  | 1.0757 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |

- **#1 ga_g005_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g005_0059**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`
- **#3 ga_g005_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`

## 第 6 代  best=1.1997  mean=0.8584  n_valid=41  archive=42
- 本代有效个体操作分布：crossover=21 | random_init=8 | random_inject=6 | crossover+mutate=5 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g006_0000 | crossover |  | 1.1997 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g006_0039 | crossover |  | 1.1203 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g006_0001 | mutate | delay | 1.1197 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g006_0002 | crossover |  | 1.1090 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 5 | ga_g006_0003 | crossover |  | 1.1078 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |

- **#1 ga_g006_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g006_0039**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g006_0001**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

## 第 7 代  best=1.2028  mean=0.7900  n_valid=49  archive=45
- 本代有效个体操作分布：crossover=23 | crossover+mutate=8 | random_inject=8 | random_init=7 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g007_0000 | crossover |  | 1.2028 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g007_0001 | crossover |  | 1.1251 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g007_0002 | mutate | delay | 1.1250 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g007_0003 | crossover |  | 1.1138 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 5 | ga_g007_0004 | crossover |  | 1.1131 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |

- **#1 ga_g007_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g007_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g007_0002**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

## 第 8 代  best=1.1995  mean=0.8630  n_valid=44  archive=46
- 本代有效个体操作分布：crossover=23 | random_inject=7 | random_init=6 | crossover+mutate=5 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g008_0000 | crossover |  | 1.1995 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g008_0001 | crossover |  | 1.1209 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g008_0002 | mutate | delay | 1.1201 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g008_0042 | crossover |  | 1.1111 | -0.1296 | -2.28 | 2 | 2 | `delay[20](vwap)` |
| 5 | ga_g008_0003 | crossover |  | 1.1096 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |

- **#1 ga_g008_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g008_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g008_0002**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

---

## 🌳 最优 Top 10 因子血缘


**[1] ga_g003_0064**  fitness=`1.2055`  
  expr = `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = safe_div(zscore_cs(log_abs(close)),zscore_cs(low))
        └─ gen=2 op=random_inject (root)
        parent[1] = log_abs(delta[10](low))
        └─ gen=0 op=random_init (root)
```

**[2] ga_g007_0001**  fitness=`1.1251`  
  expr = `rank(delay[20](ts_mean[3](low)))`
```
    └─ gen=6 op=crossover parents=2
        parent[0] = rank(volume)
        └─ gen=2 op=random_inject (root)
        parent[1] = delay[20](ts_mean[3](low))
        └─ gen=5 op=mutate mutate=delay parents=1
            parent[0] = delay[20](ts_mean[3](log_abs(returns)))
            └─ gen=3 op=crossover+mutate mutate=delay parents=2
                parent[0] = open
                └─ gen=0 op=random_init (root)
                parent[1] = delay[20](ts_mean[3](log_abs(volume)))
                └─ gen=2 op=crossover parents=2
                    parent[0] = delay[20](volume)
                    └─ gen=1 op=random_inject (root)
                    parent[1] = ts_mean[3](log_abs(volume))
                    └─ gen=0 op=random_init (root)
```

**[3] ga_g007_0002**  fitness=`1.1250`  
  expr = `delay[20](ts_mean[3](low))`
```
    └─ gen=5 op=mutate mutate=delay parents=1
        parent[0] = delay[20](ts_mean[3](log_abs(returns)))
        └─ gen=3 op=crossover+mutate mutate=delay parents=2
            parent[0] = open
            └─ gen=0 op=random_init (root)
            parent[1] = delay[20](ts_mean[3](log_abs(volume)))
            └─ gen=2 op=crossover parents=2
                parent[0] = delay[20](volume)
                └─ gen=1 op=random_inject (root)
                parent[1] = ts_mean[3](log_abs(volume))
                └─ gen=0 op=random_init (root)
```

**[4] ga_g003_0057**  fitness=`1.1163`  
  expr = `delay[20](rank(zscore_cs(open)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = delay[20](volume)
        └─ gen=1 op=random_inject (root)
        parent[1] = rank(zscore_cs(open))
        └─ gen=2 op=crossover parents=2
            parent[0] = rank(amount)
            └─ gen=0 op=random_init (root)
            parent[1] = zscore_cs(open)
            └─ gen=1 op=crossover+mutate mutate=zscore_cs parents=2
                parent[0] = covariance[60](log_abs(scale(amount)),rank(low))
                └─ gen=0 op=random_init (root)
                parent[1] = zscore_cs(returns)
                └─ gen=0 op=random_init (root)
```

**[5] ga_g003_0046**  fitness=`1.1157`  
  expr = `delay[20](ts_mean[3](ts_min[3](vwap)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = delay[20](ts_mean[3](log_abs(volume)))
        └─ gen=2 op=crossover parents=2
            parent[0] = delay[20](volume)
            └─ gen=1 op=random_inject (root)
            parent[1] = ts_mean[3](log_abs(volume))
            └─ gen=0 op=random_init (root)
        parent[1] = ts_min[3](vwap)
        └─ gen=0 op=random_init (root)
```

**[6] ga_g008_0042**  fitness=`1.1111`  
  expr = `delay[20](vwap)`
```
    └─ gen=8 op=crossover parents=2
        parent[0] = delay[20](volume)
        └─ gen=1 op=random_inject (root)
        parent[1] = vwap
        └─ gen=0 op=random_init (root)
```

**[7] ga_g002_0045**  fitness=`1.0863`  
  expr = `rank(ts_min[10](ts_min[20](open)))`
```
    └─ gen=2 op=crossover parents=2
        parent[0] = rank(amount)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](ts_min[20](open))
        └─ gen=1 op=crossover parents=2
            parent[0] = ts_min[10](open)
            └─ gen=0 op=random_init (root)
            parent[1] = ts_min[20](open)
            └─ gen=0 op=random_init (root)
```

**[8] ga_g001_0051**  fitness=`1.0858`  
  expr = `ts_min[10](ts_min[20](open))`
```
    └─ gen=1 op=crossover parents=2
        parent[0] = ts_min[10](open)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[20](open)
        └─ gen=0 op=random_init (root)
```

**[9] ga_g003_0032**  fitness=`1.0799`  
  expr = `ts_min[30](vwap)`
```
    └─ gen=3 op=crossover+mutate mutate=ts_min parents=2
        parent[0] = close
        └─ gen=0 op=random_init (root)
        parent[1] = covariance[30](amount,ts_rank[3](log_abs(low)))
        └─ gen=1 op=crossover parents=2
            parent[0] = covariance[30](amount,close)
            └─ gen=0 op=random_init (root)
            parent[1] = ts_rank[3](log_abs(low))
            └─ gen=0 op=random_init (root)
```

**[10] ga_g007_0007**  fitness=`1.0787`  
  expr = `ts_min[20](ts_min[10](open))`
```
    └─ gen=6 op=crossover parents=2
        parent[0] = ts_min[20](open)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](open)
        └─ gen=0 op=random_init (root)
```

## 第 0 代  best=1.0588  mean=0.6243  n_valid=34  archive=15
- 本代有效个体操作分布：random_init=34

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0037 | random_init |  | 1.0588 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 2 | ga_g000_0055 | random_init |  | 1.0572 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 3 | ga_g000_0017 | random_init |  | 1.0378 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 4 | ga_g000_0075 | random_init |  | 1.0237 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |
| 5 | ga_g000_0004 | random_init |  | 1.0096 | 0.1236 | 1.55 | 3 | 3 | `ts_std[10](rank(returns))` |


## 第 1 代  best=1.0858  mean=0.5912  n_valid=50  archive=18
- 本代有效个体操作分布：random_init=26 | crossover=11 | random_inject=6 | crossover+mutate=5 | mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g001_0051 | crossover |  | 1.0858 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |
| 2 | ga_g001_0000 | random_init |  | 1.0593 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 3 | ga_g001_0001 | random_init |  | 1.0576 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 4 | ga_g001_0002 | random_init |  | 1.0391 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 5 | ga_g001_0003 | random_init |  | 1.0246 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |

- **#1 ga_g001_0051**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](open)`
  - parent[1] = `ts_min[20](open)`

## 第 2 代  best=1.0863  mean=0.6313  n_valid=56  archive=24
- 本代有效个体操作分布：crossover=24 | random_init=14 | mutate=7 | random_inject=7 | crossover+mutate=4

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g002_0045 | crossover |  | 1.0863 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 2 | ga_g002_0000 | crossover |  | 1.0857 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |
| 3 | ga_g002_0001 | random_init |  | 1.0592 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 4 | ga_g002_0002 | random_init |  | 1.0576 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 5 | ga_g002_0039 | mutate | delay | 1.0511 | -0.1268 | -2.23 | 2 | 2 | `delay[20](high)` |

- **#1 ga_g002_0045**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(amount)`
  - parent[1] = `ts_min[10](ts_min[20](open))`
- **#2 ga_g002_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](open)`
  - parent[1] = `ts_min[20](open)`

## 第 3 代  best=1.2055  mean=0.7548  n_valid=57  archive=30
- 本代有效个体操作分布：crossover=31 | random_init=11 | random_inject=9 | crossover+mutate=3 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g003_0064 | crossover |  | 1.2055 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g003_0057 | crossover |  | 1.1163 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 3 | ga_g003_0046 | crossover |  | 1.1157 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 4 | ga_g003_0000 | crossover |  | 1.0820 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 5 | ga_g003_0001 | crossover |  | 1.0811 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |

- **#1 ga_g003_0064**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g003_0057**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`
- **#3 ga_g003_0046**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](ts_mean[3](log_abs(volume)))`
  - parent[1] = `ts_min[3](vwap)`

## 第 4 代  best=1.2024  mean=0.7887  n_valid=46  archive=33
- 本代有效个体操作分布：crossover=23 | random_init=11 | crossover+mutate=5 | random_inject=4 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g004_0000 | crossover |  | 1.2024 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g004_0001 | crossover |  | 1.1127 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 3 | ga_g004_0002 | crossover |  | 1.1122 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 4 | ga_g004_0003 | crossover |  | 1.0784 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 5 | ga_g004_0004 | crossover |  | 1.0775 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |

- **#1 ga_g004_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g004_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`
- **#3 ga_g004_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](ts_mean[3](log_abs(volume)))`
  - parent[1] = `ts_min[3](vwap)`

## 第 5 代  best=1.2009  mean=0.8578  n_valid=45  archive=38
- 本代有效个体操作分布：crossover=23 | random_init=9 | crossover+mutate=8 | random_inject=4 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g005_0000 | crossover |  | 1.2009 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g005_0059 | mutate | delay | 1.1212 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 3 | ga_g005_0001 | crossover |  | 1.1101 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 4 | ga_g005_0002 | crossover |  | 1.1092 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 5 | ga_g005_0003 | crossover |  | 1.0757 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |

- **#1 ga_g005_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g005_0059**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`
- **#3 ga_g005_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`

## 第 6 代  best=1.1997  mean=0.8584  n_valid=41  archive=42
- 本代有效个体操作分布：crossover=21 | random_init=8 | random_inject=6 | crossover+mutate=5 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g006_0000 | crossover |  | 1.1997 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g006_0039 | crossover |  | 1.1203 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g006_0001 | mutate | delay | 1.1197 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g006_0002 | crossover |  | 1.1090 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 5 | ga_g006_0003 | crossover |  | 1.1078 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |

- **#1 ga_g006_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g006_0039**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g006_0001**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

## 第 7 代  best=1.2028  mean=0.7900  n_valid=49  archive=45
- 本代有效个体操作分布：crossover=23 | crossover+mutate=8 | random_inject=8 | random_init=7 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g007_0000 | crossover |  | 1.2028 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g007_0001 | crossover |  | 1.1251 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g007_0002 | mutate | delay | 1.1250 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g007_0003 | crossover |  | 1.1138 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 5 | ga_g007_0004 | crossover |  | 1.1131 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |

- **#1 ga_g007_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g007_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g007_0002**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

## 第 8 代  best=1.1995  mean=0.8630  n_valid=44  archive=46
- 本代有效个体操作分布：crossover=23 | random_inject=7 | random_init=6 | crossover+mutate=5 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g008_0000 | crossover |  | 1.1995 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g008_0001 | crossover |  | 1.1209 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g008_0002 | mutate | delay | 1.1201 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g008_0042 | crossover |  | 1.1111 | -0.1296 | -2.28 | 2 | 2 | `delay[20](vwap)` |
| 5 | ga_g008_0003 | crossover |  | 1.1096 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |

- **#1 ga_g008_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g008_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g008_0002**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

---

## 🌳 最优 Top 10 因子血缘


**[1] ga_g003_0064**  fitness=`1.2055`  
  expr = `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = safe_div(zscore_cs(log_abs(close)),zscore_cs(low))
        └─ gen=2 op=random_inject (root)
        parent[1] = log_abs(delta[10](low))
        └─ gen=0 op=random_init (root)
```

**[2] ga_g007_0001**  fitness=`1.1251`  
  expr = `rank(delay[20](ts_mean[3](low)))`
```
    └─ gen=6 op=crossover parents=2
        parent[0] = rank(volume)
        └─ gen=2 op=random_inject (root)
        parent[1] = delay[20](ts_mean[3](low))
        └─ gen=5 op=mutate mutate=delay parents=1
            parent[0] = delay[20](ts_mean[3](log_abs(returns)))
            └─ gen=3 op=crossover+mutate mutate=delay parents=2
                parent[0] = open
                └─ gen=0 op=random_init (root)
                parent[1] = delay[20](ts_mean[3](log_abs(volume)))
                └─ gen=2 op=crossover parents=2
                    parent[0] = delay[20](volume)
                    └─ gen=1 op=random_inject (root)
                    parent[1] = ts_mean[3](log_abs(volume))
                    └─ gen=0 op=random_init (root)
```

**[3] ga_g007_0002**  fitness=`1.1250`  
  expr = `delay[20](ts_mean[3](low))`
```
    └─ gen=5 op=mutate mutate=delay parents=1
        parent[0] = delay[20](ts_mean[3](log_abs(returns)))
        └─ gen=3 op=crossover+mutate mutate=delay parents=2
            parent[0] = open
            └─ gen=0 op=random_init (root)
            parent[1] = delay[20](ts_mean[3](log_abs(volume)))
            └─ gen=2 op=crossover parents=2
                parent[0] = delay[20](volume)
                └─ gen=1 op=random_inject (root)
                parent[1] = ts_mean[3](log_abs(volume))
                └─ gen=0 op=random_init (root)
```

**[4] ga_g003_0057**  fitness=`1.1163`  
  expr = `delay[20](rank(zscore_cs(open)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = delay[20](volume)
        └─ gen=1 op=random_inject (root)
        parent[1] = rank(zscore_cs(open))
        └─ gen=2 op=crossover parents=2
            parent[0] = rank(amount)
            └─ gen=0 op=random_init (root)
            parent[1] = zscore_cs(open)
            └─ gen=1 op=crossover+mutate mutate=zscore_cs parents=2
                parent[0] = covariance[60](log_abs(scale(amount)),rank(low))
                └─ gen=0 op=random_init (root)
                parent[1] = zscore_cs(returns)
                └─ gen=0 op=random_init (root)
```

**[5] ga_g003_0046**  fitness=`1.1157`  
  expr = `delay[20](ts_mean[3](ts_min[3](vwap)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = delay[20](ts_mean[3](log_abs(volume)))
        └─ gen=2 op=crossover parents=2
            parent[0] = delay[20](volume)
            └─ gen=1 op=random_inject (root)
            parent[1] = ts_mean[3](log_abs(volume))
            └─ gen=0 op=random_init (root)
        parent[1] = ts_min[3](vwap)
        └─ gen=0 op=random_init (root)
```

**[6] ga_g008_0042**  fitness=`1.1111`  
  expr = `delay[20](vwap)`
```
    └─ gen=8 op=crossover parents=2
        parent[0] = delay[20](volume)
        └─ gen=1 op=random_inject (root)
        parent[1] = vwap
        └─ gen=0 op=random_init (root)
```

**[7] ga_g002_0045**  fitness=`1.0863`  
  expr = `rank(ts_min[10](ts_min[20](open)))`
```
    └─ gen=2 op=crossover parents=2
        parent[0] = rank(amount)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](ts_min[20](open))
        └─ gen=1 op=crossover parents=2
            parent[0] = ts_min[10](open)
            └─ gen=0 op=random_init (root)
            parent[1] = ts_min[20](open)
            └─ gen=0 op=random_init (root)
```

**[8] ga_g001_0051**  fitness=`1.0858`  
  expr = `ts_min[10](ts_min[20](open))`
```
    └─ gen=1 op=crossover parents=2
        parent[0] = ts_min[10](open)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[20](open)
        └─ gen=0 op=random_init (root)
```

**[9] ga_g003_0032**  fitness=`1.0799`  
  expr = `ts_min[30](vwap)`
```
    └─ gen=3 op=crossover+mutate mutate=ts_min parents=2
        parent[0] = close
        └─ gen=0 op=random_init (root)
        parent[1] = covariance[30](amount,ts_rank[3](log_abs(low)))
        └─ gen=1 op=crossover parents=2
            parent[0] = covariance[30](amount,close)
            └─ gen=0 op=random_init (root)
            parent[1] = ts_rank[3](log_abs(low))
            └─ gen=0 op=random_init (root)
```

**[10] ga_g007_0007**  fitness=`1.0787`  
  expr = `ts_min[20](ts_min[10](open))`
```
    └─ gen=6 op=crossover parents=2
        parent[0] = ts_min[20](open)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](open)
        └─ gen=0 op=random_init (root)
```

## 第 0 代  best=1.0588  mean=0.6243  n_valid=34  archive=15
- 本代有效个体操作分布：random_init=34

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0037 | random_init |  | 1.0588 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 2 | ga_g000_0055 | random_init |  | 1.0572 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 3 | ga_g000_0017 | random_init |  | 1.0378 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 4 | ga_g000_0075 | random_init |  | 1.0237 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |
| 5 | ga_g000_0004 | random_init |  | 1.0096 | 0.1236 | 1.55 | 3 | 3 | `ts_std[10](rank(returns))` |


## 第 1 代  best=1.0858  mean=0.5912  n_valid=50  archive=18
- 本代有效个体操作分布：random_init=26 | crossover=11 | random_inject=6 | crossover+mutate=5 | mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g001_0051 | crossover |  | 1.0858 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |
| 2 | ga_g001_0000 | random_init |  | 1.0593 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 3 | ga_g001_0001 | random_init |  | 1.0576 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 4 | ga_g001_0002 | random_init |  | 1.0391 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 5 | ga_g001_0003 | random_init |  | 1.0246 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |

- **#1 ga_g001_0051**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](open)`
  - parent[1] = `ts_min[20](open)`

## 第 0 代  best=1.0588  mean=0.6243  n_valid=34  archive=15
- 本代有效个体操作分布：random_init=34

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0037 | random_init |  | 1.0588 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 2 | ga_g000_0055 | random_init |  | 1.0572 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 3 | ga_g000_0017 | random_init |  | 1.0378 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 4 | ga_g000_0075 | random_init |  | 1.0237 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |
| 5 | ga_g000_0004 | random_init |  | 1.0096 | 0.1236 | 1.55 | 3 | 3 | `ts_std[10](rank(returns))` |


## 第 1 代  best=1.0858  mean=0.5912  n_valid=50  archive=18
- 本代有效个体操作分布：random_init=26 | crossover=11 | random_inject=6 | crossover+mutate=5 | mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g001_0051 | crossover |  | 1.0858 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |
| 2 | ga_g001_0000 | random_init |  | 1.0593 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 3 | ga_g001_0001 | random_init |  | 1.0576 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 4 | ga_g001_0002 | random_init |  | 1.0391 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 5 | ga_g001_0003 | random_init |  | 1.0246 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |

- **#1 ga_g001_0051**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](open)`
  - parent[1] = `ts_min[20](open)`

## 第 2 代  best=1.0863  mean=0.6313  n_valid=56  archive=24
- 本代有效个体操作分布：crossover=24 | random_init=14 | mutate=7 | random_inject=7 | crossover+mutate=4

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g002_0045 | crossover |  | 1.0863 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 2 | ga_g002_0000 | crossover |  | 1.0857 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |
| 3 | ga_g002_0001 | random_init |  | 1.0592 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 4 | ga_g002_0002 | random_init |  | 1.0576 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 5 | ga_g002_0039 | mutate | delay | 1.0511 | -0.1268 | -2.23 | 2 | 2 | `delay[20](high)` |

- **#1 ga_g002_0045**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(amount)`
  - parent[1] = `ts_min[10](ts_min[20](open))`
- **#2 ga_g002_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](open)`
  - parent[1] = `ts_min[20](open)`

## 第 3 代  best=1.2055  mean=0.7548  n_valid=57  archive=30
- 本代有效个体操作分布：crossover=31 | random_init=11 | random_inject=9 | crossover+mutate=3 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g003_0064 | crossover |  | 1.2055 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g003_0057 | crossover |  | 1.1163 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 3 | ga_g003_0046 | crossover |  | 1.1157 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 4 | ga_g003_0000 | crossover |  | 1.0820 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 5 | ga_g003_0001 | crossover |  | 1.0811 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |

- **#1 ga_g003_0064**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g003_0057**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`
- **#3 ga_g003_0046**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](ts_mean[3](log_abs(volume)))`
  - parent[1] = `ts_min[3](vwap)`

## 第 4 代  best=1.2024  mean=0.7887  n_valid=46  archive=33
- 本代有效个体操作分布：crossover=23 | random_init=11 | crossover+mutate=5 | random_inject=4 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g004_0000 | crossover |  | 1.2024 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g004_0001 | crossover |  | 1.1127 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 3 | ga_g004_0002 | crossover |  | 1.1122 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 4 | ga_g004_0003 | crossover |  | 1.0784 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 5 | ga_g004_0004 | crossover |  | 1.0775 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |

- **#1 ga_g004_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g004_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`
- **#3 ga_g004_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](ts_mean[3](log_abs(volume)))`
  - parent[1] = `ts_min[3](vwap)`

## 第 5 代  best=1.2009  mean=0.8578  n_valid=45  archive=38
- 本代有效个体操作分布：crossover=23 | random_init=9 | crossover+mutate=8 | random_inject=4 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g005_0000 | crossover |  | 1.2009 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g005_0059 | mutate | delay | 1.1212 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 3 | ga_g005_0001 | crossover |  | 1.1101 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 4 | ga_g005_0002 | crossover |  | 1.1092 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 5 | ga_g005_0003 | crossover |  | 1.0757 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |

- **#1 ga_g005_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g005_0059**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`
- **#3 ga_g005_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`

## 第 6 代  best=1.1997  mean=0.8584  n_valid=41  archive=42
- 本代有效个体操作分布：crossover=21 | random_init=8 | random_inject=6 | crossover+mutate=5 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g006_0000 | crossover |  | 1.1997 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g006_0039 | crossover |  | 1.1203 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g006_0001 | mutate | delay | 1.1197 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g006_0002 | crossover |  | 1.1090 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 5 | ga_g006_0003 | crossover |  | 1.1078 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |

- **#1 ga_g006_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g006_0039**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g006_0001**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

## 第 7 代  best=1.2028  mean=0.7900  n_valid=49  archive=45
- 本代有效个体操作分布：crossover=23 | crossover+mutate=8 | random_inject=8 | random_init=7 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g007_0000 | crossover |  | 1.2028 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g007_0001 | crossover |  | 1.1251 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g007_0002 | mutate | delay | 1.1250 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g007_0003 | crossover |  | 1.1138 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 5 | ga_g007_0004 | crossover |  | 1.1131 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |

- **#1 ga_g007_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g007_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g007_0002**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

## 第 8 代  best=1.1995  mean=0.8630  n_valid=44  archive=46
- 本代有效个体操作分布：crossover=23 | random_inject=7 | random_init=6 | crossover+mutate=5 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g008_0000 | crossover |  | 1.1995 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g008_0001 | crossover |  | 1.1209 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g008_0002 | mutate | delay | 1.1201 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g008_0042 | crossover |  | 1.1111 | -0.1296 | -2.28 | 2 | 2 | `delay[20](vwap)` |
| 5 | ga_g008_0003 | crossover |  | 1.1096 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |

- **#1 ga_g008_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g008_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g008_0002**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

---

## 🌳 最优 Top 10 因子血缘


**[1] ga_g003_0064**  fitness=`1.2055`  
  expr = `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = safe_div(zscore_cs(log_abs(close)),zscore_cs(low))
        └─ gen=2 op=random_inject (root)
        parent[1] = log_abs(delta[10](low))
        └─ gen=0 op=random_init (root)
```

**[2] ga_g007_0001**  fitness=`1.1251`  
  expr = `rank(delay[20](ts_mean[3](low)))`
```
    └─ gen=6 op=crossover parents=2
        parent[0] = rank(volume)
        └─ gen=2 op=random_inject (root)
        parent[1] = delay[20](ts_mean[3](low))
        └─ gen=5 op=mutate mutate=delay parents=1
            parent[0] = delay[20](ts_mean[3](log_abs(returns)))
            └─ gen=3 op=crossover+mutate mutate=delay parents=2
                parent[0] = open
                └─ gen=0 op=random_init (root)
                parent[1] = delay[20](ts_mean[3](log_abs(volume)))
                └─ gen=2 op=crossover parents=2
                    parent[0] = delay[20](volume)
                    └─ gen=1 op=random_inject (root)
                    parent[1] = ts_mean[3](log_abs(volume))
                    └─ gen=0 op=random_init (root)
```

**[3] ga_g007_0002**  fitness=`1.1250`  
  expr = `delay[20](ts_mean[3](low))`
```
    └─ gen=5 op=mutate mutate=delay parents=1
        parent[0] = delay[20](ts_mean[3](log_abs(returns)))
        └─ gen=3 op=crossover+mutate mutate=delay parents=2
            parent[0] = open
            └─ gen=0 op=random_init (root)
            parent[1] = delay[20](ts_mean[3](log_abs(volume)))
            └─ gen=2 op=crossover parents=2
                parent[0] = delay[20](volume)
                └─ gen=1 op=random_inject (root)
                parent[1] = ts_mean[3](log_abs(volume))
                └─ gen=0 op=random_init (root)
```

**[4] ga_g003_0057**  fitness=`1.1163`  
  expr = `delay[20](rank(zscore_cs(open)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = delay[20](volume)
        └─ gen=1 op=random_inject (root)
        parent[1] = rank(zscore_cs(open))
        └─ gen=2 op=crossover parents=2
            parent[0] = rank(amount)
            └─ gen=0 op=random_init (root)
            parent[1] = zscore_cs(open)
            └─ gen=1 op=crossover+mutate mutate=zscore_cs parents=2
                parent[0] = covariance[60](log_abs(scale(amount)),rank(low))
                └─ gen=0 op=random_init (root)
                parent[1] = zscore_cs(returns)
                └─ gen=0 op=random_init (root)
```

**[5] ga_g003_0046**  fitness=`1.1157`  
  expr = `delay[20](ts_mean[3](ts_min[3](vwap)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = delay[20](ts_mean[3](log_abs(volume)))
        └─ gen=2 op=crossover parents=2
            parent[0] = delay[20](volume)
            └─ gen=1 op=random_inject (root)
            parent[1] = ts_mean[3](log_abs(volume))
            └─ gen=0 op=random_init (root)
        parent[1] = ts_min[3](vwap)
        └─ gen=0 op=random_init (root)
```

**[6] ga_g008_0042**  fitness=`1.1111`  
  expr = `delay[20](vwap)`
```
    └─ gen=8 op=crossover parents=2
        parent[0] = delay[20](volume)
        └─ gen=1 op=random_inject (root)
        parent[1] = vwap
        └─ gen=0 op=random_init (root)
```

**[7] ga_g002_0045**  fitness=`1.0863`  
  expr = `rank(ts_min[10](ts_min[20](open)))`
```
    └─ gen=2 op=crossover parents=2
        parent[0] = rank(amount)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](ts_min[20](open))
        └─ gen=1 op=crossover parents=2
            parent[0] = ts_min[10](open)
            └─ gen=0 op=random_init (root)
            parent[1] = ts_min[20](open)
            └─ gen=0 op=random_init (root)
```

**[8] ga_g001_0051**  fitness=`1.0858`  
  expr = `ts_min[10](ts_min[20](open))`
```
    └─ gen=1 op=crossover parents=2
        parent[0] = ts_min[10](open)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[20](open)
        └─ gen=0 op=random_init (root)
```

**[9] ga_g003_0032**  fitness=`1.0799`  
  expr = `ts_min[30](vwap)`
```
    └─ gen=3 op=crossover+mutate mutate=ts_min parents=2
        parent[0] = close
        └─ gen=0 op=random_init (root)
        parent[1] = covariance[30](amount,ts_rank[3](log_abs(low)))
        └─ gen=1 op=crossover parents=2
            parent[0] = covariance[30](amount,close)
            └─ gen=0 op=random_init (root)
            parent[1] = ts_rank[3](log_abs(low))
            └─ gen=0 op=random_init (root)
```

**[10] ga_g007_0007**  fitness=`1.0787`  
  expr = `ts_min[20](ts_min[10](open))`
```
    └─ gen=6 op=crossover parents=2
        parent[0] = ts_min[20](open)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](open)
        └─ gen=0 op=random_init (root)
```

## 第 0 代  best=1.0588  mean=0.6243  n_valid=34  archive=15
- 本代有效个体操作分布：random_init=34

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0037 | random_init |  | 1.0588 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 2 | ga_g000_0055 | random_init |  | 1.0572 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 3 | ga_g000_0017 | random_init |  | 1.0378 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 4 | ga_g000_0075 | random_init |  | 1.0237 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |
| 5 | ga_g000_0004 | random_init |  | 1.0096 | 0.1236 | 1.55 | 3 | 3 | `ts_std[10](rank(returns))` |


## 第 1 代  best=1.0858  mean=0.5912  n_valid=50  archive=18
- 本代有效个体操作分布：random_init=26 | crossover=11 | random_inject=6 | crossover+mutate=5 | mutate=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g001_0051 | crossover |  | 1.0858 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |
| 2 | ga_g001_0000 | random_init |  | 1.0593 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 3 | ga_g001_0001 | random_init |  | 1.0576 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 4 | ga_g001_0002 | random_init |  | 1.0391 | 0.1511 | 1.51 | 1 | 1 | `volume` |
| 5 | ga_g001_0003 | random_init |  | 1.0246 | 0.1530 | 1.49 | 3 | 3 | `ts_mean[3](log_abs(volume))` |

- **#1 ga_g001_0051**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](open)`
  - parent[1] = `ts_min[20](open)`

## 第 2 代  best=1.0863  mean=0.6313  n_valid=56  archive=24
- 本代有效个体操作分布：crossover=24 | random_init=14 | mutate=7 | random_inject=7 | crossover+mutate=4

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g002_0045 | crossover |  | 1.0863 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 2 | ga_g002_0000 | crossover |  | 1.0857 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |
| 3 | ga_g002_0001 | random_init |  | 1.0592 | -0.1392 | -2.23 | 2 | 2 | `ts_min[20](open)` |
| 4 | ga_g002_0002 | random_init |  | 1.0576 | -0.1326 | -2.12 | 2 | 2 | `ts_min[10](open)` |
| 5 | ga_g002_0039 | mutate | delay | 1.0511 | -0.1268 | -2.23 | 2 | 2 | `delay[20](high)` |

- **#1 ga_g002_0045**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(amount)`
  - parent[1] = `ts_min[10](ts_min[20](open))`
- **#2 ga_g002_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `ts_min[10](open)`
  - parent[1] = `ts_min[20](open)`

## 第 3 代  best=1.2055  mean=0.7548  n_valid=57  archive=30
- 本代有效个体操作分布：crossover=31 | random_init=11 | random_inject=9 | crossover+mutate=3 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g003_0064 | crossover |  | 1.2055 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g003_0057 | crossover |  | 1.1163 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 3 | ga_g003_0046 | crossover |  | 1.1157 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 4 | ga_g003_0000 | crossover |  | 1.0820 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 5 | ga_g003_0001 | crossover |  | 1.0811 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |

- **#1 ga_g003_0064**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g003_0057**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`
- **#3 ga_g003_0046**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](ts_mean[3](log_abs(volume)))`
  - parent[1] = `ts_min[3](vwap)`

## 第 4 代  best=1.2024  mean=0.7887  n_valid=46  archive=33
- 本代有效个体操作分布：crossover=23 | random_init=11 | crossover+mutate=5 | random_inject=4 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g004_0000 | crossover |  | 1.2024 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g004_0001 | crossover |  | 1.1127 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 3 | ga_g004_0002 | crossover |  | 1.1122 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 4 | ga_g004_0003 | crossover |  | 1.0784 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |
| 5 | ga_g004_0004 | crossover |  | 1.0775 | -0.1460 | -2.29 | 3 | 3 | `ts_min[10](ts_min[20](open))` |

- **#1 ga_g004_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g004_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`
- **#3 ga_g004_0002**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](ts_mean[3](log_abs(volume)))`
  - parent[1] = `ts_min[3](vwap)`

## 第 5 代  best=1.2009  mean=0.8578  n_valid=45  archive=38
- 本代有效个体操作分布：crossover=23 | random_init=9 | crossover+mutate=8 | random_inject=4 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g005_0000 | crossover |  | 1.2009 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g005_0059 | mutate | delay | 1.1212 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 3 | ga_g005_0001 | crossover |  | 1.1101 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 4 | ga_g005_0002 | crossover |  | 1.1092 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |
| 5 | ga_g005_0003 | crossover |  | 1.0757 | -0.1460 | -2.29 | 4 | 4 | `rank(ts_min[10](ts_min[20](open)))` |

- **#1 ga_g005_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g005_0059**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`
- **#3 ga_g005_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `delay[20](volume)`
  - parent[1] = `rank(zscore_cs(open))`

## 第 6 代  best=1.1997  mean=0.8584  n_valid=41  archive=42
- 本代有效个体操作分布：crossover=21 | random_init=8 | random_inject=6 | crossover+mutate=5 | mutate=1

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g006_0000 | crossover |  | 1.1997 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g006_0039 | crossover |  | 1.1203 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g006_0001 | mutate | delay | 1.1197 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g006_0002 | crossover |  | 1.1090 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 5 | ga_g006_0003 | crossover |  | 1.1078 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |

- **#1 ga_g006_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g006_0039**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g006_0001**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

## 第 7 代  best=1.2028  mean=0.7900  n_valid=49  archive=45
- 本代有效个体操作分布：crossover=23 | crossover+mutate=8 | random_inject=8 | random_init=7 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g007_0000 | crossover |  | 1.2028 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g007_0001 | crossover |  | 1.1251 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g007_0002 | mutate | delay | 1.1250 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g007_0003 | crossover |  | 1.1138 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |
| 5 | ga_g007_0004 | crossover |  | 1.1131 | -0.1333 | -2.27 | 4 | 4 | `delay[20](ts_mean[3](ts_min[3](vwap)))` |

- **#1 ga_g007_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g007_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g007_0002**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

## 第 8 代  best=1.1995  mean=0.8630  n_valid=44  archive=46
- 本代有效个体操作分布：crossover=23 | random_inject=7 | random_init=6 | crossover+mutate=5 | mutate=3

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g008_0000 | crossover |  | 1.1995 | 0.1232 | 2.19 | 4 | 7 | `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))` |
| 2 | ga_g008_0001 | crossover |  | 1.1209 | -0.1329 | -2.30 | 4 | 4 | `rank(delay[20](ts_mean[3](low)))` |
| 3 | ga_g008_0002 | mutate | delay | 1.1201 | -0.1329 | -2.30 | 3 | 3 | `delay[20](ts_mean[3](low))` |
| 4 | ga_g008_0042 | crossover |  | 1.1111 | -0.1296 | -2.28 | 2 | 2 | `delay[20](vwap)` |
| 5 | ga_g008_0003 | crossover |  | 1.1096 | -0.1304 | -2.28 | 4 | 4 | `delay[20](rank(zscore_cs(open)))` |

- **#1 ga_g008_0000**  来源=`crossover`  变异点=`-`
  - parent[0] = `safe_div(zscore_cs(log_abs(close)),zscore_cs(low))`
  - parent[1] = `log_abs(delta[10](low))`
- **#2 ga_g008_0001**  来源=`crossover`  变异点=`-`
  - parent[0] = `rank(volume)`
  - parent[1] = `delay[20](ts_mean[3](low))`
- **#3 ga_g008_0002**  来源=`mutate`  变异点=`delay`
  - parent[0] = `delay[20](ts_mean[3](log_abs(returns)))`

---

## 🌳 最优 Top 10 因子血缘


**[1] ga_g003_0064**  fitness=`1.2055`  
  expr = `safe_div(zscore_cs(log_abs(close)),log_abs(delta[10](low)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = safe_div(zscore_cs(log_abs(close)),zscore_cs(low))
        └─ gen=2 op=random_inject (root)
        parent[1] = log_abs(delta[10](low))
        └─ gen=0 op=random_init (root)
```

**[2] ga_g007_0001**  fitness=`1.1251`  
  expr = `rank(delay[20](ts_mean[3](low)))`
```
    └─ gen=6 op=crossover parents=2
        parent[0] = rank(volume)
        └─ gen=2 op=random_inject (root)
        parent[1] = delay[20](ts_mean[3](low))
        └─ gen=5 op=mutate mutate=delay parents=1
            parent[0] = delay[20](ts_mean[3](log_abs(returns)))
            └─ gen=3 op=crossover+mutate mutate=delay parents=2
                parent[0] = open
                └─ gen=0 op=random_init (root)
                parent[1] = delay[20](ts_mean[3](log_abs(volume)))
                └─ gen=2 op=crossover parents=2
                    parent[0] = delay[20](volume)
                    └─ gen=1 op=random_inject (root)
                    parent[1] = ts_mean[3](log_abs(volume))
                    └─ gen=0 op=random_init (root)
```

**[3] ga_g007_0002**  fitness=`1.1250`  
  expr = `delay[20](ts_mean[3](low))`
```
    └─ gen=5 op=mutate mutate=delay parents=1
        parent[0] = delay[20](ts_mean[3](log_abs(returns)))
        └─ gen=3 op=crossover+mutate mutate=delay parents=2
            parent[0] = open
            └─ gen=0 op=random_init (root)
            parent[1] = delay[20](ts_mean[3](log_abs(volume)))
            └─ gen=2 op=crossover parents=2
                parent[0] = delay[20](volume)
                └─ gen=1 op=random_inject (root)
                parent[1] = ts_mean[3](log_abs(volume))
                └─ gen=0 op=random_init (root)
```

**[4] ga_g003_0057**  fitness=`1.1163`  
  expr = `delay[20](rank(zscore_cs(open)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = delay[20](volume)
        └─ gen=1 op=random_inject (root)
        parent[1] = rank(zscore_cs(open))
        └─ gen=2 op=crossover parents=2
            parent[0] = rank(amount)
            └─ gen=0 op=random_init (root)
            parent[1] = zscore_cs(open)
            └─ gen=1 op=crossover+mutate mutate=zscore_cs parents=2
                parent[0] = covariance[60](log_abs(scale(amount)),rank(low))
                └─ gen=0 op=random_init (root)
                parent[1] = zscore_cs(returns)
                └─ gen=0 op=random_init (root)
```

**[5] ga_g003_0046**  fitness=`1.1157`  
  expr = `delay[20](ts_mean[3](ts_min[3](vwap)))`
```
    └─ gen=3 op=crossover parents=2
        parent[0] = delay[20](ts_mean[3](log_abs(volume)))
        └─ gen=2 op=crossover parents=2
            parent[0] = delay[20](volume)
            └─ gen=1 op=random_inject (root)
            parent[1] = ts_mean[3](log_abs(volume))
            └─ gen=0 op=random_init (root)
        parent[1] = ts_min[3](vwap)
        └─ gen=0 op=random_init (root)
```

**[6] ga_g008_0042**  fitness=`1.1111`  
  expr = `delay[20](vwap)`
```
    └─ gen=8 op=crossover parents=2
        parent[0] = delay[20](volume)
        └─ gen=1 op=random_inject (root)
        parent[1] = vwap
        └─ gen=0 op=random_init (root)
```

**[7] ga_g002_0045**  fitness=`1.0863`  
  expr = `rank(ts_min[10](ts_min[20](open)))`
```
    └─ gen=2 op=crossover parents=2
        parent[0] = rank(amount)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](ts_min[20](open))
        └─ gen=1 op=crossover parents=2
            parent[0] = ts_min[10](open)
            └─ gen=0 op=random_init (root)
            parent[1] = ts_min[20](open)
            └─ gen=0 op=random_init (root)
```

**[8] ga_g001_0051**  fitness=`1.0858`  
  expr = `ts_min[10](ts_min[20](open))`
```
    └─ gen=1 op=crossover parents=2
        parent[0] = ts_min[10](open)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[20](open)
        └─ gen=0 op=random_init (root)
```

**[9] ga_g003_0032**  fitness=`1.0799`  
  expr = `ts_min[30](vwap)`
```
    └─ gen=3 op=crossover+mutate mutate=ts_min parents=2
        parent[0] = close
        └─ gen=0 op=random_init (root)
        parent[1] = covariance[30](amount,ts_rank[3](log_abs(low)))
        └─ gen=1 op=crossover parents=2
            parent[0] = covariance[30](amount,close)
            └─ gen=0 op=random_init (root)
            parent[1] = ts_rank[3](log_abs(low))
            └─ gen=0 op=random_init (root)
```

**[10] ga_g007_0007**  fitness=`1.0787`  
  expr = `ts_min[20](ts_min[10](open))`
```
    └─ gen=6 op=crossover parents=2
        parent[0] = ts_min[20](open)
        └─ gen=0 op=random_init (root)
        parent[1] = ts_min[10](open)
        └─ gen=0 op=random_init (root)
```
