"""
网格选股综合评分系统 - 使用示例

展示如何使用评分系统的各种场景

作者：AI Assistant
创建时间：2025-11-02
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from grid_stock_scoring import GridStockScorer


# ============================================================================
# 示例1：使用默认日期范围（自动获取）
# ============================================================================
def example_1_default_dates():
    """示例1：使用默认日期范围"""
    print("="*80)
    print("示例1：使用默认日期范围")
    print("="*80)
    
    # 创建评分器（自动获取日期范围）
    scorer = GridStockScorer()
    
    # 运行评分
    asyncio.run(scorer.run())


# ============================================================================
# 示例2：指定自定义日期范围
# ============================================================================
def example_2_custom_dates():
    """示例2：指定自定义日期范围"""
    print("="*80)
    print("示例2：指定自定义日期范围")
    print("="*80)
    
    # 创建评分器（自定义日期）
    scorer = GridStockScorer(
        start_date="20240101",  # 从2024年1月1日开始
        end_date="20241231"     # 到2024年12月31日
    )
    
    # 运行评分
    asyncio.run(scorer.run())


# ============================================================================
# 示例3：只处理部分标的（测试用）
# ============================================================================
async def example_3_test_run():
    """示例3：只处理部分标的进行测试"""
    print("="*80)
    print("示例3：测试模式（只处理前10只标的）")
    print("="*80)
    
    # 创建评分器
    scorer = GridStockScorer()
    
    # 1. 获取基金列表
    fund_df = scorer.get_fund_list()
    if fund_df is None or len(fund_df) == 0:
        print("❌ 错误：无法获取基金列表")
        return
    
    # 2. 只取前10只进行测试
    fund_df_test = fund_df.head(10)
    print(f"\n[测试模式] 只处理前 {len(fund_df_test)} 只标的")
    
    # 3. 处理
    results = await scorer.process_all_funds(fund_df_test)
    if results is None or len(results) == 0:
        print("❌ 错误：处理失败")
        return
    
    # 4. 最终化评分
    df_final = scorer.finalize_scores(results)
    
    # 5. 保存结果
    scorer.save_results(df_final)
    
    # 6. 打印摘要
    scorer.print_summary(df_final)


# ============================================================================
# 示例4：获取单只标的的详细评分信息
# ============================================================================
async def example_4_single_fund_detail():
    """示例4：获取单只标的的详细评分信息"""
    print("="*80)
    print("示例4：单只标的详细评分")
    print("="*80)
    
    # 创建评分器
    scorer = GridStockScorer()
    
    # 指定测试标的
    test_code = "159001.SZ"
    test_name = "易方达创业板ETF"
    
    print(f"\n正在计算 {test_name} ({test_code}) 的评分...")
    
    # 处理单只标的
    result = await scorer.process_single_fund(test_code, test_name)
    
    if result is None:
        print(f"❌ 错误：无法获取 {test_code} 的数据或计算失败")
        return
    
    # 重新计算HLScore（需要跨品种数据，这里简化处理）
    result['hl_score'] = result['hl_score']  # 暂时使用自身分位得分
    result['total'] = 0.7 * result['vol_score'] + 0.3 * result['hl_score']
    
    # 打印详细信息
    print("\n" + "="*80)
    print("评分结果详情")
    print("="*80)
    print(f"标的代码: {result['code']}")
    print(f"标的名称: {result['name']}")
    print(f"\n波动率指标:")
    print(f"  30日年化波动率: {result['hist30']:.2f}%")
    print(f"  VolScore: {result['vol_score']:.2f} 分")
    print(f"\n半衰期指标:")
    print(f"  当前半衰期: {result['hl']:.2f} 天")
    print(f"  HLScore: {result['hl_score']:.2f} 分")
    print(f"\n综合评分:")
    print(f"  Total: {result['total']:.2f} 分")
    print(f"  计算公式: 0.7×{result['vol_score']:.2f} + 0.3×{result['hl_score']:.2f} = {result['total']:.2f}")
    print("="*80)


# ============================================================================
# 示例5：批量处理并筛选高分标的
# ============================================================================
async def example_5_filter_high_scores():
    """示例5：批量处理并筛选高分标的"""
    print("="*80)
    print("示例5：筛选高分标的（Total > 70）")
    print("="*80)
    
    # 创建评分器
    scorer = GridStockScorer()
    
    # 运行完整流程
    await scorer.run()
    
    # 读取结果
    result_path = Path(__file__).parent / 'result.csv'
    if result_path.exists():
        import pandas as pd
        df = pd.read_csv(result_path)
        
        # 筛选高分标的
        high_score_df = df[df['total'] > 70]
        
        print("\n" + "="*80)
        print(f"高分标的（Total > 70）：共 {len(high_score_df)} 只")
        print("="*80)
        
        if len(high_score_df) > 0:
            print(high_score_df.to_string(index=False))
            
            # 保存高分标的
            high_score_path = Path(__file__).parent / 'high_score_funds.csv'
            high_score_df.to_csv(high_score_path, index=False, encoding='utf-8-sig')
            print(f"\n✅ 高分标的已保存到: {high_score_path}")
        else:
            print("未找到总分超过70分的标的")


# ============================================================================
# 主函数：选择运行哪个示例
# ============================================================================
def main():
    """主函数：选择运行示例"""
    print("\n")
    print("="*80)
    print("网格选股综合评分系统 - 使用示例")
    print("="*80)
    print("\n请选择要运行的示例：")
    print("  1. 使用默认日期范围（推荐）")
    print("  2. 指定自定义日期范围")
    print("  3. 测试模式（只处理前10只）")
    print("  4. 单只标的详细评分")
    print("  5. 批量处理并筛选高分标的")
    print("  0. 退出")
    
    try:
        choice = input("\n请输入选项（0-5）: ").strip()
        
        if choice == "1":
            example_1_default_dates()
        elif choice == "2":
            example_2_custom_dates()
        elif choice == "3":
            asyncio.run(example_3_test_run())
        elif choice == "4":
            asyncio.run(example_4_single_fund_detail())
        elif choice == "5":
            asyncio.run(example_5_filter_high_scores())
        elif choice == "0":
            print("退出程序")
            return
        else:
            print("❌ 无效选项，请输入0-5之间的数字")
            return
        
        print("\n✅ 示例运行完成！")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

