"""
测试Wind API获取估值数据
验证Wind全A指数PE数据获取
"""

def test_wind_valuation():
    """测试Wind全A指数PE数据获取"""
    print("=" * 70)
    print("测试 Wind API - Wind全A指数PE数据")
    print("=" * 70)
    
    try:
        from WindPy import w
        from datetime import datetime, timedelta
        import pandas as pd
        
        print("\n[1/5] 启动 Wind API...")
        w.start()
        print("  ✓ Wind API 启动成功")
        
        # 获取近5年数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365*5+30)).strftime('%Y-%m-%d')
        
        print(f"\n[2/5] 获取PE数据...")
        print(f"  指数代码: 881001.WI (Wind全A指数)")
        print(f"  数据字段: pe (市盈率)")
        print(f"  日期范围: {start_date} 至 {end_date}")
        print(f"  参数: ruleType=10 (按交易日对齐)")
        
        data = w.wsd("881001.WI", "pe", start_date, end_date, "ruleType=10")
        
        if data.ErrorCode != 0:
            print(f"\n  ✗ Wind API错误码: {data.ErrorCode}")
            w.stop()
            return False
        
        print(f"  ✓ 数据获取成功")
        
        print(f"\n[3/5] 解析数据...")
        
        # 转换为DataFrame
        df = pd.DataFrame({
            'date': data.Times,
            'pe': data.Data[0]
        })
        
        print(f"  返回数据点数: {len(df)}")
        
        # 过滤掉None值
        df = df[df['pe'].notna()]
        print(f"  有效数据点数: {len(df)}")
        
        if len(df) < 100:
            print(f"  ✗ 数据不足")
            w.stop()
            return False
        
        print(f"\n[4/5] 数据预览（最近10个交易日）:")
        print(df.tail(10).to_string())
        
        # 计算统计信息
        current_pe = df.iloc[-1]['pe']
        current_date = df.iloc[-1]['date'].strftime('%Y-%m-%d')
        min_pe = df['pe'].min()
        max_pe = df['pe'].max()
        mean_pe = df['pe'].mean()
        
        # 计算百分位
        percentile = (df['pe'] < current_pe).sum() / len(df) * 100
        
        print(f"\n[5/5] PE统计信息:")
        print(f"  数据范围: {df.iloc[0]['date'].strftime('%Y-%m-%d')} 至 {current_date}")
        print(f"  交易日数: {len(df)}")
        print(f"  当前PE: {current_pe:.2f}")
        print(f"  近{len(df)}日最小PE: {min_pe:.2f}")
        print(f"  近{len(df)}日最大PE: {max_pe:.2f}")
        print(f"  近{len(df)}日平均PE: {mean_pe:.2f}")
        print(f"  当前百分位: {percentile:.1f}%")
        
        # 测试评分规则
        print(f"\n评分测试（新规则）:")
        
        if percentile >= 95:
            score = 1.0
            level = "极高估值"
        elif percentile <= 60:
            score = 0.0
            level = "合理估值"
        else:
            score = (percentile - 60) / (95 - 60)
            level = "中等估值"
        
        print(f"  百分位 {percentile:.1f}% → 得分: {score:.2f} ({level})")
        
        # 显示各个阈值的得分
        print(f"\n评分规则示例:")
        test_percentiles = [50, 60, 70, 80, 90, 95, 98]
        for p in test_percentiles:
            if p >= 95:
                s = 1.0
            elif p <= 60:
                s = 0.0
            else:
                s = (p - 60) / (95 - 60)
            print(f"  百分位 {p:>3.0f}% → 得分: {s:.2f}")
        
        w.stop()
        print("\n✅ Wind估值数据测试成功！")
        return True
        
    except ImportError:
        print(f"\n✗ WindPy 未安装")
        print(f"  提示：请先安装 Wind 终端")
        return False
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        try:
            w.stop()
        except:
            pass
        return False


def compare_scoring_rules():
    """对比新旧评分规则"""
    print("\n" + "=" * 70)
    print("评分规则对比")
    print("=" * 70)
    
    print("\n旧规则 (v1.0.5):")
    print("  - 百分位≤80% → 0分")
    print("  - 百分位80%-95% → 线性插值")
    print("  - 百分位≥95% → 1分")
    
    print("\n新规则 (v1.0.6):")
    print("  - 百分位≤60% → 0分 ⭐")
    print("  - 百分位60%-95% → 线性插值")
    print("  - 百分位≥95% → 1分")
    
    print("\n变化说明:")
    print("  ✅ 下限从80%降至60%，更早预警")
    print("  ✅ 数据源从akshare改为Wind API，更可靠")
    print("  ✅ 使用Wind全A指数，更全面")
    
    print("\n" + "=" * 70)
    print("百分位得分对比表")
    print("=" * 70)
    
    print(f"\n{'百分位':>10s} | {'旧规则':>10s} | {'新规则':>10s} | {'差异':>10s} | {'说明':>15s}")
    print("-" * 65)
    
    percentiles = [50, 60, 70, 75, 80, 85, 90, 95, 98]
    
    for p in percentiles:
        # 旧规则
        if p >= 95:
            old_score = 1.0
        elif p <= 80:
            old_score = 0.0
        else:
            old_score = (p - 80) / (95 - 80)
        
        # 新规则
        if p >= 95:
            new_score = 1.0
        elif p <= 60:
            new_score = 0.0
        else:
            new_score = (p - 60) / (95 - 60)
        
        diff = new_score - old_score
        
        if diff > 0:
            note = "更敏感 ⭐"
        elif diff < 0:
            note = "更保守"
        else:
            note = "相同"
        
        print(f"{p:>9.0f}% | {old_score:>10.2f} | {new_score:>10.2f} | {diff:>+10.2f} | {note:>15s}")


if __name__ == "__main__":
    print("\nWind估值数据测试工具")
    print("=" * 70)
    print("测试Wind API获取Wind全A指数PE数据")
    print("=" * 70)
    
    # 运行测试
    success = test_wind_valuation()
    
    # 对比规则
    if success:
        compare_scoring_rules()
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
    
    if success:
        print("\n提示:")
        print("  ✅ Wind估值数据获取正常")
        print("  ✅ 新规则(60%-95%)比旧规则(80%-95%)更敏感")
        print("  ✅ 建议使用新规则进行逃顶评分")
    else:
        print("\n提示:")
        print("  ⚠️ 请确保 Wind 终端已启动并登录")
        print("  ⚠️ 确保有足够的权限访问Wind全A指数数据")

