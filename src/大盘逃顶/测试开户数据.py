"""
测试 akshare 开户数据获取
验证修复后的代码是否正常工作
"""

import akshare as ak
import pandas as pd
from datetime import datetime

def test_account_data():
    """测试开户数据获取"""
    
    print("=" * 70)
    print("akshare - 开户数据获取测试")
    print("=" * 70)
    
    try:
        # 获取开户数据
        print("\n[1/3] 获取开户数据...")
        df = ak.stock_account_statistics_em()
        
        if df is None or len(df) == 0:
            print("  ✗ 未获取到数据")
            return
        
        print(f"  ✓ 数据获取成功，共 {len(df)} 条记录")
        
        # 显示字段
        print(f"\n[2/3] 数据字段:")
        print(f"  {list(df.columns)}")
        
        # 处理数据
        print("\n[3/3] 数据处理...")
        df['数据日期'] = pd.to_datetime(df['数据日期'])
        df = df.sort_values('数据日期', ascending=False)
        
        print(f"  数据范围: {df['数据日期'].min().strftime('%Y-%m')} 至 {df['数据日期'].max().strftime('%Y-%m')}")
        
        # 获取最近两个月数据
        recent_two = df.head(2)
        
        if len(recent_two) < 2:
            print("  ✗ 数据不足2个月")
            return
        
        last_month = float(recent_two.iloc[0]['新增投资者-数量'])
        prev_month = float(recent_two.iloc[1]['新增投资者-数量'])
        last_date = recent_two.iloc[0]['数据日期'].strftime('%Y-%m')
        prev_date = recent_two.iloc[1]['数据日期'].strftime('%Y-%m')
        
        # 计算环比
        change_rate = (last_month - prev_month) / prev_month * 100 if prev_month > 0 else 0
        decline_rate = -change_rate  # 降幅为正数
        
        print(f"\n最近两个月开户数:")
        print(f"  {prev_date}: {prev_month:.2f} 万户")
        print(f"  {last_date}: {last_month:.2f} 万户")
        print(f"  环比变化: {change_rate:+.1f}%")
        print(f"  环比降幅: {decline_rate:.1f}%")
        
        # 评分测试
        print(f"\n评分测试（新规则）:")
        if decline_rate >= 30:
            score = 1.5
            print(f"  降幅 ≥30% → 得分: {score:.2f} ⚠️ 强烈逃顶信号")
        elif decline_rate > 0:
            score = decline_rate / 30.0 * 1.5
            print(f"  降幅 {decline_rate:.1f}% → 得分: {score:.2f}")
        else:
            score = 0.0
            print(f"  降幅 {decline_rate:.1f}% → 得分: {score:.2f} ✓ 正常")
        
        # 显示历史数据
        print(f"\n最近6个月开户数据:")
        display_df = df.head(6)[['数据日期', '新增投资者-数量', 
                                  '期末投资者-总量', '上证指数-收盘']].copy()
        display_df['数据日期'] = display_df['数据日期'].dt.strftime('%Y-%m')
        display_df['新增投资者-数量'] = display_df['新增投资者-数量'].apply(lambda x: f"{x:.2f}万")
        display_df['期末投资者-总量'] = display_df['期末投资者-总量'].apply(lambda x: f"{x:.2f}万")
        display_df['上证指数-收盘'] = display_df['上证指数-收盘'].apply(lambda x: f"{x:.2f}")
        
        display_df.columns = ['日期', '新增开户(万户)', '期末总量(万户)', '上证指数']
        print(display_df.to_string(index=False))
        
        # 分析趋势
        print(f"\n趋势分析:")
        recent_6 = df.head(6)['新增投资者-数量'].tolist()
        avg_6 = sum(recent_6) / len(recent_6)
        current = recent_6[0]
        
        if current < avg_6 * 0.7:
            print(f"  ⚠️ 当前开户数({current:.2f}万)远低于近6个月平均({avg_6:.2f}万)")
        elif current < avg_6:
            print(f"  ⚠️ 当前开户数({current:.2f}万)低于近6个月平均({avg_6:.2f}万)")
        else:
            print(f"  ✓ 当前开户数({current:.2f}万)高于近6个月平均({avg_6:.2f}万)")
        
        print("\n" + "=" * 70)
        print("测试完成！")
        print("=" * 70)
        
        # 提示
        print("\n⚠️ 注意:")
        print("  - akshare 开户数据目前更新到 2023-08")
        print("  - 如需最新数据，请使用 Wind API")
        print("  - 数据来源: 东方财富网/中国结算")
        
    except ImportError:
        print("  ✗ akshare 未安装")
        print("  请运行: pip install akshare")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def compare_scoring_rules():
    """对比新旧评分规则"""
    
    print("\n" + "=" * 70)
    print("评分规则对比")
    print("=" * 70)
    
    print("\n测试不同降幅下的得分:")
    print(f"{'降幅':>10s} | {'旧规则(满分1.0)':>20s} | {'新规则(满分1.5)':>20s} | {'变化':>10s}")
    print("-" * 70)
    
    test_declines = [0, 5, 10, 15, 20, 25, 30, 35, 40]
    
    for decline in test_declines:
        # 旧规则
        if decline >= 30:
            old_score = 1.0
        elif decline > 0:
            old_score = decline / 30.0
        else:
            old_score = 0.0
        
        # 新规则
        if decline >= 30:
            new_score = 1.5
        elif decline > 0:
            new_score = decline / 30.0 * 1.5
        else:
            new_score = 0.0
        
        change = new_score - old_score
        change_str = f"+{change:.2f}" if change > 0 else f"{change:.2f}"
        
        print(f"{decline:>9.0f}% | {old_score:>18.2f}分 | {new_score:>18.2f}分 | {change_str:>9s}")
    
    print("\n说明:")
    print("  - 新规则提高了开户数指标的权重")
    print("  - 开户数大幅下降时，得分提升50%")
    print("  - 更加重视散户退场的风险信号")


if __name__ == "__main__":
    # 运行测试
    test_account_data()
    
    # 对比评分规则
    compare_scoring_rules()
    
    print("\n提示:")
    print("  如果测试成功，说明 akshare 配置正确")
    print("  现在可以运行主程序: python escape_top_scorer.py")

