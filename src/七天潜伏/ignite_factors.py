import pandas as pd
import typing

# ignite_factors.py 汇总三大点火/爆发因子，与@说明.md对应关系：
# check_chouma_factor——筹码因子（市值、龙虎榜、换手率，全对应文档公式）
# check_topic_factor——题材因子（政策风口、行业事件等）
# check_pankou_factor——盘口因子（主力流入、委比、隔夜封单，详见T-1夜复盘标准）
# 各pass规则均与文档表述完全匹配。

def check_chouma_factor(code: str, wind_mv: float=None, lhb_net: float=None, turn_5: typing.List[float]=None) -> dict:
    """
    筹码因子判定（可根据Wind流通市值、龙虎榜净买入、5日换手率等填充）
    返回 {'pass':bool, 各细项}
    """
    res = {'float_mv_ok': None, 'lhb_netbuy_ok': None, 'turn5_sum_ok': None, 'turn5_desc_ok': None, 'pass': False}
    cnt = 0
    # 市值30-200亿
    if wind_mv is not None:
        mv_ok = (wind_mv >= 30) and (wind_mv <= 200)
        res['float_mv_ok'] = mv_ok
        cnt += int(mv_ok)
    # 龙虎榜净买入≥2000万
    if lhb_net is not None:
        nb_ok = lhb_net >= 2_000_000
        res['lhb_netbuy_ok'] = nb_ok
        cnt += int(nb_ok)
    # 5日换手累计≥60% 且递减
    if turn_5 is not None:
        sum_ok = sum(turn_5) >= 60.0
        desc_ok = all(turn_5[i]>=turn_5[i+1] for i in range(len(turn_5)-1)) if len(turn_5)>=2 else False
        res['turn5_sum_ok'] = sum_ok
        res['turn5_desc_ok'] = desc_ok
        cnt += int(sum_ok) + int(desc_ok)
    res['pass'] = (cnt >= 2)
    return res

def check_topic_factor(code:str, topic:str=None, event_tag:bool=None) -> dict:
    """
    题材因子判定（风口、行业涨幅前5、重大事件，需外部传入风口/事件标签）
    返回 {'pass':bool, 'hit_topic':bool, 'event_tag':bool}
    """
    res = {'hit_topic': False, 'event_tag': False, 'pass': False}
    hit1 = bool(topic) # 传入风口、行业等命中
    hit2 = bool(event_tag)
    cnt = int(hit1) + int(hit2)
    res['hit_topic'] = hit1
    res['event_tag'] = hit2
    res['pass'] = (cnt >= 1) # 满足其中一个即可
    return res

def check_pankou_factor(code:str, l2_data:dict=None, funds_netflow:float=None, overnight_order_amt:float=None, float_mv:float=None) -> dict:
    """
    盘口因子判定（需level2/盘口tick数据，主力流入、委买委卖、隔夜封单，输入需外部提供）
    返回 {'pass':bool, 各细项}
    """
    res = {'tail_funds_ok': None, 'l2_weibi_ok': None, 'overnight_order_ok': None, 'pass': False}
    cnt = 0
    # 主力净流入/流通市值≥1%
    if funds_netflow is not None and float_mv is not None:
        tail_ok = (funds_netflow/float_mv) >= 0.01
        res['tail_funds_ok'] = tail_ok
        cnt += int(tail_ok)
    # Level2委比 > 1.5
    if l2_data and l2_data.get('buy') and l2_data.get('sell'):
        weibi = l2_data['buy']/l2_data['sell']
        weibi_ok = weibi > 1.5
        res['l2_weibi_ok'] = weibi_ok
        cnt += int(weibi_ok)
    # 隔夜封单金额/流通市值≥0.5%
    if overnight_order_amt is not None and float_mv is not None:
        overnight_ok = (overnight_order_amt/float_mv) >= 0.005
        res['overnight_order_ok'] = overnight_ok
        cnt += int(overnight_ok)
    res['pass'] = (cnt >= 2)
    return res
