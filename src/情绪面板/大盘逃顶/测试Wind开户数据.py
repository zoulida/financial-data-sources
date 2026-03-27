"""
测试 Wind API 开户数据获取
验证 M0010401 字段是否正常工作
"""

from WindPy import w
import pandas as pd
from datetime import datetime, timedelta

def test_wind_account_data():
    """测试Wind开户数据获取"""
    
    print("=" * 70)
    print("Wind API - 开户数据获取测试")
    print("=" * 70)
    
    try:
        # 启动 Wind API
        print("\n[1/4] 启动 Wind API...")
        w.start()
        print("  ✓ Wind API 启动成功")
        
        # 设置日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        print(f"\n[2/4] 获取开户数据...")
        print(f"  日期范围: {start_date} 至 {end_date}")
        print(f"  数据字段: M0010401 (新增投资者数量)")
        
        # 使用 edb 接口获取数据
        data = w.edb("M0010401", start_date, end_date, "Fill=Previous")
        
        # 检查错误
        if data.ErrorCode != 0:
            print(f"  ✗ 错误码: {data.ErrorCode}")
            if data.ErrorCode == -40520007:
                print(f"  错误信息: 没有可用数据")
            elif data.ErrorCode == -40520010:
                print(f"  错误信息: 时间区间无数据")
            else:
                print(f"  错误信息: {data.Data}")
            w.stop()
            return
        
        print("  ✓ 数据获取成功")
        
        # 解析数据
        print("\n[3/4] 解析数据...")
        
        if not data.Data or len(data.Data[0]) == 0:
            print("  ✗ 返回数据为空")
            w.stop()
            return
        
        times = data.Times
        values = data.Data[0]
        
        print(f"  返回数据点数: {len(values)}")
        
        # 转换为DataFrame
        df = pd.DataFrame({
            'date': times,
            'value': values
        })
        
        # 按日期降序排列
        df = df.sort_values('date', ascending=False)
        
        print(f"  数据范围: {df.iloc[-1]['date'].strftime('%Y-%m')} 至 {df.iloc[0]['date'].strftime('%Y-%m')}")
        
        # 获取最近两个月数据
        print("\n[4/4] 最近两个月开户数:")
        
        if len(df) < 2:
            print("  ✗ 数据不足2个月")
            w.stop()
            return
        
        recent_two = df.head(2)
        last_month = float(recent_two.iloc[0]['value'])
        prev_month = float(recent_two.iloc[1]['value'])
        last_date = recent_two.iloc[0]['date'].strftime('%Y-%m')
        prev_date = recent_two.iloc[1]['date'].strftime('%Y-%m')
        
        print(f"  {prev_date}: {prev_month:.2f} 万户")
        print(f"  {last_date}: {last_month:.2f} 万户")
        
        # 计算环比
        if prev_month > 0:
            change_rate = (last_month - prev_month) / prev_month * 100
            decline_rate = -change_rate
            
            print(f"  环比变化: {change_rate:+.1f}%")
            print(f"  环比降幅: {decline_rate:.1f}%")
            
            # 评分测试
            print(f"\n评分测试（新规则）:")
            if decline_rate >= 30:
                score = 1.5
                print(f"  降幅 ≥30% → 得分: {score:.2f} ⚠️⚠️ 强烈逃顶信号")
            elif decline_rate > 0:
                score = decline_rate / 30.0 * 1.5
                print(f"  降幅 {decline_rate:.1f}% → 得分: {score:.2f}")
            else:
                score = 0.0
                print(f"  降幅 {decline_rate:.1f}% → 得分: {score:.2f} ✓ 正常")
        
        # 显示最近6个月数据
        print(f"\n最近6个月开户数据:")
        display_df = df.head(6).copy()
        display_df['date_str'] = display_df['date'].dt.strftime('%Y-%m')
        display_df['value_str'] = display_df['value'].apply(lambda x: f"{x:.2f}万")
        
        print(f"{'日期':>10s} | {'新增开户数':>15s}")
        print("-" * 30)
        for _, row in display_df.iterrows():
            print(f"{row['date_str']:>10s} | {row['value_str']:>15s}")
        
        # 趋势分析
        print(f"\n趋势分析:")
        recent_6 = df.head(6)['value'].tolist()
        avg_6 = sum(recent_6) / len(recent_6)
        current = recent_6[0]
        
        if current < avg_6 * 0.7:
            print(f"  ⚠️⚠️ 当前开户数({current:.2f}万)远低于近6个月平均({avg_6:.2f}万)")
            print(f"      散户入市热情极度低迷")
        elif current < avg_6:
            print(f"  ⚠️ 当前开户数({current:.2f}万)低于近6个月平均({avg_6:.2f}万)")
            print(f"     散户入市热情下降")
        else:
            print(f"  ✓ 当前开户数({current:.2f}万)高于近6个月平均({avg_6:.2f}万)")
            print(f"    散户入市热情正常或升温")
        
        print("\n" + "=" * 70)
        print("测试完成！")
        print("=" * 70)
        
        w.stop()
        print("\n✓ Wind API 已关闭")
        
    except ImportError:
        print("  ✗ WindPy 未安装")
        print("  请先安装 Wind 终端，然后运行: pip install WindPy")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            w.stop()
        except:
            pass


def show_wind_edb_info():
    """显示Wind经济数据库字段信息"""
    
    print("\n" + "=" * 70)
    print("Wind 经济数据库 (EDB) 开户数据字段说明")
    print("=" * 70)
    
    print("\n常用字段:")
    print(f"{'字段代码':>12s} | {'字段名称':>20s} | {'单位':>8s} | {'频率':>8s}")
    print("-" * 70)
    print(f"{'M0010401':>12s} | {'新增投资者数量':>20s} | {'万户':>8s} | {'月度':>8s}")
    print(f"{'M0001780':>12s} | {'新增A股账户数':>20s} | {'万户':>8s} | {'月度':>8s}")
    print(f"{'M0001781':>12s} | {'期末投资者总数':>20s} | {'万户':>8s} | {'月度':>8s}")
    
    print("\n推荐使用: M0010401 (新增投资者数量)")
    print("  - 数据最新")
    print("  - 包含所有类型投资者")
    print("  - 月度更新")
    
    print("\nWind API 调用示例:")
    print("""
    from WindPy import w
    w.start()
    
    # 获取最近3个月数据
    data = w.edb("M0010401", "2025-07-01", "2025-10-20", "Fill=Previous")
    
    # 数据访问
    times = data.Times      # 日期列表
    values = data.Data[0]   # 数值列表
    
    w.stop()
    """)


if __name__ == "__main__":
    # 运行测试
    test_wind_account_data()
    
    # 显示字段信息
    show_wind_edb_info()
    
    print("\n提示:")
    print("  如果测试成功，说明 Wind API 配置正确")
    print("  现在可以运行主程序: python escape_top_scorer.py")

