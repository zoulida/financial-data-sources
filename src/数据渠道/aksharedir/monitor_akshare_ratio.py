#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比价监控脚本 - 使用 AkShare 免费接口
监控8组对子的价差和Z-score，支持ETF现货篮合成
"""

import akshare as ak
import pandas as pd
import numpy as np
import statsmodels.api as sm
from colorama import init, Fore, Style
import time
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 设置akshare不依赖mini-racer
import os
os.environ['AKSHARE_DISABLE_MINI_RACER'] = '1'

# 初始化colorama
init(autoreset=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ratio_monitor_akshare.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 监控对子配置
PAIRS_CONFIG = {
    "000300.SH/000852.SH": {"threshold": 2.0, "type": "index"},
    "000016.SH/399303.SZ": {"threshold": 2.0, "type": "index"},
    "510500.SH/000905.SH": {"threshold": 2.0, "type": "etf_index"},
    "518880.SH/AU2306.SHF": {"threshold": 1.5, "type": "etf_futures"},
    # 暂时注释掉有问题的对子
    # "510300.SH/300现货篮": {"threshold": 1.5, "type": "etf_basket"},
    # "159949.SZ/创50现货篮": {"threshold": 1.5, "type": "etf_basket"},
    # "512880.SH/券商现货篮": {"threshold": 1.5, "type": "etf_basket"},
    # "CU0/CU1": {"threshold": 2.0, "type": "futures_spread"}
}

def retry_on_failure(max_retries=3, sleep_time=2):
    """装饰器：重试机制"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"{func.__name__} 失败，已重试{max_retries}次: {str(e)}")
                        raise e
                    logger.warning(f"{func.__name__} 第{attempt+1}次尝试失败，{sleep_time}秒后重试: {str(e)}")
                    time.sleep(sleep_time)
            return None
        return wrapper
    return decorator

@retry_on_failure()
def get_stock_data(symbol, start_date="20150101", end_date=None):
    """获取股票历史数据"""
    try:
        # 转换代码格式
        if symbol.endswith('.SH'):
            ak_symbol = symbol.replace('.SH', '')
        elif symbol.endswith('.SZ'):
            ak_symbol = symbol.replace('.SZ', '')
        else:
            ak_symbol = symbol
            
        df = ak.stock_zh_a_hist(symbol=ak_symbol, period="daily", 
                               start_date=start_date, end_date=end_date, adjust="qfq")
        if df.empty:
            raise ValueError(f"未获取到数据: {symbol}")
        
        df['date'] = pd.to_datetime(df['日期'])
        df = df.set_index('date').sort_index()
        return df['收盘']
    except Exception as e:
        logger.error(f"获取股票数据失败 {symbol}: {str(e)}")
        raise

@retry_on_failure()
def get_index_data(symbol, start_date="20150101", end_date=None):
    """获取指数历史数据"""
    try:
        if symbol.endswith('.SH'):
            ak_symbol = symbol.replace('.SH', '')
        elif symbol.endswith('.SZ'):
            ak_symbol = symbol.replace('.SZ', '')
        else:
            ak_symbol = symbol
            
        # 使用 index_zh_a_hist 接口
        df = ak.index_zh_a_hist(symbol=ak_symbol, period='daily', 
                               start_date=start_date, end_date=end_date)
        if df.empty:
            raise ValueError(f"未获取到数据: {symbol}")
        
        # 处理日期列
        df['date'] = pd.to_datetime(df['日期'])
        df = df.set_index('date').sort_index()
        
        return df['收盘']
    except Exception as e:
        logger.error(f"获取指数数据失败 {symbol}: {str(e)}")
        raise

@retry_on_failure()
def get_etf_data(symbol, start_date="20150101", end_date=None):
    """获取ETF历史数据"""
    try:
        if symbol.endswith('.SH'):
            ak_symbol = symbol.replace('.SH', '')
        elif symbol.endswith('.SZ'):
            ak_symbol = symbol.replace('.SZ', '')
        else:
            ak_symbol = symbol
            
        # 使用 fund_etf_hist_em 接口
        df = ak.fund_etf_hist_em(symbol=ak_symbol)
            
        if df.empty:
            raise ValueError(f"未获取到数据: {symbol}")
        
        # 处理日期列
        df['date'] = pd.to_datetime(df['日期'])
        df = df.set_index('date').sort_index()
        
        # 筛选日期范围
        if start_date:
            start_dt = pd.to_datetime(start_date)
            df = df[df.index >= start_dt]
        if end_date:
            end_dt = pd.to_datetime(end_date)
            df = df[df.index <= end_dt]
        
        return df['收盘']
    except Exception as e:
        logger.error(f"获取ETF数据失败 {symbol}: {str(e)}")
        raise

