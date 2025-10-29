"""
个股主力净流入最简验证脚本
功能：获取600000.SH最近1个月的主力净流入金额（时间序列数据）
依赖：仅需WindPy
接口：使用w.wsd获取时间序列数据，显示最近5个交易日数据
"""

from WindPy import w
import pandas as pd

def main():
    """主函数：获取个股主力净流入数据"""
    
    # 初始化WindPy
    print("正在初始化WindPy...")
    w.start()
    
    # 检查是否成功连接
    if not w.isconnected():
        print("WindPy连接失败，请检查：")
        print("1. Wind终端是否已启动")
        print("2. 是否已登录Wind账号")
        print("3. 网络连接是否正常")
        return
    
    print("WindPy连接成功")
    
    # 获取600000.SH的主力净流入数据
    stock_code = "600000.SH"
    field = "mfd_inflow_m"
    
    print(f"\n正在获取 {stock_code} 的主力净流入数据...")
    
    try:
        # 获取最近1个月的数据
        data = w.wsd(stock_code, field, "2025-09-21", "2025-10-20", "ruleType=10;unit=1")
        
        # 检查返回结果
        if data.ErrorCode != 0:
            print(f"数据获取失败，错误码：{data.ErrorCode}")
            print("可能原因：")
            print("1. 未开通'沪深Level-2增强'权限")
            print("2. 字段mfd_inflow_m不存在或权限不足")
            print("3. 股票代码格式错误")
            return
        
        # 获取字段信息
        field_info = data.Fields[0] if data.Fields else "mfd_inflow_m"
        
        # 获取数值（取最新值）
        values = data.Data[0] if data.Data and data.Data[0] else []
        dates = data.Times if data.Times else []
        
        if values and len(values) > 0:
            # 获取最新的净流入值
            latest_value = values[-1]
            latest_date = dates[-1] if dates else "N/A"
            
            # 打印结果
            print(f"\n=== 主力净流入数据 ===")
            print(f"股票代码：{stock_code}")
            print(f"字段名称：{field_info}")
            print(f"字段单位：万元")
            print(f"数据日期：{latest_date}")
            print(f"净流入金额：{latest_value} 万元")
            
            # 显示最近5个交易日的数据
            print(f"\n=== 最近5个交易日数据 ===")
            recent_count = min(5, len(values))
            for i in range(recent_count):
                idx = len(values) - recent_count + i
                date_str = dates[idx] if idx < len(dates) else "N/A"
                value = values[idx] if idx < len(values) else "N/A"
                print(f"{date_str}: {value} 万元")
            
            # 断言验证
            if latest_value is not None:
                print(f"\n[成功] 资金流入接口正常")
            else:
                print(f"\n[失败] 可能无权限或未登录")
        else:
            print(f"\n[失败] 未获取到有效数据")
            
    except Exception as e:
        print(f"程序执行出错：{str(e)}")
        print("请检查：")
        print("1. Wind终端是否已启动并登录")
        print("2. 是否开通了'沪深Level-2增强'权限")
        print("3. 网络连接是否正常")
    
    finally:
        # 关闭WindPy连接
        w.stop()
        print("\nWindPy连接已关闭")

if __name__ == "__main__":
    main()
