from __future__ import annotations

import numpy as np
import pandas as pd


def mask_factor(factor_df: pd.DataFrame, tradable_mask: pd.DataFrame) -> pd.DataFrame:
    """将不可参与排序的股票因子值置为 NaN。

    这里的作用很直接：
    - 因子先正常算；
    - 再用布尔掩码把不该参与横截面排名的股票屏蔽掉。

    在当前版本里，这个掩码主要体现的是：
    - 是否还在股票池中；
    - 是否已经被 ST 过滤；
    - 收盘价数据是否有效。
    """
    if factor_df.empty:
        return factor_df.copy()

    factor_df = factor_df.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    aligned_mask = tradable_mask.reindex_like(factor_df).astype("boolean").fillna(False).astype(bool)
    return factor_df.where(aligned_mask)


def rank_score(factor_df: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
    """按日做横截面分位排名打分。

    说明：
    - 每一个交易日，都会在“当日可参与排序的股票”里重新排名；
    - `pct=True` 会把排名归一化到 0~1 之间；
    - 分数越高，代表该股票在当日横截面中越靠前。

    Args:
        factor_df: 因子矩阵。
        ascending: 是否升序排名。
            - False：值越大分数越高，适合动量类因子；
            - True：值越小分数越高，适合估值、波动率这类反向因子。
    """
    if factor_df.empty:
        return factor_df.copy()

    factor_df = factor_df.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    rank_df = factor_df.rank(axis=1, ascending=ascending, pct=True, method="average")
    return rank_df


def combine_factor_scores(
    factor_score_dict: dict[str, pd.DataFrame],
    weights: dict[str, float],
) -> pd.DataFrame:
    """按权重合成综合分数。

    这里采用最简单、最透明的线性加权方式：
    1. 先把每个因子转成 0~1 的横截面分位分数；
    2. 再按预设权重加总；
    3. 最后除以总权重，得到综合分数。

    这种方式的优点是：
    - 直观；
    - 便于解释；
    - 第一版框架足够稳定。
    """
    if not factor_score_dict:
        return pd.DataFrame()

    weighted_sum = None
    total_weight = 0.0
    for name, score_df in factor_score_dict.items():
        weight = float(weights.get(name, 0.0))
        if weight == 0:
            continue

        total_weight += weight
        contribution = score_df * weight
        weighted_sum = contribution if weighted_sum is None else weighted_sum.add(contribution, fill_value=0.0)

    if weighted_sum is None or total_weight == 0:
        first_df = next(iter(factor_score_dict.values()))
        return pd.DataFrame(index=first_df.index, columns=first_df.columns, dtype=float)

    return weighted_sum / total_weight


def select_top_n(score_df: pd.DataFrame, n: int) -> pd.DataFrame:
    """根据综合分数选出每期前 N 只股票。

    输出结果是一个布尔矩阵：
    - True 代表该股票在该日入选组合；
    - False 代表未入选。

    后续回测模块会基于这个布尔矩阵，把组合转成目标权重。
    """
    if score_df.empty:
        return pd.DataFrame(index=score_df.index, columns=score_df.columns, dtype=bool)

    selection = pd.DataFrame(False, index=score_df.index, columns=score_df.columns)
    for dt, row in score_df.iterrows():
        valid = row.dropna().sort_values(ascending=False)
        top_codes = valid.head(n).index.tolist()
        if top_codes:
            selection.loc[dt, top_codes] = True
    return selection
