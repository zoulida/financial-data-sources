"""
网格选股综合评分系统
计算 70%Vol + 30%HL 的网格综合打分并降序排序

功能：
- 批量获取1800+只基金的后复权日线数据
- 计算VolScore（历史波动率、波动稳定性、近期波动衰减）
- 计算HLScore（基于OLS回归的半衰期）
- 异步协程加速、进度条显示、异常捕获

依赖：pip install pandas numpy statsmodels tqdm xtquant scipy

作者：AI Assistant
创建时间：2025-11-02
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
# 当前文件: src/网格/网格选股/grid_stock_scoring.py
# parents[0] = src/网格/网格选股/
# parents[1] = src/网格/
# parents[2] = src/
# parents[3] = 项目根目录
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

# 导入必要的模块
try:
    import statsmodels.api as sm
except ImportError:
    print("[ERROR] 错误：未安装 statsmodels，请先安装: pip install statsmodels")
    sys.exit(1)

try:
    from scipy import stats
except ImportError:
    print("[ERROR] 错误：未安装 scipy，请先安装: pip install scipy")
    sys.exit(1)

# 导入自定义模块
try:
    from data_fetcher import DataFetcher
except ImportError as e:
    print(f"[ERROR] 错误：无法导入数据获取模块 data_fetcher: {e}")
    sys.exit(1)

try:
    from fetch_all_public_funds_final import fetch_all_public_funds
except ImportError:
    print("[WARNING] 警告：无法导入 fetch_all_public_funds，将使用本地CSV文件")
    fetch_all_public_funds = None

try:
    from md.获取enddate.get_date_range import get_date_range
except ImportError:
    print("[WARNING] 警告：无法导入 get_date_range，将使用默认日期范围")
    get_date_range = None


class GridStockScorer:
    """网格选股评分器"""
    
    def __init__(self, start_date="20241101", end_date=None):
        """
        初始化评分器
        
        Args:
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD，默认为当前日期
        """
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y%m%d")
        
        # 初始化数据获取器（独立模块）
        self.data_fetcher = DataFetcher(start_date=self.start_date, end_date=self.end_date)
        
        # 存储所有基金的HL值，用于跨品种分位计算
        self.all_hl_values = []
        
        print("="*80)
        print("网格选股综合评分系统")
        print("="*80)
        print(f"数据区间: {self.start_date} ~ {self.end_date}")
    
    def get_fund_list(self):
        """获取基金列表"""
        print("\n[1/5] 获取基金列表...")
        
        # 尝试使用函数获取
        if fetch_all_public_funds is not None:
            try:
                df = fetch_all_public_funds()
                if df is not None and len(df) > 0:
                    print(f"[OK] 获取到 {len(df)} 只基金")
                    return df
            except Exception as e:
                print(f"[WARNING] 函数获取失败: {e}")
        
        # 回退到读取CSV文件
        csv_path = Path(__file__).parent / "AllPublicFunds_Ashare.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            print(f"[OK] 从CSV文件读取 {len(df)} 只基金")
            return df
        
        print("[ERROR] 错误：无法获取基金列表")
        return None
    
    def get_stock_data(self, code):
        """
        获取单只标的的后复权日线数据（调用独立数据获取模块）
        
        Args:
            code: 标的代码，如 '159001.SZ'
            
        Returns:
            pd.DataFrame: 包含 open, high, low, close, volume 的数据框
        """
        return self.data_fetcher.get_single_stock_data(code, min_days=252)
    
    def calculate_vol_score(self, df):
        """
        计算VolScore（0-100分）
        
        Total = 0.4*VolScore + 0.35*StabScore + 0.25*DecayScore
        
        Args:
            df: 包含 open, high, low, close 的数据框
            
        Returns:
            tuple: (vol_score, hist30)
        """
        try:
            close = df['close'].values
            open_price = df['open'].values
            high = df['high'].values
            low = df['low'].values
            
            # 1. 历史波动率得分（40%）
            # 计算30日收盘-收盘年化波动率（%）
            returns_30 = np.log(close[-30:] / close[-31:-1])
            hist_vol_30 = np.std(returns_30) * np.sqrt(252) * 100  # 年化百分比
            
            # VolScore = min(100, max(0, (HistVol - 10) / 0.4))
            vol_score = min(100, max(0, (hist_vol_30 - 10) / 0.4))
            
            # 2. 波动稳定性得分（35%）
            # 计算跳空比率和收益率偏度
            # 前一日收盘价
            prev_close = close[:-1]
            current_open = open_price[1:]
            
            # 开盘涨跌幅（跳空）
            gap_returns = np.abs((current_open - prev_close) / prev_close)
            
            # ATR（真实波幅）
            atr_list = []
            for i in range(1, len(df)):
                tr = max(
                    high[i] - low[i],
                    abs(high[i] - close[i-1]),
                    abs(low[i] - close[i-1])
                )
                atr_list.append(tr / close[i-1])
            
            atr_mean = np.mean(atr_list[-252:]) if len(atr_list) >= 252 else np.mean(atr_list)
            gap_mean = np.mean(gap_returns[-252:]) if len(gap_returns) >= 252 else np.mean(gap_returns)
            
            # GapRatio
            gap_ratio = gap_mean / atr_mean if atr_mean > 0 else 0
            
            # 计算收益率偏度（252日）
            returns_252 = np.log(close[-252:] / close[-253:-1]) if len(close) > 252 else np.log(close[1:] / close[:-1])
            
            if len(returns_252) >= 30:
                skewness = stats.skew(returns_252)
            else:
                skewness = 0
            
            # StabScore 计算
            if gap_ratio > 0.5:
                stab_score = 0  # 跳空魔鬼
            else:
                # 偏度惩罚
                skew_penalty = 0
                if skewness < -0.5 or skewness > 0.5:
                    skew_penalty = min(abs(skewness) - 0.5, 0.5)
                
                stab_score = 100 * (1 - gap_ratio) * (1 - skew_penalty)
                stab_score = max(0, min(100, stab_score))
            
            # 3. 近期波动衰减得分（25%）
            # 计算252日年化波动率
            returns_252_all = np.log(close[-252:] / close[-253:-1]) if len(close) > 252 else np.log(close[1:] / close[:-1])
            hist_vol_252 = np.std(returns_252_all) * np.sqrt(252) * 100
            
            # DecayScore = 100 * (HistVol30 / HistVol252)
            if hist_vol_252 > 0:
                decay_ratio = hist_vol_30 / hist_vol_252
                # 比值 ≥1 得 100，≤0.3 得 0
                decay_score = max(0, min(100, (decay_ratio - 0.3) / 0.7 * 100))
            else:
                decay_score = 0
            
            # 合成总分
            total_vol_score = 0.4 * vol_score + 0.35 * stab_score + 0.25 * decay_score
            
            return round(total_vol_score, 2), round(hist_vol_30, 2)
            
        except Exception as e:
            return 0, 0
    
    def calculate_hl_score(self, df):
        """
        计算HLScore（0-100分）
        
        基于OLS离散回归计算半衰期，滚动63天计算HL序列
        
        Args:
            df: 包含 close 的数据框
            
        Returns:
            tuple: (hl_score, current_hl)
        """
        try:
            close = df['close'].values
            
            # 确保有足够的数据（至少252个交易日）
            if len(close) < 252:
                return 0, 0
            
            # 取最近252个交易日
            close_252 = close[-252:]
            
            # 对数价格序列
            log_prices = np.log(close_252)
            
            # 计算HL函数
            def calculate_hl_single(log_prices):
                """计算单次HL值"""
                try:
                    # 构造回归数据
                    y_t = log_prices[1:]
                    y_t_1 = log_prices[:-1]
                    delta_y = y_t - y_t_1
                    
                    # OLS回归: Δy_t = α + β·y_{t-1} + ε_t
                    X = sm.add_constant(y_t_1)
                    model = sm.OLS(delta_y, X)
                    results = model.fit()
                    beta = results.params[1]
                    
                    # 计算半衰期
                    if beta < 0:
                        theta = -np.log(1 + beta)
                        hl = np.log(2) / theta
                        return hl
                    else:
                        # β≥0，说明不均值回归，返回无穷大（给0分）
                        return np.inf
                
                except:
                    return np.inf
            
            # 滚动63天计算HL序列
            hl_list = []
            window = 63
            
            for i in range(window, len(log_prices) + 1):
                window_data = log_prices[i-window:i]
                hl_val = calculate_hl_single(window_data)
                hl_list.append(hl_val)
            
            # 当前HL值（最后一个）
            current_hl = hl_list[-1] if hl_list else np.inf
            
            # 过滤掉无穷大的值
            hl_history = [x for x in hl_list if x != np.inf]
            
            if not hl_history or current_hl == np.inf:
                return 0, 0
            
            # 存储到全局列表（用于跨品种分位计算）
            self.all_hl_values.append(current_hl)
            
            # 计算自身历史分位
            hl_history_array = np.array(hl_history)
            self_percentile = 1 - (np.sum(hl_history_array <= current_hl) / len(hl_history_array))
            
            # 跨品种分位暂时设为0.5（需要在所有数据计算完后统一计算）
            # 这里先返回自身分位的得分，后续会重新计算
            hl_score = self_percentile * 100
            
            return round(hl_score, 2), round(current_hl, 2)
            
        except Exception as e:
            return 0, 0
    
    def calculate_cross_hl_score(self, hl_values_dict):
        """
        重新计算所有标的的HLScore，加入跨品种分位
        
        Args:
            hl_values_dict: {code: (self_percentile, current_hl)}
            
        Returns:
            dict: {code: hl_score}
        """
        # 获取所有有效的HL值
        all_hl = [v[1] for v in hl_values_dict.values() if v[1] > 0 and v[1] != np.inf]
        
        if not all_hl:
            return {code: 0 for code in hl_values_dict.keys()}
        
        all_hl_array = np.array(all_hl)
        
        # 重新计算每个标的的分数
        new_scores = {}
        for code, (self_pct, current_hl) in hl_values_dict.items():
            if current_hl <= 0 or current_hl == np.inf:
                new_scores[code] = 0
            else:
                # 跨品种分位
                cross_percentile = 1 - (np.sum(all_hl_array <= current_hl) / len(all_hl_array))
                
                # Score = 0.6*self_pct + 0.4*cross_pct
                hl_score = 0.6 * self_pct * 100 + 0.4 * cross_percentile * 100
                new_scores[code] = round(hl_score, 2)
        
        return new_scores
    
    async def process_single_fund(self, code, name):
        """
        处理单只基金
        
        Args:
            code: 基金代码
            name: 基金名称
            
        Returns:
            dict: 评分结果
        """
        try:
            # 获取数据
            df = self.get_stock_data(code)
            if df is None or len(df) < 252:
                return None
            
            # 计算VolScore
            vol_score, hist30 = self.calculate_vol_score(df)
            
            # 计算HLScore（初步，不含跨品种分位）
            hl_score_temp, hl = self.calculate_hl_score(df)
            
            if hist30 == 0 or hl == 0:
                return None
            
            # 返回结果（hl_score会在后续重新计算）
            return {
                'code': code,
                'name': name,
                'hist30': hist30,
                'hl': hl,
                'vol_score': vol_score,
                'hl_score': hl_score_temp,  # 临时值
                'hl_self_pct': hl_score_temp / 100,  # 保存自身分位用于后续计算
                'total': 0  # 占位，后续计算
            }
            
        except Exception as e:
            return None
    
    async def process_all_funds(self, fund_df):
        """
        异步处理所有基金
        
        Args:
            fund_df: 基金列表DataFrame
            
        Returns:
            pd.DataFrame: 评分结果
        """
        print(f"\n[2/5] 开始批量下载数据并计算指标...")
        
        # DEBUG模式：只处理前10个基金
        fund_df_to_process = fund_df########.head(10)########################################################debug
        print(f"[DEBUG] 调试模式：仅处理前 {len(fund_df_to_process)} 只基金")
        
        results = []
        
        # 创建异步任务列表
        tasks = []
        for _, row in fund_df_to_process.iterrows():
            code = row['wind_code']
            name = row['sec_name']
            task = self.process_single_fund(code, name)
            tasks.append(task)
        
        # 使用tqdm显示进度，并发执行任务
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="处理进度"):
            result = await coro
            if result is not None:
                results.append(result)
        
        print(f"[OK] 成功处理 {len(results)}/{len(fund_df_to_process)} 只基金")
        
        if not results:
            print("[ERROR] 错误：没有成功处理任何基金")
            return None
        
        return results
    
    def finalize_scores(self, results):
        """
        最终化评分（重新计算HLScore并计算总分）
        
        Args:
            results: 初步结果列表
            
        Returns:
            pd.DataFrame: 最终结果
        """
        print("\n[3/5] 重新计算HLScore（加入跨品种分位）...")
        
        # 提取HL相关数据
        hl_dict = {}
        for r in results:
            # 自身分位 = hl_self_pct
            hl_dict[r['code']] = (r['hl_self_pct'], r['hl'])
        
        # 重新计算HLScore
        new_hl_scores = self.calculate_cross_hl_score(hl_dict)
        
        # 更新结果
        for r in results:
            r['hl_score'] = new_hl_scores[r['code']]
            # 计算总分：Total = 0.7*VolScore + 0.3*HLScore
            r['total'] = round(0.7 * r['vol_score'] + 0.3 * r['hl_score'], 2)
        
        # 转换为DataFrame
        df = pd.DataFrame(results)
        
        # 按总分降序排序
        df = df.sort_values('total', ascending=False).reset_index(drop=True)
        
        # 选择需要的列
        df = df[['code', 'name', 'hist30', 'hl', 'vol_score', 'hl_score', 'total']]
        
        return df
    
    def save_results(self, df):
        """
        保存结果到CSV
        
        Args:
            df: 结果DataFrame
        """
        print("\n[4/5] 保存结果...")
        
        output_path = Path(__file__).parent / 'result.csv'
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"[OK] 结果已保存到: {output_path}")
        print(f"   共 {len(df)} 条记录")
    
    def print_summary(self, df):
        """
        打印结果摘要
        
        Args:
            df: 结果DataFrame
        """
        print("\n[5/5] 结果摘要")
        print("="*80)
        
        print("\n[TOP 10] 前10名标的：")
        print(df.head(10).to_string(index=False))
        
        print("\n[STATS] 统计信息：")
        print(f"  总标的数量: {len(df)}")
        print(f"  平均VolScore: {df['vol_score'].mean():.2f}")
        print(f"  平均HLScore: {df['hl_score'].mean():.2f}")
        print(f"  平均总分: {df['total'].mean():.2f}")
        print(f"  最高分: {df['total'].max():.2f} ({df.iloc[0]['name']})")
        print(f"  最低分: {df['total'].min():.2f}")
        
        print("\n" + "="*80)
    
    async def run(self):
        """运行完整流程"""
        start_time = datetime.now()
        
        # 1. 获取基金列表
        fund_df = self.get_fund_list()
        if fund_df is None or len(fund_df) == 0:
            print("[ERROR] 错误：无法获取基金列表")
            return
        
        # 2. 处理所有基金
        results = await self.process_all_funds(fund_df)
        if results is None or len(results) == 0:
            print("[ERROR] 错误：处理失败")
            return
        
        # 3. 最终化评分
        df_final = self.finalize_scores(results)
        
        # 4. 保存结果
        self.save_results(df_final)
        
        # 5. 打印摘要
        self.print_summary(df_final)
        
        # 计算耗时
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n[TIME] 总耗时: {elapsed:.1f} 秒")
        print("[OK] 任务完成！")


def main():
    """主函数"""
    try:
        # 获取日期范围
        if get_date_range is not None:
            try:
                start_date, end_date, reason = get_date_range()
                print(f"\n[DATE] 日期范围：{start_date} ~ {end_date} ({reason})")
            except Exception as e:
                print(f"[WARNING] 获取日期范围失败: {e}，使用默认值")
                start_date = "20241101"
                end_date = datetime.now().strftime("%Y%m%d")
        else:
            start_date = "20241101"
            end_date = datetime.now().strftime("%Y%m%d")
        
        start_date = '20241001'
        # 创建评分器
        scorer = GridStockScorer(start_date=start_date, end_date=end_date)
        
        # 运行
        asyncio.run(scorer.run())
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断，程序退出")
    except Exception as e:
        print(f"\n[ERROR] 程序异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保程序退出
        print("\n[INFO] 程序结束")
        import sys
        sys.exit(0)


if __name__ == "__main__":
    main()

