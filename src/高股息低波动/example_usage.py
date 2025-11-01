"""使用示例 - 展示不同的使用场景."""

from pathlib import Path
from main import HighDividendLowVolatilitySelector
from config import Config
from stock_filter import StockFilter
from scoring import StockScorer


def example1_quick_start() -> None:
    """示例1: 快速开始 - 使用默认参数."""
    print("=" * 80)
    print("示例1: 快速开始")
    print("=" * 80)
    
    # 直接运行，使用所有默认参数
    selector = HighDividendLowVolatilitySelector(top_n=30)
    result = selector.run()
    
    print("\n前10只股票:")
    print(result[["stock_code", "stock_name", "dividend_yield", "composite_score"]].head(10))


def example2_custom_config() -> None:
    """示例2: 自定义配置参数."""
    print("\n" + "=" * 80)
    print("示例2: 自定义配置")
    print("=" * 80)
    
    # 创建自定义配置
    config = Config()
    
    # 调整参数
    config.filter.min_dividend_years = 5  # 提高到5年
    config.filter.min_dividend_yield = 5.0  # 提高到5%
    config.output.top_n = 50  # 选取50只
    
    # 打印配置
    config.print_config()
    
    # 使用自定义配置创建筛选器
    selector = HighDividendLowVolatilitySelector(top_n=config.output.top_n)
    
    # 注意: 需要手动传递配置到各个模块
    selector.filter_engine = StockFilter(
        min_dividend_years=config.filter.min_dividend_years,
        min_dividend_yield=config.filter.min_dividend_yield,
        payout_ratio_range=config.filter.payout_ratio_range,
        min_roe=config.filter.min_roe,
        volatility_percentile=config.filter.volatility_percentile,
    )
    
    selector.scorer = StockScorer(
        dividend_factor_weight=config.scoring.dividend_factor_weight,
        volatility_factor_weight=config.scoring.volatility_factor_weight,
        yield_score_weight=config.scoring.yield_score_weight,
        stability_score_weight=config.scoring.stability_score_weight,
    )
    
    # 运行筛选
    result = selector.run()
    print(f"\n成功筛选出 {len(result)} 只股票")


def example3_step_by_step() -> None:
    """示例3: 分步执行 - 更精细的控制."""
    print("\n" + "=" * 80)
    print("示例3: 分步执行")
    print("=" * 80)
    
    selector = HighDividendLowVolatilitySelector(top_n=30)
    
    # 第一步: 构建股票池
    print("\n执行第一步: 构建选股宇宙")
    stocks = selector.step1_build_universe()
    print(f"股票池数量: {len(stocks)}")
    
    # 第二步: 获取数据
    print("\n执行第二步: 获取数据")
    dividend_df, financial_df, payout_df, volatility_df = selector.step2_fetch_data(stocks)
    
    # 第三步: 筛选
    print("\n执行第三步: 应用筛选")
    filtered_df = selector.step3_apply_filters(
        dividend_df, financial_df, payout_df, volatility_df
    )
    print(f"筛选后数量: {len(filtered_df)}")
    
    # 第四步: 打分
    print("\n执行第四步: 打分排名")
    top_stocks, full_ranking = selector.step4_score_and_rank(filtered_df)
    print(f"最终选出: {len(top_stocks)} 只")
    
    # 查看详细结果
    print("\n前5名详情:")
    cols = [
        "rank",
        "stock_code",
        "stock_name",
        "dividend_yield",
        "roe_deducted",
        "volatility_annual",
        "composite_score",
    ]
    print(top_stocks[cols].head(5))


def example4_export_to_excel() -> None:
    """示例4: 导出结果到Excel（需要openpyxl）."""
    print("\n" + "=" * 80)
    print("示例4: 导出Excel")
    print("=" * 80)
    
    try:
        import openpyxl  # type: ignore
    except ImportError:
        print("需要安装openpyxl: pip install openpyxl")
        return
    
    selector = HighDividendLowVolatilitySelector(top_n=30)
    result = selector.run()
    
    # 导出到Excel
    output_file = selector.output_dir / "high_dividend_low_vol_stocks.xlsx"
    
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        # 写入多个sheet
        result.to_excel(writer, sheet_name="最终组合", index=False)
        
        # 添加摘要sheet
        summary = selector.scorer.generate_portfolio_summary(result)
        summary.to_excel(writer, sheet_name="组合摘要", index=False)
    
    print(f"\n结果已导出到: {output_file}")


def example5_analyze_industry() -> None:
    """示例5: 分析行业分布."""
    print("\n" + "=" * 80)
    print("示例5: 行业分析")
    print("=" * 80)
    
    selector = HighDividendLowVolatilitySelector(top_n=30)
    result = selector.run()
    
    # 统计行业分布
    if "industry" in result.columns:
        industry_dist = result["industry"].value_counts()
        print("\n行业分布:")
        print(industry_dist)
        
        # 计算行业集中度
        top3_concentration = industry_dist.head(3).sum() / len(result)
        print(f"\n前3大行业集中度: {top3_concentration:.1%}")
        
        if top3_concentration > 0.6:
            print("警告: 行业集中度较高，建议关注分散化")


def main() -> None:
    """运行所有示例."""
    print("高股息低波动股票筛选 - 使用示例")
    print("\n请选择要运行的示例:")
    print("1. 快速开始")
    print("2. 自定义配置")
    print("3. 分步执行")
    print("4. 导出Excel")
    print("5. 行业分析")
    print("0. 退出")
    
    choice = input("\n请输入选项: ")
    
    examples = {
        "1": example1_quick_start,
        "2": example2_custom_config,
        "3": example3_step_by_step,
        "4": example4_export_to_excel,
        "5": example5_analyze_industry,
    }
    
    if choice in examples:
        examples[choice]()
    elif choice == "0":
        print("再见！")
    else:
        print("无效选项")


if __name__ == "__main__":
    # 运行示例1
    example1_quick_start()
    
    # 如需运行其他示例，取消注释:
    # example2_custom_config()
    # example3_step_by_step()
    # example4_export_to_excel()
    # example5_analyze_industry()

