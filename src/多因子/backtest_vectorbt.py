from __future__ import annotations

import pandas as pd
import vectorbt as vbt

from src.多因子 import config


def build_rebalance_mask(index: pd.Index, freq: str = config.REBALANCE_FREQ) -> pd.Series:
    """生成调仓日掩码。

    这里的目标是：
    - 把一串交易日索引，转换成“哪些日子需要调仓”的布尔序列；
    - 当前默认按周调仓，即每个调仓周期只在第一个有效交易日执行一次调仓。

    例如：
    - 如果频率是 `W-FRI`；
    - 那么每周对应一个 period；
    - 每个 period 里只取第一天作为组合切换日。
    """
    dt_index = pd.to_datetime(index.astype(str))
    period_index = dt_index.to_period(freq)
    first_dates = pd.Series(dt_index, index=index).groupby(period_index).head(1).index
    mask = pd.Series(False, index=index)
    mask.loc[first_dates] = True
    return mask


def build_target_weights(
    selection_df: pd.DataFrame,
    rebalance_mask: pd.Series,
) -> pd.DataFrame:
    """将选股结果转换成目标权重矩阵。

    当前版本的权重规则非常简单：
    - 调仓日：对入选股票做等权分配；
    - 非调仓日：沿用上一期权重，不主动变化；
    - 若某个调仓日没有股票入选，则权重全部归零。

    这种设计很适合作为第一版研究框架，逻辑清晰，方便验证。
    """
    if selection_df.empty:
        return selection_df.copy().astype(float)

    weights = pd.DataFrame(0.0, index=selection_df.index, columns=selection_df.columns)
    last_weights = pd.Series(0.0, index=selection_df.columns)

    for dt in selection_df.index:
        if bool(rebalance_mask.get(dt, False)):
            selected = selection_df.loc[dt].fillna(False)
            count = int(selected.sum())
            if count > 0:
                current = selected.astype(float) / count
            else:
                current = pd.Series(0.0, index=selection_df.columns)
            last_weights = current

        weights.loc[dt] = last_weights.values

    return weights


def run_vectorbt_backtest(
    close_df: pd.DataFrame,
    target_weights: pd.DataFrame,
    commission: float = config.COMMISSION,
    slippage: float = config.SLIPPAGE,
    init_cash: float = config.INITIAL_CASH,
):
    """使用 VectorBT 运行组合回测。

    回测方式：
    - 输入收盘价矩阵；
    - 输入目标权重矩阵；
    - 由 VectorBT 根据目标权重自动生成调仓订单。

    这里使用 `targetpercent`：
    - 目标是让每只股票的仓位达到给定百分比；
    - 非常适合截面选股 + 定期再平衡的组合回测场景。
    """
    if close_df.empty or target_weights.empty:
        raise ValueError("close_df 或 target_weights 为空，无法回测")

    close = close_df.copy()
    close.index = pd.to_datetime(close.index.astype(str))

    # 仅在调仓日提交目标权重订单；非调仓日保持 NaN，避免 VectorBT 每天按 targetpercent 重平衡。
    weights = target_weights.reindex_like(close_df).copy()
    weights.index = close.index
    active_order_mask = weights.ne(weights.shift()).any(axis=1)
    weights = weights.where(active_order_mask, other=pd.NA).astype(float)

    portfolio = vbt.Portfolio.from_orders(
        close=close,
        size=weights,
        size_type="targetpercent",
        init_cash=init_cash,
        fees=commission,
        slippage=slippage,
        cash_sharing=True,
        call_seq="auto",
        freq="1D",
    )
    return portfolio


def extract_backtest_results(portfolio, benchmark_close: pd.Series | None = None) -> dict[str, object]:
    """提取回测结果。

    当前统一输出几类最核心结果：
    - stats: VectorBT 的统计摘要
    - equity_curve: 组合净值曲线
    - returns: 收益率序列
    - positions: 各股票资产市值变化
    - benchmark_close: 中证 2000 收盘价序列
    - benchmark_returns: 中证 2000 日收益率序列

    注意：
    - VectorBT 默认 stats 里的 benchmark 不是我们显式指定的中证 2000；
    - 因此这里额外把中证 2000 的收益单独算出来，并覆盖 stats 中的 Benchmark Return [%]。
    """
    stats = portfolio.stats()
    benchmark_returns = None
    if benchmark_close is not None and not benchmark_close.empty:
        aligned_benchmark = benchmark_close.copy()
        aligned_benchmark.index = pd.to_datetime(aligned_benchmark.index.astype(str))
        aligned_benchmark = aligned_benchmark.reindex(portfolio.value().index).ffill()
        benchmark_returns = aligned_benchmark.pct_change().fillna(0.0)

        if len(aligned_benchmark) > 0 and pd.notna(aligned_benchmark.iloc[0]) and aligned_benchmark.iloc[0] != 0:
            benchmark_total_return = (aligned_benchmark.iloc[-1] / aligned_benchmark.iloc[0] - 1.0) * 100
            if hasattr(stats, "loc"):
                stats.loc["Benchmark Return [%]"] = benchmark_total_return

    return {
        "stats": stats,
        "equity_curve": portfolio.value(),
        "returns": portfolio.returns(),
        "positions": portfolio.asset_value(),
        "benchmark_close": benchmark_close,
        "benchmark_returns": benchmark_returns,
    }
