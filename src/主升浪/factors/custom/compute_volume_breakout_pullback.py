"""放量突破前高回踩因子:识别股价放量突破前期高点后缩量回踩的形态,回踩期间成交量不超过突破日成交量的一半。"""

from __future__ import annotations

import pandas as pd
import numpy as np


def compute_volume_breakout_pullback(
    close_df: pd.DataFrame,
    high_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    lookback_window: int = 60,
    breakout_window: int = 20,
    pullback_window: int = 5,
    volume_ratio: float = 0.5,
) -> pd.DataFrame:
    """放量突破前高后缩量回踩因子。

    逻辑:
    1. 在 ``lookback_window`` 天内寻找最高价(前高)。
    2. 最近 ``breakout_window`` 天内,某日收盘价突破前高且成交量是前高以来均量的1.5倍以上(放量突破)。
    3. 突破后 ``pullback_window`` 天内,每日成交量不超过突破日成交量的 ``volume_ratio`` 倍(缩量回踩)。
    4. 当前日期为回踩最后一天,返回信号强度(1表示满足条件,0表示不满足)。

    Args:
        close_df: 收盘价宽表。
        high_df: 最高价宽表。
        volume_df: 成交量宽表。
        lookback_window: 前高回看窗口,默认60天。
        breakout_window: 突破检测窗口,默认20天。
        pullback_window: 回踩检测窗口,默认5天。
        volume_ratio: 回踩成交量上限比例(相对于突破日),默认0.5。

    Returns:
        与 ``close_df`` 形状一致的因子矩阵,值为1或NaN。
    """
    if close_df.empty or high_df.empty or volume_df.empty:
        return close_df.copy()

    # 确保所有输入形状一致
    assert close_df.shape == high_df.shape == volume_df.shape, "输入DataFrame形状不一致"

    # 计算前高:过去lookback_window天的最高价(不含当天)
    rolling_high = high_df.rolling(window=lookback_window, min_periods=lookback_window).max().shift(1)

    # 计算前高以来的平均成交量(用于判断放量)
    # 使用rolling mean,但需要对齐前高位置,这里简化:用前高窗口内的成交量均值
    volume_mean = volume_df.rolling(window=lookback_window, min_periods=lookback_window).mean().shift(1)

    # 放量突破条件:收盘价突破前高,且当日成交量是前高以来均量的1.5倍
    breakout_price = (close_df > rolling_high)
    breakout_volume = (volume_df > 1.5 * volume_mean)
    breakout = breakout_price & breakout_volume

    # 找到每个股票每个日期的最近突破日(在breakout_window内)
    # 使用反向rolling max来标记突破日
    # 构造一个DataFrame,突破日为1,否则为0
    breakout_flag = breakout.astype(int)

    # 对于每个日期,检查过去breakout_window天内是否有突破
    # 如果有,取最近突破日的成交量
    # 使用rolling apply或循环(效率考虑,用向量化方法)
    # 方法:将突破日的成交量保留,其他设为NaN,然后向前填充
    breakout_volume_series = volume_df.where(breakout_flag == 1, other=np.nan)

    # 向前填充最近突破日的成交量(限制在breakout_window天内)
    # 使用ffill,但需要限制窗口
    # 先ffill,然后通过rolling count判断是否在窗口内
    ffill_volume = breakout_volume_series.ffill(limit=breakout_window)

    # 判断是否在窗口内:从突破日到当前日不超过breakout_window天
    # 计算距离最近突破日的天数
    # 用突破日标记的累积和来定位
    # 更简单:用rolling max判断breakout_window内是否有突破
    has_breakout_recently = breakout_flag.rolling(window=breakout_window, min_periods=1).max() > 0

    # 回踩条件:当前日期在突破后,且连续pullback_window天成交量不超过突破日成交量的volume_ratio
    # 需要检查从突破日到当前日(含)的每一天成交量都满足条件
    # 简化:只检查最近pullback_window天(假设突破发生在pullback_window天前)
    # 更精确:检查突破后到当前的所有交易日
    # 这里采用:突破后至少pullback_window天,且最近pullback_window天成交量都小于阈值
    # 先计算阈值:突破日成交量 * volume_ratio
    threshold_volume = ffill_volume * volume_ratio

    # 最近pullback_window天成交量都小于阈值
    # 使用rolling min,如果最小值大于阈值则全部满足(这里需要小于)
    # 检查最近pullback_window天成交量最大值是否小于阈值
    recent_volume_max = volume_df.rolling(window=pullback_window, min_periods=pullback_window).max()
    volume_condition = (recent_volume_max <= threshold_volume)

    # 还需要确保突破后至少经过了pullback_window天
    # 计算突破后的天数:用突破日标记的累积和
    # 从最近突破日开始计数
    # 使用expanding sum或rolling sum
    # 简单方法:检查最近pullback_window天内是否有突破日(即突破日距今不超过pullback_window天)
    # 但需求是突破后回踩几天,所以突破日应该在pullback_window天之前
    # 更合理:突破发生在pullback_window天前,然后回踩pullback_window天
    # 这里简化:突破发生在过去breakout_window天内,且当前日期距离突破日至少pullback_window天
    # 用滚动窗口判断:过去breakout_window天内有突破,且最近pullback_window天没有突破(即突破在更早)
    # 但需求是突破后回踩,所以突破日应该在pullback_window天之前
    # 实现:检查breakout_window天前到pullback_window天前之间是否有突破
    # 使用shift
    # 这里采用:过去breakout_window天内有突破,且最近pullback_window天没有突破(即突破发生在pullback_window天前)
    # 但这样会忽略突破后立即回踩的情况(突破日就在pullback_window天前)
    # 更准确:突破发生在过去breakout_window天内,且从突破日到当前日至少有pullback_window天
    # 用滚动窗口判断:过去breakout_window天内有突破,且最近pullback_window天内的成交量都满足条件
    # 且最近pullback_window天内的第一天不是突破日(即突破在更早)
    # 简化实现:检查最近pullback_window天成交量条件,且过去breakout_window天内有突破
    # 且最近pullback_window天内的第一天之前有突破
    # 使用shift
    # 这里采用:过去breakout_window天内有突破,且最近pullback_window天成交量条件满足
    # 且最近pullback_window天内的第一天之前有突破(即突破不在最近pullback_window天内)
    # 用shift(pullback_window)检查
    has_breakout_before_pullback = breakout_flag.shift(pullback_window).rolling(window=breakout_window, min_periods=1).max() > 0

    # 最终条件
    result = has_breakout_recently & volume_condition & has_breakout_before_pullback

    # 转换为1或NaN
    result = result.astype(float).where(result, other=np.nan)

    # 确保返回与close_df相同的index/columns
    result = result.reindex_like(close_df)

    return result
