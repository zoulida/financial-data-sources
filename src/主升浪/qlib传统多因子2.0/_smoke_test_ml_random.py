"""ML 链路 sanity check：用纯随机噪声特征跑 ML，估计"零信号"基线的 sharpe 分布。

如果生产回测中 ML 信号的 sharpe 高得离谱（比如 5+），可以用这个脚本判断：

    生产 sharpe ≈ 真实 alpha sharpe + 小样本 / 选股偏差 sharpe(由本脚本估计)

用法::

    python _smoke_test_ml_random.py

输出：

1. **Part A 单次诊断**：对 ridge / lasso / lightgbm 各跑一次纯噪声回测，看 sharpe。
2. **Part B 多种子 Monte Carlo**：跑 ``N_SEEDS`` 个不同种子的 ridge，给出
   "零真实信号情形下" sharpe 的均值 / 标准差 / 分位数，作为 baseline。

注意：
- 此脚本不读真实 QLib 数据，纯粹独立采样高斯特征 / 标签。
- 默认 OOS 期约 43 天（n_days=500, test_start=2025-10-01），故意设短以
  模拟生产中 7 个月 OOS 的小样本环境。
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_v2  # noqa: E402
from ml_pipeline import MLConfig, train_predict  # noqa: E402

warnings.filterwarnings("ignore")

# ---- 可调参数 ----
N_SEEDS = 20
N_DAYS = 500
N_STOCKS = 200
N_FACTORS = 113
TOPN = 50


def _build_random_panel(seed: int):
    """生成一组完全独立的随机 features 与 future_return。"""
    dates = pd.date_range("2024-01-01", periods=N_DAYS, freq="B")
    codes = [f"sh{600000 + i:06d}" for i in range(N_STOCKS)]

    rng = np.random.RandomState(seed)
    future = pd.DataFrame(
        rng.randn(N_DAYS, N_STOCKS) * 0.02, index=dates, columns=codes
    )
    factors = {}
    for i in range(N_FACTORS):
        raw = rng.randn(N_DAYS, N_STOCKS)
        df = pd.DataFrame(raw, index=dates, columns=codes)
        df = df.sub(df.mean(axis=1), axis=0).div(
            df.std(axis=1).replace(0.0, np.nan), axis=0
        )
        factors[f"noise_{i}"] = df
    return dates, codes, future, factors


def _stack_long(future: pd.DataFrame, factors):
    long_data = {
        n: f.stack(dropna=False).rename_axis(["datetime", "instrument"])
        for n, f in factors.items()
    }
    future_long = future.stack(dropna=False).rename_axis(["datetime", "instrument"])
    future_long.name = "future_return"
    return pd.DataFrame(long_data).join(future_long, how="inner")


def _eval_topn_sharpe(score_wide: pd.DataFrame, future: pd.DataFrame, topn: int) -> float:
    fut = future.loc[score_wide.index]
    daily = []
    for d in score_wide.index:
        scores = score_wide.loc[d].dropna()
        if scores.empty:
            continue
        top = scores.sort_values(ascending=False).head(topn).index
        daily.append(float(fut.loc[d].reindex(top).mean()))
    s = pd.Series(daily).dropna()
    return float(s.mean() / s.std() * np.sqrt(252)) if s.std() > 0 else 0.0


def _run_ridge_one(seed: int) -> dict:
    _, _, future, factors = _build_random_panel(seed)
    df_long = _stack_long(future, factors)
    cfg = MLConfig(
        model="ridge",
        train_end="2025-06-30",
        valid_end="2025-09-30",
        test_start="2025-10-01",
        alpha=1.0,
    )
    prediction, _ = train_predict(df_long, list(factors.keys()), "future_return", cfg)
    score_wide = prediction.unstack("instrument").sort_index()
    score_wide.index = pd.to_datetime(score_wide.index)
    return {"seed": seed, "sharpe": _eval_topn_sharpe(score_wide, future, TOPN)}


def part_a_single_compare():
    """对 ridge/lasso/lightgbm 各跑一次纯噪声回测做对比。"""
    print("=" * 72)
    print("Part A: 三模型在纯随机数据下的单次回测")
    print("=" * 72)
    _, _, future, factors = _build_random_panel(seed=42)
    df_long = _stack_long(future, factors)
    feature_cols = list(factors.keys())

    wf = workflow_v2.WorkflowV2.__new__(workflow_v2.WorkflowV2)
    wf.config = workflow_v2.WorkflowConfigV2(
        topn=TOPN,
        holding_period=1,
        test_start_time="2025-10-01",
        backtest_test_period_only=True,
    )
    wf.holding_return = future
    wf.future_return = future
    benchmark = pd.Series(0.0, index=future.index)

    signals = {}
    for model in ("ridge", "lasso", "lightgbm"):
        cfg = MLConfig(
            model=model,
            train_end="2025-06-30",
            valid_end="2025-09-30",
            test_start="2025-10-01",
            alpha=1.0,
            num_boost_round=200,
            early_stopping_rounds=20,
        )
        try:
            prediction, _ = train_predict(df_long, feature_cols, "future_return", cfg)
        except Exception as exc:
            print(f"  WARN: {model} 失败: {exc}")
            continue
        wide = prediction.unstack("instrument").sort_index()
        wide.index = pd.to_datetime(wide.index)
        signals[f"score_ml_{model}"] = wide

    bt, perf = wf._run_backtests(signals, benchmark)
    print(perf.to_string(index=False))


def part_b_monte_carlo():
    """跑 N_SEEDS 次 ridge，给出'零真实信号'的 sharpe baseline 分布。"""
    print()
    print("=" * 72)
    print(f"Part B: Monte Carlo (N_SEEDS={N_SEEDS}) -- 估计零信号 sharpe baseline")
    print("=" * 72)
    rows = []
    for seed in range(N_SEEDS):
        try:
            r = _run_ridge_one(seed)
            rows.append(r)
            print(f"  seed={seed:2d}  sharpe={r['sharpe']:+.2f}")
        except Exception as exc:
            print(f"  seed={seed:2d}  failed: {exc}")
    df = pd.DataFrame(rows)
    if df.empty:
        return
    s = df["sharpe"]
    print()
    print(f"  sharpe 均值 = {s.mean():+.3f}, std = {s.std():.3f}")
    print(f"  sharpe 区间 [{s.min():+.2f}, {s.max():+.2f}]")
    print(
        f"  分位数: 10% = {s.quantile(0.10):+.2f}, "
        f"50% = {s.quantile(0.5):+.2f}, "
        f"90% = {s.quantile(0.90):+.2f}"
    )
    print()
    print("解读：生产环境真实数据回测的 sharpe 应当显著超出本 baseline 的 90% 分位数才能算 '真信号'。")


def main():
    part_a_single_compare()
    part_b_monte_carlo()


if __name__ == "__main__":
    main()
