# -*- coding: utf-8 -*-
from __future__ import annotations
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from colorama import Fore, Style
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from db import get_prev_metric_value, now_utc8, get_earliest_pub_time
from crawler import HotItem

UTC8 = timezone(timedelta(hours=8))


@dataclass
class ScoredEvent:
    title: str
    S: float
    T: float
    A: float
    M: float
    metrics: Dict[str, Any]
    earliest_pub_time: Optional[datetime]


def _base_domain(netloc: str) -> str:
    parts = netloc.split(':')[0].split('.')
    if len(parts) >= 2:
        bd = '.'.join(parts[-2:])
    else:
        bd = netloc
    # 特例：*.gov.cn, *.edu.cn 等 3 级域名
    if bd.endswith('gov.cn') and len(parts) >= 3:
        bd = '.'.join(parts[-3:])
    return bd.lower()


def _authority_score(url: Optional[str]) -> float:
    if not url:
        return 0.7
    try:
        dom = _base_domain(urlparse(url).netloc)
    except Exception:
        return 0.7
    high = {
        'xinhuanet.com', 'reuters.com', 'bloomberg.com', 'gov.cn', 'mfa.gov.cn'
    }
    mid = {
        'people.com.cn', 'cctv.com', 'caixin.com', 'thepaper.cn'
    }
    if any(dom.endswith(x) for x in high):
        return 1.2
    if any(dom.endswith(x) for x in mid):
        return 1.0
    return 0.7


def _ln1p(x: float) -> float:
    try:
        return math.log1p(max(0.0, x))
    except Exception:
        return 0.0


def _fmt_k(v: float) -> str:
    if v is None:
        return '0k'
    return f"{int(round(v/1000.0))}k"


def _fmt_pct_int(rp: float) -> str:
    try:
        return f"{int(round(rp))}%"
    except Exception:
        return "0%"


def _color_for_s(s: float) -> str:
    if s >= 8:
        return Fore.GREEN
    if s >= 3:
        return Fore.YELLOW
    return Fore.RED


