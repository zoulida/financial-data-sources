# -*- coding: utf-8 -*-
from __future__ import annotations
import asyncio
import json
import random
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

UTC8 = timezone(timedelta(hours=8))


@dataclass
class HotItem:
    """统一热点结构"""
    title: str
    platform: str  # weibo/douyin/kuaishou/baidu/zhihu/gsdata
    read_inc_1h: Optional[float] = None  # 微博 1h 阅读增量（通过 DB 差分计算，初次抓取为当前读数）
    video_24h: Optional[int] = None      # 抖音/快手 24h 视频数
    search_ratio: Optional[float] = None # 百度指数环比（如 1.8 代表 +180%）
    follow_cnt: Optional[int] = None     # 知乎关注数
    article_10w_plus: Optional[int] = None  # 清博 10w+ 文章数量
    pub_time: Optional[str] = None       # UTC+8 字符串格式 'YYYY-MM-DD HH:MM:SS'
    source_url: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class Crawler:
    """并发爬虫：限 20 连接，UA 池化，重试 + 1~3s 随机延迟"""

    UA_POOL = [
        # 常见桌面浏览器 UA
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    ]

    def __init__(self, timeout: int = 15):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.connector = aiohttp.TCPConnector(limit=20, ssl=False)
        self.sem = asyncio.Semaphore(20)

    @staticmethod
    def now_str() -> str:
        return datetime.now(UTC8).strftime('%Y-%m-%d %H:%M:%S')

    async def _fetch_json(self, session: aiohttp.ClientSession, url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, retry: int = 3) -> Optional[Dict[str, Any]]:
        for i in range(retry):
            try:
                await asyncio.sleep(random.uniform(1, 3))
                h = {"User-Agent": random.choice(self.UA_POOL), "Accept": "application/json, text/plain, */*"}
                if headers:
                    h.update(headers)
                async with self.sem:
                    async with session.get(url, headers=h, params=params) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            try:
                                return json.loads(text)
                            except json.JSONDecodeError:
                                # 某些接口返回 JSONP 或非严格 JSON
                                m = re.search(r"\{.*\}", text, re.S)
                                if m:
                                    return json.loads(m.group(0))
                        elif resp.status in (403, 429):
                            await asyncio.sleep(1.5 * (i + 1))
                        else:
                            await asyncio.sleep(0.6)
            except Exception:
                await asyncio.sleep(0.8 * (i + 1))
        return None

    async def _fetch_text(self, session: aiohttp.ClientSession, url: str, headers: Optional[Dict[str, str]] = None, retry: int = 3) -> Optional[str]:
        for i in range(retry):
            try:
                await asyncio.sleep(random.uniform(1, 3))
                h = {"User-Agent": random.choice(self.UA_POOL)}
                if headers:
                    h.update(headers)
                async with self.sem:
                    async with session.get(url, headers=h) as resp:
                        if resp.status == 200:
                            return await resp.text()
                        elif resp.status in (403, 429):
                            await asyncio.sleep(1.5 * (i + 1))
                        else:
                            await asyncio.sleep(0.6)
            except Exception:
                await asyncio.sleep(0.8 * (i + 1))
        return None

    async def fetch_weibo(self, session: aiohttp.ClientSession, topn: int = 50) -> List[HotItem]:
        """微博热搜榜 (尝试官方侧边接口)"""
        url = "https://weibo.com/ajax/side/hotSearch"
        data = await self._fetch_json(session, url, headers={"Referer": "https://s.weibo.com/top/summary"})
        items: List[HotItem] = []
        if not data:
            return items
        realtime = data.get("data", {}).get("realtime", [])
        for obj in realtime[:topn]:
            title = obj.get("word", "").strip()
            hot_val = obj.get("num")
            try:
                hot_num = float(hot_val) if hot_val is not None else None
            except Exception:
                hot_num = None
            items.append(HotItem(
                title=title,
                platform="weibo",
                read_inc_1h=hot_num,  # 先写入当前热度，后续通过 DB 差分计算增量
                video_24h=None,
                search_ratio=None,
                follow_cnt=None,
                article_10w_plus=None,
                pub_time=self.now_str(),
                source_url=f"https://s.weibo.com/weibo?q={title}",
                extra={"current_hot": hot_num}
            ))
        return items

    async def fetch_baidu(self, session: aiohttp.ClientSession, topn: int = 50) -> List[HotItem]:
        """百度实时热点"""
        url_json = "https://top.baidu.com/api/board"
        params = {"platform": "pc", "tab": "realtime"}
        data = await self._fetch_json(session, url_json, params=params, headers={"Referer": "https://top.baidu.com/board?tab=realtime"})
        items: List[HotItem] = []
        now = self.now_str()
        if data and isinstance(data.get("data"), dict):
            for card in data["data"].get("cards", [])[:topn]:
                for content in card.get("content", [])[:topn]:
                    title = content.get("word", "").strip() or content.get("query", "").strip()
                    ratio = None
                    try:
                        ratio = float(content.get("heatChange", 0))  # 可能是环比百分比(如 1.8)
                    except Exception:
                        pass
                    url = content.get("url") or content.get("appUrl")
                    items.append(HotItem(
                        title=title,
                        platform="baidu",
                        read_inc_1h=None,
                        video_24h=None,
                        search_ratio=ratio,  # 若为空，下游按 0 处理
                        follow_cnt=None,
                        article_10w_plus=None,
                        pub_time=now,
                        source_url=url,
                        extra={"raw": content}
                    ))
            return items[:topn]
        # 兜底：解析 HTML（弱匹配）
        html = await self._fetch_text(session, "https://top.baidu.com/board?tab=realtime")
        if not html:
            return items
        titles = re.findall(r"class=\"c-single-text-ellipsis\">([^<]+)<", html)
        for t in titles[:topn]:
            items.append(HotItem(
                title=t.strip(), platform="baidu", pub_time=now,
                source_url="https://top.baidu.com/board?tab=realtime"
            ))
        return items

    async def fetch_zhihu(self, session: aiohttp.ClientSession, topn: int = 50) -> List[HotItem]:
        """知乎热榜"""
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
        params = {"limit": topn}
        data = await self._fetch_json(session, url, params=params, headers={"Referer": "https://www.zhihu.com/hot"})
        items: List[HotItem] = []
        now = self.now_str()
        if not data:
            return items
        for it in data.get("data", [])[:topn]:
            target = it.get("target", {})
            title = target.get("title") or target.get("question", {}).get("title") or ""
            follower = None
            answer_cnt = None
            # metricsArea 里可能出现“xx 万关注”
            metrics_text = (it.get("detail_text") or it.get("metrics_area", {}).get("text") or "")
            m_f = re.search(r"(\d+[\.,]?\d*)\s*万?关注", metrics_text)
            if m_f:
                try:
                    val = float(m_f.group(1).replace(",", ""))
                    if "万" in metrics_text:
                        val *= 10000
                    follower = int(val)
                except Exception:
                    pass
            # 回答数
            m_a = re.search(r"(\d+[\.,]?\d*)\s*回答", metrics_text)
            if m_a:
                try:
                    answer_cnt = int(float(m_a.group(1).replace(",", "")))
                except Exception:
                    pass
            url_q = target.get("url") or target.get("question", {}).get("url")
            if url_q and url_q.startswith("/question/"):
                url_q = "https://www.zhihu.com" + url_q
            items.append(HotItem(
                title=(title or "").strip(),
                platform="zhihu",
                read_inc_1h=None,
                video_24h=None,
                search_ratio=None,
                follow_cnt=follower,
                article_10w_plus=None,
                pub_time=now,
                source_url=url_q,
                extra={"answers": answer_cnt}
            ))
        return items

    async def fetch_gsdata(self, session: aiohttp.ClientSession, topn: int = 50) -> List[HotItem]:
        """清博指数 10w+ 爆款文章标题 & 阅读量（公开页解析，尽力而为）"""
        url = "https://www.gsdata.cn/rank/rankLive"
        html = await self._fetch_text(session, url, headers={"Referer": url})
        items: List[HotItem] = []
        now = self.now_str()
        if not html:
            return items
        # 朴素解析：标题、10万+ 标记
        # 可能的片段示例：<span class="readnum">10万+</span>
        blocks = re.findall(r"<tr[\s\S]*?</tr>", html)
        cnt = 0
        for tr in blocks:
            if "10万+" in tr:
                title_m = re.search(r"title=\"([^\"]+)\"|<a[^>]*>([^<]{4,100})</a>", tr)
                title = (title_m.group(1) or title_m.group(2)).strip() if title_m else None
                if not title:
                    continue
                items.append(HotItem(
                    title=title,
                    platform="gsdata",
                    read_inc_1h=None,
                    video_24h=None,
                    search_ratio=None,
                    follow_cnt=None,
                    article_10w_plus=1,
                    pub_time=now,
                    source_url=url,
                ))
                cnt += 1
                if cnt >= topn:
                    break
        return items

    async def fetch_douyin(self, session: aiohttp.ClientSession, topn: int = 50) -> List[HotItem]:
        """抖音热点榜（公开接口尝试）。无法稳定获取时返回空列表。video_24h 在下游按 0 处理。"""
        # 官方热搜词榜（可能需要 Cookie，尽力）
        url = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"
        data = await self._fetch_json(session, url, headers={"Referer": "https://www.douyin.com/"})
        items: List[HotItem] = []
        now = self.now_str()
        if not data:
            return items
        words = data.get("word_list") or data.get("data") or []
        for w in words[:topn]:
            title = w.get("word") or w.get("name") or ""
            items.append(HotItem(
                title=title.strip(),
                platform="douyin",
                read_inc_1h=None,
                video_24h=None,  # 若后续能拿到 24h 视频条数，可放入 extra 并更新此字段
                search_ratio=None,
                follow_cnt=None,
                article_10w_plus=None,
                pub_time=now,
                source_url="https://www.douyin.com/search/" + title,
            ))
        return items

    async def fetch_kuaishou(self, session: aiohttp.ClientSession, topn: int = 50) -> List[HotItem]:
        """快手热点（公开页解析，尽力而为）。"""
        # 快手公开页较难直接抓取，这里抓首页发现页 HTML 作为候选，标题来自热门话题卡片
        url = "https://www.kuaishou.com/"
        html = await self._fetch_text(session, url, headers={"Referer": url})
        items: List[HotItem] = []
        now = self.now_str()
        if not html:
            return items
        # 粗糙匹配 #话题 文案，并进行清洗
        topics = re.findall(r"#[^#\s]{2,30}", html)
        seen = set()

        def clean_topic(s: str) -> Optional[str]:
            s = s.strip().strip('#').strip()
            if not s:
                return None
            # 过滤 HTML 实体/百分号编码/URL/脚本片段
            if re.search(r"&[#a-zA-Z0-9]+;", s):
                return None
            if re.search(r"%[0-9A-Fa-f]{2}", s):
                return None
            if 'http' in s.lower() or 'www.' in s.lower():
                return None
            if any(x in s for x in ['<', '>', '"', "'", ';', '{', '}', '(', ')']):
                return None
            # 仅保留中英数字及少量常见符号
            if not re.match(r"^[\u4e00-\u9fa5A-Za-z0-9\s\-+·（）()【】《》!?！？,.，。：:]{2,30}$", s):
                return None
            # 去掉首尾标点
            s = re.sub(r"^[，。.!？:：\s]+|[，。.!？:：\s]+$", "", s)
            if 2 <= len(s) <= 30:
                return s
            return None

        for t in topics:
            s = clean_topic(t)
            if not s or s in seen:
                continue
            seen.add(s)
            items.append(HotItem(
                title=s,
                platform="kuaishou",
                read_inc_1h=None,
                video_24h=None,
                search_ratio=None,
                follow_cnt=None,
                article_10w_plus=None,
                pub_time=now,
                source_url="https://www.kuaishou.com/search/video?searchKey=" + s,
            ))
            if len(items) >= topn:
                break
        return items

    async def fetch_all(self) -> List[HotItem]:
        """并发抓取所有平台，返回合并列表。"""
        async with aiohttp.ClientSession(timeout=self.timeout, connector=self.connector) as session:
            tasks = [
                self.fetch_weibo(session),
                self.fetch_baidu(session),
                self.fetch_zhihu(session),
                self.fetch_gsdata(session),
                self.fetch_douyin(session),
                self.fetch_kuaishou(session),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        items: List[HotItem] = []
        for res in results:
            if isinstance(res, Exception):
                continue
            items.extend(res or [])
        return items
