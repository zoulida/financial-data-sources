# GA 因子工作流 进化报告

种群=6, 代数=1, 交叉率=0.7, 变异率=0.2, 精英保留=2, 最大深度=2, 最大节点=8


说明：本文件逐代追加，可以在 GA 运行过程中随时查看。`operation` 含义：`random_init` 初始随机, `random_inject` 本代随机注入, `random_restart` 本代重启, `elite` 从上代直接保留, `crossover` 交叉, `mutate` 变异, `crossover+mutate` 先交叉后变异, `reproduction` 原样复制。


## 第 0 代  best=0.0788  mean=0.0786  n_valid=2  archive=2
- 本代有效个体操作分布：random_init=2

| 排名 | 因子 | 来源 | 变异点 | fitness | rank_ic | IR | depth | complexity | 表达式 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ga_g000_0003 | random_init |  | 0.0788 | -0.0064 | -0.05 | 1 | 1 | `low` |
| 2 | ga_g000_0005 | random_init |  | 0.0785 | -0.0063 | -0.05 | 1 | 1 | `close` |


---

## 🌳 最优 Top 10 因子血缘


**[1] ga_g000_0003**  fitness=`0.0788`  
  expr = `low`
```
    └─ gen=0 op=random_init (root)
```

**[2] ga_g000_0005**  fitness=`0.0785`  
  expr = `close`
```
    └─ gen=0 op=random_init (root)
```
