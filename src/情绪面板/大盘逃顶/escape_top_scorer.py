"""
A股牛市逃顶打分器
每天收盘后自动运行，根据4个指标打分：
1. 融资余额 (0-1分)
2. 开户数 (0-1分)  
3. 量价背离 (0-1分+)
4. 估值百分位 (0-1分)
总分≥2.2分时发出强烈逃顶信号
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import requests
from bs4 import BeautifulSoup
import time
import json

warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 配置文件路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CURRENT_DIR, 'escape_top_history.csv')


class EscapeTopScorer:
    """逃顶打分器主类"""
    
    def __init__(self):
        """初始化打分器"""
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.scores = {
            'date': self.today,
            'financing_score': 0.0,  # 融资余额得分
            'account_score': 0.0,     # 开户数得分
            'divergence_score': 0.0,  # 量价背离得分
            'valuation_score': 0.0,   # 估值百分位得分
            'total_score': 0.0        # 总分
        }
        
    def get_financing_balance_score(self):
        """
        指标1: 融资余额评分
        规则：取融资净买入最近3日
        - 3日全为负 → 1分
        - 连续2日为负 → 0.4分
        - 只有1日为负 → 0.2分
        - 其他 → 0分
        """
        print("\n[1/4] 正在获取融资余额数据...")
        score = 0.0
        
        try:
            # 首先尝试使用Wind API获取
            try:
                from WindPy import w
                w.start()
                
                # 获取最近10天的融资融券数据（确保能取到至少3个交易日）
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
                
                # 使用 wset 接口获取融资融券交易规模数据
                # 参数说明：exchange=all（全市场），frequency=day（日度数据）
                params = (
                    f"exchange=all;"
                    f"startdate={start_date};"
                    f"enddate={end_date};"
                    f"frequency=day;"
                    f"sort=desc"  # 降序，最新数据在前
                )
                
                data = w.wset("margintradingsizeanalys(value)", params)
                
                if data.ErrorCode == 0 and data.Data and len(data.Data) > 0:
                    # 转换为DataFrame便于处理
                    df = pd.DataFrame(data.Data, index=data.Fields).T
                    df.columns = data.Fields
                    
                    # 获取期间净买入额字段（period_net_purchases）
                    if 'period_net_purchases' in df.columns:
                        # 取最近3个交易日的数据
                        net_buy_values = df['period_net_purchases'].head(3).tolist()
                        
                        # 转换为数值类型
                        net_buy_values = [float(v) for v in net_buy_values if v is not None and str(v) != 'nan']
                        
                    if len(net_buy_values) >= 2:  # 至少有2天的数据
                        negative_days = sum(1 for v in net_buy_values if v < 0)
                    
                        if len(net_buy_values) == 3 and negative_days == 3:
                            score = 1.0
                            print(f"  ✓ Wind数据：最近3日融资净买入全为负，得分: {score}")
                            print(f"    数据: {[f'{v/100000000:.2f}亿' for v in net_buy_values]}")
                        elif negative_days == 2:
                            score = 0.4
                            print(f"  ✓ Wind数据：最近{len(net_buy_values)}日有2日融资净买入为负，得分: {score}")
                            print(f"    数据: {[f'{v/100000000:.2f}亿' for v in net_buy_values]}")
                        elif negative_days == 1:
                            score = 0.2
                            print(f"  ✓ Wind数据：最近{len(net_buy_values)}日有1日融资净买入为负，得分: {score}")
                            print(f"    数据: {[f'{v/100000000:.2f}亿' for v in net_buy_values]}")
                        else:
                            print(f"  ✓ Wind数据：融资净买入情况正常，得分: {score}")
                            print(f"    最近{len(net_buy_values)}日数据: {[f'{v/100000000:.2f}亿' for v in net_buy_values]}")
                        
                        w.stop()
                        return score
                    else:
                        print("  ✗ Wind数据中未找到期间净买入额字段")
                    
                w.stop()
                
            except Exception as wind_error:
                print(f"  ✗ Wind API获取失败: {wind_error}")
            
            # Wind失败，使用东方财富网爬虫
            print("  → 尝试从东方财富网爬取数据...")
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                'sortColumns': 'TRADE_DATE',
                'sortTypes': '-1',
                'pageSize': '10',
                'pageNumber': '1',
                'reportName': 'RPT_RZRQ_LSHJ',
                'columns': 'ALL',
                'source': 'WEB',
                'client': 'WEB'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result') and data['result'].get('data'):
                    records = data['result']['data'][:3]  # 取最近3日
                    
                    # 融资净买入 = RZJME (融资净买额)
                    net_buy_values = [float(r.get('RZJME', 0)) for r in records]
                    negative_days = sum(1 for v in net_buy_values if v < 0)
                    
                    if negative_days == 3:
                        score = 1.0
                        print(f"  ✓ 东财数据：最近3日融资净买入全为负，得分: {score}")
                    elif negative_days == 2:
                        score = 0.4
                        print(f"  ✓ 东财数据：最近3日有2日融资净买入为负，得分: {score}")
                    elif negative_days == 1:
                        score = 0.2
                        print(f"  ✓ 东财数据：最近3日有1日融资净买入为负，得分: {score}")
                    else:
                        print(f"  ✓ 东财数据：融资净买入情况正常，得分: {score}")
                    
                    return score
            
            print("  ✗ 东方财富网数据获取失败")
            
        except Exception as e:
            print(f"  ✗ 融资余额数据获取异常: {e}")
        
        return score
    
    def get_new_accounts_score(self):
        """
        指标2: 开户数评分
        规则：取最新两个月"新增投资者数量"
        - 环比降幅 ≥30% → 1.5分
        - 环比降幅 0% → 0分
        - 环比降幅 0-30% → 按比例连续记分
        
        数据源：Wind API (M0010401: 新增投资者数量)
        """
        print("\n[2/4] 正在获取开户数数据...")
        score = 0.0
        
        try:
            from WindPy import w
            w.start()
            
            # 获取新增投资者数（月度数据）
            # M0010401: 新增投资者数量（万户）
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            # 使用 Fill=Previous 参数填充缺失值
            data = w.edb("M0010401", start_date, end_date, "Fill=Previous")
            
            if data.ErrorCode != 0:
                print(f"  ✗ Wind API错误码: {data.ErrorCode}")
                w.stop()
                return score
            
            if not data.Data or len(data.Data[0]) < 2:
                print(f"  ✗ Wind数据不足（需要至少2个月数据）")
                w.stop()
                return score
            
            # 获取时间序列和数据
            times = data.Times  # 日期列表
            values = data.Data[0]  # 数据列表
            
            # 转换为DataFrame便于处理
            df_wind = pd.DataFrame({
                'date': times,
                'value': values
            })
            
            # 按日期降序排列，取最近两个月
            df_wind = df_wind.sort_values('date', ascending=False).head(2)
            
            if len(df_wind) < 2:
                print(f"  ✗ Wind数据不足2个月")
                w.stop()
                return score
            
            last_month = float(df_wind.iloc[0]['value'])
            prev_month = float(df_wind.iloc[1]['value'])
            last_date = df_wind.iloc[0]['date'].strftime('%Y-%m')
            prev_date = df_wind.iloc[1]['date'].strftime('%Y-%m')
            
            if prev_month <= 0:
                print(f"  ✗ Wind数据异常：上月开户数为 {prev_month}")
                w.stop()
                return score
            
            # 计算环比变化率
            change_rate = (last_month - prev_month) / prev_month * 100
            decline_rate = -change_rate  # 降幅为正数
            
            # 根据新规则计算得分
            if decline_rate >= 30:
                score = 1.5
            elif decline_rate > 0:
                score = decline_rate / 30.0 * 1.5
            else:
                score = 0.0
            
            print(f"  ✓ Wind数据：{prev_date}({prev_month:.2f}万) → {last_date}({last_month:.2f}万)")
            print(f"    环比变化: {change_rate:+.1f}% (降幅: {decline_rate:.1f}%)")
            print(f"    得分: {score:.2f}")
            
            w.stop()
            return score
            
        except ImportError:
            print(f"  ✗ WindPy 未安装，请先安装 Wind 终端")
        except Exception as e:
            print(f"  ✗ 开户数数据获取异常: {e}")
            try:
                w.stop()
            except:
                pass
        
        return score
    
    def get_volume_divergence_score(self):
        """
        指标3: 量价背离评分 (上证指数)
        规则：取最近5日行情
        - 每日"收盘涨 & 成交量萎缩" → 按萎缩幅度计分
          - 萎缩 ≥5% → 0.2分起
          - 萎缩 ≥20% → 1.0分
          - 萎缩 5%-20%之间 → 按比例线性插值
        - 多日得分求和
        
        计分公式：
        - 萎缩率 < 5%: 0分
        - 萎缩率 = 5%: 0.2分
        - 萎缩率 5%-20%: 0.2 + (萎缩率-5%)/(20%-5%) * 0.8
        - 萎缩率 ≥ 20%: 1.0分
        
        数据源：XtQuant (getDayData)
        """
        print("\n[3/4] 正在获取量价背离数据...")
        score = 0.0
        
        try:
            # 导入数据获取模块
            import sys
            import os
            from datetime import datetime, timedelta
            
            # 添加数据模块路径
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_module_path = os.path.join(project_root, 'source', '实盘', 'xuntou', 'datadownload')
            if data_module_path not in sys.path:
                sys.path.insert(0, data_module_path)
            
            from source.实盘.xuntou.datadownload.合并下载数据 import getDayData
            
            # 上证指数代码
            index_code = '000001.SH'
            
            # 计算日期范围（最近30天，确保包含足够的交易日）
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            
            # 获取上证指数数据
            df = getDayData(
                stock_code=index_code,
                start_date=start_date,
                end_date=end_date,
                is_download=0,  # 优先从缓存读取
                dividend_type='none'  # 指数不需要复权
            )
            
            if df is not None and len(df) >= 6:
                # 取最近6个交易日（需要1个额外的用于对比）
                df = df.tail(6).reset_index(drop=True)
                
                total_score = 0.0
                divergence_count = 0
                divergence_details = []
                
                # 检查最近5日
                for i in range(1, 6):
                    current_close = df.iloc[i]['close']
                    prev_close = df.iloc[i-1]['close']
                    current_volume = df.iloc[i]['volume']
                    prev_volume = df.iloc[i-1]['volume']
                    
                    # 当日收盘价涨
                    price_up = current_close > prev_close
                    
                    # 成交量萎缩率
                    volume_shrink_rate = (prev_volume - current_volume) / prev_volume
                    
                    # 如果价格上涨且成交量萎缩≥5%，开始计分
                    if price_up and volume_shrink_rate >= 0.05:
                        divergence_count += 1
                        day_score = 0.0
                        
                        if volume_shrink_rate >= 0.20:
                            # 萎缩≥20% → 1.0分
                            day_score = 1.0
                        else:
                            # 萎缩5%-20%之间 → 线性插值
                            # 公式: 0.2 + (萎缩率-0.05)/(0.20-0.05) * (1.0-0.2)
                            day_score = 0.2 + (volume_shrink_rate - 0.05) / 0.15 * 0.8
                        
                        total_score += day_score
                        divergence_details.append(
                            f"{df.iloc[i]['date']} (量缩{volume_shrink_rate*100:.1f}%, +{day_score:.2f}分)"
                        )
                
                score = total_score
                
                print(f"  ✓ XtQuant数据：最近5日发现 {divergence_count} 日量价背离，总得分: {score:.2f}")
                if divergence_count > 0:
                    print(f"    背离详情: {'; '.join(divergence_details)}")
                
                return score
            else:
                print(f"  ✗ XtQuant数据不足：需要至少6个交易日数据（当前: {len(df) if df is not None else 0}条）")
                
        except ImportError as e:
            print(f"  ✗ 导入模块失败: {e}")
            print(f"    提示：请确保 合并下载数据.py 在 source/实盘/xuntou/datadownload/ 目录")
        except Exception as e:
            print(f"  ✗ XtQuant获取失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 如果数据获取失败，返回0分并提示
        print(f"  ⚠ 无法获取量价背离数据，默认得分: {score:.2f}")
        return score
    
    def get_valuation_percentile_score(self):
        """
        指标4: 估值百分位评分
        规则：Wind全A指数PE近5年分位
        - 分位≥95% → 1分
        - 分位≤60% → 0分
        - 分位 60-95% → 按比例线性插值
        
        数据源：Wind API (881001.WI - Wind全A指数)
        """
        print("\n[4/4] 正在获取估值百分位数据...")
        score = 0.0
        
        try:
            from WindPy import w
            from datetime import datetime, timedelta
            import pandas as pd
            
            w.start()
            
            # 获取近5年PE数据（约1250个交易日）
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365*5+30)).strftime('%Y-%m-%d')
            
            # 获取Wind全A指数PE数据
            # 881001.WI: Wind全A指数
            # pe: 市盈率
            # ruleType=10: 按交易日对齐
            data = w.wsd("881001.WI", "pe", start_date, end_date, "ruleType=10")
            
            if data.ErrorCode != 0:
                print(f"  ✗ Wind API错误码: {data.ErrorCode}")
                w.stop()
                return score
            
            if not data.Data or len(data.Data[0]) < 100:
                print(f"  ✗ Wind数据不足（当前: {len(data.Data[0]) if data.Data else 0}条）")
                w.stop()
                return score
            
            # 转换为DataFrame
            df = pd.DataFrame({
                'date': data.Times,
                'pe': data.Data[0]
            })
            
            # 过滤掉None值
            df = df[df['pe'].notna()]
            
            if len(df) < 100:
                print(f"  ✗ 有效数据不足（当前: {len(df)}条）")
                w.stop()
                return score
            
            # 获取当前PE（最新值）
            current_pe = df.iloc[-1]['pe']
            current_date = df.iloc[-1]['date'].strftime('%Y-%m-%d')
            
            # 计算百分位（当前PE在历史数据中的排名）
            percentile = (df['pe'] < current_pe).sum() / len(df) * 100
            
            # 根据新规则计算得分
            if percentile >= 95:
                score = 1.0
            elif percentile <= 60:
                score = 0.0
            else:
                # 60-95之间线性插值
                score = (percentile - 60) / (95 - 60)
            
            print(f"  ✓ Wind数据：{current_date} PE={current_pe:.2f}")
            print(f"    近{len(df)}个交易日百分位: {percentile:.1f}%")
            print(f"    得分: {score:.2f}")
            
            w.stop()
            return score
            
        except ImportError:
            print(f"  ✗ WindPy 未安装，请先安装 Wind 终端")
        except Exception as e:
            print(f"  ✗ 估值数据获取异常: {e}")
            try:
                w.stop()
            except:
                pass
        
        print(f"  ⚠ 无法获取估值数据，默认得分: {score:.2f}")
        return score
    
    def calculate_total_score(self):
        """计算总分"""
        # 获取各项得分
        self.scores['financing_score'] = self.get_financing_balance_score()
        self.scores['account_score'] = self.get_new_accounts_score()
        self.scores['divergence_score'] = self.get_volume_divergence_score()
        self.scores['valuation_score'] = self.get_valuation_percentile_score()
        
        # 计算总分
        self.scores['total_score'] = (
            self.scores['financing_score'] + 
            self.scores['account_score'] + 
            self.scores['divergence_score'] + 
            self.scores['valuation_score']
        )
        
        return self.scores
    
    def print_result(self):
        """打印结果"""
        print("\n" + "="*70)
        print(f"{self.scores['date']} 逃顶打分")
        print(f"融资余额: {self.scores['financing_score']:.1f} | "
              f"开户数: {self.scores['account_score']:.1f} | "
              f"量价背离: {self.scores['divergence_score']:.1f} | "
              f"估值百分位: {self.scores['valuation_score']:.1f}")
        print(f"总分: {self.scores['total_score']:.1f}/3分警戒")
        
        # 判断是否发出逃顶信号
        if self.scores['total_score'] >= 3:
            print("【⚠️  强烈逃顶信号！】")
        else:
            print("【✓ 暂无明显逃顶信号】")
        
        print("="*70)
    
    def save_to_history(self):
        """保存到历史记录"""
        try:
            # 读取现有历史记录
            if os.path.exists(HISTORY_FILE):
                df_history = pd.read_csv(HISTORY_FILE)
            else:
                df_history = pd.DataFrame()
            
            # 添加今日数据
            df_new = pd.DataFrame([self.scores])
            df_history = pd.concat([df_history, df_new], ignore_index=True)
            
            # 去重（如果今天已经运行过）
            df_history = df_history.drop_duplicates(subset=['date'], keep='last')
            
            # 保存
            df_history.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
            print(f"\n✓ 历史数据已保存到: {HISTORY_FILE}")
            
        except Exception as e:
            print(f"✗ 保存历史数据失败: {e}")
    
    def plot_history_chart(self):
        """绘制近3个月总分折线图"""
        try:
            if not os.path.exists(HISTORY_FILE):
                print("暂无历史数据，无法绘图")
                return
            
            # 读取历史数据
            df = pd.read_csv(HISTORY_FILE)
            df['date'] = pd.to_datetime(df['date'])
            
            # 筛选近3个月数据
            three_months_ago = datetime.now() - timedelta(days=90)
            df = df[df['date'] >= three_months_ago]
            df = df.sort_values('date')
            
            if len(df) == 0:
                print("近3个月无数据，无法绘图")
                return
            
            # 绘制图表
            fig, ax = plt.subplots(figsize=(14, 7))
            
            # 绘制总分折线
            ax.plot(df['date'], df['total_score'], 
                   marker='o', linewidth=2, markersize=6, 
                   color='#1f77b4', label='总分')
            
            # 添加警戒线
            ax.axhline(y=2.2, color='red', linestyle='--', 
                      linewidth=2, label='逃顶警戒线 (2.2分)', alpha=0.7)
            
            # 标记超过警戒线的点
            danger_points = df[df['total_score'] >= 2.2]
            if len(danger_points) > 0:
                ax.scatter(danger_points['date'], danger_points['total_score'],
                          color='red', s=100, zorder=5, marker='*', 
                          label='强烈逃顶信号')
            
            # 设置图表样式
            ax.set_xlabel('日期', fontsize=12, fontweight='bold')
            ax.set_ylabel('总分', fontsize=12, fontweight='bold')
            ax.set_title('A股逃顶信号监测 - 近3个月总分趋势', 
                        fontsize=14, fontweight='bold', pad=20)
            
            # 设置网格
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_ylim(0, 4.5)
            
            # 设置图例
            ax.legend(loc='upper left', fontsize=10)
            
            # 旋转x轴标签
            plt.xticks(rotation=45, ha='right')
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图表
            chart_file = os.path.join(CURRENT_DIR, 'escape_top_chart.png')
            plt.savefig(chart_file, dpi=150, bbox_inches='tight')
            print(f"✓ 趋势图已保存到: {chart_file}")
            
            # 显示图表
            plt.show()
            
        except Exception as e:
            print(f"✗ 绘制图表失败: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """运行完整的打分流程"""
        print("="*70)
        print("A股牛市逃顶打分器")
        print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 计算得分
        self.calculate_total_score()
        
        # 打印结果
        self.print_result()
        
        # 保存历史记录
        self.save_to_history()
        
        # 绘制图表
        self.plot_history_chart()


def main():
    """主函数"""
    try:
        scorer = EscapeTopScorer()
        scorer.run()
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

