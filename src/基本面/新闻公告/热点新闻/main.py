# -*- coding: utf-8 -*-
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timedelta, timezone
import os
import sys
from typing import List, Dict, Any

from colorama import init as colorama_init

from crawler import Crawler, HotItem
from db import get_conn, init_db, insert_hot_raw_many, upsert_hot_score, now_utc8
from scorer import dedup_and_score, print_scored_events
import scheduler

UTC8 = timezone(timedelta(hours=8))


def _batch_id() -> str:
    return now_utc8().strftime('%Y%m%d_%H%M%S')


def _now_str() -> str:
    return now_utc8().strftime('%Y-%m-%d %H:%M:%S')


def _item_metrics_dict(it: HotItem) -> Dict[str, Any]:
    extra = it.extra or {}
    return {
        'current_hot': extra.get('current_hot'),  # 微博热度（用于 1h 增量差分）
        'video_24h': it.video_24h,
        'search_ratio': it.search_ratio,
        'follow_cnt': it.follow_cnt,
        'article_10w_plus': it.article_10w_plus,
        'answers': extra.get('answers'),
        'source_url': it.source_url,
        'platform': it.platform,
    }


async def run_once(conn, crawler: Crawler) -> datetime:
    batch = _batch_id()
    now_str = _now_str()

    items: List[HotItem] = await crawler.fetch_all()

    # 写入 raw
    rows = []
    for it in items:
        metrics_json = json.dumps(_item_metrics_dict(it), ensure_ascii=False)
        pub_time = it.pub_time or now_str
        rows.append((it.platform, it.title, metrics_json, now_str, pub_time))
    if rows:
        insert_hot_raw_many(conn, batch, rows)

    # 去重 + 评分
    events = dedup_and_score(conn, items)
    print_scored_events(events)

    # 计算下次更新
    next_time = scheduler.get_next_scan_time()

    # 写入 score
    for ev in events:
        upsert_hot_score(conn, ev.title, ev.S, ev.T, ev.A, ev.M, next_time)

    return next_time


async def main_async() -> None:
    colorama_init(autoreset=True)
    conn = get_conn()
    init_db(conn)
    crawler = Crawler()

    async def _scan_once_wrapper() -> datetime:
        return await run_once(conn, crawler)

    await scheduler.run_forever(_scan_once_wrapper)


if __name__ == '__main__':
    # Windows 控制台中文输出 UTF-8
    try:
        if os.name == 'nt':
            os.system('chcp 65001 > nul')
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
    asyncio.run(main_async())
