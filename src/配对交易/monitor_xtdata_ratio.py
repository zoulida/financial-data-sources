#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比价监控脚本 - 使用 XtQuant xtdata 接口
监控多组对子的价差和Z-score，支持指数、ETF、期货等金融工具
"""

import traceback
from xtquant import xtdata
from WindPy import w
import pandas as pd
import numpy as np
import statsmodels.api as sm
from colorama import init, Fore, Style
import time
import logging
from datetime import datetime, timedelta
import warnings
import sys
import os
warnings.filterwarnings('ignore')

# 添加你的数据下载模块路径
sys.path.append(r'd:\pythonProject\firstBan\source\实盘\xuntou\datadownload')

# 尝试导入getDayData函数
try:
    from 合并下载数据 import getDayData
    print("✅ 成功导入 getDayData 函数")
except ImportError as e:
    print(f"❌ 导入 getDayData 失败: {e}")
    traceback.print_exc()
    print("将使用 xtdata 直接获取数据")
    getDayData = None

#time.sleep(10)
# 初始化colorama
init(autoreset=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ratio_monitor_xtdata.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 尝试导入配置文件
try:
    from config import PAIRS_CONFIG, XTQUANT_TOKEN, DATA_CONFIG, STATS_CONFIG, OUTPUT_CONFIG
    print("✅ 使用配置文件 config.py")
except ImportError:
    print("⚠️  未找到配置文件，使用默认配置")
    # 默认配置
    PAIRS_CONFIG = {
        "000300.SH/000852.SH": {"threshold": 2.0, "type": "index"},
        "000016.SH/399303.SZ": {"threshold": 2.0, "type": "index"},
        "510500.SH/000905.SH": {"threshold": 2.0, "type": "etf_index"},
        "518880.SH/AU0": {"threshold": 1.5, "type": "etf_futures"},
        "CU0/CU1": {"threshold": 2.0, "type": "futures_spread"},
        "510300.SH/300现货篮": {"threshold": 1.5, "type": "etf_basket"},
        "159949.SZ/创50现货篮": {"threshold": 1.5, "type": "etf_basket"},
        "512880.SH/券商现货篮": {"threshold": 1.5, "type": "etf_basket"}
    }
    XTQUANT_TOKEN = None
    DATA_CONFIG = {"start_date": "20150101", "end_date": None, "min_data_points": 40}
    STATS_CONFIG = {"z_score_window": 40, "min_half_life_data": 10}
    OUTPUT_CONFIG = {"csv_filename": "ratio_monitor_xtdata.csv", "log_filename": "ratio_monitor_xtdata.log"}

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
            ak_symbol = symbol
        elif symbol.endswith('.SZ'):
            ak_symbol = symbol
        else:
            # 根据代码判断市场
            if symbol.startswith('00') or symbol.startswith('30'):
                ak_symbol = f"{symbol}.SZ"
            elif symbol.startswith('60'):
                ak_symbol = f"{symbol}.SH"
            else:
                ak_symbol = symbol
        
        # 优先使用getDayData函数，如果不可用则使用xtdata
        if getDayData is not None:
            try:
                end_date = end_date or datetime.now().strftime('%Y%m%d')
                df = getDayData(
                    stock_code=ak_symbol,
                    start_date=start_date,
                    end_date=end_date,
                    is_download=0,  # 从缓存读取
                    dividend_type='back'  # 后复权
                )
                
                # 转换为Series格式
                close_data = df.set_index('date')['close']
                close_data.index = pd.to_datetime(close_data.index)
                close_data = close_data.sort_index()
                
                return close_data
            except Exception as e:
                logger.warning(f"getDayData 失败，回退到 xtdata: {e}")
        
        # 回退到 xtdata 直接获取
        data = xtdata.get_market_data_ex(
            field_list=['close'],
            stock_list=[ak_symbol],
            period='1d',
            start_time=start_date,
            end_time=end_date or '',
            count=-1,
            dividend_type='back'  # 后复权
        )
        
        if not data or ak_symbol not in data:
            raise ValueError(f"未获取到数据: {symbol}")
        
        # 提取收盘价数据
        close_data = data[ak_symbol]['close'].dropna()
        close_data.index = pd.to_datetime(close_data.index)
        close_data = close_data.sort_index()
        
        return close_data
    except Exception as e:
        logger.error(f"获取股票数据失败 {symbol}: {str(e)}")
        raise

@retry_on_failure()
def get_index_data(symbol, start_date="20150101", end_date=None):
    """获取指数历史数据"""
    try:
        # 转换代码格式
        if symbol.endswith('.SH'):
            ak_symbol = symbol
        elif symbol.endswith('.SZ'):
            ak_symbol = symbol
        else:
            # 根据代码判断市场
            if symbol.startswith('000') or symbol.startswith('399'):
                ak_symbol = f"{symbol}.SZ"
            elif symbol.startswith('000'):
                ak_symbol = f"{symbol}.SH"
            else:
                ak_symbol = symbol
        
        # 优先使用getDayData函数，如果不可用则使用xtdata
        if getDayData is not None:
            try:
                end_date = end_date or datetime.now().strftime('%Y%m%d')
                df = getDayData(
                    stock_code=ak_symbol,
                    start_date=start_date,
                    end_date=end_date,
                    is_download=0,  # 从缓存读取
                    dividend_type='none'  # 指数不复权
                )
                
                # 转换为Series格式
                close_data = df.set_index('date')['close']
                close_data.index = pd.to_datetime(close_data.index)
                close_data = close_data.sort_index()
                
                return close_data
            except Exception as e:
                logger.warning(f"getDayData 失败，回退到 xtdata: {e}")
        
        # 回退到 xtdata 直接获取
        data = xtdata.get_market_data_ex(
            field_list=['close'],
            stock_list=[ak_symbol],
            period='1d',
            start_time=start_date,
            end_time=end_date or '',
            count=-1
        )
        
        if not data or ak_symbol not in data:
            raise ValueError(f"未获取到数据: {symbol}")
        
        # 提取收盘价数据
        close_data = data[ak_symbol]['close'].dropna()
        close_data.index = pd.to_datetime(close_data.index)
        close_data = close_data.sort_index()
        
        return close_data
    except Exception as e:
        logger.error(f"获取指数数据失败 {symbol}: {str(e)}")
        raise

@retry_on_failure()
def get_etf_data(symbol, start_date="20150101", end_date=None):
    """获取ETF历史数据"""
    try:
        # 转换代码格式
        if symbol.endswith('.SH'):
            ak_symbol = symbol
        elif symbol.endswith('.SZ'):
            ak_symbol = symbol
        else:
            # 根据代码判断市场
            if symbol.startswith('51') or symbol.startswith('52'):
                ak_symbol = f"{symbol}.SH"
            elif symbol.startswith('15') or symbol.startswith('16'):
                ak_symbol = f"{symbol}.SZ"
            else:
                ak_symbol = symbol
                
        # 优先使用getDayData函数，如果不可用则使用xtdata
        if getDayData is not None:
            try:
                end_date = end_date or datetime.now().strftime('%Y%m%d')
                df = getDayData(
                    stock_code=ak_symbol,
                    start_date=start_date,
                    end_date=end_date,
                    is_download=0,  # 从缓存读取
                    dividend_type='none'  # ETF不复权
                )
                
                # 转换为Series格式
                close_data = df.set_index('date')['close']
                close_data.index = pd.to_datetime(close_data.index)
                close_data = close_data.sort_index()
                
                return close_data
            except Exception as e:
                logger.warning(f"getDayData 失败，回退到 xtdata: {e}")
        
        # 回退到 xtdata 直接获取
        data = xtdata.get_market_data_ex(
            field_list=['close'],
            stock_list=[ak_symbol],
            period='1d',
            start_time=start_date,
            end_time=end_date or '',
            count=-1
        )
        
        if not data or ak_symbol not in data:
            raise ValueError(f"未获取到数据: {symbol}")
        
        # 提取收盘价数据
        close_data = data[ak_symbol]['close'].dropna()
        close_data.index = pd.to_datetime(close_data.index)
        close_data = close_data.sort_index()
        
        return close_data
    except Exception as e:
        logger.error(f"获取ETF数据失败 {symbol}: {str(e)}")
        raise

@retry_on_failure()
def get_futures_data(symbol, start_date="20150101", end_date=None):
    """获取期货主力合约数据 - 使用Wind API"""
    try:
        # 期货代码转换 - 使用Wind API格式
        if symbol == "AU0":
            # 尝试主力合约的不同格式
            futures_symbols = ["AU2412.SHF", "AU2501.SHF", "AU2406.SHF"]
        elif symbol == "AG0":
            futures_symbols = ["AG2412.SHF", "AG2501.SHF", "AG2406.SHF"]
        elif symbol == "CU0":
            futures_symbols = ["CU2412.SHF", "CU2501.SHF", "CU2406.SHF"]
        elif symbol == "CU1":
            futures_symbols = ["CU2501.SHF", "CU2502.SHF", "CU2412.SHF"]
        elif symbol == "AL0":
            futures_symbols = ["AL2412.SHF", "AL2501.SHF", "AL2406.SHF"]
        elif symbol == "AL1":
            futures_symbols = ["AL2501.SHF", "AL2502.SHF", "AL2412.SHF"]
        else:
            futures_symbols = [symbol]
        
        # 尝试多个期货代码格式
        successful_data = None
        successful_symbol = None
        
        for futures_symbol in futures_symbols:
            try:
                logger.info(f"尝试获取期货数据: {futures_symbol}")
                
                # 使用Wind API获取期货数据
                data = w.wsd(
                    codes=futures_symbol,
                    fields="close",
                    beginTime=start_date,
                    endTime=end_date or datetime.now().strftime('%Y%m%d'),
                    options="Days=Trading"
                )
                
                if data.ErrorCode != 0:
                    logger.warning(f"Wind API错误 {futures_symbol}: 错误代码 {data.ErrorCode}")
                    continue
                
                # 转换为DataFrame
                if len(data.Data) > 0:
                    df = pd.DataFrame(data.Data).T
                    df.columns = data.Fields
                    df.index = data.Times
                    df.index.name = 'Date'
                    
                    # 提取收盘价数据 - Wind API返回大写字段名
                    close_data = df['CLOSE'].dropna()
                    close_data.index = pd.to_datetime(close_data.index)
                    close_data = close_data.sort_index()
                    
                    if not close_data.empty:
                        successful_data = close_data
                        successful_symbol = futures_symbol
                        logger.info(f"Wind API获取期货数据成功: {futures_symbol}, 数据点数: {len(close_data)}")
                        break
                    else:
                        logger.warning(f"期货数据为空: {futures_symbol}")
                else:
                    logger.warning(f"期货无数据: {futures_symbol}")
                    
            except Exception as e:
                logger.warning(f"尝试 {futures_symbol} 失败: {e}")
                continue
        
        if successful_data is not None:
            return successful_data
        else:
            raise ValueError(f"未获取到期货数据: {symbol}, 尝试的代码: {futures_symbols}")
    except Exception as e:
        logger.error(f"获取期货数据失败 {symbol}: {str(e)}")
        raise

@retry_on_failure()
def get_etf_holdings(symbol, date=None):
    """获取ETF持仓信息（PCF权重）"""
    try:
        # 转换代码格式
        if symbol.endswith('.SH'):
            ak_symbol = symbol
        elif symbol.endswith('.SZ'):
            ak_symbol = symbol
        else:
            if symbol.startswith('51') or symbol.startswith('52'):
                ak_symbol = f"{symbol}.SH"
            elif symbol.startswith('15') or symbol.startswith('16'):
                ak_symbol = f"{symbol}.SZ"
            else:
                ak_symbol = symbol
                
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
            
        # 使用 xtdata 获取ETF持仓数据
        # 注意：这里需要根据实际的xtdata接口调整
        # 假设有获取ETF持仓的接口
        try:
            # 尝试获取ETF持仓数据
            holdings_data = xtdata.get_financial_data(
                stock_list=[ak_symbol],
                table_list=['Top10holder'],  # 使用十大股东数据作为替代
                start_time=date,
                end_time=date
            )
            
            if not holdings_data or 'ratio' not in holdings_data:
                raise ValueError(f"未获取到持仓数据: {symbol}")
            
            # 提取权重数据
            holdings = {}
            for i, (name, ratio) in enumerate(zip(holdings_data['name'], holdings_data['ratio'])):
                if pd.notna(ratio) and ratio > 0:
                    # 这里需要根据实际数据结构调整
                    holdings[f"stock_{i}"] = ratio / 100.0  # 转换为小数
            
            return holdings
            
        except Exception as e:
            logger.warning(f"获取ETF持仓失败，使用默认权重: {str(e)}")
            # 返回默认权重（这里需要根据实际ETF调整）
            return {}
            
    except Exception as e:
        logger.error(f"获取ETF持仓失败 {symbol}: {str(e)}")
        raise

def create_etf_basket(etf_symbol, start_date="20150101", end_date=None):
    """创建ETF现货篮"""
    try:
        # 获取ETF持仓
        holdings = get_etf_holdings(etf_symbol)
        if not holdings:
            logger.warning(f"无法获取ETF持仓，使用ETF本身作为现货篮: {etf_symbol}")
            return get_etf_data(etf_symbol, start_date, end_date)
        
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
            logger.warning("没有有效的成分股数据，使用ETF本身")
            return get_etf_data(etf_symbol, start_date, end_date)
        
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
            data_b = get_futures_data(symbol_b)  # 期货主力合约
            
        elif pair_type == "futures_spread":
            data_a = get_futures_data(symbol_a)  # 期货主力合约
            data_b = get_futures_data(symbol_b)  # 期货次主力合约
            
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
        
        # 初始化 xtdata（可选设置Token）
        if XTQUANT_TOKEN:
            try:
                xtdata.set_token(XTQUANT_TOKEN)
                print("✅ XtQuant Token 设置成功")
            except Exception as e:
                print(f"⚠️  Token 设置失败: {str(e)}")
                print("继续使用免费数据接口...")
        else:
            print("ℹ️  未设置 XtQuant Token，使用免费数据接口")
            print("如需更多数据权限，可在 config.py 中设置 XTQUANT_TOKEN")
        
        # 初始化 Wind API
        try:
            w.start()
            print("✅ Wind API 连接成功")
        except Exception as e:
            print(f"⚠️  Wind API 连接失败: {str(e)}")
            print("期货数据获取可能失败，继续运行...")
        
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
            csv_filename = OUTPUT_CONFIG.get('csv_filename', 'ratio_monitor_xtdata.csv')
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
    finally:
        # 关闭 Wind API
        try:
            w.stop()
            print("✅ Wind API 连接已关闭")
        except:
            pass

if __name__ == "__main__":
    main()
