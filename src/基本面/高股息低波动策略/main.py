"""高股息低波动股票筛选主程序."""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.高股息低波动.wind_data_fetcher import WindDataFetcher
from src.高股息低波动.market_data_fetcher import MarketDataFetcher
from src.高股息低波动.stock_filter import StockFilter
from src.高股息低波动.scoring import StockScorer
from tools.shelveTool import shelve_me_week, shelve_me_today


class HighDividendLowVolatilitySelector:
    """高股息低波动股票选择器主类."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        top_n: int = 100,
    ) -> None:
        """
        初始化选择器.

        Args:
            output_dir: 输出目录（默认为data子目录）
            top_n: 最终选取的股票数量
        """
        self.output_dir = (
            output_dir
            if output_dir
            else Path(__file__).parent / "data"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.top_n = top_n
        
        # 初始化各模块
        print("=" * 80)
        print("高股息低波动股票筛选系统")
        print("=" * 80)
        
        self.wind_fetcher = WindDataFetcher()
        self.market_fetcher = MarketDataFetcher()
        self.filter_engine = StockFilter()
        self.scorer = StockScorer()
        
    @shelve_me_week
    def step1_build_universe(self) -> list[str]:
        """
        第一步: 构建选股宇宙.

        Returns:
            list[str]: 初始股票池
        """
        print("\n" + "=" * 80)
        print("第一步: 构建选股宇宙")
        print("=" * 80)
        
        # 获取主板A股
        stocks = self.wind_fetcher.get_main_board_stocks()
        print(f"\n初始股票池: {len(stocks)} 只")
        
        # 筛选上市满3年
        stocks = self.wind_fetcher.filter_by_listing_date(stocks, min_years=3)
        print(f"上市满3年: {len(stocks)} 只")
        
        # 筛选流动性（剔除后20%）
        stocks = self.wind_fetcher.filter_by_liquidity(stocks, bottom_percentile=0.2)
        print(f"流动性筛选后: {len(stocks)} 只")
        
        # 保存股票池
        universe_file = self.output_dir / "stock_universe.txt"
        with open(universe_file, "w", encoding="utf-8") as f:
            f.write("\n".join(stocks))
        print(f"\n股票池已保存至: {universe_file}")
        
        return stocks

    def step2_fetch_data(self, stocks: list[str]) -> tuple[pd.DataFrame, ...]:
        """
        第二步: 获取所有必需数据.

        Args:
            stocks: 股票代码列表

        Returns:
            tuple: (分红数据, 财务数据, 多年支付率数据, 波动率数据)
        """
        print("\n" + "=" * 80)
        print("第二步: 获取数据")
        print("=" * 80)
        
        # 获取分红数据（股息率）
        dividend_df = self.wind_fetcher.get_dividend_data(stocks)
        
        # 计算连续分红年限
        dividend_years_df = self.wind_fetcher.calculate_dividend_years(stocks, years=5)
        
        # 合并连续分红年限到分红数据
        dividend_df = dividend_df.merge(dividend_years_df[["stock_code", "dividend_years"]], 
                                         on="stock_code", how="left")
        
        # 获取财务数据
        financial_df = self.wind_fetcher.get_financial_data(stocks)
        
        # 获取多年股息支付率（计算：分红÷EPS）
        payout_df = self.wind_fetcher.get_multi_year_payout_ratio(stocks, years=3)
        
        # 获取波动率数据
        volatility_df = self.market_fetcher.calculate_volatility(stocks, period_days=252)
        
        # 保存原始数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dividend_df.to_csv(
            self.output_dir / f"dividend_data_{timestamp}.csv", index=False, encoding="utf-8-sig"
        )
        dividend_years_df.to_csv(
            self.output_dir / f"dividend_years_{timestamp}.csv", index=False, encoding="utf-8-sig"
        )
        financial_df.to_csv(
            self.output_dir / f"financial_data_{timestamp}.csv", index=False, encoding="utf-8-sig"
        )
        payout_df.to_csv(
            self.output_dir / f"payout_data_{timestamp}.csv", index=False, encoding="utf-8-sig"
        )
        volatility_df.to_csv(
            self.output_dir / f"volatility_data_{timestamp}.csv", index=False, encoding="utf-8-sig"
        )
        
        print(f"\n原始数据已保存至: {self.output_dir}")
        
        return dividend_df, financial_df, payout_df, volatility_df

    def step3_apply_filters(
        self,
        dividend_df: pd.DataFrame,
        financial_df: pd.DataFrame,
        payout_df: pd.DataFrame,
        volatility_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        第三步: 应用6条硬门槛筛选.

        Args:
            dividend_df: 分红数据
            financial_df: 财务数据
            payout_df: 多年支付率数据
            volatility_df: 波动率数据

        Returns:
            pd.DataFrame: 通过筛选的股票
        """
        print("\n" + "=" * 80)
        print("第三步: 应用6条硬门槛筛选")
        print("=" * 80)
        
        filtered_df = self.filter_engine.apply_all_filters(
            dividend_df, financial_df, payout_df, volatility_df
        )
        
        # 保存筛选后数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filtered_file = self.output_dir / f"filtered_stocks_{timestamp}.csv"
        filtered_df.to_csv(filtered_file, index=False, encoding="utf-8-sig")
        print(f"\n筛选结果已保存至: {filtered_file}")
        
        return filtered_df

    def step4_score_and_rank(self, filtered_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        第四步: 双因子打分并排名.

        Args:
            filtered_df: 筛选后的股票数据

        Returns:
            tuple: (前N只股票, 完整排名)
        """
        print("\n" + "=" * 80)
        print("第四步: 双因子打分并排名")
        print("=" * 80)
        
        # 计算综合得分
        scored_df = self.scorer.calculate_composite_score(filtered_df)
        
        # 选取前N只
        top_stocks, full_ranking = self.scorer.select_top_stocks(scored_df, self.top_n)
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存完整排名
        full_ranking_file = self.output_dir / f"full_ranking_{timestamp}.csv"
        full_ranking.to_csv(full_ranking_file, index=False, encoding="utf-8-sig")
        print(f"\n完整排名已保存至: {full_ranking_file}")
        
        # 保存前N只
        top_stocks_file = self.output_dir / f"top_{self.top_n}_stocks_{timestamp}.csv"
        top_stocks.to_csv(top_stocks_file, index=False, encoding="utf-8-sig")
        print(f"前{self.top_n}只股票已保存至: {top_stocks_file}")
        
        # 生成并保存组合摘要
        summary = self.scorer.generate_portfolio_summary(top_stocks)
        summary_file = self.output_dir / f"portfolio_summary_{timestamp}.csv"
        summary.to_csv(summary_file, index=False, encoding="utf-8-sig")
        print(f"组合摘要已保存至: {summary_file}")
        
        return top_stocks, full_ranking

    def run(self) -> pd.DataFrame:
        """
        运行完整的筛选流程.

        Returns:
            pd.DataFrame: 最终选出的前N只股票
        """
        try:
            # 第一步: 构建选股宇宙
            stocks = self.step1_build_universe()
            
            # 第二步: 获取数据
            dividend_df, financial_df, payout_df, volatility_df = self.step2_fetch_data(stocks)
            
            # 第三步: 应用硬门槛筛选
            filtered_df = self.step3_apply_filters(
                dividend_df, financial_df, payout_df, volatility_df
            )
            
            # 第四步: 打分和排名
            top_stocks, full_ranking = self.step4_score_and_rank(filtered_df)
            
            # 打印最终结果
            self._print_final_results(top_stocks)
            
            return top_stocks
            
        except Exception as e:
            print(f"\n程序运行出错: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _print_final_results(self, top_stocks: pd.DataFrame) -> None:
        """
        打印最终结果.

        Args:
            top_stocks: 最终选出的股票
        """
        print("\n" + "=" * 80)
        print(f"最终结果: 高股息低波动组合（前{self.top_n}只）")
        print("=" * 80)
        
        # 选择要显示的列
        display_cols = [
            "rank",
            "stock_code",
            "stock_name",
            "dividend_yield",
            "roe_deducted",
            "volatility_annual",
            "composite_score",
        ]
        
        # 确保列存在
        display_cols = [col for col in display_cols if col in top_stocks.columns]
        
        print("\n" + top_stocks[display_cols].to_string(index=False))
        
        # 打印统计信息
        print("\n" + "-" * 80)
        print("组合统计:")
        print(f"  平均股息率: {top_stocks['dividend_yield'].mean():.2f}%")
        print(f"  平均ROE: {top_stocks['roe_deducted'].mean():.2f}%")
        print(f"  平均波动率: {top_stocks['volatility_annual'].mean():.4f}")
        print(f"  平均综合得分: {top_stocks['composite_score'].mean():.2f}")
        print("-" * 80)


def main() -> None:
    """主函数入口."""
    import argparse
    
    parser = argparse.ArgumentParser(description="高股息低波动股票筛选系统")
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="选取前N只股票（默认100）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="输出目录路径",
    )
    
    args = parser.parse_args()
    
    # 初始化并运行
    output_dir = Path(args.output_dir) if args.output_dir else None
    selector = HighDividendLowVolatilitySelector(
        output_dir=output_dir,
        top_n=args.top_n,
    )
    
    # 运行筛选
    result = selector.run()
    
    print("\n" + "=" * 80)
    print("程序运行完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()

