from typing import List, Optional, Dict, Any
import pandas as pd
from pathlib import Path
from datetime import datetime
from xtquant.xtdata import get_full_tick, get_stock_list_in_sector

def save_tick_to_csv(tick_data: Dict[str, Any], filename: str = None) -> str:
    """
    将tick数据保存为CSV文件
    
    Args:
        tick_data: get_full_tick返回的tick数据
        filename: 保存的文件名，如果为None则自动生成
        
    Returns:
        str: 保存的文件路径
    """
    if not filename:
        today = datetime.now().strftime('%Y%m%d')
        filename = f'tick_data_{today}.csv'
    
    # 创建保存目录
    save_dir = Path(__file__).parent / 'tick_data'
    save_dir.mkdir(exist_ok=True)
    
    filepath = save_dir / filename
    
    # 转换tick数据为DataFrame
    df = pd.DataFrame.from_dict(tick_data, orient='index')
    
    # 保存到CSV
    df.to_csv(filepath, encoding='utf-8-sig')
    print(f'Tick数据已保存至: {filepath}')
    return str(filepath)


def get_paused_stocks(market: str = '沪深A股', print_result: bool = False, save_tick: bool = False) -> List[str]:
    """
    获取指定市场中的停牌股票列表
    
    Args:
        market: 市场名称，默认为'沪深A股'
        print_result: 是否打印结果，默认为False
        save_tick: 是否保存tick数据到CSV文件，默认为False
        
    Returns:
        List[str]: 停牌股票代码列表
    """
    try:
        # 1. 获取指定市场的所有股票代码
        codes = get_stock_list_in_sector(market)
        
        # 2. 获取所有股票的实时行情快照
        tick = get_full_tick(codes)  # dict{code: 快照}
        
        # 2.1 如果需要，保存tick数据到CSV
        if save_tick:
            save_tick_to_csv(tick)
        
        # 3. 过滤停牌股票：快照不存在 或 最新价==0 或 stockStatus==7 即为停牌
        paused = [s for s in codes if s not in tick or tick[s]['lastPrice'] == 0 or 
                 (tick[s].get('stockStatus') == 7)]
        
        if print_result:
            print(f'[{market}] 停牌股票共 {len(paused)} 只')
            print(paused)
            
        return paused
        
    except Exception as e:
        print(f'获取停牌股票时发生错误: {str(e)}')
        return []


if __name__ == "__main__":
    # 示例用法
    print("获取停牌股票并保存tick数据...")
    paused_stocks = get_paused_stocks(print_result=True, save_tick=True)
