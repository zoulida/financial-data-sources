import pandas as pd
import numpy as np
from typing import Dict

# === 七天潜伏量价型基础过滤 ===
# 实现逻辑见@说明.md【一】【二】部分，映射如下：
# （1）近20日内至少有一次实体涨停且距今<=13天
# （2）调整回撤<=15%，且不破涨停日开盘价（洗盘不破低）
# （3）调整天数3-7天（横盘/洗盘充分）
# （4）回踩区间"阳多阴少"、实体跌幅<4%（形态优）
# （5）有缩量十字星/小阴线，量能<=涨停日半量（筹码交换衰竭）
# （6）20日均线上穿、多头，最后价仍站上MA20
# 满足全部条件result["pass"]为True
def seven_day_lurk_base_filter(df: pd.DataFrame) -> Dict:
    """
    满足核心“7天潜伏”量价过滤，返回详细命中项。
    """
    result = {
        'pass': False,
        'hit_recent_limit_up': False,
        'last_limit_idx': None,
        'days_since_limit': None,
        'pullback_ok': False,
        'adjust_days': None,
        'shape_ok': False,
        'small_star_ok': False,
        'ma20_ok': False,
    }
    if df is None or len(df) < 25:
        return result
    df = df.copy()
    # 处理时间与涨停标记
    df['pct_chg'] = df['close'].pct_change() * 100
    df['is_limit'] = (df['pct_chg'] >= 9.8) & (np.abs(df['close'] - df['high']) < df['close'] * 0.002)
    recent20 = df.iloc[-20:]
    limit_idx = recent20.index[recent20['is_limit']].tolist()
    if not limit_idx:
        return result
    last_limit = limit_idx[-1]
    last_limit_index = df.index.get_loc(last_limit)
    days_since = len(df) - 1 - last_limit_index
    result['hit_recent_limit_up'] = (days_since <= 13)
    result['last_limit_idx'] = last_limit_index
    result['days_since_limit'] = days_since
    # 调整天数: 涨停后到今天是3-7天
    if 3 <= days_since <= 7:
        result['adjust_days'] = days_since
    else:
        return result
    # 调整深度
    adj_window = df.iloc[last_limit_index+1:]
    if adj_window.empty:
        return result
    # 回撤至今最低价
    high = df.loc[last_limit, 'high']
    open_ = df.loc[last_limit, 'open']
    pullback_low = adj_window['low'].min()
    pullback_depth = (high-pullback_low)/high if high>0 else 1
    result['pullback_ok'] = (pullback_depth <= 0.15 and pullback_low >= open_)
    if not result['pullback_ok']:
        return result
    # 量价形态
    win = adj_window.copy()
    win = win.iloc[:days_since] if len(win) >= days_since else win
    body_down = ((win['open'] - win['close'])/win['open']).fillna(0)
    reds = (win['close'] >= win['open']).sum()
    greens = (win['close'] < win['open']).sum()
    # 新增：拆分判断量价形态的两个子条件
    body_small_ok = (body_down < 0.04).all()  # 每日实体跌幅小于4%
    more_reds_ok = (reds >= greens)           # 回调区间“阳多阴少”
    result['body_small_ok'] = body_small_ok
    result['more_reds_ok'] = more_reds_ok
    shape_ok = body_small_ok and more_reds_ok
    result['shape_ok'] = shape_ok
    # 缩量十字星/小阴线
    limit_vol = df.loc[last_limit, 'volume']
    small_star = (
        ((win['close']-win['open']).abs() <= win['open']*0.005) | (win['close']<=win['open'])
    ) & (win['volume'] <= max(1.0, 0.5*limit_vol))
    result['small_star_ok'] = small_star.any()
    # MA20趋势 
    df['ma20'] = df['close'].rolling(20).mean()
    ma20_ok = (df['ma20'].iloc[-1] > df['ma20'].iloc[-2]) if not np.isnan(df['ma20'].iloc[-2]) else False
    price_above = df['close'].iloc[-1] >= df['ma20'].iloc[-1] if not np.isnan(df['ma20'].iloc[-1]) else False
    result['ma20_ok'] = (ma20_ok and price_above)
    # 最终通过：满足上述6项中的至少5项即为True
    checks = [
        result['hit_recent_limit_up'],
        result['pullback_ok'],
        result['body_small_ok'],   # 每日实体跌幅<4%
        result['more_reds_ok'],    # 阳多于阴
        result['small_star_ok'],
        result['ma20_ok']
    ]
    result['pass'] = sum(bool(x) for x in checks) >= 5
    return result
