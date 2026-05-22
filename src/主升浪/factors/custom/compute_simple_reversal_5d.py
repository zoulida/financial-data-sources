"""5 日反转因子:过去窗口跌得越多,未来反弹概率越高。"""

from __future__ import annotations

import pandas as pd


def compute_simple_reversal_5d(close_df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """过去 ``window`` 日反转因子。

    Args:
        close_df: 收盘价宽表,行=日期,列=股票代码。
        window:   回看窗口,默认 5 个交易日。

    Returns:
        与 ``close_df`` 形状一致的因子矩阵。
    """
    if close_df.empty:
        return close_df.copy()
    return -(close_df / close_df.shift(window) - 1.0)
