"""QLib 传统多因子 2.0 工作流包。

支持以下扩展（相比 1.0）：
1. 任意选择因子库目录（_root / alpha101 / alpha158 / alpha191）
2. 三种未来收益口径（持有期 close / 区间 max(high) / 区间 max(close)）
3. 三种因子过滤策略（none / threshold / topk）
4. 传统打分回测 与 ML 信号回测（LightGBM / Ridge / Lasso）
"""
