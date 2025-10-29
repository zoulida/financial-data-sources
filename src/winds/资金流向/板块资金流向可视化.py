"""
板块资金流向可视化脚本
功能：获取申万一级行业最近5个交易日的板块净流入额并可视化
依赖：WindPy、pandas、seaborn、matplotlib
"""

from WindPy import w
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def main():
    """主函数：获取板块资金流向数据并可视化"""
    
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
    
    try:
        # 获取申万一级行业板块数据
        print("\n正在获取申万一级行业板块数据...")
        
        # 使用wset获取申万一级行业板块
        sector_data = w.wset("sectorconstituent", "date=20241220;sectorid=a39901011g000000")
        
        if sector_data.ErrorCode != 0:
            print(f"板块数据获取失败，错误码：{sector_data.ErrorCode}")
            print("请检查Wind终端是否已开通相关权限")
            return
        
        # 获取板块代码列表
        sector_codes = sector_data.Data[1]  # 板块代码
        sector_names = sector_data.Data[2]  # 板块名称
        
        print(f"获取到 {len(sector_codes)} 个申万一级行业板块")
        
        # 获取最近5个交易日的净流入数据
        print("正在获取板块净流入数据...")
        
        # 获取最近5个交易日的数据
        net_inflow_data = w.wss(sector_codes, "net_inflow", "tradeDate=20241220;unit=1")
        
        if net_inflow_data.ErrorCode != 0:
            print(f"净流入数据获取失败，错误码：{net_inflow_data.ErrorCode}")
            print("可能原因：")
            print("1. 未开通'沪深Level-2增强'权限")
            print("2. 字段net_inflow不存在或权限不足")
            print("3. 板块代码格式错误")
            print("\nWind终端开通路径：")
            print("1. 打开Wind终端")
            print("2. 点击'工具' -> '数据权限管理'")
            print("3. 找到'沪深Level-2增强'权限并开通")
            return
        
        # 构建DataFrame
        df_data = []
        for i, code in enumerate(sector_codes):
            if i < len(net_inflow_data.Data[0]):
                value = net_inflow_data.Data[0][i]
                if value is not None:
                    df_data.append({
                        '行业名称': sector_names[i] if i < len(sector_names) else f"板块{i+1}",
                        '日期': '2024-12-20',
                        '净流入(万元)': value
                    })
        
        if not df_data:
            print("未获取到有效数据，可能原因：")
            print("1. 未开通'沪深Level-2增强'权限")
            print("2. 数据源暂时不可用")
            print("\nWind终端开通路径：")
            print("1. 打开Wind终端")
            print("2. 点击'工具' -> '数据权限管理'")
            print("3. 找到'沪深Level-2增强'权限并开通")
            return
        
        df = pd.DataFrame(df_data)
        
        # 按净流入金额排序
        df = df.sort_values('净流入(万元)', ascending=False)
        
        print(f"\n=== 板块净流入数据 ===")
        print(f"数据条数：{len(df)}")
        print(f"数据预览：")
        print(df.head(10))
        
        # 创建可视化图表
        plt.figure(figsize=(15, 10))
        
        # 使用seaborn绘制柱状图
        sns.barplot(data=df.head(20), x='净流入(万元)', y='行业名称', hue='日期')
        
        plt.title('申万一级行业板块净流入情况\n数据来源于 Wind API 资金流向模块，字段 net_inflow', 
                 fontsize=14, pad=20)
        plt.xlabel('净流入金额 (万元)', fontsize=12)
        plt.ylabel('行业名称', fontsize=12)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图片
        plt.savefig('板块资金流向图.png', dpi=300, bbox_inches='tight')
        print("\n图表已保存为 '板块资金流向图.png'")
        
        # 显示图表
        plt.show()
        
        # 统计信息
        total_inflow = df['净流入(万元)'].sum()
        positive_count = len(df[df['净流入(万元)'] > 0])
        negative_count = len(df[df['净流入(万元)'] < 0])
        
        print(f"\n=== 统计信息 ===")
        print(f"总净流入：{total_inflow:.2f} 万元")
        print(f"净流入为正的板块：{positive_count} 个")
        print(f"净流入为负的板块：{negative_count} 个")
        
    except Exception as e:
        print(f"程序执行出错：{str(e)}")
        print("请检查：")
        print("1. Wind终端是否已启动并登录")
        print("2. 是否开通了'沪深Level-2增强'权限")
        print("3. 网络连接是否正常")
        print("4. 是否安装了必要的Python包：pandas, seaborn, matplotlib")
    
    finally:
        # 关闭WindPy连接
        w.stop()
        print("\nWindPy连接已关闭")

if __name__ == "__main__":
    main()
