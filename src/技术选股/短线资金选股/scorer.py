"""
多因子打分引擎
==============
5个维度，总分100分：
  1. 资金流向（30分）
  2. 量价异动（25分）
  3. 技术形态（20分）
  4. 筹码结构（15分）
  5. 基本面安全垫（10分）
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional

from 技术选股.短线资金选股.config import (
    # 资金流向
    FLOW_LOOKBACK_DAYS,
    FLOW_RECENT_WINDOW,
    FLOW_BAD_DAY_THRESHOLD,
    FLOW_PREBREAK_RET_LOW,
    FLOW_PREBREAK_RET_HIGH,
    SCORE_FLOW_14D_MAX,
    SCORE_FLOW_ACCEL_MAX,
    SCORE_FLOW_STABILITY_MAX,
    SCORE_FLOW_PREBREAK_MAX,
    # 量价异动
    VOL_SURGE_LOW,
    VOL_SURGE_BEST,
    VOL_SURGE_HIGH,
    SCORE_VOL_SURGE_MAX,
    AMOUNT_STABILITY_LOW,
    AMOUNT_STABILITY_HIGH,
    SCORE_AMOUNT_STABILITY_MAX,
    SCORE_PULLBACK_VOLUME_MAX,
    # 技术形态
    MA_DISTANCE_LOW,
    MA_DISTANCE_HIGH,
    SCORE_MA_TREND_MAX,
    SCORE_MACD_MAX,
    SCORE_PLATFORM_MAX,
    # 筹码结构
    SHRINK_RATIO_THRESHOLD,
    AMP_NARROW_RATIO,
    SCORE_SHRINK_EXPAND_MAX,
    SCORE_AMP_NARROW_MAX,
    POS_BEST_LOW,
    POS_BEST_HIGH,
    SCORE_POSITION_MAX,
    # 权重
    WEIGHT_VOLUME_PRICE,
    WEIGHT_CHIP,
)


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """限制值在 [lo, hi] 区间。"""
    return max(lo, min(hi, val))


def _percentile_score(value: float, all_values: pd.Series, max_score: float) -> float:
    """按全池排名分位打分。值越大分越高。"""
    if pd.isna(value) or all_values.dropna().empty:
        return 0.0
    rank = (all_values.dropna() <= value).sum() / max(1, len(all_values.dropna()))
    return round(rank * max_score, 2)


def _sum_amount(df: Optional[pd.DataFrame], window: int) -> float:
    """获取最近 window 天成交额累计。"""
    if df is None or "amount" not in df.columns:
        return np.nan
    amt = pd.to_numeric(df["amount"], errors="coerce").dropna().tail(window)
    if amt.empty:
        return np.nan
    return float(amt.sum())


def _window_sum(series: pd.Series, window: int) -> float:
    """获取最近 window 天数值累计。"""
    vals = pd.to_numeric(series, errors="coerce").dropna().tail(window)
    if vals.empty:
        return np.nan
    return float(vals.sum())


def _window_ratio(series: pd.Series, amount_df: Optional[pd.DataFrame], window: int) -> float:
    """获取最近 window 天净流入 / 成交额 比率。"""
    numerator = _window_sum(series, window)
    denominator = _sum_amount(amount_df, window)
    if pd.notna(numerator) and pd.notna(denominator) and denominator > 0:
        return numerator / denominator
    return np.nan


def score_capital_flow(
    wind_df: Optional[pd.DataFrame],
    all_wind_data: Dict[str, pd.DataFrame],
    kline_df: Optional[pd.DataFrame],
    all_kline_data: Dict[str, pd.DataFrame],
) -> Dict[str, float]:
    """
    资金流向维度打分（14日波段版）。

    波段思路：
      1. 看 14 日净流入强度
      2. 看近 5 日是否较前 9 日改善
      3. 看过程中是否存在明显砸盘坏日
      4. 看资金介入时，股价是否仍处于“未充分拉升”的预启动区
    """
    result = {
        "flow_14d_score": 0.0,
        "flow_accel_score": 0.0,
        "flow_stability_score": 0.0,
        "flow_prebreak_score": 0.0,
        "capital_flow_total": 0.0,
    }

    if wind_df is None or wind_df.empty or kline_df is None or kline_df.empty:
        return result

    lookback = FLOW_LOOKBACK_DAYS
    recent_window = FLOW_RECENT_WINDOW
    prev_window = lookback - recent_window
    mfd_col = "mfd_inflow_m"

    if mfd_col not in wind_df.columns or "amount" not in kline_df.columns or "close" not in kline_df.columns:
        return result

    flow_series = pd.to_numeric(wind_df[mfd_col], errors="coerce").dropna().tail(lookback)
    kline_tail = kline_df.tail(lookback).copy()
    amt_series = pd.to_numeric(kline_tail["amount"], errors="coerce").dropna()
    close_series = pd.to_numeric(kline_df["close"], errors="coerce").dropna()

    if len(flow_series) < lookback or len(amt_series) < lookback or len(close_series) < 20:
        return result

    flow_14d = _window_ratio(flow_series, kline_tail, lookback)
    all_flow_14d = []
    all_flow_accel = []

    for code, wdf in all_wind_data.items():
        kdf = all_kline_data.get(code)
        if wdf is None or kdf is None or mfd_col not in wdf.columns or "amount" not in kdf.columns:
            continue
        peer_flow_series = pd.to_numeric(wdf[mfd_col], errors="coerce").dropna().tail(lookback)
        peer_kline_tail = kdf.tail(lookback)
        if len(peer_flow_series) < lookback or len(peer_kline_tail) < lookback:
            continue

        peer_flow_14d = _window_ratio(peer_flow_series, peer_kline_tail, lookback)
        all_flow_14d.append(peer_flow_14d)

        peer_recent = _window_ratio(peer_flow_series.tail(recent_window), peer_kline_tail.tail(recent_window), recent_window)
        peer_prev = _window_ratio(peer_flow_series.head(prev_window), peer_kline_tail.head(prev_window), prev_window)
        all_flow_accel.append(peer_recent - peer_prev if pd.notna(peer_recent) and pd.notna(peer_prev) else np.nan)

    result["flow_14d_score"] = _percentile_score(flow_14d, pd.Series(all_flow_14d), SCORE_FLOW_14D_MAX)

    recent_flow_ratio = _window_ratio(flow_series.tail(recent_window), kline_tail.tail(recent_window), recent_window)
    prev_flow_ratio = _window_ratio(flow_series.head(prev_window), kline_tail.head(prev_window), prev_window)
    flow_accel = recent_flow_ratio - prev_flow_ratio if pd.notna(recent_flow_ratio) and pd.notna(prev_flow_ratio) else np.nan
    result["flow_accel_score"] = _percentile_score(flow_accel, pd.Series(all_flow_accel), SCORE_FLOW_ACCEL_MAX)

    daily_flow_ratio = flow_series.reset_index(drop=True) / amt_series.reset_index(drop=True)
    bad_days = int((daily_flow_ratio < FLOW_BAD_DAY_THRESHOLD).sum())
    if bad_days <= 1:
        result["flow_stability_score"] = SCORE_FLOW_STABILITY_MAX
    elif bad_days == 2:
        result["flow_stability_score"] = round(SCORE_FLOW_STABILITY_MAX * 0.7, 2)
    elif bad_days == 3:
        result["flow_stability_score"] = round(SCORE_FLOW_STABILITY_MAX * 0.35, 2)

    ret_14d = close_series.iloc[-1] / close_series.iloc[-lookback] - 1 if close_series.iloc[-lookback] > 0 else np.nan
    ma20 = close_series.rolling(20).mean().iloc[-1]
    ma20_prev = close_series.rolling(20).mean().iloc[-5] if len(close_series) >= 24 else np.nan
    ma20_slope = ma20 / ma20_prev - 1 if pd.notna(ma20) and pd.notna(ma20_prev) and ma20_prev > 0 else np.nan
    last_close = close_series.iloc[-1]

    if pd.notna(flow_14d) and flow_14d > 0 and pd.notna(ret_14d):
        if FLOW_PREBREAK_RET_LOW <= ret_14d <= FLOW_PREBREAK_RET_HIGH and pd.notna(ma20) and last_close >= ma20 * 0.98:
            result["flow_prebreak_score"] = SCORE_FLOW_PREBREAK_MAX
        elif -0.08 <= ret_14d < FLOW_PREBREAK_RET_LOW and pd.notna(ma20_slope) and ma20_slope >= 0:
            result["flow_prebreak_score"] = round(SCORE_FLOW_PREBREAK_MAX * 0.6, 2)
        elif FLOW_PREBREAK_RET_HIGH < ret_14d <= 0.15:
            result["flow_prebreak_score"] = round(SCORE_FLOW_PREBREAK_MAX * 0.35, 2)

    result["capital_flow_total"] = round(
        result["flow_14d_score"]
        + result["flow_accel_score"]
        + result["flow_stability_score"]
        + result["flow_prebreak_score"],
        2,
    )
    return result


# ════════════════════════════════════════════════════════════
# 维度2：量价异动（25分）
# ════════════════════════════════════════════════════════════

def score_volume_price(df: pd.DataFrame) -> Dict[str, float]:
    """
    量价异动维度打分。

    波段思路：
      1. 看近 5 日量能是否温和放大，而不是只看今天
      2. 看近 10 日成交额是否稳定抬升
      3. 看回踩阶段是否缩量，避免高位乱放量
    """
    result = {
        "vol_surge_score": 0.0,
        "amount_stability_score": 0.0,
        "pullback_volume_score": 0.0,
        "volume_price_total": 0.0,
    }
    if df is None or len(df) < 35:
        return result

    close = pd.to_numeric(df["close"], errors="coerce")
    vol = pd.to_numeric(df["volume"], errors="coerce")
    amt = pd.to_numeric(df["amount"], errors="coerce")

    recent5_vol = vol.tail(5).mean()
    prev20_vol = vol.iloc[-25:-5].mean()
    if pd.notna(recent5_vol) and pd.notna(prev20_vol) and prev20_vol > 0:
        vol_surge = recent5_vol / prev20_vol
        if VOL_SURGE_LOW <= vol_surge <= VOL_SURGE_HIGH:
            if vol_surge <= VOL_SURGE_BEST:
                ratio = (vol_surge - VOL_SURGE_LOW) / (VOL_SURGE_BEST - VOL_SURGE_LOW)
            else:
                ratio = 1.0 - (vol_surge - VOL_SURGE_BEST) / (VOL_SURGE_HIGH - VOL_SURGE_BEST) * 0.5
            result["vol_surge_score"] = round(_clamp(ratio) * SCORE_VOL_SURGE_MAX, 2)

    recent10_amt = amt.tail(10).mean()
    prev20_amt = amt.iloc[-30:-10].mean()
    if pd.notna(recent10_amt) and pd.notna(prev20_amt) and prev20_amt > 0:
        amount_ratio = recent10_amt / prev20_amt
        if AMOUNT_STABILITY_LOW <= amount_ratio <= AMOUNT_STABILITY_HIGH:
            ratio = (amount_ratio - AMOUNT_STABILITY_LOW) / (AMOUNT_STABILITY_HIGH - AMOUNT_STABILITY_LOW)
            result["amount_stability_score"] = round(_clamp(ratio) * SCORE_AMOUNT_STABILITY_MAX, 2)

    ret_3d = close.iloc[-1] / close.iloc[-4] - 1 if close.iloc[-4] > 0 else np.nan
    ret_10d = close.iloc[-1] / close.iloc[-11] - 1 if close.iloc[-11] > 0 else np.nan
    recent3_vol = vol.tail(3).mean()
    prev7_vol = vol.iloc[-10:-3].mean()
    if (
        pd.notna(ret_3d)
        and pd.notna(ret_10d)
        and pd.notna(recent3_vol)
        and pd.notna(prev7_vol)
        and prev7_vol > 0
    ):
        if ret_10d > 0 and -0.05 <= ret_3d <= 0.02 and recent3_vol <= prev7_vol * 0.9:
            result["pullback_volume_score"] = SCORE_PULLBACK_VOLUME_MAX
        elif ret_10d > 0 and recent3_vol <= prev7_vol:
            result["pullback_volume_score"] = round(SCORE_PULLBACK_VOLUME_MAX * 0.5, 2)

    raw_total = (
        result["vol_surge_score"]
        + result["amount_stability_score"]
        + result["pullback_volume_score"]
    )
    result["volume_price_total"] = round(
        raw_total * 25.0 / (SCORE_VOL_SURGE_MAX + SCORE_AMOUNT_STABILITY_MAX + SCORE_PULLBACK_VOLUME_MAX),
        2,
    )
    return result


# ════════════════════════════════════════════════════════════
# 维度3：技术形态（20分）
# ════════════════════════════════════════════════════════════

def score_technical(df: pd.DataFrame) -> Dict[str, float]:
    """
    技术形态维度打分。

    波段思路：
      1. 均线由修复转顺，不追求当天暴拉
      2. MACD 关注修复和抬升
      3. 平台整理充分，比“今天突破”更重要
    """
    result = {
        "ma_trend_score": 0.0,
        "macd_score": 0.0,
        "platform_score": 0.0,
        "technical_total": 0.0,
    }
    if df is None or len(df) < 40:
        return result

    close = pd.to_numeric(df["close"], errors="coerce")
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    ma30 = close.rolling(30).mean()
    last_close = close.iloc[-1]

    if pd.notna(ma10.iloc[-1]) and pd.notna(ma20.iloc[-1]) and pd.notna(ma30.iloc[-1]):
        ma_distance = ma10.iloc[-1] / ma20.iloc[-1] - 1 if ma20.iloc[-1] > 0 else np.nan
        ma20_slope = ma20.iloc[-1] / ma20.iloc[-5] - 1 if pd.notna(ma20.iloc[-5]) and ma20.iloc[-5] > 0 else np.nan
        cond_stack = ma10.iloc[-1] >= ma20.iloc[-1] >= ma30.iloc[-1]
        cond_price = last_close >= ma10.iloc[-1] * 0.98
        if cond_stack and cond_price and pd.notna(ma20_slope) and ma20_slope > 0:
            if pd.notna(ma_distance) and MA_DISTANCE_LOW <= ma_distance <= MA_DISTANCE_HIGH:
                result["ma_trend_score"] = SCORE_MA_TREND_MAX
            else:
                result["ma_trend_score"] = round(SCORE_MA_TREND_MAX * 0.7, 2)
        elif ma10.iloc[-1] >= ma20.iloc[-1] and pd.notna(ma20_slope) and ma20_slope >= 0:
            result["ma_trend_score"] = round(SCORE_MA_TREND_MAX * 0.45, 2)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_bar = (dif - dea) * 2
    if len(macd_bar) >= 5:
        bar_tail = macd_bar.tail(5)
        bar_now = macd_bar.iloc[-1]
        if (dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]) or (bar_now > 0 and macd_bar.iloc[-2] <= 0):
            result["macd_score"] = SCORE_MACD_MAX
        elif bar_tail.is_monotonic_increasing and bar_now > bar_tail.iloc[0]:
            result["macd_score"] = round(SCORE_MACD_MAX * 0.7, 2)
        elif dif.iloc[-1] > dea.iloc[-1] and bar_now > 0:
            result["macd_score"] = round(SCORE_MACD_MAX * 0.5, 2)

    range_15 = close.tail(15)
    if len(range_15) == 15:
        high_15 = range_15.max()
        low_15 = range_15.min()
        range_ratio = (high_15 - low_15) / low_15 if low_15 > 0 else np.nan
        pos_15 = (last_close - low_15) / (high_15 - low_15) if high_15 > low_15 else 0.0
        if pd.notna(range_ratio):
            if range_ratio <= 0.12 and pos_15 >= 0.6:
                result["platform_score"] = SCORE_PLATFORM_MAX
            elif range_ratio <= 0.18 and pos_15 >= 0.5:
                result["platform_score"] = round(SCORE_PLATFORM_MAX * 0.6, 2)

    raw_total = result["ma_trend_score"] + result["macd_score"] + result["platform_score"]
    result["technical_total"] = round(
        raw_total * 20.0 / (SCORE_MA_TREND_MAX + SCORE_MACD_MAX + SCORE_PLATFORM_MAX),
        2,
    )
    return result


# ════════════════════════════════════════════════════════════
# 维度4：筹码结构（15分）
# ════════════════════════════════════════════════════════════

def score_chip_structure(df: pd.DataFrame) -> Dict[str, float]:
    """
    筹码结构维度打分。

    波段思路：
      1. 最近有缩量沉淀
      2. 波动率/振幅收窄，筹码趋稳
      3. 所处位置偏低位中枢，而不是高位末端
    """
    result = {
        "shrink_score": 0.0,
        "amp_narrow_score": 0.0,
        "position_score": 0.0,
        "chip_total": 0.0,
    }
    if df is None or len(df) < 60:
        return result

    close = pd.to_numeric(df["close"], errors="coerce")
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    vol = pd.to_numeric(df["volume"], errors="coerce")

    recent5_vol = vol.tail(5).mean()
    prev20_vol = vol.iloc[-25:-5].mean()
    if pd.notna(recent5_vol) and pd.notna(prev20_vol) and prev20_vol > 0:
        shrink_ratio = recent5_vol / prev20_vol
        if shrink_ratio <= SHRINK_RATIO_THRESHOLD:
            ratio = 1.0 - shrink_ratio / SHRINK_RATIO_THRESHOLD
            result["shrink_score"] = round(_clamp(ratio) * SCORE_SHRINK_EXPAND_MAX, 2)
        elif shrink_ratio <= 0.9:
            result["shrink_score"] = round(SCORE_SHRINK_EXPAND_MAX * 0.35, 2)

    recent10_high = high.iloc[-10:].max()
    recent10_low = low.iloc[-10:].min()
    prev30_high = high.iloc[-40:-10].max()
    prev30_low = low.iloc[-40:-10].min()
    amp_10d = (recent10_high - recent10_low) / recent10_low if recent10_low > 0 else np.nan
    amp_30d = (prev30_high - prev30_low) / prev30_low if prev30_low > 0 else np.nan
    if pd.notna(amp_10d) and pd.notna(amp_30d) and amp_30d > 0:
        narrow_ratio = amp_10d / amp_30d
        if narrow_ratio <= AMP_NARROW_RATIO:
            ratio = 1.0 - narrow_ratio / AMP_NARROW_RATIO
            result["amp_narrow_score"] = round(_clamp(ratio) * SCORE_AMP_NARROW_MAX, 2)
        elif narrow_ratio <= 0.8:
            result["amp_narrow_score"] = round(SCORE_AMP_NARROW_MAX * 0.4, 2)

    low_60d = close.iloc[-60:].min()
    high_60d = close.iloc[-60:].max()
    if high_60d > low_60d:
        pos = (close.iloc[-1] - low_60d) / (high_60d - low_60d)
        if POS_BEST_LOW <= pos <= POS_BEST_HIGH:
            result["position_score"] = SCORE_POSITION_MAX
        elif pos < POS_BEST_LOW:
            result["position_score"] = round(SCORE_POSITION_MAX * pos / POS_BEST_LOW * 0.6, 2)
        elif pos <= 0.7:
            ratio = 1.0 - (pos - POS_BEST_HIGH) / (0.7 - POS_BEST_HIGH)
            result["position_score"] = round(_clamp(ratio) * SCORE_POSITION_MAX * 0.8, 2)

    result["chip_total"] = round(
        result["shrink_score"] + result["amp_narrow_score"] + result["position_score"],
        2,
    )
    return result


# ════════════════════════════════════════════════════════════
# 综合打分
# ════════════════════════════════════════════════════════════

def score_stock(
    code: str,
    kline_df: pd.DataFrame,
    wind_df: Optional[pd.DataFrame],
    all_wind_data: Dict[str, pd.DataFrame],
    all_kline_data: Dict[str, pd.DataFrame],
    market_cap: float,
    is_st: bool = False,
    wind_available: bool = True,
) -> Dict[str, float]:
    """对单只股票进行综合打分。"""
    result = {"code": code}

    cap_scores = score_capital_flow(wind_df, all_wind_data, kline_df, all_kline_data)
    vol_scores = score_volume_price(kline_df)
    tech_scores = score_technical(kline_df)
    chip_scores = score_chip_structure(kline_df)

    result.update(cap_scores)
    result.update(vol_scores)
    result.update(tech_scores)
    result.update(chip_scores)

    has_wind_data = wind_df is not None and not wind_df.empty
    if wind_available and has_wind_data:
        total = (
            cap_scores["capital_flow_total"]
            + vol_scores["volume_price_total"]
            + tech_scores["technical_total"]
            + chip_scores["chip_total"]
        )
    else:
        vp_scale = (WEIGHT_VOLUME_PRICE + 18) / WEIGHT_VOLUME_PRICE
        chip_scale = (WEIGHT_CHIP + 12) / WEIGHT_CHIP
        total = (
            vol_scores["volume_price_total"] * vp_scale
            + tech_scores["technical_total"]
            + chip_scores["chip_total"] * chip_scale
        )

    result["total_score"] = round(total, 2)
    return result
