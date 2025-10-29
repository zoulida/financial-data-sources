"""
测试 Wind API 融资余额数据获取
验证修复后的代码是否正常工作
"""

from WindPy import w
import pandas as pd
from datetime import datetime, timedelta

def test_margin_data():
    """测试融资余额数据获取"""
    
    print("=" * 70)
    print("Wind API - 融资余额数据获取测试")
    print("=" * 70)
    
    try:
        # 启动 Wind API
        print("\n[1/4] 启动 Wind API...")
        w.start()
        print("  ✓ Wind API 启动成功")
        
        # 设置日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        print(f"\n[2/4] 获取融资融券数据...")
        print(f"  日期范围: {start_date} 至 {end_date}")
        
        # 使用 wset 接口获取数据
        params = (
            f"exchange=all;"
            f"startdate={start_date};"
            f"enddate={end_date};"
            f"frequency=day;"
            f"sort=desc"  # 降序，最新数据在前
        )
        
        data = w.wset("margintradingsizeanalys(value)", params)
        
        # 检查错误
        if data.ErrorCode != 0:
            print(f"  ✗ 错误码: {data.ErrorCode}")
            print(f"  错误信息: {data.Data}")
            return
        
        print("  ✓ 数据获取成功")
        
        # 解析数据
        print("\n[3/4] 解析数据...")
        print(f"  返回字段: {data.Fields}")
        
        df = pd.DataFrame(data.Data, index=data.Fields).T
        df.columns = data.Fields
        
        print(f"  数据行数: {len(df)}")
        print(f"  数据列数: {len(df.columns)}")
        
        # 检查期间净买入额字段
        if 'period_net_purchases' in df.columns:
            print("  ✓ 找到 'period_net_purchases' 字段")
            
            # 获取最近3日数据
            net_buy_values = df['period_net_purchases'].head(3).tolist()
            net_buy_values = [float(v) for v in net_buy_values if v is not None and str(v) != 'nan']
            
            print(f"\n[4/4] 最近3日融资净买入额:")
            for i, v in enumerate(net_buy_values):
                status = "📉" if v < 0 else "📈"
                print(f"  第{i+1}日: {status} {v/100000000:+.2f} 亿元")
            
            # 评分测试
            negative_days = sum(1 for v in net_buy_values if v < 0)
            
            print(f"\n评分测试:")
            print(f"  负值天数: {negative_days}/{len(net_buy_values)}")
            
            if len(net_buy_values) == 3 and negative_days == 3:
                score = 1.0
                print(f"  ✓ 3日全为负 → 得分: {score}")
            elif negative_days == 2:
                score = 0.4
                print(f"  ✓ 2日为负 → 得分: {score}")
            else:
                score = 0.0
                print(f"  ✓ 正常情况 → 得分: {score}")
            
            # 显示完整数据
            print(f"\n完整数据（最近5日）:")
            display_df = df.head(5)[['end_date', 'margin_balance', 
                                      'period_net_purchases', 
                                      'margin_balance_ratio_negmktcap']].copy()
            
            # 格式化显示
            display_df['margin_balance'] = display_df['margin_balance'].apply(
                lambda x: f"{float(x)/1e8:.2f}亿" if x is not None else 'N/A'
            )
            display_df['period_net_purchases'] = display_df['period_net_purchases'].apply(
                lambda x: f"{float(x)/1e8:+.2f}亿" if x is not None else 'N/A'
            )
            display_df['margin_balance_ratio_negmktcap'] = display_df['margin_balance_ratio_negmktcap'].apply(
                lambda x: f"{float(x):.2f}%" if x is not None else 'N/A'
            )
            
            display_df.columns = ['日期', '融资余额', '期间净买入额', '余额占流通市值比']
            print(display_df.to_string(index=False))
            
        else:
            print("  ✗ 未找到 'period_net_purchases' 字段")
            print(f"  可用字段: {list(df.columns)}")
        
        print("\n" + "=" * 70)
        print("测试完成！")
        print("=" * 70)
        
    except ImportError:
        print("  ✗ WindPy 未安装")
        print("  请先安装 Wind 终端，然后运行: pip install WindPy")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 关闭连接
        try:
            w.stop()
            print("\n✓ Wind API 已关闭")
        except:
            pass


def compare_methods():
    """对比新旧方法（仅用于演示）"""
    
    print("\n" + "=" * 70)
    print("新旧方法对比")
    print("=" * 70)
    
    print("\n❌ 旧方法（不推荐）:")
    print("""
    data = w.wsd("881001.WI", "margin_netbuyamt", start_date, end_date, "")
    
    问题:
    - 不是标准接口
    - 数据可能不稳定
    - 字段名称不清晰
    """)
    
    print("\n✅ 新方法（推荐）:")
    print("""
    params = (
        f"exchange=all;"
        f"startdate={start_date};"
        f"enddate={end_date};"
        f"frequency=day;"
        f"sort=desc"
    )
    data = w.wset("margintradingsizeanalys(value)", params)
    
    优势:
    - ✓ 官方推荐的标准接口
    - ✓ 数据稳定可靠
    - ✓ 字段名称清晰 (period_net_purchases)
    - ✓ 支持多种频率 (日/周/月)
    - ✓ 字段更丰富完整
    """)


if __name__ == "__main__":
    # 运行测试
    test_margin_data()
    
    # 显示方法对比
    compare_methods()
    
    print("\n提示:")
    print("  如果测试成功，说明 Wind API 配置正确")
    print("  现在可以运行主程序: python escape_top_scorer.py")

