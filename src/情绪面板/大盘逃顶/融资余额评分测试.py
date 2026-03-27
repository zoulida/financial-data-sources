"""
融资余额评分规则测试
测试新的评分规则（v1.0.5）
"""

def test_financing_score_rules():
    """测试融资余额评分规则"""
    
    print("=" * 70)
    print("融资余额评分规则测试 (v1.0.5)")
    print("=" * 70)
    
    # 测试用例
    test_cases = [
        # (案例名称, 最近3日数据, 预期得分)
        ("3日全为负", [-100, -50, -80], 1.0),
        ("2日为负", [-100, 50, -80], 0.4),
        ("1日为负", [-100, 50, 80], 0.2),
        ("全部为正", [100, 50, 80], 0.0),
        ("前2日负后1日正", [-100, -50, 80], 0.4),
        ("前1日负后2日正", [-100, 50, 80], 0.2),
        ("前1日正后2日负", [100, -50, -80], 0.4),
        ("中间1日负", [100, -50, 80], 0.2),
    ]
    
    print("\n测试结果:")
    print(f"{'案例':20s} | {'数据(亿元)':>40s} | {'负日数':>8s} | {'预期':>8s} | {'实际':>8s} | {'结果':>8s}")
    print("-" * 100)
    
    for case_name, data, expected in test_cases:
        negative_days = sum(1 for v in data if v < 0)
        
        # 应用评分规则
        if negative_days == 3:
            actual = 1.0
        elif negative_days == 2:
            actual = 0.4
        elif negative_days == 1:
            actual = 0.2
        else:
            actual = 0.0
        
        # 格式化数据
        data_str = ", ".join([f"{v:+.0f}" for v in data])
        
        # 判断通过/失败
        passed = "✓ 通过" if abs(actual - expected) < 0.01 else "✗ 失败"
        
        print(f"{case_name:20s} | {data_str:>40s} | {negative_days:>8d} | {expected:>8.1f} | {actual:>8.1f} | {passed:>8s}")
    
    print("\n" + "=" * 70)
    print("评分规则说明")
    print("=" * 70)
    print("""
规则 v1.0.5 (最新):
  - 3日全为负 → 1.0分  (最高风险)
  - 2日为负   → 0.4分  (中度风险)
  - 1日为负   → 0.2分  (轻度风险) ⭐ 新增
  - 其他情况  → 0.0分  (正常)

规则 v1.0.4 (旧版):
  - 3日全为负 → 1.0分
  - 2日为负   → 0.4分
  - 其他情况  → 0.0分

变更说明:
  ✅ 增加了1日为负的情况，记0.2分
  ✅ 更精细的风险分级
  ✅ 提高预警敏感度
    """)


def show_score_comparison():
    """对比新旧评分规则"""
    
    print("\n" + "=" * 70)
    print("新旧规则对比")
    print("=" * 70)
    
    print(f"\n{'负日数':>10s} | {'旧规则(v1.0.4)':>20s} | {'新规则(v1.0.5)':>20s} | {'变化':>10s}")
    print("-" * 70)
    
    rules_old = {3: 1.0, 2: 0.4, 1: 0.0, 0: 0.0}
    rules_new = {3: 1.0, 2: 0.4, 1: 0.2, 0: 0.0}
    
    for neg_days in [3, 2, 1, 0]:
        old_score = rules_old[neg_days]
        new_score = rules_new[neg_days]
        change = new_score - old_score
        
        if change > 0:
            change_str = f"+{change:.1f} ⭐"
        elif change < 0:
            change_str = f"{change:.1f}"
        else:
            change_str = "无变化"
        
        print(f"{neg_days:>10d} | {old_score:>20.1f} | {new_score:>20.1f} | {change_str:>10s}")
    
    print("\n影响:")
    print("  ✅ 提高了单日异常的敏感度")
    print("  ✅ 能更早发现市场情绪转变")
    print("  ⚠️ 总分范围不变，仍为0-4.5分")


def show_real_examples():
    """显示实际场景示例"""
    
    print("\n" + "=" * 70)
    print("实际场景示例")
    print("=" * 70)
    
    scenarios = [
        {
            'name': '牛市顶部',
            'data': [-200, -150, -180],
            'description': '连续3日大额融资净流出，机构开始撤退'
        },
        {
            'name': '调整初期',
            'data': [-80, 120, -60],
            'description': '资金观望，出现分歧，2日净流出'
        },
        {
            'name': '震荡市场',
            'data': [-50, 80, 120],
            'description': '偶尔出现单日净流出，整体尚可'
        },
        {
            'name': '牛市中期',
            'data': [150, 200, 180],
            'description': '资金持续流入，市场热情高涨'
        }
    ]
    
    print()
    for scenario in scenarios:
        data = scenario['data']
        negative_days = sum(1 for v in data if v < 0)
        
        if negative_days == 3:
            score = 1.0
        elif negative_days == 2:
            score = 0.4
        elif negative_days == 1:
            score = 0.2
        else:
            score = 0.0
        
        data_str = ", ".join([f"{v:+.0f}亿" for v in data])
        
        print(f"场景: {scenario['name']}")
        print(f"  数据: {data_str}")
        print(f"  说明: {scenario['description']}")
        print(f"  得分: {score:.1f}分")
        
        if score >= 1.0:
            print(f"  判断: 🚨🚨 高风险！建议减仓")
        elif score >= 0.4:
            print(f"  判断: ⚠️ 中度风险，需要警惕")
        elif score >= 0.2:
            print(f"  判断: ⚠️ 轻度风险，保持关注")
        else:
            print(f"  判断: ✅ 正常，可以持仓")
        
        print()


if __name__ == "__main__":
    # 运行测试
    test_financing_score_rules()
    
    # 显示对比
    show_score_comparison()
    
    # 显示示例
    show_real_examples()
    
    print("\n提示:")
    print("  新规则从 v1.0.5 开始生效")
    print("  增加了1日为负记0.2分的情况")
    print("  使风险预警更加敏感和精细")

