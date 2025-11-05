"""
fetch_all_public_funds() 函数使用示例

该函数已添加 @shelve_me_today 装饰器，缓存有效期为1天。
同一天内多次调用会直接从缓存读取，避免重复请求 Wind API。
"""

import sys
from pathlib import Path

# 方式1：添加项目路径（如果还没有添加）
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# 导入函数
from src.网格.网格选股.fetch_all_public_funds_final import fetch_all_public_funds


def example_1_basic_usage():
    """示例1：基本使用"""
    print("="*80)
    print("示例1：基本使用 - 获取所有基金列表")
    print("="*80)
    
    # 调用函数获取数据
    df = fetch_all_public_funds()
    
    if df is not None:
        print(f"\n✅ 成功获取 {len(df)} 只基金")
        print(f"DataFrame 列: {df.columns.tolist()}")
        print(f"\n前5条数据:")
        print(df.head())
    else:
        print("\n❌ 获取失败")


def example_2_get_fund_codes():
    """示例2：提取基金代码列表"""
    print("\n" + "="*80)
    print("示例2：提取基金代码列表")
    print("="*80)
    
    df = fetch_all_public_funds()
    
    if df is not None:
        # 获取所有基金代码
        fund_codes = df['wind_code'].tolist()
        
        print(f"\n总共 {len(fund_codes)} 只基金")
        print(f"前10只基金代码: {fund_codes[:10]}")
        
        # 按交易所分组
        sh_funds = [code for code in fund_codes if code.endswith('.SH')]
        sz_funds = [code for code in fund_codes if code.endswith('.SZ')]
        
        print(f"\n上交所基金: {len(sh_funds)} 只")
        print(f"深交所基金: {len(sz_funds)} 只")


def example_3_filter_by_name():
    """示例3：按名称筛选基金"""
    print("\n" + "="*80)
    print("示例3：按名称筛选基金")
    print("="*80)
    
    df = fetch_all_public_funds()
    
    if df is not None:
        # 筛选包含 "ETF" 的基金
        etf_funds = df[df['sec_name'].str.contains('ETF', na=False)]
        print(f"\nETF基金数量: {len(etf_funds)}")
        print(f"ETF基金示例:")
        print(etf_funds.head(10))
        
        # 筛选包含 "科创" 的基金
        kechuang_funds = df[df['sec_name'].str.contains('科创', na=False)]
        print(f"\n科创相关基金数量: {len(kechuang_funds)}")
        print(f"科创基金示例:")
        print(kechuang_funds.head())


def example_4_export_to_different_format():
    """示例4：导出为不同格式"""
    print("\n" + "="*80)
    print("示例4：导出为不同格式")
    print("="*80)
    
    df = fetch_all_public_funds()
    
    if df is not None:
        # 导出为 Excel
        excel_file = 'funds_list.xlsx'
        df.to_excel(excel_file, index=False)
        print(f"\n✅ 已导出为 Excel: {excel_file}")
        
        # 导出为 JSON
        json_file = 'funds_list.json'
        df.to_json(json_file, orient='records', force_ascii=False, indent=2)
        print(f"✅ 已导出为 JSON: {json_file}")
        
        # 导出为纯文本（仅代码）
        txt_file = 'fund_codes.txt'
        with open(txt_file, 'w') as f:
            for code in df['wind_code']:
                f.write(code + '\n')
        print(f"✅ 已导出为文本: {txt_file}")


def example_5_use_with_wind_api():
    """示例5：结合 Wind API 使用"""
    print("\n" + "="*80)
    print("示例5：结合 Wind API 使用（获取前10只基金的净值）")
    print("="*80)
    
    df = fetch_all_public_funds()
    
    if df is not None:
        from WindPy import w
        
        w.start()
        
        # 获取前10只基金
        fund_codes = df['wind_code'].tolist()[:10]
        
        print(f"\n正在获取前10只基金的最新净值...")
        
        # 获取最新净值
        nav_data = w.wss(
            fund_codes,
            "nav,NAV_date",  # 单位净值、净值日期
        )
        
        if nav_data.ErrorCode == 0:
            import pandas as pd
            nav_df = pd.DataFrame(
                nav_data.Data,
                index=['最新净值', '净值日期'],
                columns=nav_data.Codes
            ).T
            
            print(f"\n最新净值数据:")
            print(nav_df)
        else:
            print(f"获取净值失败: {nav_data.ErrorCode}")
        
        w.close()


def example_6_cache_demo():
    """示例6：演示缓存功能"""
    print("\n" + "="*80)
    print("示例6：演示缓存功能")
    print("="*80)
    
    import time
    
    print("\n第一次调用（从 Wind 获取数据）:")
    start = time.time()
    df1 = fetch_all_public_funds()
    time1 = time.time() - start
    print(f"耗时: {time1:.2f} 秒")
    
    print("\n第二次调用（从缓存读取）:")
    start = time.time()
    df2 = fetch_all_public_funds()
    time2 = time.time() - start
    print(f"耗时: {time2:.2f} 秒")
    
    print(f"\n速度提升: {time1/time2:.1f}x")
    print(f"数据一致性: {'✅ 一致' if df1.equals(df2) else '❌ 不一致'}")


if __name__ == '__main__':
    # 运行所有示例
    print("\n" + "="*80)
    print("fetch_all_public_funds() 使用示例集")
    print("="*80)
    
    # 基本使用
    example_1_basic_usage()
    
    # 提取代码列表
    example_2_get_fund_codes()
    
    # 按名称筛选
    example_3_filter_by_name()
    
    # 导出不同格式
    # example_4_export_to_different_format()  # 取消注释以运行
    
    # 结合 Wind API
    # example_5_use_with_wind_api()  # 取消注释以运行（需要 Wind 终端）
    
    # 缓存演示
    example_6_cache_demo()
    
    print("\n" + "="*80)
    print("所有示例运行完成！")
    print("="*80)

