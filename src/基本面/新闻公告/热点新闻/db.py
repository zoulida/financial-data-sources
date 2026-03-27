# -*- coding: utf-8 -*-
"""
SQLite 持久化层
- 数据库文件: 位于当前目录 hotnews.db
- 表结构:
  hot_raw(扫描批次, 平台, 标题, 热度 JSON, 抓取时间, 首发时间)
  hot_score(标题, S, T, A, M, 下次更新时间)

说明:
- 为兼容 Windows，优先使用标准库 sqlite3；若环境缺失，回退到 pysqlite3。
- 提供写入与查询接口，供主流程调用。
"""
from __future__ import annotations
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone, timedelta

# 兼容 sqlite3
try:
    import sqlite3  # 标准库
except Exception:  # pragma: no cover
    from pysqlite3 import dbapi2 as sqlite3  # 兜底方案

# 常量
UTC8 = timezone(timedelta(hours=8))
DB_FILE = os.path.join(os.path.dirname(__file__), 'hotnews.db')


def get_conn(db_path: str = DB_FILE) -> sqlite3.Connection:
    """获取 SQLite 连接，设置 row factory。"""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """初始化表结构和索引。"""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hot_raw (
            batch_id TEXT,
            platform TEXT,
            title TEXT,
            metrics_json TEXT,
            fetched_at TEXT,
            pub_time TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_hot_raw_title ON hot_raw(title);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_hot_raw_batch ON hot_raw(batch_id);
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hot_score (
            title TEXT PRIMARY KEY,
            S REAL,
            T REAL,
            A REAL,
            M REAL,
            next_update_at TEXT
        )
        """
    )
    conn.commit()


def insert_hot_raw_many(
    conn: sqlite3.Connection,
    batch_id: str,
    rows: list[tuple[str, str, str, str, str]]
) -> None:
    """批量插入 hot_raw。

    :param rows: 列表元素为 (platform, title, metrics_json, fetched_at, pub_time)
    """
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO hot_raw(batch_id, platform, title, metrics_json, fetched_at, pub_time)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [(batch_id, p, t, m, fa, pt) for (p, t, m, fa, pt) in rows]
    )
    conn.commit()


def upsert_hot_score(
    conn: sqlite3.Connection,
    title: str,
    s: float,
    t: float,
    a: float,
    m: float,
    next_update_at: datetime,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO hot_score(title, S, T, A, M, next_update_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(title) DO UPDATE SET
            S=excluded.S,
            T=excluded.T,
            A=excluded.A,
            M=excluded.M,
            next_update_at=excluded.next_update_at
        """,
        (
            title,
            float(s) if s is not None else None,
            float(t) if t is not None else None,
            float(a) if a is not None else None,
            float(m) if m is not None else None,
            next_update_at.astimezone(UTC8).strftime('%Y-%m-%d %H:%M:%S'),
        ),
    )
    conn.commit()


def get_prev_metric_value(
    conn: sqlite3.Connection,
    title: str,
    platform: str,
    key: str,
    minutes_back: int = 60,
) -> tuple[float | int | None, datetime | None]:
    """获取指定标题在指定平台的某 JSON 指标在约 1 小时前的值。

    策略：取 (当前时间 - minutes_back) 之前最近的一条记录；若不存在则返回 (None, None)。
    """
    target_ts = datetime.now(UTC8) - timedelta(minutes=minutes_back)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT metrics_json, fetched_at FROM hot_raw
        WHERE title=? AND platform=? AND fetched_at<=?
        ORDER BY fetched_at DESC LIMIT 1
        """,
        (title, platform, target_ts.strftime('%Y-%m-%d %H:%M:%S')),
    )
    row = cur.fetchone()
    if not row:
        return None, None
    try:
        data = json.loads(row['metrics_json'] or '{}')
        val = data.get(key)
        ts = datetime.strptime(row['fetched_at'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=UTC8)
        return val, ts
    except Exception:
        return None, None


def get_earliest_pub_time(conn: sqlite3.Connection, title: str) -> datetime | None:
    """查询历史上该标题最早的 pub_time（如果没有则返回 None）。"""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT MIN(pub_time) AS min_pt FROM hot_raw WHERE title=?
        """,
        (title,),
    )
    row = cur.fetchone()
    if not row or not row['min_pt']:
        return None
    try:
        return datetime.strptime(row['min_pt'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=UTC8)
    except Exception:
        return None


def now_utc8() -> datetime:
    return datetime.now(UTC8)
