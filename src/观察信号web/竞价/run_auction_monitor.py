# -*- coding: utf-8 -*-
"""
竞价监控启动脚本
支持定时启动和持续监控
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from auction_monitor import AuctionMonitor


def wait_until_auction():
    """等待到竞价时间"""
    now = datetime.now()
    
    # 如果已经过了9:20，等到明天
    if now.time() > datetime.strptime('09:20', '%H:%M').time():
        tomorrow = now + timedelta(days=1)
        next_auction = datetime.combine(tomorrow.date(), datetime.strptime('09:15', '%H:%M').time())
        print(f"今天竞价已结束，程序将在明天 {next_auction.strftime('%Y-%m-%d %H:%M:%S')} 启动")
        time.sleep((next_auction - now).total_seconds())
        return True
    
    # 如果还没到9:15，等到9:15
    elif now.time() < datetime.strptime('09:15', '%H:%M').time():
        today_auction = datetime.combine(now.date(), datetime.strptime('09:15', '%H:%M').time())
        print(f"等待竞价开始，将在 {today_auction.strftime('%H:%M:%S')} 启动监控")
        time.sleep((today_auction - now).total_seconds())
        return True
    
    # 正好在竞价时间内
    else:
        print("当前处于竞价时间内，立即启动监控")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("竞价监控启动程序")
    print("=" * 60)
    
    monitor = AuctionMonitor()
    
    while True:
        try:
            # 检查是否为交易日
            if not monitor.is_trading_day():
                print("今天不是交易日，程序退出")
                break
            
            # 等待到竞价时间
            need_wait = wait_until_auction()
            
            if need_wait:
                continue  # 重新检查是否为交易日
            
            # 执行竞价监控
            print("开始执行竞价监控...")
            monitor.monitor_auction()
            
            # 监控完成后询问是否继续
            print("\n竞价监控完成")
            choice = input("是否继续监控下一个交易日？(y/n): ").lower()
            if choice != 'y':
                break
            
            # 等待到下一个交易日
            print("等待下一个交易日...")
            time.sleep(60)  # 每分钟检查一次
            
        except KeyboardInterrupt:
            print("\n程序被用户中断")
            break
        except Exception as e:
            print(f"程序运行出错：{e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)  # 出错后等待1分钟再重试


if __name__ == "__main__":
    main()
