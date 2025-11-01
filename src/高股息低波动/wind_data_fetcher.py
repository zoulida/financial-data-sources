"""Wind数据获取模块 - 获取财务数据和基本信息."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from WindPy import w
from tqdm import tqdm
import sys
from pathlib import Path

# 添加项目路径以导入shelve_tool
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from tools.shelveTool import shelve_me_week, shelve_me_today


class WindDataFetcher:
    """Wind数据获取类，用于获取股票财务数据和基本信息."""

    def __init__(self) -> None:
        """初始化Wind接口."""
        self.w = w
        self.w.start()
        print("Wind接口初始化成功")

    def __del__(self) -> None:
        """关闭Wind接口."""
        try:
            self.w.stop()
        except Exception:
            pass
    n = None
    @shelve_me_today(n)
    def get_main_board_stocks(self) -> List[str]:
        """
        获取沪深主板A股列表，剔除ST、*ST、退市整理股.
        
        缓存策略: 按天缓存（每天更新一次）

        Returns:
            List[str]: 符合条件的股票代码列表
        """
        print("\n正在获取沪深主板A股列表...")
        
        # 获取所有A股
        data = self.w.wset(
            "sectorconstituent",
            "sectorid=a001010100000000;field=wind_code,sec_name",
        )
        
        if data.ErrorCode != 0:
            print(f"获取股票列表失败: {data.Data}")
            return []
        
        all_stocks = data.Data[0]
        stock_names = data.Data[1]
        
        # 剔除ST、*ST、退市整理股
        filtered_stocks = []
        for code, name in zip(all_stocks, stock_names):
            if "ST" not in name and "退市" not in name:
                filtered_stocks.append(code)
        
        print(f"获取到 {len(filtered_stocks)} 只主板A股（已剔除ST、退市股）")
        return filtered_stocks

    def filter_by_listing_date(
        self, stock_codes: List[str], min_years: int = 3
    ) -> List[str]:
        """
        根据上市时间筛选股票.

        Args:
            stock_codes: 股票代码列表
            min_years: 最少上市年限

        Returns:
            List[str]: 符合上市年限的股票列表
        """
        print(f"\n正在筛选上市满 {min_years} 年的股票...")
        
        cutoff_date = datetime.now() - timedelta(days=min_years * 365)
        filtered_stocks = []
        
        # 分批查询以提高效率
        batch_size = 500
        for i in tqdm(range(0, len(stock_codes), batch_size), desc="查询上市日期"):
            batch = stock_codes[i : i + batch_size]
            data = self.w.wss(batch, "ipo_date")
            
            if data.ErrorCode != 0:
                continue
            
            for code, ipo_date in zip(data.Codes, data.Data[0]):
                if ipo_date and isinstance(ipo_date, datetime):
                    if ipo_date <= cutoff_date:
                        filtered_stocks.append(code)
        
        print(f"筛选后剩余 {len(filtered_stocks)} 只股票")
        return filtered_stocks

    def filter_by_liquidity(
        self, stock_codes: List[str], bottom_percentile: float = 0.2
    ) -> List[str]:
        """
        根据流动性筛选股票，剔除最近1年成交额后20%的股票.

        Args:
            stock_codes: 股票代码列表
            bottom_percentile: 剔除的底部百分位

        Returns:
            List[str]: 符合流动性要求的股票列表
        """
        print(f"\n正在筛选流动性（剔除年成交额后 {bottom_percentile*100:.0f}%）...")
        
        end_date = datetime.now().strftime("%Y%m%d")
        
        year_amounts = {}
        
        # 分批查询年成交额
        batch_size = 500
        for i in tqdm(range(0, len(stock_codes), batch_size), desc="查询年成交额"):
            batch = stock_codes[i : i + batch_size]
            data = self.w.wss(
                batch,
                "yq_amount",
                f"unit=1;tradeDate={end_date}",
            )
            
            if data.ErrorCode != 0:
                continue
            
            for code, amt in zip(data.Codes, data.Data[0]):
                if amt and amt > 0:
                    year_amounts[code] = amt
        
        # 计算阈值
        amounts = list(year_amounts.values())
        threshold = pd.Series(amounts).quantile(bottom_percentile)
        
        # 筛选
        filtered_stocks = [
            code for code, amt in year_amounts.items() if amt >= threshold
        ]
        
        print(f"筛选后剩余 {len(filtered_stocks)} 只股票")
        print(f"年成交额阈值: {threshold/1e8:.2f} 亿元")
        return filtered_stocks

    @shelve_me_today(n)
    def get_dividend_data(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取股票分红数据（股息率和基本信息）.
        
        缓存策略: 按天缓存（每天更新一次）

        Args:
            stock_codes: 股票代码列表

        Returns:
            pd.DataFrame: 包含股息率的DataFrame
        """
        print("\n正在获取分红数据（股息率）...")
        
        current_year = datetime.now().year
        trade_date = f"{current_year - 1}1231"
        
        fields = [
            "sec_name",  # 股票简称
            "dividendyield2",  # 股息率（近12个月）
        ]
        
        all_data = []
        batch_size = 500
        
        for i in tqdm(range(0, len(stock_codes), batch_size), desc="获取股息率"):
            batch = stock_codes[i : i + batch_size]
            data = self.w.wss(batch, ",".join(fields), f"tradeDate={trade_date}")
            
            if data.ErrorCode != 0:
                continue
            
            batch_df = pd.DataFrame(
                {
                    "stock_code": data.Codes,
                    "stock_name": data.Data[0],
                    "dividend_yield": data.Data[1],
                }
            )
            all_data.append(batch_df)
        
        if all_data:
            result_df = pd.concat(all_data, ignore_index=True)
            # 填充缺失值：股息率缺失设置为0
            result_df["dividend_yield"] = result_df["dividend_yield"].fillna(0)
            print(f"成功获取 {len(result_df)} 只股票的股息率")
            return result_df
        else:
            return pd.DataFrame()
    
    @shelve_me_today(n)
    def calculate_dividend_years(self, stock_codes: List[str], years: int = 5) -> pd.DataFrame:
        """
        计算连续分红年限（基于历史是否分红数据）.
        
        缓存策略: 按天缓存（每天更新一次）

        Args:
            stock_codes: 股票代码列表
            years: 查询历史年数（默认5年）

        Returns:
            pd.DataFrame: 包含连续分红年限的DataFrame
        """
        print(f"\n正在计算连续分红年限（查询过去 {years} 年）...")
        
        current_year = datetime.now().year
        dividend_records = {code: [] for code in stock_codes}
        
        # 查询过去N年的分红情况
        for year_offset in range(years):
            report_date = f"{current_year - 1 - year_offset}1231"
            
            for i in tqdm(
                range(0, len(stock_codes), 500),
                desc=f"查询 {current_year - 1 - year_offset} 年分红情况",
            ):
                batch = stock_codes[i : i + 500]
                data = self.w.wss(batch, "div_ifdiv", f"rptDate={report_date}")
                
                if data.ErrorCode != 0:
                    continue
                
                for code, is_div in zip(data.Codes, data.Data[0]):
                    # div_ifdiv: "是"表示分红，"否"表示不分红
                    # 也可能返回 1/0，做兼容处理
                    if is_div in ["是", 1, "1", True]:
                        dividend_records[code].append(1)
                    else:
                        dividend_records[code].append(0)
        
        # 计算连续分红年限
        result_data = []
        for code, records in dividend_records.items():
            if not records:
                continue
            
            # 从最近的年份开始计算连续分红年数
            consecutive_years = 0
            for is_div in records:
                if is_div == 1:
                    consecutive_years += 1
                else:
                    break  # 遇到不分红就停止
            
            result_data.append(
                {
                    "stock_code": code,
                    "dividend_years": consecutive_years,
                    "total_years_checked": len(records),
                }
            )
        
        result_df = pd.DataFrame(result_data)
        print(f"成功计算 {len(result_df)} 只股票的连续分红年限")
        return result_df

    @shelve_me_today(n)
    def get_financial_data(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取财务数据（ROE、资产负债率等）.
        
        缓存策略: 按天缓存（每天更新一次）

        Args:
            stock_codes: 股票代码列表

        Returns:
            pd.DataFrame: 包含财务数据的DataFrame
        """
        print("\n正在获取财务数据...")
        
        current_year = datetime.now().year
        report_date = f"{current_year - 1}1231"
        trade_date = datetime.now().strftime("%Y%m%d")
        
        all_data = []
        batch_size = 500
        
        for i in tqdm(range(0, len(stock_codes), batch_size), desc="获取财务数据"):
            batch = stock_codes[i : i + batch_size]
            
            # 第一步：获取财务指标（ROE、负债率）
            financial_fields = ["roe_deducted", "debttoassets"]
            data1 = self.w.wss(batch, ",".join(financial_fields), f"rptDate={report_date}")
            
            # 第二步：获取行业分类
            data2 = self.w.wss(batch, "wicsname2024", f"tradeDate={trade_date};industryType=1")
            
            if data1.ErrorCode != 0 or data2.ErrorCode != 0:
                continue
            
            batch_df = pd.DataFrame(
                {
                    "stock_code": data1.Codes,
                    "roe_deducted": data1.Data[0],
                    "debt_ratio": data1.Data[1],
                    "industry": data2.Data[0],
                }
            )
            all_data.append(batch_df)
        
        if all_data:
            result_df = pd.concat(all_data, ignore_index=True)
            # 填充缺失值
            result_df["roe_deducted"] = result_df["roe_deducted"].fillna(0)
            result_df["debt_ratio"] = result_df["debt_ratio"].fillna(0)
            result_df["industry"] = result_df["industry"].fillna("未知")
            
            print(f"成功获取 {len(result_df)} 只股票的财务数据")
            return result_df
        else:
            return pd.DataFrame()

    @shelve_me_today(n)
    def get_multi_year_payout_ratio(
        self, stock_codes: List[str], years: int = 3
    ) -> pd.DataFrame:
        """
        计算多年股息支付率（年度累计分红÷每股收益）.
        
        缓存策略: 按天缓存（每天更新一次）

        Args:
            stock_codes: 股票代码列表
            years: 查询年数

        Returns:
            pd.DataFrame: 包含多年股息支付率统计的DataFrame
        """
        print(f"\n正在计算过去 {years} 年股息支付率...")
        
        current_year = datetime.now().year
        payout_data = {code: [] for code in stock_codes}
        
        fields = [
            "div_aualaccmdivpershare",  # 年度累计单位分红
            "eps_basic",  # 基本每股收益
        ]
        
        for year_offset in range(years):
            year = current_year - 1 - year_offset
            report_date = f"{year}1231"
            
            for i in tqdm(
                range(0, len(stock_codes), 500),
                desc=f"查询 {year} 年数据",
            ):
                batch = stock_codes[i : i + 500]
                # 添加 year 和 currencyType 参数
                data = self.w.wss(
                    batch, 
                    ",".join(fields), 
                    f"year={year};rptDate={report_date};currencyType="
                )
                
                if data.ErrorCode != 0:
                    continue
                
                # data.Data[0] 是分红，data.Data[1] 是EPS
                for code, div_per_share, eps in zip(data.Codes, data.Data[0], data.Data[1]):
                    # 计算股息支付率 = 年度累计分红 ÷ EPS
                    if div_per_share is not None and eps is not None and eps > 0:
                        payout_ratio = (div_per_share / eps) * 100  # 转换为百分比
                        payout_data[code].append(payout_ratio)
        
        # 计算平均值和标准差
        result_data = []
        for code, ratios in payout_data.items():
            if ratios:
                # 有数据：计算平均值和标准差
                result_data.append(
                    {
                        "stock_code": code,
                        "avg_payout_ratio": sum(ratios) / len(ratios),
                        "payout_std": pd.Series(ratios).std() if len(ratios) > 1 else 0,
                        "payout_count": len(ratios),
                    }
                )
            else:
                # 没有数据：设置为0
                result_data.append(
                    {
                        "stock_code": code,
                        "avg_payout_ratio": 0.0,
                        "payout_std": 0.0,
                        "payout_count": 0,
                    }
                )
        
        result_df = pd.DataFrame(result_data)
        missing_count = (result_df["avg_payout_ratio"] == 0).sum()
        print(f"成功计算 {len(result_df)} 只股票的股息支付率统计")
        if missing_count > 0:
            print(f"  其中 {missing_count} 只股票无数据（已设置为0）")
        if len(result_df) > 0:
            print(f"  平均支付率: {result_df['avg_payout_ratio'].mean():.2f}%")
        return result_df


def main() -> None:
    """测试Wind数据获取功能."""
    fetcher = WindDataFetcher()
    
    # 获取主板股票
    stocks = fetcher.get_main_board_stocks()
    print(f"主板股票数量: {len(stocks)}")
    
    # 测试获取前10只股票的数据
    if stocks:
        test_stocks = stocks[:10]
        
        print("\n" + "=" * 80)
        print("测试数据获取")
        print("=" * 80)
        
        # 测试股息率
        dividend_df = fetcher.get_dividend_data(test_stocks)
        print("\n股息率数据示例:")
        print(dividend_df.head())
        
        # 测试连续分红年限
        dividend_years_df = fetcher.calculate_dividend_years(test_stocks, years=5)
        print("\n连续分红年限示例:")
        print(dividend_years_df.head())
        
        # 测试财务数据
        financial_df = fetcher.get_financial_data(test_stocks)
        print("\n财务数据示例:")
        print(financial_df.head())
        
        # 测试股息支付率计算
        payout_df = fetcher.get_multi_year_payout_ratio(test_stocks, years=3)
        print("\n股息支付率示例:")
        print(payout_df.head())


if __name__ == "__main__":
    main()

