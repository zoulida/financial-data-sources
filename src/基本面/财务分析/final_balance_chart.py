"""
Wind资产负债表图表生成器 - 最终版
支持真实数据和示例数据两种模式
"""

from WindPy import w
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import sys

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def get_wind_data(stock_code, report_date=None):
    """
    从Wind获取真实财务数据
    """
    w.start()
    
    try:
        # 财务指标映射
        indicators_map = {
            '现金': 'monetary_cap',           # 货币资金
            '短期借款': 'tot_cur_liab',        # 流动负债合计
            '应收款': 'acct_rcv',             # 应收账款
            '应付款': 'acct_payable',         # 应付账款
            '预付款': 'prepay',               # 预付款项
            '预收款': 'adv_rcv',              # 预收账款
            '存货': 'inventories',            # 存货
            '薪酬&税': 'empl_ben_payable',    # 应付职工薪酬
            '固定资产': 'fix_assets',        # 固定资产
            '其他流动': 'oth_cur_assets',     # 其他流动资产
            '无形资产': 'intang_assets',      # 无形资产
            '长期借款': 'tot_non_cur_liab',   # 非流动负债合计
            '其他非流动': 'oth_non_cur_assets' # 其他非流动资产
        }
        
        wind_fields = list(indicators_map.values())
        
        print(f"尝试从Wind获取 {stock_code} 的财务数据...")
        
        # 逐个字段获取数据，便于调试
        df_data = {}
        success_count = 0
        fail_fields = []
        
        print(f"逐个获取 {len(wind_fields)} 个财务字段的数据...")
        
        for i, field in enumerate(wind_fields):
            try:
                print(f"获取字段 {i+1}/{len(wind_fields)}: {field}")
                
                # 构建正确的Wind API参数格式
                if report_date:
                    # 使用正确的参数格式：unit=1;rptDate=YYYYMMDD;rptType=1
                    field_options = f"unit=1;rptDate={report_date.replace('-', '')};rptType=1"
                else:
                    # 不指定报告期时使用：unit=1;rptType=1
                    field_options = "unit=1;rptType=1"
                
                print(f"  参数: {field_options}")
                
                # 逐个获取字段数据
                field_data = w.wss(stock_code, [field], field_options)
                
                if field_data.ErrorCode == 0 and len(field_data.Data) > 0 and len(field_data.Data[0]) > 0:
                    value = field_data.Data[0][0]
                    chinese_name = [k for k, v in indicators_map.items() if v == field][0]
                    
                    if value is not None:
                        df_data[chinese_name] = [value]
                        print(f"  [OK] {chinese_name}: {value}")
                        success_count += 1
                    else:
                        print(f"  [FAIL] {chinese_name}: None (数据为空)")
                        fail_fields.append(f"{chinese_name}({field})")
                else:
                    chinese_name = [k for k, v in indicators_map.items() if v == field][0]
                    print(f"  [FAIL] {chinese_name}: API错误 {field_data.ErrorCode}")
                    fail_fields.append(f"{chinese_name}({field})")
                    
            except Exception as e:
                chinese_name = [k for k, v in indicators_map.items() if v == field][0]
                print(f"  [ERROR] {chinese_name}: 异常 - {e}")
                fail_fields.append(f"{chinese_name}({field})")
        
        print(f"\n获取结果: 成功 {success_count} 个，失败 {len(fail_fields)} 个")
        if fail_fields:
            print(f"失败的字段: {', '.join(fail_fields)}")
        
        if not df_data:
            print("没有获取到任何有效数据")
            return None
        
        # 创建DataFrame
        df = pd.DataFrame(df_data).T
        df.columns = ['value']
        
        print(f"成功创建DataFrame，包含 {len(df)} 个指标")
        return df
        
    except Exception as e:
        print(f"获取Wind数据时发生错误: {e}")
        return None
    finally:
        w.stop()

def get_sample_data(stock_code="600519.SH"):
    """
    获取示例数据（模拟真实财务数据）
    """
    print("使用示例数据（模拟真实财务指标）...")
    
    # 基于贵州茅台实际财务结构模拟的数据（单位：亿元）
    sample_data = {
        '600519.SH': {  # 贵州茅台
            '现金': 1200.5,
            '短期借款': 50.2,
            '应收款': 25.8,
            '应付款': 180.3,
            '预付款': 15.6,
            '预收款': 95.4,
            '存货': 380.9,
            '薪酬&税': 45.7,
            '固定资产': 220.5,
            '其他流动': 85.2,
            '无形资产': 12.3,
            '长期借款': 10.8,
            '其他非流动': 35.6
        },
        '000001.SZ': {  # 平安银行
            '现金': 3500.2,
            '短期借款': 280.5,
            '应收款': 120.8,
            '应付款': 450.3,
            '预付款': 25.6,
            '预收款': 85.4,
            '存货': 0.0,  # 银行通常无存货
            '薪酬&税': 125.7,
            '固定资产': 180.5,
            '其他流动': 520.2,
            '无形资产': 45.3,
            '长期借款': 850.8,
            '其他非流动': 280.6
        },
        '000002.SZ': {  # 万科A
            '现金': 850.5,
            '短期借款': 320.2,
            '应收款': 180.8,
            '应付款': 680.3,
            '预付款': 95.6,
            '预收款': 450.4,
            '存货': 5200.9,  # 房地产公司存货高
            '薪酬&税': 85.7,
            '固定资产': 120.5,
            '其他流动': 220.2,
            '无形资产': 25.3,
            '长期借款': 1800.8,
            '其他非流动': 150.6
        }
    }
    
    # 如果没有该股票的示例数据，使用默认数据
    if stock_code not in sample_data:
        print(f"没有 {stock_code} 的示例数据，使用默认模板")
        sample_data[stock_code] = sample_data['600519.SH']
    
    df = pd.DataFrame.from_dict(sample_data[stock_code], orient='index', columns=['value'])
    return df

