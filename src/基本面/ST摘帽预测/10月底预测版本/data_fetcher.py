"""
数据获取模块

负责从Wind API获取所有需要的财务数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List
from WindPy import w
import warnings
warnings.filterwarnings('ignore')


class WindDataFetcher:
    """Wind数据获取器"""
    
    def __init__(self):
        """初始化Wind连接"""
        self.w = w
        self.w.start()
        print("Wind API已启动")
        
        # 获取当前年份
        self.current_year = datetime.now().year
        self.current_date = datetime.now()
    
    def __del__(self):
        """关闭Wind连接"""
        try:
            self.w.stop()
            print("Wind API已关闭")
        except:
            pass
    
    def get_st_stocks(self) -> List[str]:
        """
        获取ST板块股票代码列表
        
        Returns:
            ST股票代码列表
        """
        print("正在获取ST板块股票列表...")
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 使用Wind板块功能获取ST板块股票
        # sectorid=1000011270000000 是ST板块ID
        data = self.w.wset("sectorconstituent", f"date={today};sectorid=1000011270000000")
        
        if data.ErrorCode != 0:
            raise Exception(f"获取ST股票列表失败: ErrorCode={data.ErrorCode}")
        
        codes = data.Data[1]  # 股票代码在Data[1]
        print(f"获取到 {len(codes)} 只ST股票")
        
        return codes
    
    def fetch_quarterly_data(self, codes: List[str]) -> pd.DataFrame:
        """
        获取当年Q1、Q2、Q3三个季度的数据
        
        Parameters:
            codes: 股票代码列表
            
        Returns:
            包含Q1、Q2、Q3三个季度数据的DataFrame
        """
        print("正在获取Q1、Q2、Q3三个季度财务数据...")
        
        # 使用今年的数据
        q1_date = f"{self.current_year}0331"
        q2_date = f"{self.current_year}0630"
        q3_date = f"{self.current_year}0930"
        print(f"  使用报告期: Q1={q1_date}, Q2={q2_date}, Q3={q3_date} (年份: {self.current_year})")
        
        # 定义需要获取的字段
        fields = [
            "np_belongto_parcomsh",      # 归属母公司股东的净利润（累计）
            "deductedprofit_ttm2",        # 扣除非经常性损益后归属母公司股东的净利润（TTM）
            "oper_rev",                   # 营业收入（累计）
            "grossprofitmargin",          # 销售毛利率
            "expensetosales",             # 销售期间费用率
            "fin_exp_is",                 # 财务费用
            "eqy_belongto_parcomsh",     # 归属母公司股东的权益（净资产）
            "fa_nrgl",                    # 非经常性损益
        ]
        
        # 分批获取数据（每批500只）
        batch_size = 500
        all_data = []
        
        # 获取Q1、Q2、Q3三个季度的数据
        quarters = [
            ('Q1', q1_date),
            ('Q2', q2_date),
            ('Q3', q3_date),
        ]
        
        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i+batch_size]
            print(f"  处理第 {i//batch_size + 1} 批，共 {len(batch_codes)} 只股票")
            
            codes_str = ",".join(batch_codes)
            
            # 为每只股票初始化数据字典
            stock_data = {code: {} for code in batch_codes}
            
            # 获取每个季度的数据
            for quarter_name, quarter_date in quarters:
                # 获取该季度的所有字段数据
                for field_idx, field in enumerate(fields):
                    try:
                        field_data = self.w.wsd(
                            codes_str,
                            field,
                            quarter_date,
                            quarter_date,
                            f"Period=Q;rptType=1;unit=1"
                        )
                        
                        if field_data.ErrorCode == 0 and len(field_data.Data) > 0 and len(field_data.Data[0]) > 0:
                            # Data[0]是按股票顺序的数据列表
                            for stock_idx, code in enumerate(batch_codes):
                                if stock_idx < len(field_data.Data[0]):
                                    val = field_data.Data[0][stock_idx]
                                    # 存储字段名：Q1_字段名, Q2_字段名, Q3_字段名
                                    field_name_map = {
                                        0: '归母净利润',
                                        1: '扣非净利润',
                                        2: '营业收入',
                                        3: '毛利率',
                                        4: '期间费用率',
                                        5: '财务费用',
                                        6: '净资产',
                                        7: '非经常性损益',
                                    }
                                    if field_idx in field_name_map:
                                        col_name = f"{quarter_name}_{field_name_map[field_idx]}"
                                        stock_data[code][col_name] = val if val is not None else np.nan
                        else:
                            # 如果获取失败，填充None
                            for code in batch_codes:
                                field_name_map = {
                                    0: '归母净利润',
                                    1: '扣非净利润',
                                    2: '营业收入',
                                    3: '毛利率',
                                    4: '期间费用率',
                                    5: '财务费用',
                                    6: '净资产',
                                    7: '非经常性损益',
                                }
                                if field_idx in field_name_map:
                                    col_name = f"{quarter_name}_{field_name_map[field_idx]}"
                                    stock_data[code][col_name] = np.nan
                    except Exception as e:
                        print(f"    警告：字段 {field} 在{quarter_name}获取失败: {str(e)}")
                        for code in batch_codes:
                            field_name_map = {
                                0: '归母净利润',
                                1: '扣非净利润',
                                2: '营业收入',
                                3: '毛利率',
                                4: '期间费用率',
                                5: '财务费用',
                                6: '净资产',
                                7: '非经常性损益',
                            }
                            if field_idx in field_name_map:
                                col_name = f"{quarter_name}_{field_name_map[field_idx]}"
                                stock_data[code][col_name] = np.nan
            
            # 将数据转换为DataFrame行
            for code in batch_codes:
                row = {'code': code}
                row.update(stock_data[code])
                all_data.append(row)
        
        df = pd.DataFrame(all_data)
        print(f"完成，共获取 {len(df)} 只股票的数据")
        
        # 调试：打印第一只股票的数据
        if len(df) > 0:
            print(f"  示例：第一只股票的数据列: {list(df.columns)}")
            if 'Q3_营业收入' in df.columns:
                print(f"  Q3营业收入非空: {df['Q3_营业收入'].notna().sum()} / {len(df)}")
        
        return df
    
    def fetch_q3_single_quarter_data(self, codes: List[str]) -> pd.DataFrame:
        """
        获取Q3单季数据（单季营收、单季同比、单季毛利率、单季期间费用率）
        
        Parameters:
            codes: 股票代码列表
            
        Returns:
            包含Q3单季数据的DataFrame
        """
        print("正在获取Q3单季数据...")
        
        # 使用今年的数据
        q2_date = f"{self.current_year}0630"
        q3_date = f"{self.current_year}0930"
        last_year_q2_date = f"{self.current_year-1}0630"
        last_year_q3_date = f"{self.current_year-1}0930"
        print(f"  使用报告期: Q2={q2_date}, Q3={q3_date} (年份: {self.current_year})")
        print(f"  去年同期: Q2={last_year_q2_date}, Q3={last_year_q3_date} (用于计算同比)")
        
        batch_size = 500
        all_data = []
        
        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i+batch_size]
            
            codes_str = ",".join(batch_codes)
            
            # 使用w.wsd获取Q3累计营业收入
            data_q3 = self.w.wsd(
                codes_str,
                "oper_rev",
                q3_date,
                q3_date,
                f"Period=Q;rptType=1;unit=1"
            )
            
            # 使用w.wsd获取Q2累计营业收入
            data_q2 = self.w.wsd(
                codes_str,
                "oper_rev",
                q2_date,
                q2_date,
                f"Period=Q;rptType=1;unit=1"
            )
            
            # 使用w.wsd获取Q3毛利率和期间费用率
            data_gross = self.w.wsd(
                codes_str,
                "grossprofitmargin",
                q3_date,
                q3_date,
                f"Period=Q;rptType=1;unit=1"
            )
            
            data_expense = self.w.wsd(
                codes_str,
                "expensetosales",
                q3_date,
                q3_date,
                f"Period=Q;rptType=1;unit=1"
            )
            
            # 获取去年Q3、Q2、Q1累计营收（用于计算同比）
            last_year_q1_date = f"{self.current_year-1}0331"
            
            data_last_q3 = self.w.wsd(
                codes_str,
                "oper_rev",
                last_year_q3_date,
                last_year_q3_date,
                f"Period=Q;rptType=1;unit=1"
            )
            
            data_last_q2 = self.w.wsd(
                codes_str,
                "oper_rev",
                last_year_q2_date,
                last_year_q2_date,
                f"Period=Q;rptType=1;unit=1"
            )
            
            # 同时获取去年Q1数据，作为Q2数据获取失败时的备选
            data_last_q1 = self.w.wsd(
                codes_str,
                "oper_rev",
                last_year_q1_date,
                last_year_q1_date,
                f"Period=Q;rptType=1;unit=1"
            )
            
            # 解析数据
            # 调试：检查第一批数据
            if i == 0 and len(batch_codes) > 0:
                print(f"  调试：检查数据获取情况（第一只股票 {batch_codes[0]}）")
                print(f"    今年Q3数据: ErrorCode={data_q3.ErrorCode}, 数据长度={len(data_q3.Data[0]) if data_q3.ErrorCode == 0 and len(data_q3.Data) > 0 else 0}")
                print(f"    今年Q2数据: ErrorCode={data_q2.ErrorCode}, 数据长度={len(data_q2.Data[0]) if data_q2.ErrorCode == 0 and len(data_q2.Data) > 0 else 0}")
                print(f"    去年Q3数据: ErrorCode={data_last_q3.ErrorCode}, 数据长度={len(data_last_q3.Data[0]) if data_last_q3.ErrorCode == 0 and len(data_last_q3.Data) > 0 else 0}")
                print(f"    去年Q2数据: ErrorCode={data_last_q2.ErrorCode}, 数据长度={len(data_last_q2.Data[0]) if data_last_q2.ErrorCode == 0 and len(data_last_q2.Data) > 0 else 0}")
                print(f"    去年Q1数据: ErrorCode={data_last_q1.ErrorCode}, 数据长度={len(data_last_q1.Data[0]) if data_last_q1.ErrorCode == 0 and len(data_last_q1.Data) > 0 else 0}")
            
            for idx in range(len(batch_codes)):
                code = batch_codes[idx]
                
                # Q3单季营收 = Q3累计 - Q2累计
                q3_rev = None
                if (data_q3.ErrorCode == 0 and data_q2.ErrorCode == 0 and 
                    len(data_q3.Data) > 0 and len(data_q2.Data) > 0 and
                    idx < len(data_q3.Data[0]) and idx < len(data_q2.Data[0])):
                    rev_q3 = data_q3.Data[0][idx]
                    rev_q2 = data_q2.Data[0][idx]
                    if rev_q3 is not None and rev_q2 is not None:
                        q3_rev = rev_q3 - rev_q2
                
                # 去年Q3单季营收
                last_q3_rev = None
                last_rev_q3 = None
                last_rev_q2 = None
                
                # 尝试获取去年Q3累计数据
                if (data_last_q3.ErrorCode == 0 and
                    len(data_last_q3.Data) > 0 and
                    idx < len(data_last_q3.Data[0])):
                    last_rev_q3 = data_last_q3.Data[0][idx]
                
                # 尝试获取去年Q2累计数据
                if (data_last_q2.ErrorCode == 0 and
                    len(data_last_q2.Data) > 0 and
                    idx < len(data_last_q2.Data[0])):
                    last_rev_q2 = data_last_q2.Data[0][idx]
                
                # 尝试获取去年Q1累计数据（作为Q2获取失败时的备选）
                last_rev_q1 = None
                if (data_last_q1.ErrorCode == 0 and
                    len(data_last_q1.Data) > 0 and
                    idx < len(data_last_q1.Data[0])):
                    last_rev_q1 = data_last_q1.Data[0][idx]
                
                # 计算去年Q3单季营收
                if last_rev_q3 is not None and last_rev_q2 is not None:
                    # 最佳情况：有Q2和Q3数据，直接计算
                    last_q3_rev = last_rev_q3 - last_rev_q2
                elif last_rev_q3 is not None and last_rev_q1 is not None:
                    # 备选方案：Q2获取失败，使用Q3累计 - Q1累计 * 2（假设Q1和Q2相等）
                    # 但更准确的方法是：如果有Q1和Q3，可以用 Q3单季 = Q3累计 - Q1累计 * 2
                    # 或者更保守：Q3单季 = (Q3累计 - Q1累计) * 2/3（假设Q1、Q2、Q3按比例增长）
                    # 这里使用：Q3单季 = Q3累计 - Q1累计（假设Q2 = Q1，即Q1+Q2 = Q1*2）
                    # 但这样会高估Q3单季，更保守的方法是：
                    # Q3单季 ≈ (Q3累计 - Q1累计) / 2，假设Q1、Q2、Q3平均分配
                    # 或者：Q3单季 = Q3累计 - Q1累计 * 1.5（假设Q2是Q1的1.5倍）
                    # 最简单：Q3单季 = (Q3累计 - Q1累计) * (2/3)，假设Q3单季占(Q3-Q1)的2/3
                    last_q3_rev = (last_rev_q3 - last_rev_q1) * (2/3) if last_rev_q3 > last_rev_q1 else None
                elif last_rev_q3 is not None:
                    # 最后备选：只有Q3数据，使用Q3累计/3作为估算（假设Q1、Q2、Q3平均分配）
                    last_q3_rev = last_rev_q3 / 3 if last_rev_q3 > 0 else None
                
                # 调试：打印第一只股票的详细数据
                if i == 0 and idx == 0:
                    print(f"  调试：第一只股票 {code} 的详细数据:")
                    print(f"    今年Q3累计: {rev_q3 if 'rev_q3' in locals() else 'N/A'}")
                    print(f"    今年Q2累计: {rev_q2 if 'rev_q2' in locals() else 'N/A'}")
                    print(f"    今年Q3单季: {q3_rev}")
                    print(f"    去年Q3累计: {last_rev_q3 if 'last_rev_q3' in locals() else 'N/A'}")
                    print(f"    去年Q2累计: {last_rev_q2 if 'last_rev_q2' in locals() else 'N/A'}")
                    print(f"    去年Q1累计: {last_rev_q1 if 'last_rev_q1' in locals() else 'N/A'}")
                    print(f"    去年Q3单季: {last_q3_rev}")
                    if last_q3_rev is not None:
                        print(f"    计算方法: {'Q3-Q2' if last_rev_q2 is not None else ('Q3-Q1估算' if last_rev_q1 is not None else 'Q3/3估算')}")
                
                # Q3单季同比
                q3_yoy = np.nan
                if q3_rev is not None and last_q3_rev is not None and last_q3_rev != 0:
                    q3_yoy = (q3_rev - last_q3_rev) / last_q3_rev
                elif i == 0 and idx == 0:
                    print(f"  调试：同比计算失败原因:")
                    print(f"    q3_rev: {q3_rev}")
                    print(f"    last_q3_rev: {last_q3_rev}")
                    if last_q3_rev == 0:
                        print(f"    去年Q3单季营收为0，无法计算同比")
                
                # Q3单季毛利率和期间费用率
                q3_gross_margin = None
                q3_expense_ratio = None
                if data_gross.ErrorCode == 0 and len(data_gross.Data) > 0 and idx < len(data_gross.Data[0]):
                    q3_gross_margin = data_gross.Data[0][idx]
                if data_expense.ErrorCode == 0 and len(data_expense.Data) > 0 and idx < len(data_expense.Data[0]):
                    q3_expense_ratio = data_expense.Data[0][idx]
                
                row = {
                    'code': code,
                    'Q3单季营收': q3_rev if q3_rev is not None else np.nan,
                    'Q3单季同比': q3_yoy,
                    'Q3单季毛利率': q3_gross_margin if q3_gross_margin is not None else np.nan,
                    'Q3单季期间费用率': q3_expense_ratio if q3_expense_ratio is not None else np.nan,
                }
                all_data.append(row)
        
        df = pd.DataFrame(all_data)
        print(f"完成，共获取 {len(df)} 只股票的Q3单季数据")
        
        return df
    
    def fetch_market_cap(self, codes: List[str]) -> pd.DataFrame:
        """
        使用w.wss获取最新总市值
        
        Parameters:
            codes: 股票代码列表
            
        Returns:
            包含总市值的DataFrame
        """
        print("正在获取最新总市值...")
        
        # 使用昨天的日期获取总市值（今天的数据可能未更新）
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        
        batch_size = 500
        all_data = []
        
        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i+batch_size]
            
            # 使用w.wss获取总市值
            data = self.w.wss(
                batch_codes,
                "mkt_cap_ard",  # 总市值
                f"unit=1;tradeDate={yesterday}"
            )
            
            if data.ErrorCode != 0:
                print(f"  警告: 第 {i//batch_size + 1} 批市值获取失败，ErrorCode={data.ErrorCode}")
                for code in batch_codes:
                    all_data.append({'code': code, '总市值': np.nan})
                continue
            
            for idx, code in enumerate(data.Codes):
                mkt_cap = data.Data[0][idx] if data.Data[0][idx] is not None else np.nan
                all_data.append({'code': code, '总市值': mkt_cap})
        
        df = pd.DataFrame(all_data)
        print(f"完成，共获取 {len(df)} 只股票的市值数据")
        
        return df
    
    def fetch_q4_revenue_ratio(self, codes: List[str]) -> pd.DataFrame:
        """
        获取最近2年四季度营收占比（可选）
        
        Parameters:
            codes: 股票代码列表
            
        Returns:
            包含Q4营收占比的DataFrame
        """
        print("正在获取前三年Q4营收占比...")
        
        # 计算最近3年的年度和Q4日期（用于计算前三年Q4平均占比）
        years = [self.current_year - 1, self.current_year - 2, self.current_year - 3]
        
        batch_size = 500
        all_data = []
        
        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i+batch_size]
            
            # 批量获取数据
            year_revs = {}  # {year: {code: revenue}}
            q3_revs = {}    # {year: {code: revenue}}
            
            codes_str = ",".join(batch_codes)
            
            for year in years:
                year_date = f"{year}1231"
                q3_date = f"{year}0930"
                
                # 使用w.wsd获取全年营收
                data_year = self.w.wsd(
                    codes_str,
                    "oper_rev",
                    year_date,
                    year_date,
                    f"Period=A;rptType=1;unit=1"
                )
                
                # 使用w.wsd获取Q3累计营收
                data_q3 = self.w.wsd(
                    codes_str,
                    "oper_rev",
                    q3_date,
                    q3_date,
                    f"Period=Q;rptType=1;unit=1"
                )
                
                year_revs[year] = {}
                q3_revs[year] = {}
                
                if data_year.ErrorCode == 0 and len(data_year.Data) > 0 and len(data_year.Data[0]) > 0:
                    for idx, code in enumerate(batch_codes):
                        if idx < len(data_year.Data[0]):
                            year_revs[year][code] = data_year.Data[0][idx]
                
                if data_q3.ErrorCode == 0 and len(data_q3.Data) > 0 and len(data_q3.Data[0]) > 0:
                    for idx, code in enumerate(batch_codes):
                        if idx < len(data_q3.Data[0]):
                            q3_revs[year][code] = data_q3.Data[0][idx]
            
            # 计算每只股票的Q4营收占比
            for code in batch_codes:
                ratios = []
                for year in years:
                    year_rev = year_revs[year].get(code)
                    q3_rev = q3_revs[year].get(code)
                    
                    if year_rev is not None and q3_rev is not None and year_rev != 0:
                        q4_rev = year_rev - q3_rev
                        ratio = q4_rev / year_rev
                        ratios.append(ratio)
                
                # 计算前三年Q4平均占比
                avg_ratio = np.mean(ratios) if ratios else np.nan
                all_data.append({
                    'code': code,
                    'Q4营收占比均值': avg_ratio  # 前三年Q4平均占比
                })
        
        df = pd.DataFrame(all_data)
        print(f"完成，共获取 {len(df)} 只股票的Q4营收占比数据")
        
        return df
    
    def fetch_additional_data(self, codes: List[str]) -> pd.DataFrame:
        """
        获取其他数据：非经常损益指引、审计意见、违规处罚次数、经营现金流
        
        Parameters:
            codes: 股票代码列表
            
        Returns:
            包含其他数据的DataFrame
        """
        print("正在获取其他数据（审计意见、违规标识、经营现金流等）...")
        
        q3_date = f"{self.current_year}0930"
        
        batch_size = 500
        all_data = []
        
        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i+batch_size]
            
            # 获取审计意见代码
            # 使用 stmnote_audit_category 字段，返回字符串（如"无保留意见"）
            data_audit = self.w.wss(
                batch_codes,
                "stmnote_audit_category",  # 审计意见类型（字符串格式）
                f"rptDate={q3_date}"
            )
            
            # 获取违规处罚次数
            # 使用 cac_illegalitynum 字段，统计今年1月1日至今的违规处罚次数
            start_date = f"{self.current_year}0101"
            end_date = self.current_date.strftime('%Y%m%d')
            data_violation = self.w.wss(
                batch_codes,
                "cac_illegalitynum",  # 违规处罚次数
                f"startDate={start_date};endDate={end_date}"
            )
            
            # 获取经营现金流
            data_ocf = self.w.wss(
                batch_codes,
                "net_cash_flows_oper_act",  # 经营活动产生的现金流量净额
                f"unit=1;rptDate={q3_date};rptType=1"
            )
            
            
            # 解析数据
            for idx, code in enumerate(batch_codes):
                # 获取审计意见（字符串格式）
                audit_opinion = None
                if data_audit.ErrorCode == 0 and idx < len(data_audit.Data[0]):
                    audit_opinion = data_audit.Data[0][idx]
                
                ocf = None
                if data_ocf.ErrorCode == 0 and idx < len(data_ocf.Data[0]):
                    ocf = data_ocf.Data[0][idx]
                
                # 违规处罚次数（今年1月1日至今）
                violation_count = 0  # 默认0（无违规处罚）
                if data_violation.ErrorCode == 0 and idx < len(data_violation.Data[0]):
                    violation_count_raw = data_violation.Data[0][idx]
                    # 转换为整数，如果为None则默认为0
                    if violation_count_raw is not None:
                        try:
                            violation_count = int(violation_count_raw)
                        except (ValueError, TypeError):
                            violation_count = 0
                
                row = {
                    'code': code,
                    '非经常损益指引': 0.0,  # 默认值，若无指引则为0（后续会从季度数据中获取）
                    '审计意见': audit_opinion if audit_opinion is not None else '',  # 字符串格式，如"无保留意见"
                    '违规立案标识': violation_count,  # 违规处罚次数（今年1月1日至今）
                    '经营现金流': ocf if ocf is not None else np.nan,
                }
                all_data.append(row)
        
        df = pd.DataFrame(all_data)
        print(f"完成，共获取 {len(df)} 只股票的其他数据")
        
        return df
    
    def get_stock_names(self, codes: List[str]) -> pd.DataFrame:
        """
        获取股票名称
        
        Parameters:
            codes: 股票代码列表
            
        Returns:
            包含代码和名称的DataFrame
        """
        print("正在获取股票名称...")
        
        batch_size = 500
        all_data = []
        
        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i+batch_size]
            
            data = self.w.wss(
                batch_codes,
                "sec_name",
                ""
            )
            
            if data.ErrorCode != 0:
                for code in batch_codes:
                    all_data.append({'code': code, 'name': ''})
                continue
            
            for idx, code in enumerate(data.Codes):
                name = data.Data[0][idx] if data.Data[0][idx] is not None else ''
                all_data.append({'code': code, 'name': name})
        
        df = pd.DataFrame(all_data)
        
        return df