@retry_on_failure()
def get_futures_data(symbol, start_date="20150101", end_date=None):
    """获取期货主力合约数据"""
    try:
        df = ak.futures_main_sina(symbol=symbol)
        if df.empty:
            raise ValueError(f"未获取到数据: {symbol}")
        
        df['date'] = pd.to_datetime(df['日期'])
        df = df.set_index('date').sort_index()
        
        # 筛选日期范围
        if start_date:
            start_dt = pd.to_datetime(start_date)
            df = df[df.index >= start_dt]
        if end_date:
            end_dt = pd.to_datetime(end_date)
            df = df[df.index <= end_dt]
            
        return df['收盘价']
    except Exception as e:
        logger.error(f"获取期货数据失败 {symbol}: {str(e)}")
        raise

@retry_on_failure()
def get_etf_holdings(symbol, date=None):
    """获取ETF持仓信息（PCF权重）"""
    try:
        if symbol.endswith('.SH'):
            ak_symbol = symbol.replace('.SH', '')
        elif symbol.endswith('.SZ'):
            ak_symbol = symbol.replace('.SZ', '')
        else:
            ak_symbol = symbol
            
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
            
        df = ak.fund_etf_cust_hold(symbol=ak_symbol, date=date)
        if df.empty:
            raise ValueError(f"未获取到持仓数据: {symbol}")
        
        # 提取股票代码和权重
        holdings = {}
        for _, row in df.iterrows():
            stock_code = row['股票代码']
            weight = row['持仓比例'] / 100.0  # 转换为小数
            holdings[stock_code] = weight
            
        return holdings
    except Exception as e:
        logger.error(f"获取ETF持仓失败 {symbol}: {str(e)}")
        raise

def create_etf_basket(etf_symbol, start_date="20150101", end_date=None):
    """创建ETF现货篮"""
    try:
        # 获取ETF持仓
        holdings = get_etf_holdings(etf_symbol)
        if not holdings:
            raise ValueError(f"无法获取ETF持仓: {etf_symbol}")
        
        logger.info(f"获取到{etf_symbol}持仓股票{len(holdings)}只")
        
        # 获取成分股数据
        basket_prices = []
        valid_stocks = {}
        
        for stock_code, weight in holdings.items():
            try:
                # 添加市场后缀
                if stock_code.startswith('00') or stock_code.startswith('30'):
                    full_code = f"{stock_code}.SZ"
                elif stock_code.startswith('60'):
                    full_code = f"{stock_code}.SH"
                else:
                    continue
                    
                price_data = get_stock_data(full_code, start_date, end_date)
                if not price_data.empty:
                    valid_stocks[full_code] = (price_data, weight)
                    logger.info(f"成功获取成分股数据: {full_code}")
                else:
                    logger.warning(f"成分股数据为空: {full_code}")
                    
            except Exception as e:
                logger.warning(f"获取成分股失败 {stock_code}: {str(e)}")
                continue
        
        if not valid_stocks:
            raise ValueError("没有有效的成分股数据")
        
        # 计算现货篮价格
        all_dates = set()
        for price_data, _ in valid_stocks.values():
            all_dates.update(price_data.index)
        
        all_dates = sorted(all_dates)
        basket_series = pd.Series(index=all_dates, dtype=float)
        
        for date in all_dates:
            basket_price = 0
            total_weight = 0
            
            for price_data, weight in valid_stocks.values():
                if date in price_data.index:
                    basket_price += price_data[date] * weight
                    total_weight += weight
            
            if total_weight > 0:
                basket_series[date] = basket_price / total_weight
        
        basket_series = basket_series.dropna().sort_index()
        logger.info(f"成功创建现货篮，数据点{len(basket_series)}个")
        return basket_series
        
    except Exception as e:
        logger.error(f"创建ETF现货篮失败 {etf_symbol}: {str(e)}")
        raise

def half_life(spread):
    """计算OU半衰期"""
    try:
        y = spread.diff().dropna()
        x = spread.shift(1).dropna()
        
        if len(y) < 10 or len(x) < 10:
            return np.inf
            
        x = sm.add_constant(x)
        model = sm.OLS(y, x).fit()
        beta = model.params.iloc[1]
        
        if beta >= 0:
            return np.inf
        else:
            return -np.log(2) / beta
    except Exception as e:
        logger.warning(f"计算半衰期失败: {str(e)}")
        return np.inf

def calc_z_half_life(spread):
    """计算Z-score和半衰期"""
    try:
        if len(spread) < 40:
            return np.nan, np.inf, "数据不足"
        
        # 计算40日滚动统计
        rolling_mean = spread.rolling(window=40).mean()
        rolling_std = spread.rolling(window=40).std()
        
        # 最新Z-score
        latest_spread = spread.iloc[-1]
        latest_mean = rolling_mean.iloc[-1]
        latest_std = rolling_std.iloc[-1]
        
        if pd.isna(latest_std) or latest_std == 0:
            z_score = np.nan
        else:
            z_score = (latest_spread - latest_mean) / latest_std
        
        # 计算半衰期
        half_life_days = half_life(spread)
        
        # 偏离方向
        direction = "A贵" if latest_spread > 0 else "B贵"
        
        return z_score, half_life_days, direction
        
    except Exception as e:
        logger.error(f"计算Z-score和半衰期失败: {str(e)}")
        return np.nan, np.inf, "计算失败"

