from __future__ import annotations

import pandas as pd


def build_tradable_mask(
    universe_df: pd.DataFrame,
    close_df: pd.DataFrame,
) -> pd.DataFrame:
    """构建最终可交易股票掩码。

    注意：
    - 按你当前要求，这一版“只过滤 ST，其他不过滤”；
    - ST 已经在 `data_loader.load_base_universe()` 阶段处理掉；
    - 因此这里不再做流动性、上市天数、停牌、涨跌停等过滤；
    - 这里只保留最基础的技术性约束：
      1. 股票必须仍在当前股票池列中；
      2. 收盘价必须存在；
      3. 收盘价必须大于 0。

    这样做的目的是：
    - 尽量遵守“只过滤 ST”的需求；
    - 同时保证后续因子计算和回测不会因为空值或异常价格直接报错。
    """
    if close_df.empty:
        return pd.DataFrame(index=close_df.index, columns=close_df.columns, dtype=bool)

    # 先根据股票池代码生成一个基础布尔矩阵。
    # 只有在当前股票池中的股票，才有资格进入后续打分与回测。
    allowed_codes = set(universe_df["code"].tolist()) if not universe_df.empty else set()
    base_mask = pd.DataFrame(False, index=close_df.index, columns=close_df.columns)
    valid_columns = [code for code in close_df.columns if code in allowed_codes]
    if valid_columns:
        base_mask.loc[:, valid_columns] = True

    # 这里只保留最小必要的数据有效性过滤。
    price_mask = close_df.notna() & (close_df > 0)

    tradable_mask = base_mask & price_mask
    return tradable_mask.astype(bool)
