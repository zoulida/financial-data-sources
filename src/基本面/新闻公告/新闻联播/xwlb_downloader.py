"""
新闻联播下载器
"""
import os
import re
import json
import time
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path

from .config import Config
from .utils import setup_logger, clean_text, extract_date_from_url, ensure_dir


class XWLBDownloader:
    """新闻联播文字版下载器"""
    
    def __init__(self, save_dir=None, logger=None):
        """
        初始化下载器
        
        Args:
            save_dir: 保存目录，默认为配置的数据目录
            logger: 日志记录器，默认为新建
        """
        # 初始化数据保存目录
        if save_dir is None:
            self.save_dir = Config.ensure_data_dir()
        else:
            self.save_dir = ensure_dir(save_dir)
        
        # 初始化日志记录器
        self.logger = logger or setup_logger('xwlb_downloader', 
                                            log_file=os.path.join(self.save_dir, 'download.log'))
        
        # 会话对象
        self.session = requests.Session()
        self.session.headers.update(Config.HEADERS)
        
        self.logger.info("新闻联播下载器初始化完成，保存目录：%s", self.save_dir)
    
    def _make_request(self, url, retry=3, timeout=10):
        """发送HTTP请求并获取响应"""
        for attempt in range(retry):
            try:
                self.logger.debug(f"正在请求 URL: {url}")
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                self.logger.warning(f"请求失败 ({attempt+1}/{retry}): {e}")
                if attempt < retry - 1:
                    time.sleep(2)  # 等待2秒后重试
                else:
                    self.logger.error(f"请求URL失败: {url}")
                    raise
    
    def get_daily_news_list(self, date=None):
        """
        获取指定日期的新闻列表
        
        Args:
            date: 日期字符串，格式为YYYYMMDD，默认为当天
            
        Returns:
            list: 新闻项列表
        """
        # 获取指定日期的视频列表页URL
        url = Config.get_video_list_url(date)
        self.logger.info(f"获取日期 {date or '今天'} 的新闻列表: {url}")
        
        try:
            response = self._make_request(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找包含新闻的列表
            news_list = []
            
            # 查找视频列表
            video_list = soup.select('.rilitop ul li a')
            if not video_list:
                video_list = soup.select('.image_list ul li a')  # 备选选择器
            
            for item in video_list:
                # 提取链接和标题
                link = item.get('href', '')
                title = item.text.strip() or item.get('title', '无标题')
                
                # 跳过非新闻联播项
                if '《新闻联播》' not in title and '新闻联播' not in title:
                    continue
                
                if link and title:
                    news_list.append({
                        'title': clean_text(title),
                        'url': link if link.startswith('http') else (Config.CCTV_URL.rstrip('/') + link)
                    })
            
            self.logger.info(f"找到 {len(news_list)} 条新闻联播")
            return news_list
            
        except Exception as e:
            self.logger.error(f"获取新闻列表失败: {e}")
            return []
    
    def get_news_content(self, news_url):
        """
        获取新闻内容
        
        Args:
            news_url: 新闻URL
            
        Returns:
            dict: 新闻内容字典
        """
        self.logger.info(f"获取新闻内容: {news_url}")
        
        try:
            response = self._make_request(news_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取标题
            title_elem = soup.select_one('title')
            if not title_elem:
                title_elem = soup.select_one('.ph_title_l') or soup.select_one('h1')
            title = title_elem.text.strip() if title_elem else "无标题"
            # 清理标题中的[视频]
            if title.startswith('[视频]'):
                title = title.replace('[视频]', '').strip()
            
            # 提取日期 - 优先从 .laiyuan 中提取“更新时间”
            date_elem = soup.select_one('.laiyuan')
            if date_elem:
                date_text = ' '.join(date_elem.get_text(separator=' ').split())
                import re
                # 兼容全角/半角冒号与可变空白，优先匹配“更新时间：YYYY年MM月DD日 HH:MM”
                upd_match = re.search(r'更新\s*时间\s*[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{2})', date_text)
                if upd_match:
                    date_str = f"{upd_match.group(1)}-{upd_match.group(2).zfill(2)}-{upd_match.group(3).zfill(2)} {upd_match.group(4).zfill(2)}:{upd_match.group(5)}"
                else:
                    # 退化匹配纯日期时间
                    date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{2})', date_text)
                    if date_match:
                        date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)} {date_match.group(4).zfill(2)}:{date_match.group(5)}"
                    else:
                        # 仍未匹配则保留原文本（可能是“来源：央视网”）
                        date_str = date_text
            else:
                # 如果没有找到日期，从URL或标题提取
                date_obj = extract_date_from_url(news_url)
                date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
            
            # 提取内容区域
            # 详情页（VIDE链接）优先 #content_area，其它页面再尝试 .video_brief
            prefer_detail = 'VIDE' in news_url
            content_elem = None
            if prefer_detail:
                content_elem = soup.select_one('#content_area')
                if not content_elem:
                    content_elem = soup.select_one('.video_brief')
            else:
                content_elem = soup.select_one('.video_brief')
                if not content_elem:
                    content_elem = soup.select_one('#content_area')
            if not content_elem:
                # 备选方案
                content_elem = soup.select_one('.cnt_bd') or soup.select_one('.text_con')
            
            # 处理内容
            paragraphs = []
            html_content = ''
            if content_elem:
                # 保留原始HTML，尽量接近网页段落结构
                html_content = content_elem.decode_contents().strip()
                # 同时提取纯文本段落
                text = content_elem.get_text(separator='\n').strip()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                paragraphs = lines
            else:
                # 兜底：遍历页面所有<p>
                for p in soup.select('p'):
                    text = p.text.strip()
                    if text and len(text) > 10:  # 过滤掉太短的内容
                        paragraphs.append(text)
            
            # 组装新闻数据
            news_data = {
                'title': title,
                'date': date_str,
                'url': news_url,
                'paragraphs': paragraphs,
                'content': '\n\n'.join(paragraphs),
                'html': html_content
            }
            
            self.logger.info(f"获取新闻内容成功: {title}")
            return news_data
            
        except Exception as e:
            self.logger.error(f"获取新闻内容失败: {e}")
            return {
                'title': '获取失败',
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'url': news_url,
                'paragraphs': [],
                'content': f'获取内容失败: {str(e)}'
            }
    
    def get_day_links(self, date_str):
        """
        从当日列表页提取节目页与分条链接（仿照原仓库做法：收集所有 <a> href，去重后第一个为节目页，之后为分条）
        返回: (program_url, segment_links)
        """
        url = Config.get_video_list_url(date_str)
        self.logger.info(f"从当日列表页提取链接: {url}")
        try:
            resp = self._make_request(url)
            soup = BeautifulSoup(resp.content, 'html.parser')
            anchors = soup.find_all('a', href=True)
            raw_links = []
            for a in anchors:
                href = a['href'].strip()
                if not href:
                    continue
                # 统一链接
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://tv.cctv.com' + href
                if href not in raw_links:
                    raw_links.append(href)
            if not raw_links:
                self.logger.info("当日列表页未提取到任何链接")
                return None, []
            # 第一个当做节目页，其余为分条候选
            program_url = raw_links[0]
            # 仅保留 tv.cctv.com 上的 VIDE*.shtml 作为分条
            import re
            segment_links = []
            for link in raw_links[1:]:
                if ('tv.cctv.com' in link) and re.search(r'/\d{4}/\d{2}/\d{2}/VIDE[\w]+\.shtml$', link):
                    segment_links.append(link)
            self.logger.info(f"当日列表页：节目页={program_url}, 分条={len(segment_links)} 条")
            return program_url, segment_links
        except Exception as e:
            self.logger.error(f"当日列表页提取失败: {e}")
            return None, []

    def get_news_details_list(self, news_links):
        """
        获取多条新闻的详细内容
        
        Args:
            news_links: 新闻链接列表
            
        Returns:
            list: 新闻详情列表
        """
        self.logger.info(f"开始获取 {len(news_links)} 条新闻的详细内容")
        news_details = []
        
        for i, link in enumerate(news_links, 1):
            try:
                self.logger.info(f"正在获取第 {i}/{len(news_links)} 条新闻")
                news_data = self.get_news_content(link)
                news_details.append(news_data)
                time.sleep(0.5)  # 避免请求过快
            except Exception as e:
                self.logger.error(f"获取新闻失败: {link}, 错误: {e}")
                continue
        
        return news_details
    
    def extract_segment_links(self, program_url):
        """从节目页提取分条新闻链接（VIDE*.shtml）"""
        self.logger.info(f"从节目页提取分条新闻链接: {program_url}")
        try:
            resp = self._make_request(program_url)
            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            import re
            # 1) 在完整HTML中用正则扫描所有 VIDE*.shtml 链接（绝对/协议相对/相对）
            patterns = [
                r'https?://tv\.cctv\.com/\d{4}/\d{2}/\d{2}/VIDE[\w]+\.shtml',
                r'//tv\.cctv\.com/\d{4}/\d{2}/\d{2}/VIDE[\w]+\.shtml',
                r'/\d{4}/\d{2}/\d{2}/VIDE[\w]+\.shtml',
            ]
            for pat in patterns:
                for m in re.findall(pat, html):
                    href = m
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        href = 'https://tv.cctv.com' + href
                    links.append(href)
            # 2) 作为补充：遍历 <a> 标签
            for a in soup.find_all('a', href=True):
                raw = a['href']
                href = raw.strip()
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://tv.cctv.com' + href
                if re.search(r'/\d{4}/\d{2}/\d{2}/VIDE[\w]+\.shtml$', href) and 'tv.cctv.com' in href:
                    links.append(href)
            # 去重并保持顺序
            seen = set()
            ordered = []
            for u in links:
                if u not in seen:
                    ordered.append(u)
                    seen.add(u)
            self.logger.info(f"提取到 {len(ordered)} 条分条链接")
            return ordered
        except Exception as e:
            self.logger.error(f"提取分条链接失败: {e}")
            return []

    def search_segments_by_cctv(self, date_str):
        """
        通过央视站内搜索按日期聚合分条链接。
        1) 尝试 JSON 接口 ifsearch.php（若可用）
        2) 解析 HTML 搜索结果页，使用正则提取当日 VIDE*.shtml 链接
        返回：去重后的分条链接列表
        """
        from urllib.parse import quote
        y, m, d = date_str[:4], date_str[4:6], date_str[6:8]
        cn_date = f"{y}年{int(m)}月{int(d)}日"
        keywords = f"新闻联播 {cn_date}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        }
        links = []
        try:
            # 1) JSON风格接口（有的时期可用）
            json_url = f"https://search.cctv.com/ifsearch.php?page=1&qtext={quote(keywords)}&type=video&sort=date"
            self.logger.info(f"尝试央视JSON搜索: {json_url}")
            r = requests.get(json_url, headers=headers, timeout=10)
            if r.ok:
                try:
                    data = r.json()
                    for item in data.get('list', []) or data.get('result', []) or []:
                        url = item.get('url') or item.get('vdUrl') or ''
                        if url and 'VIDE' in url:
                            links.append(url)
                except Exception:
                    pass
        except Exception as e:
            self.logger.debug(f"JSON搜索失败: {e}")
        try:
            # 2) HTML 搜索结果页
            html_url = f"https://search.cctv.com/search.php?qtext={quote(keywords)}&type=video&sort=date"
            self.logger.info(f"尝试央视HTML搜索: {html_url}")
            r = requests.get(html_url, headers=headers, timeout=10)
            if r.ok:
                html = r.text
                import re
                # 仅提取当天路径的LINK
                pat = rf'https?://tv\\.cctv\\.com/{y}/{m}/{d}/VIDE[\\w]+\\.shtml'
                for mobj in re.findall(pat, html):
                    links.append(mobj)
                # 也兼容协议相对或相对
                pat2 = rf'//tv\\.cctv\\.com/{y}/{m}/{d}/VIDE[\\w]+\\.shtml'
                for mobj in re.findall(pat2, html):
                    links.append('https:' + mobj)
                pat3 = rf'/{y}/{m}/{d}/VIDE[\\w]+\\.shtml'
                for mobj in re.findall(pat3, html):
                    links.append('https://tv.cctv.com' + mobj)
        except Exception as e:
            self.logger.debug(f"HTML搜索失败: {e}")

        # 去重保持顺序
        seen, ordered = set(), []
        for u in links:
            if u not in seen:
                ordered.append(u)
                seen.add(u)
        self.logger.info(f"站内搜索获取到 {len(ordered)} 条分条链接")
        return ordered

    def download_daily_news(self, date=None, save=True, get_details=False, details_plain=False):
        """
        下载指定日期的新闻联播文字版
        
        Args:
            date: 日期字符串，格式为YYYYMMDD，默认为当天
            save: 是否保存到文件，默认为True
            get_details: 是否获取所有新闻的详细内容，默认为False
            
        Returns:
            dict: 新闻数据字典
        """
        date_str = date or Config.get_today_date()
        self.logger.info(f"开始下载 {date_str} 的新闻联播")
        
        # 尝试方法 1: 当日列表页直接提取（推荐，兼容性更好）
        program_url, segments_from_day = self.get_day_links(date_str)
        news_data = None
        if program_url:
            self.logger.info("使用方法 1: 当日列表页解析成功")
            news_data = self.get_news_content(program_url)
        else:
            # 尝试方法 2: 旧的CSS选择器方式
            self.logger.info("尝试方法 2: 使用CSS选择器获取列表")
            news_list = self.get_daily_news_list(date_str)
            if news_list:
                target_news = news_list[0]
                program_url = target_news['url']
                self.logger.info(f"使用方法 2 找到新闻: {target_news['title']}")
                news_data = self.get_news_content(program_url)
        
        if not news_data:
            # 尝试方法 2: 获取最新一期的新闻联播
            self.logger.info("尝试方法 2: 获取最新一期的新闻联播")
            news_data = self.get_latest_news()
            program_url = news_data.get('url') if news_data else None
            
            if not news_data or not news_data.get('content'):
                self.logger.warning(f"未找到新闻联播内容")
                return None
        
        # 添加元数据
        news_data['download_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        news_data['date_requested'] = date_str
        
        # 如果需要获取详细新闻列表
        if get_details:
            self.logger.info("开始获取所有新闻的详细内容")
            detail_links = []
            # 优先使用当日列表页解析到的分条链接
            if segments_from_day:
                detail_links = segments_from_day
            elif program_url:
                # 否则从节目页提取分条链接
                detail_links = self.extract_segment_links(program_url)
            # 最终兜底：站内搜索按日期聚合
            if not detail_links:
                detail_links = self.search_segments_by_cctv(date_str)
            if detail_links:
                news_data['news_details'] = self.get_news_details_list(detail_links)
        
        # 保存到文件
        if save:
            save_path = self._save_news_to_file(news_data, date_str, save_markdown=True, details_plain=details_plain)
            news_data['saved_path'] = str(save_path)
        
        return news_data
        
    def get_latest_news(self):
        """
        获取最新的新闻联播
        
        Returns:
            dict: 新闻内容字典
        """
        self.logger.info(f"获取最新一期新闻联播")
        
        try:
            # 先获取首页
            response = self._make_request(Config.LATEST_URL)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 尝试找到最新一期的链接
            latest_link = None
            
            # 查找所有包含"新闻联播"的链接
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                title = link.get('title', '') + link.text
                href = link.get('href')
                if '新闻联播' in title and href and 'VIDE' in href:
                    latest_link = href if href.startswith('http') else ('https://tv.cctv.com' + href)
                    self.logger.info(f"找到最新的新闻联播链接: {latest_link}")
                    break
            
            # 如果找到了链接，获取其内容
            if latest_link:
                return self.get_news_content(latest_link)
            else:
                # 使用搜索功能获取
                self.logger.info("使用搜索功能获取新闻联播")
                return self._get_news_from_search()
                
        except Exception as e:
            self.logger.error(f"获取最新新闻失败: {e}")
            # 尝试搜索方式
            return self._get_news_from_search()
    
    def _get_news_from_search(self):
        """通过搜索获取新闻联播内容"""
        try:
            response = self._make_request(Config.SEARCH_URL)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 寻找搜索结果中的第一个相关视频
            for item in soup.select('.list_lt li'):
                link_elem = item.select_one('a')
                if not link_elem:
                    continue
                    
                title = link_elem.text.strip()
                href = link_elem.get('href')
                
                if '新闻联播' in title and href:
                    self.logger.info(f"从搜索结果中找到新闻: {title}")
                    return self.get_news_content(href)
                    
            self.logger.warning("在搜索结果中未找到相关新闻")
            return None
            
        except Exception as e:
            self.logger.error(f"从搜索获取新闻失败: {e}")
            return None
    
    def _save_news_to_file(self, news_data, date_str, save_markdown=False, details_plain=False):
        """保存新闻到文件"""
        # 创建日期目录
        date_dir = ensure_dir(os.path.join(self.save_dir, date_str))
        
        # 保存JSON格式
        json_path = os.path.join(date_dir, "news_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        # 保存纯文本格式
        txt_path = os.path.join(date_dir, "news_content.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"标题: {news_data['title']}\n")
            f.write(f"日期: {news_data['date']}\n")
            f.write(f"链接: {news_data['url']}\n\n")
            f.write(news_data['content'])
        
        # 如果需要保存Markdown格式
        if save_markdown:
            md_path = os.path.join(date_dir, f"{date_str}.md")
            self._save_as_markdown(news_data, md_path, date_str, details_plain)
        
        self.logger.info(f"新闻已保存至: {txt_path}")
        return txt_path
    
    def _save_as_markdown(self, news_data, md_path, date_str, details_plain=False):
        """保存为Markdown格式（参考GitHub项目格式）"""
        with open(md_path, 'w', encoding='utf-8') as f:
            # 标题
            f.write(f"# 《新闻联播》 ({date_str})\n\n")
            
            # 新闻摘要
            f.write("## 新闻摘要\n\n")
            f.write(news_data.get('content', ''))
            f.write("\n\n")
            
            # 详细新闻
            if 'news_details' in news_data and news_data['news_details']:
                f.write("## 详细新闻\n\n")
                for detail in news_data['news_details']:
                    f.write(f"### {detail.get('title', '无标题')}\n\n")
                    if details_plain:
                        f.write(detail.get('content', ''))
                        f.write("\n\n")
                    else:
                        html = detail.get('html')
                        if html:
                            f.write(html)
                            f.write("\n\n")
                        else:
                            f.write(detail.get('content', ''))
                            f.write("\n\n")
                    f.write(f"[查看原文]({detail.get('url', '')})\n\n")
            
            # 更新时间戳
            f.write("---\n\n")
            f.write(f"(更新时间戳: {int(time.time() * 1000)})\n\n")
        
        self.logger.info(f"Markdown文件已保存至: {md_path}")
