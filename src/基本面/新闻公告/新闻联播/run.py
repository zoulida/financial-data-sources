"""
独立启动脚本 - 可以直接运行，无需使用 -m 参数
使用方法：python run.py
"""
import os
import sys
import argparse
import logging
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

# 现在可以使用绝对导入
from src.新闻公告.新闻联播.xwlb_downloader import XWLBDownloader
from src.新闻公告.新闻联播.config import Config
from src.新闻公告.新闻联播.utils import setup_logger, get_previous_date

# 设置控制台编码
if sys.platform == 'win32':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except:
        pass
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
    
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志级别
    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = setup_logger('xwlb_main', level=getattr(logging, log_level))
    
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
        news_data = downloader.download_daily_news(date=download_date, get_details=args.details)
        
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
