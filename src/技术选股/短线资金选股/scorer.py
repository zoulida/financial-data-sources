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
    SCORE_MFD_3D_MAX, SCORE_MFD_CLOSE_MAX, SCORE_MFD_RATE_MAX, SCORE_MFD_ACTIVE_MAX,
    # 量价异动
    VOL_RATIO_LOW, VOL_RATIO_BEST, VOL_RATIO_HIGH, SCORE_VOL_RATIO_MAX,
    TURN_ACCEL_LOW, TURN_ACCEL_HIGH, SCORE_TURN_ACCEL_MAX,
    AMT_RATIO_LOW, AMT_RATIO_HIGH, SCORE_AMT_RATIO_MAX,
    SCORE_VOL_PRICE_MAX,
    # 技术形态
    MOMENTUM_5D_BEST_LOW, MOMENTUM_5D_BEST_HIGH, SCORE_MOMENTUM_MAX,
    SCORE_MA_MULTI_MAX, SCORE_MACD_MAX, SCORE_BREAKOUT_MAX,
    # 筹码结构
    SCORE_SHRINK_EXPAND_MAX, AMP_NARROW_RATIO, SCORE_AMP_BREAKOUT_MAX,
    POS_BEST_LOW, POS_BEST_HIGH, SCORE_POSITION_MAX,
    # 基本面
    MCAP_BEST_LOW, MCAP_BEST_HIGH, MCAP_OK_LOW, SCORE_MCAP_MAX,
    MIN_AVG_AMOUNT_20D, SCORE_LIQUIDITY_MAX,
    MIN_LIST_DAYS, SCORE_SAFETY_MAX,
    # 权重
    WEIGHT_CAPITAL_FLOW, WEIGHT_VOLUME_PRICE, WEIGHT_TECHNICAL,
    WEIGHT_CHIP, WEIGHT_FUNDAMENTAL,
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


def _latest_amount(df: Optional[pd.DataFrame], offset: int = 0) -> float:
    """获取最近第 offset 天成交额。offset=0 表示最新，1 表示前一日。"""
    if df is None or "amount" not in df.columns:
        return np.nan
    amt = pd.to_numeric(df["amount"], errors="coerce").dropna()
    if len(amt) <= offset:
        return np.nan
    return float(amt.iloc[-1 - offset])


def _sum_amount(df: Optional[pd.DataFrame], window: int) -> float:
    """获取最近 window 天成交额累计。"""
    if df is None or "amount" not in df.columns:
        return np.nan
    amt = pd.to_numeric(df["amount"], errors="coerce").dropna().tail(window)
    if amt.empty:
        return np.nan
    return float(amt.sum())


# ════════════════════════════════════════════════════════════
# 维度1：资金流向（30分）
# ════════════════════════════════════════════════════════════

