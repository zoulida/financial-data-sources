"""
量价背离评分规则测试 (v1.0.6 新规则)
测试按萎缩幅度比例计分
"""

def calculate_divergence_score(shrink_rate):
    """
    计算单日量价背离得分
    
    参数:
        shrink_rate: 成交量萎缩率 (0.0-1.0)
    
    返回:
        score: 得分
    """
    if shrink_rate < 0.05:
        return 0.0
    elif shrink_rate >= 0.20:
        return 1.0
    else:
        # 5%-20%之间线性插值
        return 0.2 + (shrink_rate - 0.05) / 0.15 * 0.8


def test_scoring_rules():
    """测试量价背离评分规则"""
    
    print("=" * 70)
    print("量价背离评分规则测试 (v1.0.6)")
    print("=" * 70)
    
    print("\n新规则:")
    print("  - 萎缩 < 5%: 0分")
    print("  - 萎缩 = 5%: 0.2分")
    print("  - 萎缩 5%-20%: 0.2 + (萎缩率-5%)/(20%-5%) * 0.8")
    print("  - 萎缩 ≥ 20%: 1.0分")
    print("  - 多日得分求和")
    
    # 测试用例
    test_cases = [
        # (萎缩率%, 描述)
        (0, "无萎缩"),
        (3, "轻微萎缩"),
        (5, "达到阈值"),
        (8, "轻度背离"),
        (10, "轻度背离"),
        (12, "中度背离"),
        (15, "中度背离"),
        (18, "较重背离"),
        (20, "重度背离"),
        (25, "严重背离"),
        (30, "极度背离"),
    ]
    
    print("\n" + "=" * 70)
    print("单日得分测试")
    print("=" * 70)
    print(f"{'萎缩率':>10s} | {'描述':>12s} | {'得分':>8s} | {'计算公式':>35s}")
    print("-" * 70)
    
    for shrink_pct, desc in test_cases:
        shrink_rate = shrink_pct / 100.0
        score = calculate_divergence_score(shrink_rate)
        
        if shrink_pct < 5:
            formula = "< 5%, 不计分"
        elif shrink_pct == 5:
            formula = "= 5%, 基础分"
        elif shrink_pct < 20:
            formula = f"0.2 + ({shrink_pct}-5)/(20-5)*0.8"
        else:
            formula = "≥ 20%, 满分"
        
        print(f"{shrink_pct:>9.0f}% | {desc:>12s} | {score:>8.2f} | {formula:>35s}")


