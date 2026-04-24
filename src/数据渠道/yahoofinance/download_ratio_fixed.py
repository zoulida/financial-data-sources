#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化数据下载脚本 - 价格比率监控 (修复版)
使用多种数据源下载金融数据并计算价格比率统计
"""

import pandas as pd
import numpy as np
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
import warnings
import requests
import ssl
warnings.filterwarnings('ignore')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ratio_monitor.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 代理配置
PROXY = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

# 禁用SSL验证
ssl._create_default_https_context = ssl._create_unverified_context

# 品种清单与 Yahoo 代码映射
SYMBOL_MAPPING = {
    # 贵金属
    'XAU': 'GC=F', 'XAG': 'SI=F', 'PT': 'PL=F',
    # 有色
    'CU': 'HG=F', 'AL': 'ALI=F', 'ZN': 'ZN=F', 'NI': 'NIF=F',
    # 黑色
    'I': 'IRON=F', 'RB': 'RB=F', 'HC': 'HC=F', 'OC': 'OK=F',
    # 能源
    'Brent': 'BZ=F', 'WTI': 'CL=F', 'NG': 'NG=F', 'URAN': 'URA',
    # 农产品
    'C': 'C=F', 'W': 'W=F', 'S': 'S=F', 'SM': 'SM=F',
    # 航运
    'BCI': 'BDI', 'BPI': 'BDRY', 'BSI': 'BDRY',
    # 宏观/跨市场
    'NASDAQ': '^IXIC', 'DXY': 'UUP', 'Copper': 'HG=F', 'Oil': 'CL=F', 
    'CSI300': 'ASHR', 'CFFEX10Y': 'CBON'
}

# 对比值对子定义
RATIO_PAIRS = [
    # 贵金属比率
    ('XAU', 'XAG'),  # 金银比
    ('XAU', 'PT'),   # 金铂比
    # 有色比率
    ('CU', 'AL'),    # 铜铝比
    ('CU', 'ZN'),    # 铜锌比
    # 黑色比率
    ('I', 'RB'),     # 铁矿石螺纹钢比
    ('RB', 'HC'),    # 螺纹钢热卷比
    # 能源比率
    ('Brent', 'WTI'), # 布伦特WTI比
    ('WTI', 'NG'),   # 原油天然气比
    # 农产品比率
    ('C', 'W'),      # 玉米小麦比
    ('S', 'SM'),     # 大豆豆粕比
    # 宏观比率
    ('NASDAQ', 'DXY'), # 纳指美元比
    ('Copper', 'Oil'), # 铜油比
    ('CSI300', 'DXY'), # 沪深300美元比
]

class RatioMonitor:
    """价格比率监控类"""
    
    def __init__(self, data_dir: str = 'data', cache_dir: str = 'cache'):
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        self.start_date = '2015-01-01'
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 创建目录
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 存储下载的数据
        self.price_data = {}
        
        # 请求延迟（避免429错误）
        self.request_delay = 2  # 2秒延迟
        
    def download_symbol_data_yahoo_api(self, symbol: str, yahoo_code: str, max_retries: int = 3) -> Optional[pd.DataFrame]:
        """
        使用Yahoo Finance API直接下载数据
        
        Args:
            symbol: 品种代码
            yahoo_code: Yahoo Finance 代码
            max_retries: 最大重试次数
            
        Returns:
            价格数据DataFrame或None
        """
        cache_file = os.path.join(self.cache_dir, f'{symbol}_{yahoo_code}.parquet')
        
        # 检查缓存
        if os.path.exists(cache_file):
            try:
                cached_data = pd.read_parquet(cache_file)
                # 检查数据是否连续到最近
                last_date = cached_data.index[-1].date()
                today = datetime.now().date()
                if (today - last_date).days <= 7:  # 7天内认为数据较新
                    logger.info(f"使用缓存数据: {symbol} ({yahoo_code})")
                    return cached_data
            except Exception as e:
                logger.warning(f"读取缓存失败 {symbol}: {e}")
        
        # 下载数据
        for attempt in range(max_retries):
            try:
                logger.info(f"下载数据: {symbol} ({yahoo_code}) - 尝试 {attempt + 1}/{max_retries}")
                
                # 添加延迟避免429错误
                if attempt > 0:
                    time.sleep(self.request_delay * (attempt + 1))
                
                # 构造Yahoo Finance API URL
                end_time = int(datetime.now().timestamp())
                start_time = int(datetime.strptime(self.start_date, '%Y-%m-%d').timestamp())
                
                api_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_code}?period1={start_time}&period2={end_time}&interval=1d"
                
                # 发送请求
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(api_url, headers=headers, proxies=PROXY, timeout=30, verify=False)
                
                if response.status_code == 429:
                    logger.warning(f"请求频率过高，等待 {self.request_delay * 5} 秒后重试")
                    time.sleep(self.request_delay * 5)
                    continue
                elif response.status_code != 200:
                    logger.error(f"API请求失败: {response.status_code}")
                    continue
                
                # 解析JSON数据
                data = response.json()
                
                if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
                    logger.warning(f"API返回数据格式异常: {symbol}")
                    continue
                
                result = data['chart']['result'][0]
                
                if 'timestamp' not in result or 'indicators' not in result:
                    logger.warning(f"API返回数据缺少必要字段: {symbol}")
                    continue
                
                timestamps = result['timestamp']
                quotes = result['indicators']['quote'][0]
                
                if 'close' not in quotes:
                    logger.warning(f"API返回数据缺少收盘价: {symbol}")
                    continue
                
                # 构建DataFrame
                dates = [datetime.fromtimestamp(ts) for ts in timestamps]
                closes = quotes['close']
                
                # 过滤掉None值
                valid_data = [(date, close) for date, close in zip(dates, closes) if close is not None]
                
                if not valid_data:
                    logger.warning(f"没有有效的价格数据: {symbol}")
                    continue
                
                dates, prices = zip(*valid_data)
                
                price_data = pd.DataFrame({symbol: prices}, index=dates)
                price_data.index.name = 'Date'
                
                # 保存缓存
                price_data.to_parquet(cache_file)
                logger.info(f"下载成功: {symbol} ({yahoo_code}) - {len(price_data)} 条记录")
                return price_data
                
            except Exception as e:
                logger.error(f"下载失败 {symbol} ({yahoo_code}) - 尝试 {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.request_delay * (attempt + 1))
                else:
                    logger.error(f"下载最终失败: {symbol} ({yahoo_code})")
        
        return None
    
    def download_all_data(self) -> Dict[str, pd.DataFrame]:
        """下载所有品种数据"""
        logger.info("开始下载所有品种数据...")
        
        for i, (symbol, yahoo_code) in enumerate(SYMBOL_MAPPING.items()):
            # 添加延迟避免请求过于频繁
            if i > 0:
                time.sleep(self.request_delay)
            
            data = self.download_symbol_data_yahoo_api(symbol, yahoo_code)
            if data is not None:
                self.price_data[symbol] = data
            else:
                logger.error(f"跳过品种: {symbol}")
        
        logger.info(f"成功下载 {len(self.price_data)} 个品种数据")
        return self.price_data
    
    def calculate_ratio_stats(self, symbol_a: str, symbol_b: str) -> Dict:
        """
        计算两个品种的比率统计
        
        Args:
            symbol_a: 品种A
            symbol_b: 品种B
            
        Returns:
            统计结果字典
        """
        if symbol_a not in self.price_data or symbol_b not in self.price_data:
            return None
        
        try:
            # 获取价格数据
            price_a = self.price_data[symbol_a]['Close'] if 'Close' in self.price_data[symbol_a].columns else self.price_data[symbol_a].iloc[:, 0]
            price_b = self.price_data[symbol_b]['Close'] if 'Close' in self.price_data[symbol_b].columns else self.price_data[symbol_b].iloc[:, 0]
            
            # 对齐日期
            common_dates = price_a.index.intersection(price_b.index)
            if len(common_dates) < 50:  # 至少需要50个数据点
                return None
            
            price_a_aligned = price_a.loc[common_dates]
            price_b_aligned = price_b.loc[common_dates]
            
            # 计算对数价差
            log_ratio = np.log(price_a_aligned / price_b_aligned)
            
            # 计算Z-score (40日窗口)
            window = min(40, len(log_ratio))
            if window < 10:
                return None
            
            rolling_mean = log_ratio.rolling(window=window).mean()
            rolling_std = log_ratio.rolling(window=window).std()
            z_score = (log_ratio - rolling_mean) / rolling_std
            
            # 获取最新值
            latest_ratio = log_ratio.iloc[-1]
            latest_z_score = z_score.iloc[-1]
            latest_date = common_dates[-1]
            
            # 计算半衰期 (OU过程估计)
            half_life = self._estimate_half_life(log_ratio.dropna())
            
            return {
                'symbol_a': symbol_a,
                'symbol_b': symbol_b,
                'latest_ratio': latest_ratio,
                'latest_z_score': latest_z_score,
                'half_life': half_life,
                'last_trade_date': latest_date,
                'data_points': len(common_dates)
            }
            
        except Exception as e:
            logger.error(f"计算比率统计失败 {symbol_a}/{symbol_b}: {e}")
            return None
    
    def _estimate_half_life(self, spread: pd.Series) -> float:
        """
        估计半衰期 (OU过程)
        
        Args:
            spread: 价差序列
            
        Returns:
            半衰期（天）
        """
        try:
            if len(spread) < 10:
                return np.nan
            
            # 计算一阶差分
            spread_diff = spread.diff().dropna()
            spread_lag = spread.shift(1).dropna()
            
            # 对齐数据
            min_len = min(len(spread_diff), len(spread_lag))
            spread_diff = spread_diff.iloc[-min_len:]
            spread_lag = spread_lag.iloc[-min_len:]
            
            # OLS回归: Δspread = α + β * spread_lag + ε
            X = sm.add_constant(spread_lag)
            model = sm.OLS(spread_diff, X).fit()
            
            # 计算半衰期: -ln(2) / ln(1 + β)
            beta = model.params.iloc[1]
            if beta >= 0 or abs(beta) >= 1:
                return np.nan
            
            half_life = -np.log(2) / np.log(1 + beta)
            return max(0, half_life)  # 确保非负
            
        except Exception as e:
            logger.warning(f"半衰期计算失败: {e}")
            return np.nan
    
    def calculate_all_ratios(self) -> List[Dict]:
        """计算所有比率对子的统计"""
        logger.info("开始计算比率统计...")
        
        results = []
        for symbol_a, symbol_b in RATIO_PAIRS:
            stats = self.calculate_ratio_stats(symbol_a, symbol_b)
            if stats is not None:
                results.append(stats)
                logger.info(f"计算完成: {symbol_a}/{symbol_b} - Z-score: {stats['latest_z_score']:.3f}")
            else:
                logger.warning(f"跳过比率: {symbol_a}/{symbol_b}")
        
        return results
    
    def save_results(self, results: List[Dict], filename: str = 'ratio_monitor.csv'):
        """保存结果到CSV文件"""
        if not results:
            logger.warning("没有结果可保存")
            return
        
        df = pd.DataFrame(results)
        df = df.sort_values('latest_z_score', key=abs, ascending=False)
        
        # 格式化输出
        df['latest_ratio'] = df['latest_ratio'].round(6)
        df['latest_z_score'] = df['latest_z_score'].round(3)
        df['half_life'] = df['half_life'].round(2)
        df['last_trade_date'] = df['last_trade_date'].dt.strftime('%Y-%m-%d')
        
        # 添加比率对名称
        df['ratio_pair'] = df['symbol_a'] + '/' + df['symbol_b']
        
        # 重新排列列
        columns = ['ratio_pair', 'symbol_a', 'symbol_b', 'latest_ratio', 
                  'latest_z_score', 'half_life', 'last_trade_date', 'data_points']
        df = df[columns]
        
        # 保存文件
        output_path = os.path.join(self.data_dir, filename)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"结果已保存到: {output_path}")
        
        return df
    
    def print_extreme_warnings(self, df: pd.DataFrame):
        """打印极端值警告"""
        extreme_ratios = df[abs(df['latest_z_score']) >= 2]
        
        if len(extreme_ratios) > 0:
            print("\n" + "="*60)
            print("🚨 极端比率警告 (|Z-score| >= 2)")
            print("="*60)
            
            for _, row in extreme_ratios.iterrows():
                z_score = row['latest_z_score']
                color = "\033[91m" if z_score > 2 else "\033[94m"  # 红色或蓝色
                reset = "\033[0m"
                
                print(f"{color}{row['ratio_pair']:15} | Z-score: {z_score:6.3f} | "
                      f"半衰期: {row['half_life']:6.1f}天 | 日期: {row['last_trade_date']}{reset}")
            
            print("="*60)
        else:
            print("\n✅ 未发现极端比率 (|Z-score| < 2)")

def main():
    """主函数"""
    print("🚀 启动量化数据比率监控系统 (修复版)")
    print("="*50)
    
    # 创建监控器
    monitor = RatioMonitor()
    
    try:
        # 下载数据
        monitor.download_all_data()
        
        if not monitor.price_data:
            logger.error("未获取到任何数据，程序退出")
            return
        
        # 计算比率统计
        results = monitor.calculate_all_ratios()
        
        if not results:
            logger.error("未计算出任何比率统计，程序退出")
            return
        
        # 保存结果
        df = monitor.save_results(results)
        
        # 打印极端值警告
        monitor.print_extreme_warnings(df)
        
        # 打印汇总信息
        print(f"\n📊 监控汇总:")
        print(f"   品种数量: {len(monitor.price_data)}")
        print(f"   比率对数量: {len(results)}")
        print(f"   极端比率数量: {len(df[abs(df['latest_z_score']) >= 2])}")
        print(f"   数据保存路径: data/ratio_monitor.csv")
        
        logger.info("程序执行完成")
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        raise

if __name__ == "__main__":
    main()
