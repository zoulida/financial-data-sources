"""
配对交易全市场扫描系统 - 主程序

整合所有模块，完成从数据获取到配对筛选、协整检验、
半衰期估计、评分排序的完整流程。
"""

import sys
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from tools.shelveTool import shelve_me_week

# 添加项目根目录到sys.path（支持虚拟环境）
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config import Config
from data_fetcher import DataFetcher
from pair_screener import PairScreener
from cointegration import CointegrationTester
from ou_estimator import OUEstimator
from scoring import PairScorer
from progress_manager import ProgressManager

# 配置日志
log_file = Config.Output.LOG_FILE
logging.basicConfig(
    level=getattr(logging, Config.System.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class PairsTradingScanner:
    """配对交易全市场扫描器"""
    
    def __init__(self, resume: bool = True):
        """
        初始化扫描器
        
        Args:
            resume: 是否从上次中断处继续
        """
        logger.info("="*80)
        logger.info("配对交易全市场扫描系统")
        logger.info("="*80)
        
        self.resume = resume
        
        # 初始化各个模块
        logger.info("初始化模块...")
        self.data_fetcher = DataFetcher()
        self.pair_screener = PairScreener()
        self.coint_tester = CointegrationTester()
        self.ou_estimator = OUEstimator()
        self.scorer = PairScorer()
        self.progress_manager = ProgressManager()
        
        logger.info("模块初始化完成")
    
    def step1_get_universe(self):
        """步骤1: 获取股票池、ETF池、可转债池"""
        logger.info("\n" + "="*80)
        logger.info("步骤1: 获取资产池")
        logger.info("="*80)
        
        # 获取股票池
        logger.info("获取股票池...")
        stocks_df = self.data_fetcher.get_stock_universe()
        logger.info(f"股票池: {len(stocks_df)} 只")
        
        # 获取ETF池
        logger.info("获取ETF池...")
        etfs_df = self.data_fetcher.get_etf_universe()
        logger.info(f"ETF池: {len(etfs_df)} 只")
        
        # 获取可转债池
        logger.info("获取可转债池...")
        bonds_df = self.data_fetcher.get_convertible_bond_universe()
        logger.info(f"可转债池: {len(bonds_df)} 只")
        
        # 合并所有标的
        all_symbols = []
        symbol_info = {}
        
        # 添加股票
        for _, row in stocks_df.iterrows():
            code = row['code']
            all_symbols.append(code)
            symbol_info[code] = {
                'name': row['name'],
                'type': 'stock',
                'market_cap': row.get('market_cap', np.nan)
            }
        
        # 添加ETF
        for _, row in etfs_df.iterrows():
            code = row['code']
            all_symbols.append(code)
            symbol_info[code] = {
                'name': row['name'],
                'type': 'etf',
                'avg_amount': row.get('avg_amount', np.nan)
            }
        
        # 添加可转债
        for _, row in bonds_df.iterrows():
            code = row['code']
            all_symbols.append(code)
            symbol_info[code] = {
                'name': row['name'],
                'type': 'bond',
                'carrying_value': row.get('carrying_value', np.nan),
                'avg_amount': row.get('avg_amount', np.nan)
            }
        
        logger.info(f"总标的数: {len(all_symbols)}")
        logger.info(f"  股票: {len(stocks_df)}")
        logger.info(f"  ETF: {len(etfs_df)}")
        logger.info(f"  可转债: {len(bonds_df)}")
        
        return all_symbols, symbol_info
    
    def step2_get_price_data(self, symbols):
        """步骤2: 获取价格数据"""
        logger.info("\n" + "="*80)
        logger.info("步骤2: 获取价格数据")
        logger.info("="*80)
        
        logger.info(f"开始获取 {len(symbols)} 个标的的价格数据...")
        
        price_data = self.data_fetcher.get_batch_price_data(symbols)
        
        logger.info(f"成功获取 {len(price_data)} 个标的的价格数据")
        
        # 过滤数据点不足的标的
        min_points = Config.PairScreen.MIN_DATA_POINTS
        valid_price_data = {
            code: prices for code, prices in price_data.items()
            if len(prices) >= min_points
        }
        
        logger.info(f"过滤后剩余 {len(valid_price_data)} 个标的（数据点>={min_points}）")
        
        return valid_price_data

    @shelve_me_week
    def step3_screen_pairs(self, price_data, symbol_info):
        """步骤3: 配对初筛"""
        logger.info("\n" + "="*80)
        logger.info("步骤3: 配对初筛")
        logger.info("="*80)
        
        passed_pairs, results_df = self.pair_screener.screen_all_pairs(
            price_data, 
            symbol_info
        )
        
        # 保存初筛结果
        results_df.to_csv('cache/screening_results.csv', index=False, encoding='utf-8-sig')
        logger.info(f"初筛结果已保存到 cache/screening_results.csv")
        
        # 显示统计信息
        stats = self.pair_screener.get_screening_stats(results_df)
        logger.info(f"\n初筛统计:")
        logger.info(f"  总配对数: {stats['total_pairs']}")
        logger.info(f"  通过数量: {stats['passed_pairs']}")
        logger.info(f"  通过率: {stats['pass_rate']:.2f}%")
        
        return passed_pairs
    
    def step4_test_cointegration_and_half_life(self, pairs, price_data):
        """步骤4: 协整检验和半衰期估计（批量处理）"""
        logger.info("\n" + "="*80)
        logger.info("步骤4: 协整检验和半衰期估计")
        logger.info("="*80)
        
        # 检查是否有未完成的进度
        remaining_pairs = pairs
        if self.resume:
            remaining_pairs = self.progress_manager.get_remaining_pairs(pairs)
            
            if len(remaining_pairs) < len(pairs):
                logger.info(f"从上次中断处继续，剩余 {len(remaining_pairs)} 个配对")
        
        if len(remaining_pairs) == 0:
            logger.info("所有配对已处理完成，加载结果...")
            all_results = self.progress_manager.get_all_results()
            return pd.DataFrame(all_results)
        
        # 初始化任务
        if len(remaining_pairs) == len(pairs):
            self.progress_manager.initialize_task(pairs)
        
        # 创建批次
        batches = self.progress_manager.create_batches(remaining_pairs)
        logger.info(f"共 {len(batches)} 个批次待处理")
        
        # 处理每个批次
        stats = {
            'total': 0,
            'missing_data': 0,
            'coint_failed': 0,
            'half_life_failed': 0,
            'passed': 0
        }
        
        for batch_idx, batch_pairs in enumerate(tqdm(batches, desc="处理批次")):
            logger.info(f"\n处理批次 {batch_idx + 1}/{len(batches)}")
            
            batch_results = []
            
            for code1, code2 in tqdm(batch_pairs, desc=f"批次{batch_idx+1}", leave=False):
                stats['total'] += 1
                try:
                    # 获取价格数据
                    price1 = price_data.get(code1)
                    price2 = price_data.get(code2)
                    
                    if price1 is None or price2 is None:
                        stats['missing_data'] += 1
                        continue
                    
                    # 协整检验
                    coint_passed, p_value, beta, spread = self.coint_tester.test_cointegration(
                        price1, price2
                    )
                    
                    if not coint_passed:
                        stats['coint_failed'] += 1
                        continue
                    
                    # OU半衰期估计
                    half_life, phi = self.ou_estimator.estimate_half_life(spread)
                    hl_passed = True #self.ou_estimator.test_half_life(half_life)
                    
                    if not hl_passed:
                        stats['half_life_failed'] += 1
                        continue
                    
                    stats['passed'] += 1
                    
                    # 计算得分
                    score = self.scorer.calculate_score(p_value, half_life)
                    
                    # 对齐数据计算相关系数
                    aligned_data = pd.DataFrame({'p1': price1, 'p2': price2}).dropna()
                    correlation = aligned_data['p1'].corr(aligned_data['p2'])
                    
                    # 保存结果
                    batch_results.append({
                        'code1': code1,
                        'code2': code2,
                        'p_value': p_value,
                        'beta': beta,
                        'half_life': half_life,
                        'phi': phi,
                        'score': score,
                        'correlation': correlation,
                        'data_points': len(aligned_data)
                    })
                    
                except Exception as e:
                    logger.warning(f"处理配对失败: {code1} - {code2}, 错误: {e}")
                    continue
            
            # 标记批次完成
            self.progress_manager.mark_batch_completed(batch_pairs, batch_results, batch_idx)
            
            logger.info(f"批次 {batch_idx + 1} 完成，通过 {len(batch_results)} 个配对")
        
        # 完成任务
        self.progress_manager.finalize_task()
        
        # 输出统计信息
        logger.info(f"\n步骤4处理统计:")
        logger.info(f"  总配对: {stats['total']}")
        logger.info(f"  缺少数据: {stats['missing_data']}")
        logger.info(f"  协整检验未通过: {stats['coint_failed']}")
        logger.info(f"  半衰期检验未通过: {stats['half_life_failed']}")
        logger.info(f"  通过所有检验: {stats['passed']}")
        
        # 获取所有结果
        all_results = self.progress_manager.get_all_results()
        
        if len(all_results) == 0:
            # 如果没有结果，返回空的DataFrame但包含必要的列
            logger.warning("没有配对通过协整和半衰期检验")
            results_df = pd.DataFrame(columns=[
                'code1', 'code2', 'p_value', 'beta', 'half_life', 
                'phi', 'score', 'correlation', 'data_points'
            ])
        else:
            results_df = pd.DataFrame(all_results)
        
        logger.info(f"\n协整和半衰期检验完成，通过 {len(results_df)} 个配对")
        
        return results_df
    
    def step5_score_and_rank(self, results_df, symbol_info):
        """步骤5: 评分和排序"""
        logger.info("\n" + "="*80)
        logger.info("步骤5: 评分和排序")
        logger.info("="*80)
        
        # 检查是否有结果
        if len(results_df) == 0:
            logger.warning("没有配对通过检验，无法进行评分排序")
            # 返回空的DataFrame但包含必要的列
            empty_df = pd.DataFrame(columns=[
                'code1', 'code2', 'name1', 'name2', 'p_value', 'beta', 
                'half_life', 'phi', 'score', 'correlation', 'data_points'
            ])
            return empty_df, empty_df
        
        # 检查必要的列
        if 'p_value' not in results_df.columns or 'half_life' not in results_df.columns:
            logger.error(f"DataFrame缺少必要的列。现有列: {list(results_df.columns)}")
            logger.error("无法进行评分，请检查步骤4的输出")
            empty_df = pd.DataFrame(columns=[
                'code1', 'code2', 'name1', 'name2', 'p_value', 'beta', 
                'half_life', 'phi', 'score', 'correlation', 'data_points'
            ])
            return empty_df, empty_df
        
        # 评分（如果还没有score列）
        if 'score' not in results_df.columns:
            scored_df = self.scorer.score_pairs(results_df)
        else:
            scored_df = results_df.sort_values('score', ascending=False).reset_index(drop=True)
        
        # 添加名称信息
        scored_df['name1'] = scored_df['code1'].map(lambda x: symbol_info.get(x, {}).get('name', ''))
        scored_df['name2'] = scored_df['code2'].map(lambda x: symbol_info.get(x, {}).get('name', ''))
        
        # 获取前N名
        top_pairs = self.scorer.get_top_pairs(scored_df)
        
        logger.info(f"获取前 {len(top_pairs)} 名配对")
        
        # 显示统计信息
        stats = self.scorer.get_scoring_stats(scored_df)
        logger.info(f"\n评分统计:")
        logger.info(f"  总配对数: {stats['total_pairs']}")
        logger.info(f"  最高分: {stats['max_score']:.2f}")
        logger.info(f"  最低分: {stats['min_score']:.2f}")
        logger.info(f"  平均分: {stats['avg_score']:.2f}")
        
        return top_pairs, scored_df
    
    def step6_save_results(self, top_pairs, all_results):
        """步骤6: 保存结果"""
        logger.info("\n" + "="*80)
        logger.info("步骤6: 保存结果")
        logger.info("="*80)
        
        # 保存前100名配对
        output_file = Config.Output.RESULT_FILE
        output_columns = [
            'code1', 'code2', 'name1', 'name2', 
            'beta', 'score', 'half_life', 'p_value',
            'correlation', 'data_points'
        ]
        
        # 确保所有列都存在
        available_columns = [col for col in output_columns if col in top_pairs.columns]
        
        top_pairs[available_columns].to_csv(
            output_file, 
            index=False, 
            encoding='utf-8-sig',
            float_format='%.4f'
        )
        
        logger.info(f"前{len(top_pairs)}名配对已保存到: {output_file}")
        
        # 保存所有结果
        all_output_file = 'pairs_result_all.csv'
        all_results[available_columns].to_csv(
            all_output_file,
            index=False,
            encoding='utf-8-sig',
            float_format='%.4f'
        )
        
        logger.info(f"所有配对结果已保存到: {all_output_file}")
        
        # 生成汇总报告
        self.generate_summary_report(top_pairs, all_results)
    
    def generate_summary_report(self, top_pairs, all_results):
        """生成汇总报告"""
        report_file = Config.Output.SUMMARY_FILE
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("配对交易全市场扫描 - 汇总报告\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 进度信息
            progress_info = self.progress_manager.get_progress_info()
            f.write("任务执行信息:\n")
            f.write(f"  开始时间: {progress_info.get('start_time', 'N/A')}\n")
            f.write(f"  结束时间: {progress_info.get('end_time', 'N/A')}\n")
            f.write(f"  状态: {progress_info.get('status', 'N/A')}\n\n")
            
            # 整体统计
            f.write("整体统计:\n")
            f.write(f"  通过所有检验的配对数: {len(all_results)}\n")
            f.write(f"  输出前N名: {len(top_pairs)}\n\n")
            
            # 评分统计
            f.write("评分统计:\n")
            f.write(f"  最高分: {all_results['score'].max():.2f}\n")
            f.write(f"  最低分: {all_results['score'].min():.2f}\n")
            f.write(f"  平均分: {all_results['score'].mean():.2f}\n")
            f.write(f"  中位数: {all_results['score'].median():.2f}\n\n")
            
            # 半衰期统计
            f.write("半衰期统计:\n")
            f.write(f"  最小半衰期: {all_results['half_life'].min():.2f}天\n")
            f.write(f"  最大半衰期: {all_results['half_life'].max():.2f}天\n")
            f.write(f"  平均半衰期: {all_results['half_life'].mean():.2f}天\n")
            f.write(f"  中位数半衰期: {all_results['half_life'].median():.2f}天\n\n")
            
            # p值统计
            f.write("p值统计:\n")
            f.write(f"  最小p值: {all_results['p_value'].min():.4f}\n")
            f.write(f"  最大p值: {all_results['p_value'].max():.4f}\n")
            f.write(f"  平均p值: {all_results['p_value'].mean():.4f}\n\n")
            
            # 前10名配对
            f.write("前10名配对:\n")
            f.write("-" * 80 + "\n")
            for idx, row in top_pairs.head(10).iterrows():
                f.write(f"{idx+1}. {row['code1']} ({row['name1']}) - {row['code2']} ({row['name2']})\n")
                f.write(f"   Score: {row['score']:.2f}, 半衰期: {row['half_life']:.2f}天, p值: {row['p_value']:.4f}\n")
            
            f.write("\n" + "="*80 + "\n")
        
        logger.info(f"汇总报告已保存到: {report_file}")
    
    def run(self):
        """运行完整流程"""
        start_time = datetime.now()
        
        try:
            # 步骤1: 获取资产池
            all_symbols, symbol_info = self.step1_get_universe()
            
            # 步骤2: 获取价格数据
            price_data = self.step2_get_price_data(all_symbols)
            
            # 步骤3: 配对初筛
            passed_pairs = self.step3_screen_pairs(price_data, symbol_info)
            
            # 步骤4: 协整检验和半衰期估计
            results_df = self.step4_test_cointegration_and_half_life(passed_pairs, price_data)
            
            # 步骤5: 评分和排序
            top_pairs, all_results = self.step5_score_and_rank(results_df, symbol_info)
            
            # 步骤6: 保存结果
            self.step6_save_results(top_pairs, all_results)
            
            # 完成
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"\n{'='*80}")
            logger.info(f"扫描完成！总耗时: {elapsed_time/60:.2f} 分钟")
            logger.info(f"结果文件: {Config.Output.RESULT_FILE}")
            logger.info(f"汇总报告: {Config.Output.SUMMARY_FILE}")
            logger.info(f"{'='*80}\n")
            
        except KeyboardInterrupt:
            logger.warning("\n用户中断，进度已保存")
        except Exception as e:
            logger.error(f"\n发生错误: {e}", exc_info=True)
            raise


if __name__ == '__main__':
    # 创建扫描器并运行（缓存由shelve装饰器自动管理）
    scanner = PairsTradingScanner(resume=False)
    scanner.run()

