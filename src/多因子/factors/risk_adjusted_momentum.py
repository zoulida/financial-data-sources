from __future__ import annotations

import numpy as np
import pandas as pd


def compute_risk_adjusted_momentum(
    close_df: pd.DataFrame,
    window: int = 20,
) -> pd.DataFrame:
    """计算风险调整后动量因子。

    因子思想：
    - 不是简单看“谁涨得多”；
    - 而是看“谁在相对可控的波动下涨得更好”。

    简化公式：
        过去 N 日收益率 / 过去 N 日日收益波动率

    这样做的好处：
    - 可以压低那些虽然涨得快、但过程很剧烈的股票分数；
    - 更贴近“小盘股波段”里“强且相对稳”的选股逻辑。

    Args:
        close_df: 收盘价矩阵，行是日期，列是股票代码。
        window: 计算窗口，默认 20 个交易日。

    Returns:
        风险调整动量因子矩阵。
    """
    if close_df.empty:
        return close_df.copy()

    # 先计算日收益率，这是后面滚动波动率的基础。
    returns = close_df.pct_change()

    # 过去 N 日累计收益率。
    rolling_return = close_df / close_df.shift(window) - 1.0

    # 过去 N 日日收益率的标准差，用来刻画波动大小。
    rolling_vol = returns.rolling(window, min_periods=window).std()

    # 如果波动率为 0，会出现除零问题，因此先替换成 NaN。
    factor_df = rolling_return.divide(rolling_vol.replace(0, np.nan))

    # 再把可能产生的正负无穷统一替换成 NaN，避免污染后续排名。
    return factor_df.replace([np.inf, -np.inf], np.nan)
