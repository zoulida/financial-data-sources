"""
工具函数模块
"""
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path


def setup_logger(name, log_file=None, level=logging.INFO):
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def clean_text(text):
    """清理文本，去除多余空白字符"""
    if not text:
        return ""
    
    # 替换HTML标签
    text = re.sub(r'<.*?>', '', text)
    
    # 删除多余空白
    text = re.sub(r'\s+', ' ', text)
    
    # 去除首尾空白
    return text.strip()


def extract_title(html_content):
    """从HTML内容中提取标题"""
    title_pattern = re.compile(r'<title>(.*?)</title>')
    match = title_pattern.search(html_content)
    if match:
        return clean_text(match.group(1))
    return "未知标题"


def extract_date_from_url(url):
    """从URL中提取日期"""
    date_pattern = re.compile(r'/(\d{8})\.shtml')
    match = date_pattern.search(url)
    if match:
        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            return date_obj
        except ValueError:
            pass
    return datetime.now()


def get_previous_date(days=1, date_format="%Y%m%d"):
    """获取前N天的日期字符串"""
    today = datetime.now()
    previous_date = today - timedelta(days=days)
    return previous_date.strftime(date_format)


def ensure_dir(directory):
    """确保目录存在"""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path