def _parse_time_str(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').replace(tzinfo=UTC8)
    except Exception:
        return None


def _compute_weibo_inc(conn, item: HotItem) -> float:
    if item.platform != 'weibo':
        return 0.0
    cur_hot = 0.0
    try:
        cur_hot = float((item.extra or {}).get('current_hot') or item.read_inc_1h or 0.0)
    except Exception:
        cur_hot = 0.0
    prev, _ts = get_prev_metric_value(conn, title=item.title, platform='weibo', key='current_hot', minutes_back=60)
    try:
        prev_val = float(prev) if prev is not None else None
    except Exception:
        prev_val = None
    if prev_val is None:
        return 0.0
    inc = max(0.0, cur_hot - prev_val)
    return inc


def dedup_and_score(conn, items: List[HotItem]) -> List[ScoredEvent]:
    titles = [it.title for it in items if it.title]
    if not titles:
        return []

    # TF-IDF (char 2-4gram) 适配中文
    vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 4))
    X = vectorizer.fit_transform(titles)
    sim = cosine_similarity(X)

    # 聚类（贪心）
    clusters: List[List[int]] = []
    visited = set()
    n = len(titles)
    for i in range(n):
        if i in visited:
            continue
        group = [i]
        visited.add(i)
        for j in range(i + 1, n):
            if j in visited:
                continue
            if sim[i, j] >= 0.75:
                group.append(j)
                visited.add(j)
        clusters.append(group)

    results: List[ScoredEvent] = []
    now = now_utc8()

    for group in clusters:
        group_items = [items[idx] for idx in group]
        # 确定代表标题：最早 pub_time 的那条
        def _item_time(it: HotItem) -> datetime:
            t = _parse_time_str(it.pub_time) or now
            return t
        group_items.sort(key=_item_time)
        rep = group_items[0]

        # 融合指标
        weibo_inc = 0.0
        dy_ks_video = 0
        baidu_ratio = 0.0
        zhihu_follow = 0
        qp_10w = 0
        earliest_pub = _parse_time_str(rep.pub_time) or now
        earliest_url = rep.source_url

        for it in group_items:
            # Earliest
            t = _parse_time_str(it.pub_time)
            if t and t < earliest_pub:
                earliest_pub = t
                earliest_url = it.source_url or earliest_url
            # 指标融合
            if it.platform == 'weibo':
                weibo_inc += _compute_weibo_inc(conn, it)
            if it.platform in ('douyin', 'kuaishou'):
                try:
                    dy_ks_video += int(it.video_24h or 0)
                except Exception:
                    pass
            if it.platform == 'baidu':
                try:
                    r = float(it.search_ratio or 0.0)
                    baidu_ratio = max(baidu_ratio, r)
                except Exception:
                    pass
            if it.platform == 'zhihu':
                try:
                    zhihu_follow = max(zhihu_follow, int(it.follow_cnt or 0))
                except Exception:
                    pass
            if it.platform == 'gsdata':
                try:
                    qp_10w += int(it.article_10w_plus or 0)
                except Exception:
                    pass

        # 历史最早首发时间（跨批次）
        try:
            hist_earliest = get_earliest_pub_time(conn, rep.title)
            if hist_earliest and hist_earliest < earliest_pub:
                earliest_pub = hist_earliest
        except Exception:
            pass

        # M 计算
        r_pct = baidu_ratio * 100 if baidu_ratio <= 10 else baidu_ratio
        M = (
            1.0
            + _ln1p(weibo_inc / 10000.0)
            + _ln1p(float(dy_ks_video))
            + _ln1p(float(max(0.0, r_pct)))
            + _ln1p(zhihu_follow / 100.0)
            + _ln1p(qp_10w * 3.0)
        )
        if M <= 0:
            M = 0.0001

        # T 计算（小时）
        if earliest_pub is None:
            T = 1.0
        else:
            diff_h = (now - earliest_pub).total_seconds() / 3600.0
            T = max(1.0, round(diff_h, 1))

        # A 计算
        A = _authority_score(earliest_url)

        # S 计算
        S = round((T * A) / M, 2)

        metrics = {
            'weibo_inc_1h': round(weibo_inc, 0),
            'video_24h_sum': int(dy_ks_video),
            'baidu_ratio_pct': float(r_pct),
            'zhihu_follow': int(zhihu_follow),
            'article_10w_plus': int(qp_10w),
            'source_url': earliest_url,
        }
        results.append(ScoredEvent(
            title=rep.title,
            S=S, T=float(T), A=float(A), M=float(round(M, 4)),
            metrics=metrics,
            earliest_pub_time=earliest_pub,
        ))

    # 按 S 降序
    results.sort(key=lambda x: x.S, reverse=True)
    return results


def print_scored_events(events: List[ScoredEvent]) -> None:
    for ev in events:
        weibo_k = _fmt_k(ev.metrics.get('weibo_inc_1h', 0.0))
        video_sum = ev.metrics.get('video_24h_sum', 0)
        r_pct = ev.metrics.get('baidu_ratio_pct', 0.0)
        zhihu = ev.metrics.get('zhihu_follow', 0)
        qp = ev.metrics.get('article_10w_plus', 0)

        color = _color_for_s(ev.S)
        now_str = now_utc8().strftime('%H:%M:%S')
        line = (
            f"{now_str}  S={ev.S:.2f}  T={ev.T:.1f}h  A={ev.A:.1f}  M={ev.M:.2f}  | "
            f"微博+{weibo_k} 抖音+{int(video_sum)} 百度+{_fmt_pct_int(r_pct)} 知乎+{int(zhihu)} 10w+{int(qp)}  | {ev.title}"
        )
        print(color + line + Style.RESET_ALL)
