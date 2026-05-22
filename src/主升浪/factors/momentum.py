from __future__ import annotations

import pandas as pd


def compute_momentum_factor(close_df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """计算中期动量因子。

    因子定义：
        当日收盘价 / N日前收盘价 - 1

    直观理解：
    - 如果一只股票过去 20 个交易日涨得越多，动量值越高；
    - 在波段策略里，这个因子用于寻找“中短期趋势较强”的标的。

    Args:
        close_df: 收盘价矩阵，行是日期，列是股票代码。
        window: 回看窗口，默认 20 个交易日。

    Returns:
        与 `close_df` 形状一致的因子矩阵。
    """
    if close_df.empty:
        return close_df.copy()

    return close_df / close_df.shift(window) - 1.0
