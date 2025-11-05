"""
ST摘帽预测脚本

功能：
1. 使用Wind API获取当年1-3季度财务数据
2. 预测全年财务数据
3. 对股票进行打分筛选
4. 输出候选股票列表

作者：AI Assistant
日期：2025-01-20
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List
import warnings
from tools.shelveTool import shelve_me_week
warnings.filterwarnings('ignore')

from data_fetcher import WindDataFetcher


class ST摘帽预测器:
    """ST摘帽预测主类"""
    
    def __init__(self):
        """初始化"""
        # 创建数据获取器
        self.data_fetcher = WindDataFetcher()
        
        # 获取当前年份
        self.current_year = datetime.now().year
        self.current_date = datetime.now()
    
    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, 'data_fetcher'):
                del self.data_fetcher
        except:
            pass
    @shelve_me_week
    def get_st_stocks(self) -> List[str]:
        """获取ST板块股票代码列表（委托给数据获取器）"""
        return self.data_fetcher.get_st_stocks()
        
    @shelve_me_week
    def fetch_quarterly_data(self, codes: List[str]) -> pd.DataFrame:
        """获取当年1-3季度累计数据（委托给数据获取器）"""
        return self.data_fetcher.fetch_quarterly_data(codes)
    
    def fetch_q3_single_quarter_data(self, codes: List[str]) -> pd.DataFrame:
        """获取Q3单季数据（委托给数据获取器）"""
        return self.data_fetcher.fetch_q3_single_quarter_data(codes)
    
    def fetch_market_cap(self, codes: List[str]) -> pd.DataFrame:
        """获取最新总市值（委托给数据获取器）"""
        return self.data_fetcher.fetch_market_cap(codes)
    
    def fetch_q4_revenue_ratio(self, codes: List[str]) -> pd.DataFrame:
        """获取最近2年四季度营收占比（委托给数据获取器）"""
        return self.data_fetcher.fetch_q4_revenue_ratio(codes)
    
    def fetch_additional_data(self, codes: List[str]) -> pd.DataFrame:
        """获取其他数据（委托给数据获取器）"""
        return self.data_fetcher.fetch_additional_data(codes)
    
    def get_stock_names(self, codes: List[str]) -> pd.DataFrame:
        """获取股票名称（委托给数据获取器）"""
        return self.data_fetcher.get_stock_names(codes)
    
    def predict_full_year(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        预测全年数据
        
        Parameters:
            df: 包含所有财务数据的DataFrame
            
        Returns:
            添加了预测字段的DataFrame
        """
        print("正在预测全年数据...")
        
        # 调试：检查基础数据字段
        print(f"数据行数: {len(df)}")
        print(f"\n基础字段数据完整性:")
        if '累计营业收入' in df.columns:
            print(f"  累计营业收入非空: {df['累计营业收入'].notna().sum()} / {len(df)}")
            if df['累计营业收入'].notna().sum() > 0:
                print(f"    示例值: {df[df['累计营业收入'].notna()]['累计营业收入'].iloc[0]}")
        if 'Q3单季营收' in df.columns:
            print(f"  Q3单季营收非空: {df['Q3单季营收'].notna().sum()} / {len(df)}")
            if df['Q3单季营收'].notna().sum() > 0:
                print(f"    示例值: {df[df['Q3单季营收'].notna()]['Q3单季营收'].iloc[0]}")
        if '财务费用' in df.columns:
            print(f"  财务费用非空: {df['财务费用'].notna().sum()} / {len(df)}")
        if '净资产' in df.columns:
            print(f"  净资产非空: {df['净资产'].notna().sum()} / {len(df)}")
            if df['净资产'].notna().sum() > 0:
                print(f"    示例值: {df[df['净资产'].notna()]['净资产'].iloc[0]}")
        if '毛利率' in df.columns:
            print(f"  毛利率非空: {df['毛利率'].notna().sum()} / {len(df)}")
        if 'Q3单季毛利率' in df.columns:
            print(f"  Q3单季毛利率非空: {df['Q3单季毛利率'].notna().sum()} / {len(df)}")
        
        # 打印前3只股票的关键字段数据
        debug_cols = ['code', '累计营业收入', 'Q3单季营收', 'Q3单季同比', '财务费用', '净资产', 'Q3_毛利率', 'Q3单季毛利率']
        debug_cols = [col for col in debug_cols if col in df.columns]
        if len(debug_cols) > 1:
            print(f"\n前3只股票的关键数据:")
            print(df[debug_cols].head(3).to_string())
        
        # Q4营收预测
        # 方法1：Q4营收 = Q3单季营收 * (1 + Q3单季营收同比)
        # Q3单季营收 = Q3累计营收 - Q2累计营收
        if 'Q3_营业收入' in df.columns and 'Q2_营业收入' in df.columns:
            df['Q3单季营收'] = df['Q3_营业收入'].fillna(0) - df['Q2_营业收入'].fillna(0)
            df['Q4营收预测1'] = df['Q3单季营收'] * (1 + df['Q3单季同比'].fillna(0))
        else:
            df['Q4营收预测1'] = 0
        
        # 方法2：若最近2年Q4占比均值>40%，则 Q4营收 = 全年营收指引 * 前三年Q4平均占比
        # 全年营收指引 = 累计营收 / (1 - 前三年Q4平均占比)
        mask_q4_ratio = (df['Q4营收占比均值'].fillna(0) > 0.4) if 'Q4营收占比均值' in df.columns else pd.Series([False] * len(df))
        if mask_q4_ratio.any():
            df.loc[mask_q4_ratio, '全年营收指引'] = (
                df.loc[mask_q4_ratio, '累计营业收入'] / 
                (1 - df.loc[mask_q4_ratio, 'Q4营收占比均值'])
            )
            df.loc[mask_q4_ratio, 'Q4营收预测2'] = (
                df.loc[mask_q4_ratio, '全年营收指引'] * 
                df.loc[mask_q4_ratio, 'Q4营收占比均值']
            )
        
        # 选择Q4营收预测值
        df['Q4营收预测'] = df['Q4营收预测1']
        if 'Q4营收预测2' in df.columns:
            df.loc[mask_q4_ratio, 'Q4营收预测'] = df.loc[mask_q4_ratio, 'Q4营收预测2']
        
        # 全年营收 = Q1+Q2+Q3累计 + Q4营收
        df['预测全年营收'] = df['累计营业收入'].fillna(0) + df['Q4营收预测'].fillna(0)
        
        # 全年毛利 = 全年营收 * Q3毛利率（单季）
        if 'Q3_毛利率' in df.columns:
            df['预测全年毛利'] = df['预测全年营收'] * df['Q3_毛利率'].fillna(0) / 100
        else:
            df['预测全年毛利'] = 0
        
        # 全年费用 = 全年营收 * Q3期间费用率（单季）
        if 'Q3_期间费用率' in df.columns:
            df['预测全年费用'] = df['预测全年营收'] * df['Q3_期间费用率'].fillna(0) / 100
        else:
            df['预测全年费用'] = 0
        
        # 财务费用年化（Q3财务费用 * 4/3）
        df['财务费用年化'] = df['财务费用'].fillna(0) * 4 / 3
        
        # 全年净利 = (毛利 - 费用 - 财务费用年化) * (1-0.25) + 非经常损益指引
        df['预测全年净利'] = (
            (df['预测全年毛利'] - df['预测全年费用'] - df['财务费用年化']) * 0.75 + 
            df['非经常损益指引'].fillna(0)
        )
        
        # 全年扣非 = 全年净利 - 非经常损益指引
        df['预测全年扣非'] = df['预测全年净利'] - df['非经常损益指引'].fillna(0)
        
        # 年末净资产 = Q3净资产 + 全年净利（移除分红计划）
        df['预测年末净资产'] = (
            df['净资产'].fillna(0) + 
            df['预测全年净利'].fillna(0)
        )
        
        print("全年预测完成")
        
        return df
    
    def calculate_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算得分
        
        硬门槛5项（每项1分）：
        1. 净利>0
        2. 扣非>0
        3. 营收≥1亿
        4. 净资产>0
        5. 违规标识=0
        
        软指标3项（每项1分）：
        1. 经营现金流/营收≥0.7
        2. 毛利率同比>0
        3. 期间费用率同比<0
        （注：审计意见不再作为打分项，但保留在结果列表中）
        
        Parameters:
            df: 包含所有数据的DataFrame
            
        Returns:
            添加了得分字段的DataFrame
        """
        print("正在计算得分...")
        
        # 初始化得分
        df['硬门槛得分'] = 0
        df['软指标得分'] = 0
        df['总分'] = 0
        
        # 硬门槛1：净利>0
        df.loc[df['预测全年净利'].fillna(-1) > 0, '硬门槛得分'] += 1
        
        # 硬门槛2：扣非>0
        df.loc[df['预测全年扣非'].fillna(-1) > 0, '硬门槛得分'] += 1
        
        # 硬门槛3：营收≥1亿
        df.loc[df['预测全年营收'].fillna(0) >= 100000000, '硬门槛得分'] += 1
        
        # 硬门槛4：净资产>0
        df.loc[df['预测年末净资产'].fillna(-1) > 0, '硬门槛得分'] += 1
        
        # 硬门槛5：违规标识=0（违规处罚次数为0）
        # 注意：审计意见不再作为打分项，但数据会保留在结果列表中
        df.loc[df['违规立案标识'].fillna(1) == 0, '硬门槛得分'] += 1
        
        # 软指标1：经营现金流/营收≥0.7
        cash_flow_ratio = df['经营现金流'].fillna(0) / df['预测全年营收'].replace(0, np.nan)
        df.loc[cash_flow_ratio.fillna(-1) >= 0.7, '软指标得分'] += 1
        
        # 软指标2：毛利率同比>0
        # 需要计算毛利率同比，这里暂时用Q3单季毛利率作为参考
        # 如果有历史毛利率数据，可以计算同比
        # 暂时跳过此项，或使用其他逻辑
        # 注意：实际使用时需要获取去年同期的毛利率数据进行对比
        
        # 软指标3：期间费用率同比<0
        # 同样需要历史数据，暂时跳过
        # 注意：实际使用时需要获取去年同期的期间费用率数据进行对比
        
        # 软指标4：预告披露日≤1月31日（已移除，不再使用）
        
        # 计算总分
        df['总分'] = df['硬门槛得分'] + df['软指标得分']
        
        print("得分计算完成")
        
        return df
    
    def filter_and_sort(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        筛选和排序
        
        筛选条件（自动放宽）：
        - 优先：总分≥7 且 总市值≤30亿
        - 如果无结果，放宽到：总分≥5 且 总市值≤50亿
        - 如果仍无结果，放宽到：总分≥4 且 总市值≤100亿
        - 如果仍无结果，只保留总分≥3的股票
        
        排序：
        - 按score降序
        - 按市值升序
        
        Parameters:
            df: 包含所有数据和得分的DataFrame
            
        Returns:
            筛选和排序后的DataFrame
        """
        print("正在筛选和排序...")
        
        # 调试：检查筛选条件
        print(f"筛选前股票数: {len(df)}")
        
        # 逐步放宽筛选条件
        score_thresholds = [7, 5, 4, 3]
        mktcap_thresholds = [30e8, 50e8, 100e8, float('inf')]
        
        df_filtered = pd.DataFrame()
        used_condition = None
        
        for score_threshold, mktcap_threshold in zip(score_thresholds, mktcap_thresholds):
            mask = (df['总分'] >= score_threshold) & (df['总市值'].fillna(float('inf')) <= mktcap_threshold)
            df_filtered = df[mask].copy()
            
            if len(df_filtered) > 0:
                mktcap_str = f"{mktcap_threshold/1e8:.0f}亿" if mktcap_threshold != float('inf') else "无限制"
                used_condition = f"总分≥{score_threshold} 且 市值≤{mktcap_str}"
                print(f"使用筛选条件: {used_condition}")
                print(f"筛选后股票数: {len(df_filtered)}")
                break
            else:
                mktcap_str = f"{mktcap_threshold/1e8:.0f}亿" if mktcap_threshold != float('inf') else "无限制"
                print(f"尝试条件: 总分≥{score_threshold} 且 市值≤{mktcap_str} -> 无结果")
        
        # 如果所有条件都无结果，显示统计信息
        if len(df_filtered) == 0:
            print("\n警告：所有筛选条件都无结果，显示统计信息...")
            print(f"总分≥7的股票数: {len(df[df['总分'] >= 7])}")
            print(f"总分≥5的股票数: {len(df[df['总分'] >= 5])}")
            print(f"总分≥4的股票数: {len(df[df['总分'] >= 4])}")
            print(f"总分≥3的股票数: {len(df[df['总分'] >= 3])}")
            print(f"市值≤30亿的股票数: {len(df[df['总市值'].fillna(float('inf')) <= 30e8])}")
            print(f"市值≤50亿的股票数: {len(df[df['总市值'].fillna(float('inf')) <= 50e8])}")
            print(f"市值≤100亿的股票数: {len(df[df['总市值'].fillna(float('inf')) <= 100e8])}")
            # 返回所有股票，按分数排序
            df_filtered = df.copy()
            print("返回所有股票（按分数排序）")
        
        # 排序：先按总分降序，再按市值升序
        df_filtered = df_filtered.sort_values(
            by=['总分', '总市值'],
            ascending=[False, True]
        )
        
        print(f"筛选完成，共 {len(df_filtered)} 只股票符合条件")
        
        return df_filtered
    
    def run(self) -> pd.DataFrame:
        """
        运行完整的预测流程
        
        Returns:
            最终结果DataFrame
        """
        print("=" * 60)
        print("ST摘帽预测程序开始运行")
        print("=" * 60)
        
        # 1. 获取ST股票池
        codes = self.get_st_stocks()
        print(f"获取到 {len(codes)} 只ST股票")
        if len(codes) == 0:
            print("警告：ST股票列表为空！")
            return pd.DataFrame(columns=['code', 'name', '总分', '预测全年净利', '预测全年扣非', 
                                        '预测年末净资产', '总市值', '审计意见', '备注'])
        
        # 2. 获取各项数据
        df_quarterly = self.fetch_quarterly_data(codes)
        df_q3 = self.fetch_q3_single_quarter_data(codes)
        df_mktcap = self.fetch_market_cap(codes)
        df_q4_ratio = self.fetch_q4_revenue_ratio(codes)
        df_additional = self.fetch_additional_data(codes)
        df_names = self.get_stock_names(codes)
        
        # 3. 合并所有数据
        print("正在合并数据...")
        print(f"季度数据: {len(df_quarterly)} 行")
        print(f"Q3单季数据: {len(df_q3)} 行")
        print(f"市值数据: {len(df_mktcap)} 行")
        print(f"Q4占比数据: {len(df_q4_ratio)} 行")
        print(f"其他数据: {len(df_additional)} 行")
        print(f"名称数据: {len(df_names)} 行")
        
        df = df_quarterly.copy()
        df = df.merge(df_q3, on='code', how='left')
        df = df.merge(df_mktcap, on='code', how='left')
        df = df.merge(df_q4_ratio, on='code', how='left')
        df = df.merge(df_additional, on='code', how='left')
        df = df.merge(df_names, on='code', how='left')
        
        print(f"合并后数据: {len(df)} 行")
        
        # 计算累计数据（Q3累计）
        # Q3累计 = Q1 + Q2 + Q3单季
        if 'Q3_营业收入' in df.columns and 'Q2_营业收入' in df.columns and 'Q1_营业收入' in df.columns:
            df['累计营业收入'] = df['Q1_营业收入'].fillna(0) + df['Q2_营业收入'].fillna(0) + df['Q3_营业收入'].fillna(0)
            df['累计归母净利润'] = df['Q1_归母净利润'].fillna(0) + df['Q2_归母净利润'].fillna(0) + df['Q3_归母净利润'].fillna(0)
            df['累计扣非净利润'] = df['Q1_扣非净利润'].fillna(0) + df['Q2_扣非净利润'].fillna(0) + df['Q3_扣非净利润'].fillna(0)
            df['财务费用'] = df['Q3_财务费用'].fillna(0)  # 使用Q3的财务费用
            df['净资产'] = df['Q3_净资产'].fillna(0)  # 使用Q3的净资产
            df['毛利率'] = df['Q3_毛利率'].fillna(0)  # 使用Q3的毛利率
            df['期间费用率'] = df['Q3_期间费用率'].fillna(0)  # 使用Q3的期间费用率
            df['非经常性损益'] = df['Q1_非经常性损益'].fillna(0) + df['Q2_非经常性损益'].fillna(0) + df['Q3_非经常性损益'].fillna(0)
        
        # 计算非经常损益指引（年化：Q1+Q2+Q3累计 * 4/3）
        if '非经常性损益' in df.columns:
            df['非经常损益指引'] = df['非经常性损益'].fillna(0) * 4 / 3
        
        # 4. 预测全年数据
        df = self.predict_full_year(df)
        
        # 5. 计算得分
        df = self.calculate_score(df)
        
        # 6. 调试信息：打印数据统计
        print("\n" + "=" * 60)
        print("数据统计信息")
        print("=" * 60)
        print(f"总股票数: {len(df)}")
        print(f"有数据的股票数: {len(df[df['code'].notna()])}")
        print(f"\n得分分布:")
        print(f"  硬门槛得分分布:")
        print(df['硬门槛得分'].value_counts().sort_index().to_string())
        print(f"  软指标得分分布:")
        print(df['软指标得分'].value_counts().sort_index().to_string())
        print(f"  总分分布:")
        print(df['总分'].value_counts().sort_index().to_string())
        print(f"\n总分≥7的股票数: {len(df[df['总分'] >= 7])}")
        print(f"市值≤30亿的股票数: {len(df[df['总市值'].fillna(float('inf')) <= 30e8])}")
        print(f"总分≥7且市值≤30亿的股票数: {len(df[(df['总分'] >= 7) & (df['总市值'].fillna(float('inf')) <= 30e8)])}")
        
        # 打印前10只股票的详细得分信息
        print(f"\n前10只股票的详细得分:")
        print("-" * 60)
        debug_cols = ['code', 'name', '硬门槛得分', '软指标得分', '总分', '总市值', 
                      '预测全年净利', '预测全年扣非', '预测全年营收']
        debug_cols = [col for col in debug_cols if col in df.columns]
        print(df[debug_cols].head(10).to_string(index=False))
        print("=" * 60 + "\n")
        
        # 6. 筛选和排序
        df_result = self.filter_and_sort(df)
        
        # 7. 准备输出列
        output_columns = [
            'code', 'name', '总分', '预测全年净利', '预测全年扣非', 
            '预测年末净资产', '总市值', '审计意见', '备注'
        ]
        
        # 添加备注信息和审计意见
        df_result['备注'] = ''
        
        # 确保所有列都存在，如果审计意见不存在则填充空字符串
        for col in output_columns:
            if col not in df_result.columns:
                if col == '审计意见':
                    df_result[col] = ''
                else:
                    df_result[col] = np.nan
        
        df_output = df_result[output_columns].copy()
        
        print("=" * 60)
        print("ST摘帽预测程序运行完成")
        print("=" * 60)
        
        return df_output


def main():
    """主函数"""
    try:
        # 创建预测器实例
        predictor = ST摘帽预测器()
        
        # 运行预测
        df_result = predictor.run()
        
        # 保存结果
        output_file = "st摘帽候选.csv"
        df_result.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到: {output_file}")
        
        # 打印前20行
        print("\n前20行结果：")
        print("=" * 100)
        print(df_result.head(20).to_string(index=False))
        print("=" * 100)
        
    except Exception as e:
        print(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

