# -*- coding: utf-8 -*-
"""
竞价监控程序
功能：在开盘日9:15-9:20期间，每10秒获取A股tick数据，记录竞价最大金额
作者：自动生成
日期：2026-02-27
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, time as dt_time
from pathlib import Path

# 添加工具路径
TOOLS_PATH = Path(r"D:\pythonworkspace\zldtools")
if TOOLS_PATH.exists() and str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

try:
    from tools.tradeCal import is_open_day
    from xtquant import xtdata
except ImportError as e:
    print(f"错误：无法导入必要模块，请确保路径正确：{e}")
    sys.exit(1)


class AuctionMonitor:
    """竞价监控器"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.csv_file = self.data_dir / "auction_max_amounts.csv"
        
    def get_a_share_codes(self):
        """获取A股代码列表"""
        print(">>> 正在获取 A 股代码列表...")
        try:
            a_share_codes = xtdata.get_stock_list_in_sector("沪深A股")
            # 剔除北交所和退市整理股票
            a_share_codes = [c for c in a_share_codes 
                           if not (c.startswith(('688', '689', '83', '87')))]
            print(f">>> 共获取 {len(a_share_codes)} 只 A 股")
            return a_share_codes
        except Exception as e:
            print(f"获取A股代码失败：{e}")
            return []
    
    def is_trading_day(self):
        """判断今天是否为交易日"""
        today_str = datetime.now().strftime("%Y%m%d")
        return is_open_day(today_str)
    
    def is_in_auction_time(self):
        """判断当前是否在竞价时间（9:15-9:20）"""
        now = datetime.now()
        current_time = now.time()
        auction_start = dt_time(9, 15)
        auction_end = dt_time(9, 20)
        return auction_start <= current_time < auction_end
    
    def get_tick_amounts(self, stock_codes):
        """获取股票tick数据中的amount"""
        amounts = {}
        
        try:
            # 使用get_full_tick获取全市场tick数据
            print("    正在获取全市场tick数据...")
            full_tick = xtdata.get_full_tick(['SH', 'SZ'])
            
            # full_tick是字典格式，包含所有股票的tick数据
            for code in stock_codes:
                if code in full_tick:
                    tick_info = full_tick[code]
                    
                    # 检查是否有amount字段
                    if isinstance(tick_info, dict) and 'amount' in tick_info:
                        amount = tick_info['amount']
                        if amount > 0:  # 只记录有成交的股票
                            amounts[code] = amount
                    elif isinstance(tick_info, (tuple, list)) or hasattr(tick_info, '__len__'):
                        # 如果是数组格式，amount通常在索引6的位置
                        if len(tick_info) >= 7:
                            amount = tick_info[6]
                            if amount > 0:
                                amounts[code] = amount
                                
        except Exception as e:
            print(f"获取tick数据失败：{e}")
            
        return amounts
    
    def monitor_auction(self):
        """监控竞价过程"""
        if not self.is_trading_day():
            print("今天不是交易日，退出监控")
            return
        
        print(">>> 今天是交易日，开始监控竞价...")
        
        # 获取A股列表
        stock_codes = self.get_a_share_codes()
        if not stock_codes:
            print("获取股票代码失败，退出")
            return
        
        # 记录每只股票的最大amount
        max_amounts = {}
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        print(f">>> 开始监控 {today_str} 竞价数据...")
        
        while self.is_in_auction_time():
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"[{current_time}] 正在获取tick数据...")
            
            # 获取当前amount数据
            current_amounts = self.get_tick_amounts(stock_codes)
            
            if current_amounts:
                print(f"  获取到 {len(current_amounts)} 只股票的成交数据")
                # 显示前5只股票的数据
                sample_codes = list(current_amounts.keys())[:5]
                for code in sample_codes:
                    amount = current_amounts[code]
                    print(f"    {code}: {amount:,.0f}")
                if len(current_amounts) > 5:
                    print(f"    ... 还有 {len(current_amounts) - 5} 只股票")
            else:
                print(f"  当前无成交数据")
            
            # 更新最大值
            for code, amount in current_amounts.items():
                if code not in max_amounts or amount > max_amounts[code]:
                    max_amounts[code] = amount
            
            # 等待10秒
            time.sleep(10)
        
        # 计算当日竞价最大金额总和
        total_max_amount = sum(max_amounts.values())
        
        print(f">>> 竞价结束，当日竞价最大金额总和：{total_max_amount:,.0f}")
        
        # 保存到CSV
        self.save_to_csv(today_str, total_max_amount, len(max_amounts))
        
        return total_max_amount
    
    def save_to_csv(self, date_str, total_amount, stock_count):
        """保存数据到CSV文件"""
        # 准备数据
        new_data = pd.DataFrame([{
            'date': date_str,
            'total_max_amount': total_amount,
            'stock_count': stock_count,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        
        # 如果文件不存在，创建新文件；否则追加
        if self.csv_file.exists():
            new_data.to_csv(self.csv_file, mode='a', header=False, index=False, encoding='utf-8-sig')
        else:
            new_data.to_csv(self.csv_file, index=False, encoding='utf-8-sig')
        
        print(f">>> 数据已保存到：{self.csv_file}")
    
    def run(self):
        """运行竞价监控"""
        print("=" * 60)
        print("竞价监控程序")
        print("=" * 60)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"当前时间：{current_time}")
        print(f"是否交易日：{'是' if self.is_trading_day() else '否'}")
        
        if self.is_in_auction_time():
            print("当前处于竞价时间（9:15-9:20）")
            self.monitor_auction()
        else:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"当前时间 {current_time} 不在竞价时间内")
            
            if self.is_trading_day():
                # 计算等待时间
                now = datetime.now()
                auction_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
                
                if now < auction_start:
                    wait_seconds = (auction_start - now).total_seconds()
                    wait_minutes = int(wait_seconds // 60)
                    wait_seconds_rem = int(wait_seconds % 60)
                    print(f"等待竞价开始，还需等待 {wait_minutes} 分 {wait_seconds_rem} 秒...")
                    
                    # 等待到竞价时间
                    import time
                    time.sleep(wait_seconds)
                    
                    # 重新检查时间
                    if self.is_in_auction_time():
                        print("竞价时间开始，开始监控...")
                        self.monitor_auction()
                    else:
                        print("等待后仍不在竞价时间内，可能已错过")
                else:
                    print("今日竞价时间已过")
            else:
                print("今天不是交易日，无需监控")


def main():
    """主函数"""
    monitor = AuctionMonitor()
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