def monitor_one(pair_name, config):
    """监控单个对子"""
    try:
        logger.info(f"开始监控对子: {pair_name}")
        
        # 解析对子
        parts = pair_name.split('/')
        if len(parts) != 2:
            raise ValueError(f"对子格式错误: {pair_name}")
        
        symbol_a, symbol_b = parts[0], parts[1]
        pair_type = config["type"]
        threshold = config["threshold"]
        
        # 获取数据
        if pair_type == "index":
            data_a = get_index_data(symbol_a)
            data_b = get_index_data(symbol_b)
            
        elif pair_type == "etf_index":
            data_a = get_etf_data(symbol_a)
            data_b = get_index_data(symbol_b)
            
        elif pair_type == "etf_futures":
            data_a = get_etf_data(symbol_a)
            data_b = get_futures_data("AU0")  # 黄金主力合约
            
        elif pair_type == "futures_spread":
            data_a = get_futures_data("CU0")  # 铜主力合约
            data_b = get_futures_data("CU1")  # 铜次主力合约
            
        elif pair_type == "etf_basket":
            data_a = get_etf_data(symbol_a)
            data_b = create_etf_basket(symbol_a)
            
        else:
            raise ValueError(f"不支持的对子类型: {pair_type}")
        
        # 数据对齐
        common_dates = data_a.index.intersection(data_b.index)
        if len(common_dates) < 40:
            raise ValueError(f"共同交易日不足40天: {len(common_dates)}")
        
        data_a_aligned = data_a.loc[common_dates]
        data_b_aligned = data_b.loc[common_dates]
        
        # 前向填充缺失值
        data_a_aligned = data_a_aligned.fillna(method='ffill')
        data_b_aligned = data_b_aligned.fillna(method='ffill')
        
        # 计算价差
        spread = np.log(data_a_aligned / data_b_aligned)
        spread = spread.dropna()
        
        if len(spread) < 40:
            raise ValueError(f"有效价差数据不足40天: {len(spread)}")
        
        # 计算统计指标
        z_score, half_life_days, direction = calc_z_half_life(spread)
        
        # 检查是否触发警告
        if not pd.isna(z_score) and abs(z_score) >= threshold:
            warning_msg = f"⚠️  警告: {pair_name} Z-score={z_score:.3f} >= {threshold}"
            print(f"{Fore.RED}{warning_msg}{Style.RESET_ALL}")
            logger.warning(warning_msg)
        else:
            logger.info(f"✅ {pair_name} 正常: Z-score={z_score:.3f}")
        
        # 返回结果
        result = {
            '对子名': pair_name,
            '最新日期': spread.index[-1].strftime('%Y-%m-%d'),
            'Z_score': z_score,
            '半衰期': half_life_days,
            '阈值': threshold,
            '偏离方向': direction,
            '数据点数': len(spread)
        }
        
        logger.info(f"✅ {pair_name} 监控完成")
        return result
        
    except Exception as e:
        error_msg = f"❌ {pair_name} 监控失败: {str(e)}"
        print(f"{Fore.YELLOW}{error_msg}{Style.RESET_ALL}")
        logger.error(error_msg)
        return None

def main():
    """主函数"""
    try:
        logger.info("🚀 开始比价监控任务")
        print(f"{Fore.GREEN}🚀 开始比价监控任务{Style.RESET_ALL}")
        
        results = []
        
        # 监控所有对子
        for pair_name, config in PAIRS_CONFIG.items():
            result = monitor_one(pair_name, config)
            if result:
                results.append(result)
            time.sleep(1)  # 避免请求过于频繁
        
        # 保存结果到CSV
        if results:
            df_results = pd.DataFrame(results)
            csv_filename = 'ratio_monitor_akshare.csv'
            df_results.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            
            logger.info(f"✅ 结果已保存到: {csv_filename}")
            print(f"{Fore.GREEN}✅ 结果已保存到: {csv_filename}{Style.RESET_ALL}")
            
            # 显示汇总
            print(f"\n{Fore.CYAN}📊 监控汇总:{Style.RESET_ALL}")
            for _, row in df_results.iterrows():
                status = "⚠️" if abs(row['Z_score']) >= row['阈值'] else "✅"
                print(f"{status} {row['对子名']}: Z={row['Z_score']:.3f}, 半衰期={row['半衰期']:.1f}天")
        else:
            logger.error("❌ 没有成功监控到任何对子")
            print(f"{Fore.RED}❌ 没有成功监控到任何对子{Style.RESET_ALL}")
        
        logger.info("🏁 比价监控任务完成")
        print(f"{Fore.GREEN}🏁 比价监控任务完成{Style.RESET_ALL}")
        
    except Exception as e:
        error_msg = f"❌ 主程序异常: {str(e)}"
        logger.error(error_msg)
        print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
