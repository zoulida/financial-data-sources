"""评分模块 - 实现双因子打分逻辑."""

from typing import Tuple
import pandas as pd
import numpy as np


class StockScorer:
    """股票评分类，实现双因子打分逻辑."""

    def __init__(
        self,
        dividend_factor_weight: float = 0.5,
        volatility_factor_weight: float = 0.5,
        yield_score_weight: float = 0.6,
        stability_score_weight: float = 0.4,
    ) -> None:
        """
        初始化评分器.

        Args:
            dividend_factor_weight: 红利因子权重（默认0.5）
            volatility_factor_weight: 低波因子权重（默认0.5）
            yield_score_weight: 股息率排名权重（默认0.6）
            stability_score_weight: 股息稳定性权重（默认0.4）
        """
        self.dividend_factor_weight = dividend_factor_weight
        self.volatility_factor_weight = volatility_factor_weight
        self.yield_score_weight = yield_score_weight
        self.stability_score_weight = stability_score_weight
        
        print("\n评分器初始化:")
        print(f"  - 红利因子权重: {dividend_factor_weight}")
        print(f"  - 低波因子权重: {volatility_factor_weight}")
        print(f"  - 股息率排名权重: {yield_score_weight}")
        print(f"  - 股息稳定性权重: {stability_score_weight}")

    def calculate_rank_score(self, series: pd.Series, ascending: bool = False) -> pd.Series:
        """
        将数值转换为排名分数（0-100）.

        Args:
            series: 需要排名的数据序列
            ascending: True表示数值越小分数越高，False表示数值越大分数越高

        Returns:
            pd.Series: 排名分数（0-100）
        """
        rank = series.rank(ascending=ascending, method="min")
        max_rank = len(series)
        score = (rank / max_rank) * 100
        return score

    def calculate_dividend_yield_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算股息率排名分数.

        Args:
            df: 包含dividend_yield列的DataFrame

        Returns:
            pd.Series: 股息率排名分数（0-100）
        """
        return self.calculate_rank_score(df["dividend_yield"], ascending=False)

    def calculate_dividend_stability_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算股息稳定性分数（基于股息支付率标准差的倒数）.

        Args:
            df: 包含payout_std列的DataFrame

        Returns:
            pd.Series: 股息稳定性分数（0-100）
        """
        # 标准差越小，稳定性越高，分数越高
        # 使用标准差的倒数进行排名
        stability = 1 / (df["payout_std"] + 0.001)  # 加小值避免除零
        return self.calculate_rank_score(stability, ascending=False)

    def calculate_dividend_factor_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算红利因子得分 = 0.6×股息率排名分 + 0.4×股息稳定性排名分.

        Args:
            df: 包含dividend_yield和payout_std的DataFrame

        Returns:
            pd.Series: 红利因子得分（0-100）
        """
        yield_score = self.calculate_dividend_yield_score(df)
        stability_score = self.calculate_dividend_stability_score(df)
        
        dividend_score = (
            self.yield_score_weight * yield_score
            + self.stability_score_weight * stability_score
        )
        
        return dividend_score

    def calculate_volatility_factor_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算低波因子得分 = 100 - 波动率百分位×100.

        Args:
            df: 包含volatility_annual列的DataFrame

        Returns:
            pd.Series: 低波因子得分（0-100）
        """
        # 计算波动率百分位
        volatility_percentile = df["volatility_annual"].rank(method="min") / len(df)
        
        # 波动率越低，分数越高
        volatility_score = 100 - (volatility_percentile * 100)
        
        return volatility_score

    def calculate_composite_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算综合得分 = 0.5×红利因子 + 0.5×低波因子.

        Args:
            df: 包含所有需要评分数据的DataFrame

        Returns:
            pd.DataFrame: 添加了各项得分的DataFrame
        """
        print("\n" + "=" * 60)
        print("开始计算综合得分")
        print("=" * 60)
        
        result_df = df.copy()
        
        # 计算各项得分
        print("\n计算红利因子得分...")
        result_df["dividend_factor_score"] = self.calculate_dividend_factor_score(df)
        
        print("计算低波因子得分...")
        result_df["volatility_factor_score"] = self.calculate_volatility_factor_score(df)
        
        # 计算综合得分
        print("计算综合得分...")
        result_df["composite_score"] = (
            self.dividend_factor_weight * result_df["dividend_factor_score"]
            + self.volatility_factor_weight * result_df["volatility_factor_score"]
        )
        
        # 按综合得分排序
        result_df = result_df.sort_values("composite_score", ascending=False)
        result_df["rank"] = range(1, len(result_df) + 1)
        
        print(f"\n评分完成！共 {len(result_df)} 只股票")
        print("\n得分分布统计:")
        print(result_df["composite_score"].describe())
        
        return result_df

    def select_top_stocks(
        self, df: pd.DataFrame, top_n: int = 30
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        选取综合得分前N只股票.

        Args:
            df: 包含综合得分的DataFrame
            top_n: 选取数量

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (前N只股票, 完整排名)
        """
        print("\n" + "=" * 60)
        print(f"选取综合得分前 {top_n} 只股票")
        print("=" * 60)
        
        # 确保按分数排序
        df_sorted = df.sort_values("composite_score", ascending=False).reset_index(drop=True)
        
        # 选取前N只
        top_stocks = df_sorted.head(top_n).copy()
        
        print(f"\n成功选取前 {top_n} 只股票")
        print(f"得分范围: {top_stocks['composite_score'].min():.2f} - {top_stocks['composite_score'].max():.2f}")
        
        return top_stocks, df_sorted

    def generate_portfolio_summary(self, top_stocks: pd.DataFrame) -> pd.DataFrame:
        """
        生成投资组合摘要信息.

        Args:
            top_stocks: 前N只股票的DataFrame

        Returns:
            pd.DataFrame: 组合摘要信息
        """
        summary = pd.DataFrame(
            {
                "指标": [
                    "股票数量",
                    "平均股息率(%)",
                    "平均ROE(%)",
                    "平均波动率",
                    "平均综合得分",
                ],
                "数值": [
                    len(top_stocks),
                    top_stocks["dividend_yield"].mean(),
                    top_stocks["roe_deducted"].mean(),
                    top_stocks["volatility_annual"].mean(),
                    top_stocks["composite_score"].mean(),
                ],
            }
        )
        
        return summary


def main() -> None:
    """测试评分功能."""
    # 创建测试数据
    np.random.seed(42)
    n = 50
    
    df = pd.DataFrame(
        {
            "stock_code": [f"{i:06d}.SZ" for i in range(n)],
            "stock_name": [f"股票{i}" for i in range(n)],
            "dividend_yield": np.random.uniform(4, 8, n),
            "payout_std": np.random.uniform(1, 10, n),
            "volatility_annual": np.random.uniform(0.1, 0.3, n),
            "roe_deducted": np.random.uniform(8, 15, n),
        }
    )
    
    # 测试评分
    scorer = StockScorer()
    scored_df = scorer.calculate_composite_score(df)
    
    print("\n评分结果示例（前10名）:")
    print(
        scored_df[
            [
                "rank",
                "stock_code",
                "stock_name",
                "dividend_yield",
                "volatility_annual",
                "dividend_factor_score",
                "volatility_factor_score",
                "composite_score",
            ]
        ].head(10)
    )
    
    # 选取前30只
    top_30, full_ranking = scorer.select_top_stocks(scored_df, top_n=30)
    
    print("\n投资组合摘要:")
    summary = scorer.generate_portfolio_summary(top_30)
    print(summary)


if __name__ == "__main__":
    main()