def create_balance_sheet_chart(stock_code, data, report_date=None, is_sample=False):
    """
    创建资产负债表柱状图
    """
    if data is None or data.empty:
        print("没有数据可供绘图")
        return
    
    # 获取股票名称
    try:
        w.start()
        name_data = w.wss(stock_code, "sec_name")
        stock_name = name_data.Data[0][0] if name_data.ErrorCode == 0 else stock_code
        w.stop()
    except:
        stock_name = stock_code
    
    # 过滤有效数据
    valid_data = data[data['value'].notna() & (data['value'] != '') & (data['value'] != 0)]
    
    if valid_data.empty:
        print("没有有效数据可供绘图")
        return
    
    # 准备数据
    indicators = valid_data.index.tolist()
    values = [float(v) for v in valid_data['value']]
    
    # 颜色设置：资产蓝色，负债红色
    asset_items = ['现金', '应收款', '预付款', '存货', '固定资产', '其他流动', '无形资产', '其他非流动']
    colors = ['#3498db' if item in asset_items else '#e74c3c' for item in indicators]
    
    # 创建图表
    plt.figure(figsize=(16, 10))
    bars = plt.bar(range(len(indicators)), values, color=colors, alpha=0.8, 
                   edgecolor='black', linewidth=1.2, width=0.7)
    
    # 标题和标签
    data_source = "示例数据" if is_sample else "Wind数据"
    title_date = report_date if report_date else "最新报告期"
    plt.title(f'{stock_name} 资产负债表 ({title_date}) - {data_source}', 
             fontsize=18, fontweight='bold', pad=25)
    plt.xlabel('财务指标', fontsize=14, fontweight='bold')
    plt.ylabel('金额 (亿元)', fontsize=14, fontweight='bold')
    
    # X轴标签
    plt.xticks(range(len(indicators)), indicators, rotation=45, ha='right', fontsize=12)
    
    # 数值标签
    max_val = max(values) if values else 1
    for i, (bar, value) in enumerate(zip(bars, values)):
        if value > 0:
            plt.text(bar.get_x() + bar.get_width()/2., 
                    value + max_val*0.02,
                    f'{value:.1f}亿', ha='center', va='bottom', 
                    fontsize=11, fontweight='bold')
    
    # 图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#3498db', alpha=0.8, label='资产类科目'),
        Patch(facecolor='#e74c3c', alpha=0.8, label='负债类科目')
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=12)
    
    # 网格和布局
    plt.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    plt.tight_layout()
    
    # 保存和显示
    date_str = report_date.replace('-', '') if report_date else "latest"
    data_prefix = "sample" if is_sample else "wind"
    filename = f'{stock_code}_资产负债表_{date_str}_{data_prefix}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"图表已保存: {filename}")
    plt.show()

def main():
    """主程序"""
    # 默认参数
    default_stock = "600519.SH"
    default_date = "2024-12-31"
    
    # 解析命令行参数
    stock_code = default_stock
    report_date = default_date
    use_sample = False
    
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--sample":
            use_sample = True
        elif arg == "--help":
            print("使用方法:")
            print("python final_balance_chart.py [股票代码] [报告期] [--sample]")
            print("示例:")
            print("  python final_balance_chart.py 600519.SH 2025-06-30")
            print("  python final_balance_chart.py 000001.SZ --sample")
            return
        elif i == 1:
            stock_code = arg
        elif i == 2:
            report_date = arg
    
    print("=" * 70)
    print("Wind 资产负债表图表生成器 - 最终版")
    print("=" * 70)
    print(f"股票代码: {stock_code}")
    print(f"报告期: {report_date}")
    print(f"数据模式: {'示例数据' if use_sample else 'Wind真实数据'}")
    print("-" * 70)
    
    # 获取数据
    if use_sample:
        data = get_sample_data(stock_code)
        is_sample = True
    else:
        data = get_wind_data(stock_code, report_date)
        is_sample = False
        
        # 如果Wind数据获取失败，询问是否使用示例数据
        if data is None:
            print("\nWind数据获取失败！")
            print("可能原因：")
            print("1. Wind终端未登录")
            print("2. 数据权限不足")
            print("3. 网络连接问题")
            print("4. 字段名不匹配")
            
            response = input("\n是否使用示例数据继续？(y/n): ").lower().strip()
            if response in ['y', 'yes', '是']:
                data = get_sample_data(stock_code)
                is_sample = True
            else:
                print("程序结束")
                return
    
    # 显示数据
    if data is not None and not data.empty:
        print(f"\n获取到的财务数据 ({'示例' if is_sample else 'Wind真实'}):")
        for idx, row in data.iterrows():
            val = row['value']
            if pd.notna(val) and val != '' and val != 0:
                if isinstance(val, (int, float)):
                    print(f"{idx}: {val:.2f}亿元")
                else:
                    print(f"{idx}: {val}")
            else:
                print(f"{idx}: 无数据")
        
        # 生成图表
        print(f"\n生成图表...")
        create_balance_sheet_chart(stock_code, data, report_date, is_sample)
        print("完成!")
    else:
        print("获取数据失败!")

if __name__ == "__main__":
    main()
