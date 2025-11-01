"""配置文件 - 定义筛选和评分的参数."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class FilterConfig:
    """筛选配置."""

    # 选股宇宙配置
    min_listing_years: int = 3  # 最少上市年限
    liquidity_bottom_percentile: float = 0.2  # 剔除成交额后20%

    # 硬门槛配置
    min_dividend_years: int = 3  # 最少连续分红年限
    min_dividend_yield: float = 4.0  # 最低股息率(%)
    payout_ratio_range: Tuple[float, float] = (30.0, 70.0)  # 股息支付率范围(%)
    min_roe: float = 8.0  # 最低扣非ROE(%)
    volatility_percentile: float = 0.3  # 波动率百分位阈值（保留最低30%）


@dataclass
class ScoringConfig:
    """评分配置."""

    # 因子权重
    dividend_factor_weight: float = 0.5  # 红利因子权重
    volatility_factor_weight: float = 0.5  # 低波因子权重

    # 红利因子内部权重
    yield_score_weight: float = 0.6  # 股息率排名权重
    stability_score_weight: float = 0.4  # 股息稳定性权重


@dataclass
class DataConfig:
    """数据配置."""

    # 历史数据周期
    volatility_period_days: int = 252  # 波动率计算周期（约1年）
    payout_history_years: int = 3  # 股息支付率历史年数


@dataclass
class OutputConfig:
    """输出配置."""

    top_n: int = 100  # 最终选取股票数量
    save_intermediate_results: bool = True  # 是否保存中间结果


class Config:
    """总配置类."""

    def __init__(self) -> None:
        """初始化配置."""
        self.filter = FilterConfig()
        self.scoring = ScoringConfig()
        self.data = DataConfig()
        self.output = OutputConfig()

    def print_config(self) -> None:
        """打印当前配置."""
        print("\n" + "=" * 80)
        print("当前配置参数")
        print("=" * 80)

        print("\n【选股宇宙配置】")
        print(f"  最少上市年限: {self.filter.min_listing_years} 年")
        print(f"  流动性筛选: 剔除成交额后 {self.filter.liquidity_bottom_percentile*100:.0f}%")

        print("\n【硬门槛配置】")
        print(f"  连续分红年限: ≥ {self.filter.min_dividend_years} 年")
        print(f"  股息率: ≥ {self.filter.min_dividend_yield}%")
        print(
            f"  股息支付率: {self.filter.payout_ratio_range[0]}%-{self.filter.payout_ratio_range[1]}%"
        )
        print(f"  扣非ROE: ≥ {self.filter.min_roe}%")
        print(f"  波动率: ≤ 全市场 {self.filter.volatility_percentile*100:.0f}%")

        print("\n【评分配置】")
        print(f"  红利因子权重: {self.scoring.dividend_factor_weight}")
        print(f"  低波因子权重: {self.scoring.volatility_factor_weight}")
        print(f"  股息率排名权重: {self.scoring.yield_score_weight}")
        print(f"  股息稳定性权重: {self.scoring.stability_score_weight}")

        print("\n【数据配置】")
        print(f"  波动率计算周期: {self.data.volatility_period_days} 交易日")
        print(f"  股息支付率历史: {self.data.payout_history_years} 年")

        print("\n【输出配置】")
        print(f"  最终选取数量: 前 {self.output.top_n} 只")
        print(f"  保存中间结果: {self.output.save_intermediate_results}")

        print("=" * 80)


# 默认配置实例
default_config = Config()


def main() -> None:
    """测试配置."""
    config = Config()
    config.print_config()


if __name__ == "__main__":
    main()

