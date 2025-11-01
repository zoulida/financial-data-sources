"""股票筛选模块 - 实现6条硬门槛筛选逻辑."""

from typing import List, Tuple
import pandas as pd
import numpy as np
from tqdm import tqdm


class StockFilter:
    """股票筛选类，实现硬门槛筛选逻辑."""

    def __init__(
        self,
        min_dividend_years: int = 3,
        min_dividend_yield: float = 4.0,
        payout_ratio_range: Tuple[float, float] = (30.0, 70.0),
        min_roe: float = 8.0,
        volatility_percentile: float = 0.3,
    ) -> None:
        """
        初始化筛选器.

        Args:
            min_dividend_years: 最少连续分红年限（默认3年）
            min_dividend_yield: 最低股息率（默认4%）
            payout_ratio_range: 股息支付率范围（默认30%-70%）
            min_roe: 最低扣非ROE（默认8%）
            volatility_percentile: 波动率百分位阈值（默认30%，即保留最低30%）
        """
        self.min_dividend_years = min_dividend_years
        self.min_dividend_yield = min_dividend_yield
        self.payout_ratio_range = payout_ratio_range
        self.min_roe = min_roe
        self.volatility_percentile = volatility_percentile
        
        print(f"\n筛选器初始化:")
        print(f"  - 连续分红年限 ≥ {min_dividend_years} 年")
        print(f"  - 股息率 ≥ {min_dividend_yield}%")
        print(f"  - 股息支付率: {payout_ratio_range[0]}%-{payout_ratio_range[1]}%")
        print(f"  - 扣非ROE ≥ {min_roe}%")
        print(f"  - 波动率 ≤ 全市场 {volatility_percentile*100}%")

    def filter_dividend_years(
        self, df: pd.DataFrame, column: str = "dividend_years"
    ) -> pd.DataFrame:
        """
        筛选①: 连续分红年限 ≥ 3年.

        Args:
            df: 包含分红年限的DataFrame
            column: 分红年限列名

        Returns:
            pd.DataFrame: 筛选后的DataFrame
        """
        print(f"\n[筛选①] 连续分红年限 ≥ {self.min_dividend_years} 年")
        print(f"  筛选前: {len(df)} 只")
        
        mask = df[column] >= self.min_dividend_years
        result = df[mask].copy()
        
        print(f"  筛选后: {len(result)} 只 (剔除 {len(df) - len(result)} 只)")
        return result

    def filter_dividend_yield(
        self, df: pd.DataFrame, column: str = "dividend_yield"
    ) -> pd.DataFrame:
        """
        筛选②: 最近年度股息率 ≥ 4%.

        Args:
            df: 包含股息率的DataFrame
            column: 股息率列名

        Returns:
            pd.DataFrame: 筛选后的DataFrame
        """
        print(f"\n[筛选②] 股息率 ≥ {self.min_dividend_yield}%")
        print(f"  筛选前: {len(df)} 只")
        
        mask = df[column] >= self.min_dividend_yield
        result = df[mask].copy()
        
        print(f"  筛选后: {len(result)} 只 (剔除 {len(df) - len(result)} 只)")
        return result

    def filter_payout_ratio(
        self, df: pd.DataFrame, column: str = "avg_payout_ratio"
    ) -> pd.DataFrame:
        """
        筛选③: 过去3年平均股息支付率在30%-70%之间.

        Args:
            df: 包含股息支付率的DataFrame
            column: 股息支付率列名

        Returns:
            pd.DataFrame: 筛选后的DataFrame
        """
        print(
            f"\n[筛选③] 股息支付率: {self.payout_ratio_range[0]}%-{self.payout_ratio_range[1]}%"
        )
        print(f"  筛选前: {len(df)} 只")
        
        mask = (df[column] >= self.payout_ratio_range[0]) & (
            df[column] <= self.payout_ratio_range[1]
        )
        result = df[mask].copy()
        
        print(f"  筛选后: {len(result)} 只 (剔除 {len(df) - len(result)} 只)")
        return result

    def filter_roe(self, df: pd.DataFrame, column: str = "roe_deducted") -> pd.DataFrame:
        """
        筛选④: 最近年报扣非ROE ≥ 8%.

        Args:
            df: 包含ROE的DataFrame
            column: ROE列名

        Returns:
            pd.DataFrame: 筛选后的DataFrame
        """
        print(f"\n[筛选④] 扣非ROE ≥ {self.min_roe}%")
        print(f"  筛选前: {len(df)} 只")
        
        mask = df[column] >= self.min_roe
        result = df[mask].copy()
        
        print(f"  筛选后: {len(result)} 只 (剔除 {len(df) - len(result)} 只)")
        return result

    def filter_debt_ratio_by_industry(
        self,
        df: pd.DataFrame,
        debt_column: str = "debt_ratio",
        industry_column: str = "industry",
    ) -> pd.DataFrame:
        """
        筛选⑤: 资产负债率低于行业中位数（行业中性）.

        Args:
            df: 包含资产负债率和行业的DataFrame
            debt_column: 资产负债率列名
            industry_column: 行业列名

        Returns:
            pd.DataFrame: 筛选后的DataFrame
        """
        print("\n[筛选⑤] 资产负债率 ≤ 行业中位数")
        print(f"  筛选前: {len(df)} 只")
        
        # 按行业分组计算中位数
        industry_median = df.groupby(industry_column)[debt_column].median()
        
        # 为每只股票找到其行业中位数并比较
        mask = df.apply(
            lambda row: row[debt_column] <= industry_median.get(row[industry_column], np.inf)
            if pd.notna(row[debt_column]) and pd.notna(row[industry_column])
            else False,
            axis=1,
        )
        
        result = df[mask].copy()
        
        print(f"  筛选后: {len(result)} 只 (剔除 {len(df) - len(result)} 只)")
        print(f"  涉及 {len(industry_median)} 个行业")
        return result

    def filter_volatility(
        self, df: pd.DataFrame, column: str = "volatility_annual"
    ) -> pd.DataFrame:
        """
        筛选⑥: 波动率处于全市场最低30%.

        Args:
            df: 包含波动率的DataFrame
            column: 波动率列名

        Returns:
            pd.DataFrame: 筛选后的DataFrame
        """
        print(f"\n[筛选⑥] 波动率 ≤ 全市场 {self.volatility_percentile*100}%分位数")
        print(f"  筛选前: {len(df)} 只")
        
        threshold = df[column].quantile(self.volatility_percentile)
        mask = df[column] <= threshold
        result = df[mask].copy()
        
        print(f"  筛选后: {len(result)} 只 (剔除 {len(df) - len(result)} 只)")
        print(f"  波动率阈值: {threshold:.4f}")
        return result

    def apply_all_filters(
        self,
        dividend_df: pd.DataFrame,
        financial_df: pd.DataFrame,
        payout_df: pd.DataFrame,
        volatility_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        应用所有6条硬门槛筛选.

        Args:
            dividend_df: 分红数据DataFrame
            financial_df: 财务数据DataFrame
            payout_df: 多年股息支付率DataFrame
            volatility_df: 波动率DataFrame

        Returns:
            pd.DataFrame: 通过所有筛选的股票DataFrame
        """
        print("\n" + "=" * 60)
        print("开始应用6条硬门槛筛选")
        print("=" * 60)
        
        # 合并所有数据
        print("\n正在合并数据...")
        df = dividend_df.copy()
        df = df.merge(financial_df, on="stock_code", how="inner")
        df = df.merge(payout_df, on="stock_code", how="inner")
        df = df.merge(volatility_df, on="stock_code", how="inner")
        
        print(f"合并后总数: {len(df)} 只")
        
        # 依次应用6条筛选
        df = self.filter_dividend_years(df)
        df = self.filter_dividend_yield(df)
        df = self.filter_payout_ratio(df)
        df = self.filter_roe(df)
        df = self.filter_debt_ratio_by_industry(df)
        df = self.filter_volatility(df)
        
        print("\n" + "=" * 60)
        print(f"筛选完成！最终通过: {len(df)} 只股票")
        print("=" * 60)
        
        return df


def main() -> None:
    """测试筛选功能."""
    # 创建测试数据
    np.random.seed(42)
    n = 100
    
    dividend_df = pd.DataFrame(
        {
            "stock_code": [f"{i:06d}.SZ" for i in range(n)],
            "stock_name": [f"股票{i}" for i in range(n)],
            "dividend_yield": np.random.uniform(2, 8, n),
            "dividend_years": np.random.randint(1, 6, n),
        }
    )
    
    financial_df = pd.DataFrame(
        {
            "stock_code": [f"{i:06d}.SZ" for i in range(n)],
            "roe_deducted": np.random.uniform(5, 15, n),
            "debt_ratio": np.random.uniform(20, 60, n),
            "industry": np.random.choice(["银行", "食品", "医药", "科技"], n),
        }
    )
    
    payout_df = pd.DataFrame(
        {
            "stock_code": [f"{i:06d}.SZ" for i in range(n)],
            "avg_payout_ratio": np.random.uniform(20, 80, n),
            "payout_std": np.random.uniform(1, 10, n),
        }
    )
    
    volatility_df = pd.DataFrame(
        {
            "stock_code": [f"{i:06d}.SZ" for i in range(n)],
            "volatility_annual": np.random.uniform(0.1, 0.5, n),
        }
    )
    
    # 测试筛选
    filter_engine = StockFilter()
    result = filter_engine.apply_all_filters(
        dividend_df, financial_df, payout_df, volatility_df
    )
    
    print("\n筛选结果示例:")
    print(result.head(10))


if __name__ == "__main__":
    main()

