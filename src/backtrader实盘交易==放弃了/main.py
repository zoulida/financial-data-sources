"""
Backtrader 实盘交易主程序
========================

基于 Backtrader 和 XtQuant 实现的实盘交易系统。

策略：买入 159100.SZ，1手=100股，持有。
"""

import sys
import os
from queue import Queue
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backtrader as bt
from xtquant import xtdata
from xtquant_broker import XtQuantBroker
from simple_buy_strategy import SimpleBuyStrategy
from tick_subscriber import TickSubscriber
from tick_data_feed import TickDataFeed


def create_data_feed(stock_code: str):
    """
    创建数据源
    
    Parameters:
    -----------
    stock_code : str
        股票代码，例如 '159100.SZ'
    
    Returns:
    --------
    bt.feeds.PandasData
        数据源对象
    """
    # 使用 XtQuant 获取历史数据
    try:
        # 获取最近100天的数据
        data = xtdata.get_market_data_ex(
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=[stock_code],
            period='1d',
            count=100
        )
        
        if not data or stock_code not in data:
            raise ValueError(f"无法获取 {stock_code} 的数据")
        
        # 转换为 DataFrame
        import pandas as pd
        
        # 提取各个字段
        df_data = {}
        for field in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if field in data[stock_code]:
                df_data[field] = data[stock_code][field]
        
        if not df_data:
            raise ValueError(f"数据为空: {stock_code}")
        
        # 创建 DataFrame
        df = pd.DataFrame(df_data)
        df.index = pd.to_datetime(df.index) if hasattr(df.index, 'to_datetime') else df.index
        
        # 确保列名正确
        df.columns = [col.lower() for col in df.columns]
        
        if df.empty:
            raise ValueError(f"未获取到 {stock_code} 的历史数据，请确认该代码可用且已连接 xtdata")
        
        print(f"[数据] 成功加载 {stock_code} 数据，共 {len(df)} 条记录")
        print(f"[数据] 数据范围: {df.index[0]} 到 {df.index[-1]}")
        
        # 创建 Backtrader 数据源
        data_feed = bt.feeds.PandasData(
            dataname=df,
            datetime=None,  # 使用索引作为日期
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1
        )
        
        return data_feed
        
    except Exception as e:
        print(f"[错误] 创建数据源失败: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """主函数"""
    print("="*60)
    print("Backtrader 实盘交易系统")
    print("="*60)
    
    # ==================== 配置参数 ====================
    # 交易账号配置（请根据实际情况修改）
    ACCOUNT_ID = "8886063599"  # 您的账号
    ACCOUNT_TYPE = "STOCK"  # 账号类型
    QMT_PATH = r"D:\国金证券QMT交易端\userdata_mini"  # QMT 路径
    
    # 策略参数
    STOCK_CODE = "159100.SZ"  # 目标股票
    BUY_VOLUME = 100  # 买入数量（1手=100股）
    
    # ==================== 初始化 XtQuant ====================
    print("\n[初始化] 初始化 XtQuant...")
    # 注意：xtdata.download_sector_data() 可能会阻塞，如果不需要板块数据可以跳过
    # 如果需要板块数据，建议在程序启动前手动下载，或使用后台线程
    try:
        # 设置 xtdata 不显示连接消息（可选）
        xtdata.enable_hello = False
        
        # 跳过下载板块数据，避免阻塞
        # 如果确实需要板块数据，可以取消下面的注释，但要注意可能会卡住
        # xtdata.download_sector_data()
        
        print("[初始化] XtQuant 初始化完成（已跳过板块数据下载）")
    except Exception as e:
        print(f"[警告] XtQuant 初始化警告: {e}")
    tick_subscriber = None
    
    # ==================== 创建 Cerebro 引擎 ====================
    print("\n[引擎] 创建 Cerebro 引擎...")
    cerebro = bt.Cerebro()
    
    # ==================== 创建 tick 数据源 ====================
    print(f"\n[数据] 初始化 {STOCK_CODE} tick 数据 feed...")
    tick_queue = Queue()
    tick_data_feed = TickDataFeed(tick_queue=tick_queue, stock_code=STOCK_CODE)
    cerebro.adddata(tick_data_feed, name=f"{STOCK_CODE}_tick")
    print(f"[数据] Tick 数据 feed 已添加")

    print(f"\n[数据] 订阅 {STOCK_CODE} tick 数据...")
    tick_subscriber = TickSubscriber()
    if not tick_subscriber.subscribe([STOCK_CODE], tick_queue=tick_queue):
        print(f"[错误] tick 数据订阅失败，终止程序")
        return
    
    # ==================== 创建 Broker ====================
    print("\n[Broker] 创建 XtQuant Broker...")
    try:
        broker = XtQuantBroker(
            account_id=ACCOUNT_ID,
            account_type=ACCOUNT_TYPE,
            path=QMT_PATH,
            session=0,  # 0 表示自动生成
            commission=0.0003  # 佣金 0.03%
        )
        cerebro.setbroker(broker)
        print(f"[Broker] Broker 创建完成")
    except Exception as e:
        print(f"[错误] Broker 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ==================== 添加策略 ====================
    print(f"\n[策略] 添加策略...")
    cerebro.addstrategy(
        SimpleBuyStrategy,
        stock_code=STOCK_CODE,
        buy_volume=BUY_VOLUME
    )
    print(f"[策略] 策略添加完成")
    
    # ==================== 打印当前资金 ====================
    initial_cash = broker.getcash()
    print(f"\n[资金] 当前可用资金: {initial_cash:.2f} 元")
    
    # ==================== 运行策略 ====================
    print("\n" + "="*60)
    print("开始运行策略...")
    print("="*60 + "\n")
    
    try:
        # 运行策略（实时模式）
        cerebro.run(runonce=False)
        
        print("\n" + "="*60)
        print("策略运行完成")
        print("="*60)
        
        # 打印最终状态
        final_value = cerebro.broker.getvalue()
        final_cash = cerebro.broker.getcash()
        print(f"\n[最终状态]")
        print(f"  总资产: {final_value:.2f} 元")
        print(f"  可用资金: {final_cash:.2f} 元")
        
    except KeyboardInterrupt:
        print("\n[中断] 用户中断策略运行")
    except Exception as e:
        print(f"\n[错误] 策略运行异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 停止 Broker
        print("\n[清理] 停止 Broker...")
        try:
            if tick_subscriber:
                tick_subscriber.unsubscribe()
            if 'broker' in locals():
                broker.stop()
        except Exception as e:
            print(f"[清理] 关闭资源异常: {e}")
        print("[清理] 清理完成")


if __name__ == "__main__":
    main()

