"""
新闻联播文字版下载主程序
"""
import os
import sys
import argparse
import locale
from datetime import datetime

from .xwlb_downloader import XWLBDownloader
from .config import Config
from .utils import setup_logger, get_previous_date

# 设置控制台编码
if sys.platform == 'win32':
    # 尝试设置控制台编码为utf-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except:
        pass
    # 确保输出流使用utf-8编码
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='下载新闻联播文字版')
    
    parser.add_argument('-d', '--date', 
                        help='指定日期，格式为YYYYMMDD，默认为今天')
    
    parser.add_argument('-o', '--output', 
                        help='指定输出目录，默认为配置中的数据目录')
    
    parser.add_argument('--yesterday', action='store_true',
                        help='下载昨天的新闻联播')
    
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细日志')
    
    parser.add_argument('--details', action='store_true',
                        help='获取所有新闻的详细内容（会花费较长时间）')
    
    parser.add_argument('--details-plain', action='store_true',
                        help='详细新闻以纯文本写入Markdown（不包含HTML标签）')
    
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志级别
    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = setup_logger('xwlb_main', level=getattr(sys.modules['logging'], log_level))
    
    # 确定下载日期
    if args.yesterday:
        download_date = get_previous_date()
        logger.info(f"将下载昨天 ({download_date}) 的新闻联播")
    elif args.date:
        download_date = args.date
        logger.info(f"将下载 {download_date} 的新闻联播")
    else:
        download_date = Config.get_today_date()
        logger.info(f"将下载今天 ({download_date}) 的新闻联播")
    
    # 确定输出目录
    output_dir = args.output or Config.DATA_DIR
    
    try:
        # 创建下载器
        downloader = XWLBDownloader(save_dir=output_dir, logger=logger)
        
        # 下载新闻
        news_data = downloader.download_daily_news(
            date=download_date,
            get_details=args.details,
            details_plain=args.details_plain
        )
        
        if news_data:
            logger.info(f"成功下载新闻: {news_data['title']}")
            logger.info(f"保存路径: {news_data.get('saved_path')}")
            print(f"\n新闻标题: {news_data['title']}")
            print(f"新闻日期: {news_data['date']}")
            print(f"字数统计: {len(news_data['content'])} 字符")
            print(f"保存路径: {news_data.get('saved_path')}")
            return 0
        else:
            logger.error(f"未找到 {download_date} 的新闻联播")
            print(f"错误: 未找到 {download_date} 的新闻联播")
            return 1
            
    except Exception as e:
        logger.exception(f"下载过程中出错: {e}")
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
