import sys
import os
sys.path.append('PYPlugins通达信官方量化/user')

try:
    from tqcenter import tq
    print("✅ tqcenter 导入成功")
    
    # 尝试初始化
    tq.initialize(__file__)
    print("✅ TQ 初始化成功")
    
    # 尝试获取简单数据 - 使用历史日期
    print("正在获取数据...")
    df_real = tq.get_market_data(
        field_list=['Close'],
        stock_list=['600519.SH'],
        start_time="20260101",  # 使用2024年数据
        end_time="20260407",
        dividend_type='front',
        period='1d',
        fill_data=True
    )
    print("✅ 数据获取成功")
    #print(f"数据形状: {df_real.shape}")
    print(df_real)
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