def test_multi_day_scenarios():
    """测试多日累计场景"""
    
    print("\n" + "=" * 70)
    print("多日累计场景测试")
    print("=" * 70)
    
    scenarios = [
        {
            'name': '正常市场',
            'days': [
                (True, 2),   # 涨2%, 量缩2%
                (True, 3),   # 涨, 量缩3%
                (False, 5),  # 跌, 量缩5%
                (True, 1),   # 涨, 量缩1%
                (False, 8),  # 跌, 量缩8%
            ],
            'description': '偶有小幅萎缩，整体正常'
        },
        {
            'name': '轻度预警',
            'days': [
                (True, 6),   # 涨, 量缩6%
                (True, 8),   # 涨, 量缩8%
                (True, 7),   # 涨, 量缩7%
                (False, 5),  # 跌, 量缩5%
                (True, 2),   # 涨, 量缩2%
            ],
            'description': '连续3日量价背离，萎缩幅度不大'
        },
        {
            'name': '中度风险',
            'days': [
                (True, 12),  # 涨, 量缩12%
                (True, 15),  # 涨, 量缩15%
                (False, 8),  # 跌, 量缩8%
                (True, 10),  # 涨, 量缩10%
                (True, 18),  # 涨, 量缩18%
            ],
            'description': '多日中度萎缩，需要警惕'
        },
        {
            'name': '高度风险',
            'days': [
                (True, 22),  # 涨, 量缩22%
                (True, 25),  # 涨, 量缩25%
                (True, 20),  # 涨, 量缩20%
                (True, 18),  # 涨, 量缩18%
                (True, 15),  # 涨, 量缩15%
            ],
            'description': '连续5日量价背离，萎缩严重'
        },
        {
            'name': '实际案例',
            'days': [
                (True, 19.5),  # 20251015
                (True, 7.7),   # 20251016
                (False, 15),   # 跌
                (True, 11.1),  # 20251020
                (False, 5),    # 跌
            ],
            'description': '实际运行结果：3日背离'
        }
    ]
    
    print()
    for scenario in scenarios:
        print(f"\n场景: {scenario['name']}")
        print(f"说明: {scenario['description']}")
        print(f"\n  {'日期':>8s} | {'涨跌':>6s} | {'量缩率':>8s} | {'是否背离':>10s} | {'单日得分':>10s}")
        print("  " + "-" * 60)
        
        total_score = 0.0
        divergence_count = 0
        
        for idx, (price_up, shrink_pct) in enumerate(scenario['days'], 1):
            shrink_rate = shrink_pct / 100.0
            is_divergence = price_up and shrink_rate >= 0.05
            
            if is_divergence:
                day_score = calculate_divergence_score(shrink_rate)
                total_score += day_score
                divergence_count += 1
            else:
                day_score = 0.0
            
            price_status = "涨" if price_up else "跌"
            divergence_status = "✓ 是" if is_divergence else "✗ 否"
            
            print(f"  Day{idx:>4d} | {price_status:>6s} | {shrink_pct:>7.1f}% | {divergence_status:>10s} | {day_score:>10.2f}")
        
        print(f"\n  背离天数: {divergence_count}")
        print(f"  总得分: {total_score:.2f}")
        
        if total_score >= 2.0:
            print(f"  判断: 🚨 高风险，强烈逃顶信号")
        elif total_score >= 1.0:
            print(f"  判断: ⚠️ 中度风险，需要警惕")
        elif total_score >= 0.5:
            print(f"  判断: ⚠️ 轻度风险，保持关注")
        else:
            print(f"  判断: ✅ 正常，可以持仓")


def compare_old_new_rules():
    """对比新旧规则"""
    
    print("\n" + "=" * 70)
    print("新旧规则对比")
    print("=" * 70)
    
    print("\n旧规则 (v1.0.5):")
    print("  - 只有萎缩≥20%才计分")
    print("  - 1日→1分, 2日→1.5分, 3日+→继续+0.5")
    
    print("\n新规则 (v1.0.6):")
    print("  - 萎缩≥5%就计分")
    print("  - 5%→0.2分, 20%→1.0分, 中间线性插值")
    print("  - 多日求和")
    
    print("\n优势对比:")
    print("  ✅ 更早捕捉风险信号（5% vs 20%）")
    print("  ✅ 更精细的分级（连续计分 vs 阶梯计分）")
    print("  ✅ 更合理的累计（求和 vs 固定加分）")
    print("  ✅ 分数范围更大（0-5分 vs 0-3分）")
    
    # 对比示例
    print("\n典型场景对比:")
    print(f"\n  {'场景':20s} | {'萎缩情况':>30s} | {'旧规则':>10s} | {'新规则':>10s} | {'差异':>10s}")
    print("  " + "-" * 85)
    
    comparison_cases = [
        ("轻度背离", "3日萎缩10%", 0.0, 3*calculate_divergence_score(0.10)),
        ("中度背离", "2日萎缩15%, 1日萎缩25%", 1.5, 2*calculate_divergence_score(0.15)+1.0),
        ("重度背离", "3日萎缩25%", 2.0, 3.0),
        ("实际案例", "19.5%, 7.7%, 11.1%", 1.0, 
         calculate_divergence_score(0.195)+calculate_divergence_score(0.077)+calculate_divergence_score(0.111)),
    ]
    
    for name, desc, old_score, new_score in comparison_cases:
        diff = new_score - old_score
        diff_str = f"{diff:+.2f}"
        print(f"  {name:20s} | {desc:>30s} | {old_score:>10.2f} | {new_score:>10.2f} | {diff_str:>10s}")


if __name__ == "__main__":
    # 运行所有测试
    test_scoring_rules()
    test_multi_day_scenarios()
    compare_old_new_rules()
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
    print("\n说明:")
    print("  新规则 (v1.0.6) 提供了更灵敏、更精细的量价背离评分")
    print("  可以更早发现市场风险信号")
    print("  建议配合其他指标综合判断")

