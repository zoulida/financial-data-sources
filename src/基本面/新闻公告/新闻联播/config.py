"""
配置文件
"""
import os
from datetime import datetime
from pathlib import Path


class Config:
    # 新闻联播官网URL
    BASE_URL = "http://tv.cctv.com/lm/xwlb/"
    
    # 视频列表URL格式
    VIDEO_LIST_URL = "http://tv.cctv.com/lm/xwlb/day/{date}.shtml"
    
    # 备用URL：央视网搜索结果
    SEARCH_URL = "https://search.cctv.com/search.php?qtext=%E6%96%B0%E9%97%BB%E8%81%94%E6%92%AD&sort=relevance&type=video&vtime=&datepid=1&channel=&page=1"
    
    # 央视新闻联播官方网页 - 最新一期
    LATEST_URL = "http://tv.cctv.com/lm/xwlb/"
    
    # 中央广播电视总台官网
    CCTV_URL = "https://www.cctv.com/"
    
    # 保存路径
    BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = BASE_DIR / "data"
    
    # 用户代理
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    # 请求头
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Referer": "http://tv.cctv.com/lm/xwlb/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }
    
    # 日期格式
    DATE_FORMAT = "%Y%m%d"
    
    # 日志格式
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @staticmethod
    def get_today_date():
        """获取今天的日期字符串"""
        return datetime.now().strftime(Config.DATE_FORMAT)
    
    @staticmethod
    def get_video_list_url(date=None):
        """获取指定日期的视频列表URL"""
        if date is None:
            date = Config.get_today_date()
        return Config.VIDEO_LIST_URL.format(date=date)
    
    @staticmethod
    def ensure_data_dir():
        """确保数据目录存在"""
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        return Config.DATA_DIR
