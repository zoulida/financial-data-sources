"""
获取所有上市公募基金代码（含 ETF、LOF、普通开放、封闭、FOF、REITs 等）
使用 Wind API 从 Wind 终端拉取数据并保存为 CSV

✅ 已验证可用 - 板块ID: 1000019786000000
✅ 已添加 @shelve_me_today 缓存 - 每天只从 Wind 获取一次数据

使用示例：
    # 方式1：直接运行脚本
    python fetch_all_public_funds_final.py
    
    # 方式2：在其他程序中调用
    from src.网格.网格选股.fetch_all_public_funds_final import fetch_all_public_funds
    
    df = fetch_all_public_funds()
    if df is not None:
        print(f"获取到 {len(df)} 只基金")
        fund_codes = df['wind_code'].tolist()
        fund_names = df['sec_name'].tolist()
"""
from WindPy import w
import pandas as pd
import datetime as dt
import os
import sys
from pathlib import Path

# 添加项目路径以导入shelve_tool
# 当前文件: src/网格/网格选股/fetch_all_public_funds_final.py
# parents[3] = 项目根目录（假设 tools 在项目根目录下）
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from tools.shelveTool import shelve_me_today

n = None
@shelve_me_today(n)
def fetch_all_public_funds():
    """
    获取所有上市公募基金代码和名称
    
    该函数使用 @shelve_me_today 装饰器，缓存有效期为1天。
    同一天内多次调用会直接从缓存读取，不会重复请求 Wind API。
    
    Returns:
        pd.DataFrame: 包含两列的 DataFrame
            - wind_code: 基金代码（如 '159001.SZ'）
            - sec_name: 基金名称（如 '货币ETF'）
        None: 获取失败时返回 None
    
    Example:
        >>> df = fetch_all_public_funds()
        >>> if df is not None:
        ...     print(f"获取到 {len(df)} 只基金")
        ...     fund_codes = df['wind_code'].tolist()
    """
    print("="*80)
    print("Wind API - 获取所有上市公募基金")
    print("="*80)
    
    # 初始化 Wind 连接
    print("\n正在连接 Wind 终端...")
    w.start()
    
    today = dt.date.today().strftime('%Y-%m-%d')
    print(f"查询日期: {today}")
    
    # 全部上市基金（含 ETF/LOF/普通开放/封闭/FOF/REITs）
    # 板块ID: 1000019786000000 - "全部上市基金"
    print("\n正在获取基金数据...")
    all_funds = w.wset("sectorconstituent",
                       f"date={today};sectorid=1000019786000000")
    
    if all_funds.ErrorCode == 0 and all_funds.Data and len(all_funds.Data) > 0:
        # 构建 DataFrame
        df = pd.DataFrame({
            'wind_code': all_funds.Data[1],
            'sec_name': all_funds.Data[2]
        })
        
        print(f"\n[成功] 获取到 {len(df)} 只基金")
        
        # 统计交易所分布
        df['market'] = df['wind_code'].str.split('.').str[-1]
        market_counts = df['market'].value_counts()
        print(f"\n交易所分布:")
        for market, count in market_counts.items():
            print(f"  {market}: {count} 只")
        
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(current_dir, 'AllPublicFunds_Ashare.csv')
        
        # 保存到 CSV（只保留代码和名称列）
        df[['wind_code', 'sec_name']].to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f'\n[成功] 已导出 {len(df)} 只基金代码')
        print(f'保存路径: {output_file}')
        
        print(f'\n前 10 条数据预览:')
        print(df[['wind_code', 'sec_name']].head(10).to_string(index=False))
        
        print(f'\n数据统计:')
        print(f'  - 总基金数量: {len(df)}')
        print(f'  - 文件大小: {os.path.getsize(output_file) / 1024:.2f} KB')
        
        # 关闭 Wind 连接
        w.close()
        print('\n' + "="*80)
        print('Wind 连接已关闭')
        
        # 返回 DataFrame（只包含代码和名称列）
        return df[['wind_code', 'sec_name']]
    else:
        error_msg = f'Wind 返回错误 (ErrorCode: {all_funds.ErrorCode})'
        print(f'\n[错误] {error_msg}')
        print('请检查:')
        print('  1. Wind 终端是否已登录')
        print('  2. 网络连接是否正常')
        print('  3. Wind 账户权限是否足够')
        
        # 关闭 Wind 连接
        w.close()
        return None

if __name__ == '__main__':
    df = fetch_all_public_funds()
    
    if df is not None:
        print('\n提示:')
        print('  - 数据已成功保存到 AllPublicFunds_Ashare.csv')
        print('  - 包含所有上市公募基金（ETF、LOF、封闭式、开放式等）')
        print('  - 可用于后续净值、持仓、业绩数据的批量获取')
        print(f'  - 返回 DataFrame 形状: {df.shape}')
    else:
        print('\n获取失败，请检查上述错误信息')

