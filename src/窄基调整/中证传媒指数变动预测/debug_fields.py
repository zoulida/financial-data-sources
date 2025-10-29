#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试字段信息
查看Wind API实际返回的字段
"""

from wind_api_utils import init_wind_api, close_wind_api, get_stock_basic_info

def debug_wind_fields():
    """调试Wind API返回的字段"""
    print("=" * 80)
    print("调试Wind API字段信息")
    print("=" * 80)
    
    # 初始化Wind API
    if not init_wind_api():
        print("Wind API初始化失败")
        return
    
    try:
        # 测试少量股票
        test_stocks = ["000001.SZ", "000002.SZ"]
        
        print(f"\n测试股票: {test_stocks}")
        print("请求字段: sec_name,ipo_date,delist_date,sec_status,mkt,windcode")
        
        # 获取股票基本信息
        df_info = get_stock_basic_info(test_stocks, batch_size=2)
        
        if df_info is not None:
            print(f"\n✓ 成功获取数据")
            print(f"数据形状: {df_info.shape}")
            print(f"实际字段: {list(df_info.columns)}")
            print(f"\n数据预览:")
            print(df_info.head())
            
            # 检查每个字段的数据类型和内容
            print(f"\n字段详情:")
            for col in df_info.columns:
                print(f"  {col}: {df_info[col].dtype}")
                print(f"    非空值数量: {df_info[col].notna().sum()}")
                print(f"    唯一值数量: {df_info[col].nunique()}")
                if df_info[col].notna().sum() > 0:
                    print(f"    示例值: {df_info[col].dropna().iloc[0]}")
                print()
        else:
            print("✗ 未获取到数据")
    
    except Exception as e:
        print(f"✗ 调试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        close_wind_api()
    
    print("\n" + "=" * 80)
    print("调试完成！")
    print("=" * 80)

if __name__ == "__main__":
    debug_wind_fields()