def score_capital_flow(wind_df: Optional[pd.DataFrame],
                       all_wind_data: Dict[str, pd.DataFrame],
                       kline_df: Optional[pd.DataFrame],
                       all_kline_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
    """
    资金流向维度打分。

    参数:
        wind_df: 单只股票的 Wind 资金流向 DataFrame (date + mfd字段)
        all_wind_data: 全池 Wind 数据，用于计算排名分位
        kline_df: 单只股票的日K线数据，用于成交额归一化
        all_kline_data: 全池日K线数据，用于成交额归一化后的横向比较

    返回:
        dict: 各子因子分数 + 维度总分
    """
    result = {
        "mfd_3d_score": 0.0,
        "mfd_close_score": 0.0,
        "mfd_rate_score": 0.0,
        "mfd_active_score": 0.0,
        "capital_flow_total": 0.0,
    }

    if wind_df is None or wind_df.empty:
        return result

    # ── 近3日主力净流入累计 ──
    mfd_col = "mfd_inflow_m"
    if mfd_col in wind_df.columns:
        recent3 = wind_df[mfd_col].dropna().tail(3)
        cum_3d = recent3.sum() if len(recent3) > 0 else 0.0
        amt_3d = _sum_amount(kline_df, 3)
        norm_cum_3d = cum_3d / amt_3d if pd.notna(amt_3d) and amt_3d > 0 else np.nan

        # 计算全池分位
        all_cum_3d = []
        for code, wdf in all_wind_data.items():
            if wdf is not None and mfd_col in wdf.columns:
                r3 = wdf[mfd_col].dropna().tail(3)
                raw_cum_3d = r3.sum() if len(r3) > 0 else 0.0
                kdf = all_kline_data.get(code)
                raw_amt_3d = _sum_amount(kdf, 3)
                all_cum_3d.append(raw_cum_3d / raw_amt_3d if pd.notna(raw_amt_3d) and raw_amt_3d > 0 else np.nan)
        all_series = pd.Series(all_cum_3d)
        result["mfd_3d_score"] = _percentile_score(norm_cum_3d, all_series, SCORE_MFD_3D_MAX)

    # ── 今日尾盘主力净流入 ──
    close_col = "mfd_inflow_close_m"
    if close_col in wind_df.columns:
        latest_close = wind_df[close_col].dropna().iloc[-1] if not wind_df[close_col].dropna().empty else 0.0
        latest_amt = _latest_amount(kline_df)
        norm_latest_close = latest_close / latest_amt if pd.notna(latest_amt) and latest_amt > 0 else np.nan
        all_close = []
        for code, wdf in all_wind_data.items():
            if wdf is not None and close_col in wdf.columns:
                v = wdf[close_col].dropna().iloc[-1] if not wdf[close_col].dropna().empty else 0.0
                kdf = all_kline_data.get(code)
                raw_amt = _latest_amount(kdf)
                all_close.append(v / raw_amt if pd.notna(raw_amt) and raw_amt > 0 else np.nan)
        result["mfd_close_score"] = _percentile_score(
            norm_latest_close, pd.Series(all_close), SCORE_MFD_CLOSE_MAX
        )

    # ── 主力净流入率 ──
    rate_col = "mfd_inflowrate_m"
    if rate_col in wind_df.columns:
        latest_rate = wind_df[rate_col].dropna().iloc[-1] if not wind_df[rate_col].dropna().empty else 0.0
        all_rate = []
        for code, wdf in all_wind_data.items():
            if wdf is not None and rate_col in wdf.columns:
                v = wdf[rate_col].dropna().iloc[-1] if not wdf[rate_col].dropna().empty else 0.0
                all_rate.append(v)
        result["mfd_rate_score"] = _percentile_score(
            latest_rate, pd.Series(all_rate), SCORE_MFD_RATE_MAX
        )

    # ── 净主动买入额 ──
    active_col = "mfd_netbuyamt_a"
    if active_col in wind_df.columns:
        latest_active = wind_df[active_col].dropna().iloc[-1] if not wind_df[active_col].dropna().empty else 0.0
        latest_amt = _latest_amount(kline_df)
        norm_latest_active = latest_active / latest_amt if pd.notna(latest_amt) and latest_amt > 0 else np.nan
        all_active = []
        for code, wdf in all_wind_data.items():
            if wdf is not None and active_col in wdf.columns:
                v = wdf[active_col].dropna().iloc[-1] if not wdf[active_col].dropna().empty else 0.0
                kdf = all_kline_data.get(code)
                raw_amt = _latest_amount(kdf)
                all_active.append(v / raw_amt if pd.notna(raw_amt) and raw_amt > 0 else np.nan)
        result["mfd_active_score"] = _percentile_score(
            norm_latest_active, pd.Series(all_active), SCORE_MFD_ACTIVE_MAX
        )

    result["capital_flow_total"] = round(
        result["mfd_3d_score"] + result["mfd_close_score"] +
        result["mfd_rate_score"] + result["mfd_active_score"], 2
    )
    return result


# ════════════════════════════════════════════════════════════
# 维度2：量价异动（25分）
# ════════════════════════════════════════════════════════════

def score_volume_price(df: pd.DataFrame) -> Dict[str, float]:
    """
    量价异动维度打分。基于日K线数据。

    参数:
        df: 日K线 DataFrame，需含 close/open/high/low/volume/amount 列
    """
    result = {
        "vol_ratio_score": 0.0,
        "turn_accel_score": 0.0,
        "amt_ratio_score": 0.0,
        "vol_price_score": 0.0,
        "volume_price_total": 0.0,
    }
    if df is None or len(df) < 25:
        return result

    vol = pd.to_numeric(df["volume"], errors="coerce")
    amt = pd.to_numeric(df["amount"], errors="coerce") if "amount" in df.columns else vol
    close = pd.to_numeric(df["close"], errors="coerce")
    open_ = pd.to_numeric(df["open"], errors="coerce")

    # ── 量比：今日成交量 / 20日均量 ──
    vol_ma20 = vol.rolling(20).mean()
    today_vol = vol.iloc[-1]
    ma20_val = vol_ma20.iloc[-2]  # 用前一日的20日均量（不含今日）
    if pd.notna(today_vol) and pd.notna(ma20_val) and ma20_val > 0:
        vr = today_vol / ma20_val
        if VOL_RATIO_LOW <= vr <= VOL_RATIO_HIGH:
            # 在 [LOW, BEST] 线性上升，[BEST, HIGH] 线性下降
            if vr <= VOL_RATIO_BEST:
                ratio = (vr - VOL_RATIO_LOW) / (VOL_RATIO_BEST - VOL_RATIO_LOW)
            else:
                ratio = 1.0 - (vr - VOL_RATIO_BEST) / (VOL_RATIO_HIGH - VOL_RATIO_BEST) * 0.5
            result["vol_ratio_score"] = round(_clamp(ratio) * SCORE_VOL_RATIO_MAX, 2)

    # ── 换手率加速：3日均量 / 20日均量 ──
    vol_ma3 = vol.rolling(3).mean()
    v3 = vol_ma3.iloc[-1]
    v20 = vol_ma20.iloc[-1]
    if pd.notna(v3) and pd.notna(v20) and v20 > 0:
        ta = v3 / v20
        if TURN_ACCEL_LOW <= ta <= TURN_ACCEL_HIGH:
            ratio = (ta - TURN_ACCEL_LOW) / (TURN_ACCEL_HIGH - TURN_ACCEL_LOW)
            result["turn_accel_score"] = round(_clamp(ratio) * SCORE_TURN_ACCEL_MAX, 2)

    # ── 成交额放大 ──
    amt_ma20 = amt.rolling(20).mean()
    today_amt = amt.iloc[-1]
    a20 = amt_ma20.iloc[-2]
    if pd.notna(today_amt) and pd.notna(a20) and a20 > 0:
        ar = today_amt / a20
        if AMT_RATIO_LOW <= ar <= AMT_RATIO_HIGH:
            ratio = (ar - AMT_RATIO_LOW) / (AMT_RATIO_HIGH - AMT_RATIO_LOW)
            result["amt_ratio_score"] = round(_clamp(ratio) * SCORE_AMT_RATIO_MAX, 2)

    # ── 量价配合 ──
    # 放量上涨（今日量 > 20日均量 且 收阳）
    is_up = close.iloc[-1] > open_.iloc[-1] if pd.notna(close.iloc[-1]) and pd.notna(open_.iloc[-1]) else False
    vol_expand = (pd.notna(today_vol) and pd.notna(ma20_val) and today_vol > ma20_val)
    if is_up and vol_expand:
        result["vol_price_score"] = SCORE_VOL_PRICE_MAX
    elif is_up and not vol_expand:
        # 缩量上涨，给一半分
        result["vol_price_score"] = round(SCORE_VOL_PRICE_MAX * 0.5, 2)
    elif not is_up and vol_expand:
        # 放量下跌，不加分
        result["vol_price_score"] = 0.0

    result["volume_price_total"] = round(
        result["vol_ratio_score"] + result["turn_accel_score"] +
        result["amt_ratio_score"] + result["vol_price_score"], 2
    )
    return result


# ════════════════════════════════════════════════════════════
# 维度3：技术形态（20分）
# ════════════════════════════════════════════════════════════

def score_technical(df: pd.DataFrame) -> Dict[str, float]:
    """
    技术形态维度打分。

    参数:
        df: 日K线 DataFrame
    """
    result = {
        "momentum_score": 0.0,
        "ma_multi_score": 0.0,
        "macd_score": 0.0,
        "breakout_score": 0.0,
        "technical_total": 0.0,
    }
    if df is None or len(df) < 30:
        return result

    close = pd.to_numeric(df["close"], errors="coerce")

    # ── 5日动量 ──
    if len(close) >= 6:
        ret_5d = close.iloc[-1] / close.iloc[-6] - 1 if close.iloc[-6] > 0 else 0
        if MOMENTUM_5D_BEST_LOW <= ret_5d <= MOMENTUM_5D_BEST_HIGH:
            # 在最优区间内线性打分
            ratio = (ret_5d - MOMENTUM_5D_BEST_LOW) / (MOMENTUM_5D_BEST_HIGH - MOMENTUM_5D_BEST_LOW)
            result["momentum_score"] = round(_clamp(ratio) * SCORE_MOMENTUM_MAX, 2)
        elif ret_5d > MOMENTUM_5D_BEST_HIGH:
            # 超出最优区间，给基础分后递减
            over = ret_5d - MOMENTUM_5D_BEST_HIGH
            result["momentum_score"] = round(max(0, SCORE_MOMENTUM_MAX * (1 - over / 0.10)), 2)

    # ── 均线多头：站上5日+10日MA ──
    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    last_close = close.iloc[-1]
    above_ma5 = last_close > ma5.iloc[-1] if pd.notna(ma5.iloc[-1]) else False
    above_ma10 = last_close > ma10.iloc[-1] if pd.notna(ma10.iloc[-1]) else False
    if above_ma5 and above_ma10:
        result["ma_multi_score"] = SCORE_MA_MULTI_MAX
    elif above_ma5:
        result["ma_multi_score"] = round(SCORE_MA_MULTI_MAX * 0.5, 2)

    # ── MACD状态 ──
    if len(close) >= 35:
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd_bar = (dif - dea) * 2

        bar_today = macd_bar.iloc[-1]
        bar_yest = macd_bar.iloc[-2]

        # 金叉：DIF上穿DEA
        dif_cross = (dif.iloc[-1] > dea.iloc[-1]) and (dif.iloc[-2] <= dea.iloc[-2])
        # 柱状线由负转正
        bar_turn_pos = (bar_today > 0) and (bar_yest <= 0)
        # 柱状线持续放大（正值增大）
        bar_expanding = (bar_today > 0) and (bar_today > bar_yest)

        if dif_cross or bar_turn_pos:
            result["macd_score"] = SCORE_MACD_MAX
        elif bar_expanding:
            result["macd_score"] = round(SCORE_MACD_MAX * 0.6, 2)

    # ── 突破整理：收盘价突破20日最高价 ──
    if len(close) >= 21:
        high_20d = close.iloc[-21:-1].max()  # 前20日（不含今日）的最高收盘价
        if pd.notna(high_20d) and last_close > high_20d:
            result["breakout_score"] = SCORE_BREAKOUT_MAX

    result["technical_total"] = round(
        result["momentum_score"] + result["ma_multi_score"] +
        result["macd_score"] + result["breakout_score"], 2
    )
    return result


# ════════════════════════════════════════════════════════════
# 维度4：筹码结构（15分）
# ════════════════════════════════════════════════════════════

def score_chip_structure(df: pd.DataFrame) -> Dict[str, float]:
    """
    筹码结构维度打分。

    参数:
        df: 日K线 DataFrame
    """
    result = {
        "shrink_expand_score": 0.0,
        "amp_breakout_score": 0.0,
        "position_score": 0.0,
        "chip_total": 0.0,
    }
    if df is None or len(df) < 60:
        return result

    close = pd.to_numeric(df["close"], errors="coerce")
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    vol = pd.to_numeric(df["volume"], errors="coerce")

    # ── 缩量后放量 ──
    vol_ma20 = vol.rolling(20).mean()
    vol_ma5_prev = vol.iloc[-6:-1].mean()  # 前5日均量（不含今日）
    today_vol = vol.iloc[-1]
    ma20_val = vol_ma20.iloc[-1]

    if (pd.notna(today_vol) and pd.notna(ma20_val) and pd.notna(vol_ma5_prev)
            and ma20_val > 0):
        # 条件：今日量 > 20日均量 且 前5日均量 < 20日均量（缩量蓄势后放量启动）
        if today_vol > ma20_val and vol_ma5_prev < ma20_val:
            expand_ratio = today_vol / ma20_val
            result["shrink_expand_score"] = round(
                min(1.0, (expand_ratio - 1.0) / 2.0) * SCORE_SHRINK_EXPAND_MAX, 2
            )

    # ── 振幅收窄后突破 ──
    if len(df) >= 40:
        # 近10日振幅
        recent10_high = high.iloc[-10:].max()
        recent10_low = low.iloc[-10:].min()
        amp_10d = (recent10_high - recent10_low) / recent10_low if recent10_low > 0 else 999

        # 前30日振幅（第11日到第40日）
        prev30_high = high.iloc[-40:-10].max()
        prev30_low = low.iloc[-40:-10].min()
        amp_30d = (prev30_high - prev30_low) / prev30_low if prev30_low > 0 else 999

        if amp_30d > 0 and amp_10d < amp_30d * AMP_NARROW_RATIO:
            # 振幅收窄，且今日放量
            if pd.notna(today_vol) and pd.notna(ma20_val) and today_vol > ma20_val:
                result["amp_breakout_score"] = SCORE_AMP_BREAKOUT_MAX

    # ── 底部位置 ──
    if len(close) >= 60:
        low_60d = close.iloc[-60:].min()
        high_60d = close.iloc[-60:].max()
        if high_60d > low_60d:
            pos = (close.iloc[-1] - low_60d) / (high_60d - low_60d)
            if POS_BEST_LOW <= pos <= POS_BEST_HIGH:
                # 低位启动区间，满分
                result["position_score"] = SCORE_POSITION_MAX
            elif pos < POS_BEST_LOW:
                # 太底部（可能还在下跌）
                result["position_score"] = round(SCORE_POSITION_MAX * pos / POS_BEST_LOW * 0.5, 2)
            elif pos <= 0.7:
                # 中位，递减
                ratio = 1.0 - (pos - POS_BEST_HIGH) / (0.7 - POS_BEST_HIGH)
                result["position_score"] = round(_clamp(ratio) * SCORE_POSITION_MAX * 0.7, 2)

    result["chip_total"] = round(
        result["shrink_expand_score"] + result["amp_breakout_score"] +
        result["position_score"], 2
    )
    return result


# ════════════════════════════════════════════════════════════
# 维度5：基本面安全垫（10分）
# ════════════════════════════════════════════════════════════

def score_fundamental(market_cap: float, df: pd.DataFrame,
                      is_st: bool = False) -> Dict[str, float]:
    """
    基本面安全垫打分。

    参数:
        market_cap: 流通市值（亿元）
        df: 日K线 DataFrame
        is_st: 是否ST股
    """
    result = {
        "mcap_score": 0.0,
        "liquidity_score": 0.0,
        "safety_score": 0.0,
        "fundamental_total": 0.0,
    }

    # ── 市值区间 ──
    if pd.notna(market_cap):
        if MCAP_BEST_LOW <= market_cap <= MCAP_BEST_HIGH:
            result["mcap_score"] = SCORE_MCAP_MAX
        elif MCAP_OK_LOW <= market_cap < MCAP_BEST_LOW:
            ratio = (market_cap - MCAP_OK_LOW) / (MCAP_BEST_LOW - MCAP_OK_LOW)
            result["mcap_score"] = round(ratio * SCORE_MCAP_MAX * 0.5, 2)

    # ── 流动性：20日日均成交额 ──
    if df is not None and "amount" in df.columns and len(df) >= 20:
        amt = pd.to_numeric(df["amount"], errors="coerce")
        avg_amt_20d = amt.tail(20).mean()
        if pd.notna(avg_amt_20d) and avg_amt_20d >= MIN_AVG_AMOUNT_20D:
            result["liquidity_score"] = SCORE_LIQUIDITY_MAX
        elif pd.notna(avg_amt_20d) and avg_amt_20d > 0:
            ratio = avg_amt_20d / MIN_AVG_AMOUNT_20D
            result["liquidity_score"] = round(_clamp(ratio) * SCORE_LIQUIDITY_MAX, 2)

    # ── 非ST/非新股 ──
    if not is_st:
        if df is not None and len(df) >= MIN_LIST_DAYS:
            result["safety_score"] = SCORE_SAFETY_MAX
        elif df is not None and len(df) >= 30:
            result["safety_score"] = round(SCORE_SAFETY_MAX * 0.5, 2)

    result["fundamental_total"] = round(
        result["mcap_score"] + result["liquidity_score"] + result["safety_score"], 2
    )
    return result


# ════════════════════════════════════════════════════════════
# 综合打分
# ════════════════════════════════════════════════════════════

def score_stock(code: str,
                kline_df: pd.DataFrame,
                wind_df: Optional[pd.DataFrame],
                all_wind_data: Dict[str, pd.DataFrame],
                all_kline_data: Dict[str, pd.DataFrame],
                market_cap: float,
                is_st: bool = False,
                wind_available: bool = True) -> Dict[str, float]:
    """
    对单只股票进行综合打分。

    参数:
        code: 股票代码
        kline_df: 日K线 DataFrame
        wind_df: Wind 资金流向 DataFrame (可为 None)
        all_wind_data: 全池 Wind 数据（用于排名分位）
        all_kline_data: 全池日K线数据（用于成交额归一化）
        market_cap: 流通市值（亿元）
        is_st: 是否ST
        wind_available: Wind 是否可用

    返回:
        dict: 包含各维度分数、总分、详情
    """
    result = {"code": code}

    # ── 各维度打分 ──
    cap_scores = score_capital_flow(wind_df, all_wind_data, kline_df, all_kline_data)
    vol_scores = score_volume_price(kline_df)
    tech_scores = score_technical(kline_df)
    chip_scores = score_chip_structure(kline_df)
    fund_scores = score_fundamental(market_cap, kline_df, is_st)

    result.update(cap_scores)
    result.update(vol_scores)
    result.update(tech_scores)
    result.update(chip_scores)
    result.update(fund_scores)

    # ── 总分计算 ──
    if wind_available and cap_scores["capital_flow_total"] > 0:
        # Wind 可用：正常权重
        total = (
            cap_scores["capital_flow_total"] +
            vol_scores["volume_price_total"] +
            tech_scores["technical_total"] +
            chip_scores["chip_total"] +
            fund_scores["fundamental_total"]
        )
    else:
        # Wind 不可用：资金流向30分重新分配到量价(+18)和筹码(+12)
        # 量价维度满分 25 → 43，筹码维度满分 15 → 27
        vp_scale = (WEIGHT_VOLUME_PRICE + 18) / WEIGHT_VOLUME_PRICE
        chip_scale = (WEIGHT_CHIP + 12) / WEIGHT_CHIP
        total = (
            vol_scores["volume_price_total"] * vp_scale +
            tech_scores["technical_total"] +
            chip_scores["chip_total"] * chip_scale +
            fund_scores["fundamental_total"]
        )

    result["total_score"] = round(total, 2)
    return result
