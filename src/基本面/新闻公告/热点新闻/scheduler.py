# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime, time, timedelta, timezone
from typing import Awaitable, Callable

UTC8 = timezone(timedelta(hours=8))


def is_market_open(at: datetime | None = None) -> bool:
    """判断 A 股是否开市 (工作日 09:30-11:30, 13:00-15:00, UTC+8)。"""
    now = (at or datetime.now(UTC8)).astimezone(UTC8)
    if now.weekday() >= 5:
        return False
    t = now.time()
    am_open = time(9, 30)
    am_close = time(11, 30)
    pm_open = time(13, 0)
    pm_close = time(15, 0)
    return (am_open <= t <= am_close) or (pm_open <= t <= pm_close)


def get_next_scan_time(at: datetime | None = None) -> datetime:
    """根据是否开市返回下一次扫描时间（开市每 15 分钟，其余每 2 小时）。"""
    now = (at or datetime.now(UTC8)).astimezone(UTC8)
    interval = timedelta(minutes=15) if is_market_open(now) else timedelta(hours=2)
    return now + interval


async def run_forever(scan_once: Callable[[], Awaitable[datetime]]) -> None:
    """以动态间隔循环运行。scan_once 需返回下一次扫描的时间戳。"""
    while True:
        try:
            next_time = await scan_once()
        except Exception:
            # 兜底：若本轮失败，按非开市节奏 2 小时后再试
            now = datetime.now(UTC8)
            next_time = now + timedelta(hours=2)
        now = datetime.now(UTC8)
        sleep_sec = max(5, int((next_time - now).total_seconds()))
        # 人类可读提示
        print(f"下次扫描：{next_time.astimezone(UTC8).strftime('%H:%M')}")
        try:
            # 精准睡眠
            from asyncio import sleep
            await sleep(sleep_sec)
        except Exception:
            pass
