import requests
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

# 尝试导入akshare作为备选数据源
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: akshare模块未安装")

# 尝试导入pandas_market_calendars作为备选数据源
try:
    import pandas_market_calendars as mcal
    PANDAS_MARKET_CALENDARS_AVAILABLE = True
except ImportError:
    PANDAS_MARKET_CALENDARS_AVAILABLE = False
    print("警告: pandas_market_calendars模块未安装")

def get_pandas_market_calendars(year: int = None) -> pd.DataFrame:
    """
    使用pandas_market_calendars获取交易日历
    
    Args:
        year: 年份，如果为None则使用当前年份
    
    Returns:
        pd.DataFrame: 包含日期和是否交易日的DataFrame
    """
    if not PANDAS_MARKET_CALENDARS_AVAILABLE:
        return pd.DataFrame()
    
    if year is None:
        year = datetime.now().year
    
    try:
        # 获取上交所交易日历
        cn_exchange = mcal.get_calendar('SSE')
        
        # 获取指定日期范围内的交易日
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        schedule = cn_exchange.schedule(start_date=start_date, end_date=end_date)
        trade_days = schedule.index.strftime('%Y-%m-%d').tolist()
        
        # 创建DataFrame
        df = pd.DataFrame({
            'date': trade_days,
            'is_trading_day': 1,
            'day_type': '交易日'
        })
        
        print(f"pandas_market_calendars获取到{year}年{len(df)}个交易日")
        return df
        
    except Exception as e:
        print(f"pandas_market_calendars获取{year}年交易日历失败: {e}")
        return pd.DataFrame()

def get_akshare_calendar(year: int = None) -> pd.DataFrame:
    """
    使用akshare获取交易日历
    
    Args:
        year: 年份，如果为None则使用当前年份
    
    Returns:
        pd.DataFrame: 包含日期和是否交易日的DataFrame
    """
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    if year is None:
        year = datetime.now().year
    
    try:
        # 使用akshare获取交易日历
        df = ak.tool_trade_date_hist_sina()
        
        # 转换日期格式
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
        
        # 筛选指定年份的数据
        year_start = f"{year}-01-01"
        year_end = f"{year}-12-31"
        
        df_filtered = df[(df['trade_date'] >= year_start) & (df['trade_date'] <= year_end)].copy()
        
        # 添加是否交易日列（akshare的数据都是交易日）
        df_filtered['is_trading_day'] = 1
        df_filtered['day_type'] = "交易日"
        
        # 重命名列以保持一致性
        df_filtered = df_filtered.rename(columns={'trade_date': 'date'})
        
        print(f"akshare获取到{year}年{len(df_filtered)}个交易日")
        return df_filtered[['date', 'is_trading_day', 'day_type']]
        
    except Exception as e:
        print(f"akshare获取{year}年交易日历失败: {e}")
        return pd.DataFrame()

def get_szse_calendar_api(year: int = None) -> pd.DataFrame:
    """
    使用深交所API获取交易日历（原方法）
    
    Args:
        year: 年份，如果为None则使用当前年份
    
    Returns:
        pd.DataFrame: 包含日期和是否交易日的DataFrame
    """
    if year is None:
        year = datetime.now().year
    
    # 深交所日历API
    base_url = "https://www.szse.cn/api/report/index/oneindex/month"
    
    all_days = []
    
    # 检查年份是否合理（不能超过当前年份太多）
    current_year = datetime.now().year
    if year > current_year:
        print(f"警告: {year}年超过当前年份{current_year}，可能没有数据")
        # 如果请求未来年份，尝试获取当前年份作为备选
        year = current_year
        print(f"改为获取{year}年数据")
    
    for month in range(1, 13):
        try:
            url = f"{base_url}?month={year}-{month:02d}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(url, timeout=10, headers=headers)
            
            # 检查HTTP状态码
            if response.status_code == 404:
                print(f"警告: {year}年{month:02d}月数据不存在(404)，可能该年份数据未发布")
                # 如果是404，可能整个年份都没有数据，停止后续请求
                if month == 1:
                    print(f"提示: {year}年整年数据可能未发布，深交所API可能已失效")
                return pd.DataFrame()
            elif response.status_code != 200:
                print(f"获取{year}年{month:02d}月数据失败，HTTP状态码: {response.status_code}")
                continue
            
            response.raise_for_status()
            
            data = response.json()
            
            if "data" in data and isinstance(data["data"], list):
                for day_info in data["data"]:
                    if isinstance(day_info, dict):
                        date_str = day_info.get("date", "")
                        is_trade = day_info.get("trade", False)
                        
                        # 确定日期类型
                        if is_trade:
                            day_type = "交易日"
                        else:
                            # 可以根据需要进一步细化非交易日的类型
                            day_type = "非交易日"
                        
                        all_days.append({
                            "date": date_str,  # 格式: YYYY-MM-DD
                            "is_trading_day": 1 if is_trade else 0,
                            "day_type": day_type
                        })
            
            print(f"已获取{year}年{month:02d}月日历数据")
            
        except requests.RequestException as e:
            print(f"获取{year}年{month:02d}月数据失败: {e}")
            continue
        except json.JSONDecodeError as e:
            print(f"解析{year}年{month:02d}月数据失败: {e}")
            continue
        except Exception as e:
            print(f"处理{year}年{month:02d}月数据时发生未知错误: {e}")
            continue
    
    # 转换为DataFrame
    df = pd.DataFrame(all_days)
    
    if not df.empty:
        # 按日期排序
        df = df.sort_values("date").reset_index(drop=True)
        print(f"深交所API获取{year}年共{len(df)}天的日历数据")
        print(f"其中交易日: {df['is_trading_day'].sum()}天")
    else:
        print(f"深交所API未能获取{year}年的日历数据")
    
    return df

def get_szse_calendar(year: int = None) -> pd.DataFrame:
    """
    获取深交所当年日历，优先使用pandas_market_calendars，然后是akshare，最后是深交所API
    
    Args:
        year: 年份，如果为None则使用当前年份
    
    Returns:
        pd.DataFrame: 包含日期和是否交易日的DataFrame
                     columns: ['date', 'is_trading_day', 'day_type']
    """
    if year is None:
        year = datetime.now().year
    
    print(f"正在获取{year}年交易日历...")
    
    # 优先使用pandas_market_calendars
    if PANDAS_MARKET_CALENDARS_AVAILABLE:
        print("尝试使用pandas_market_calendars获取交易日历...")
        df = get_pandas_market_calendars(year)
        if not df.empty:
            return df
        print("pandas_market_calendars获取失败，尝试akshare...")
    
    # 备选方案1：使用akshare
    if AKSHARE_AVAILABLE:
        print("尝试使用akshare获取交易日历...")
        df = get_akshare_calendar(year)
        if not df.empty:
            return df
        print("akshare获取失败，尝试深交所API...")
    
    # 备选方案2：使用深交所API
    print("尝试使用深交所API获取交易日历...")
    df = get_szse_calendar_api(year)
    if not df.empty:
        return df
    
    print(f"所有数据源都无法获取{year}年交易日历")
    return pd.DataFrame()

def get_szse_trading_days(year: int = None) -> List[str]:
    """
    获取深交所当年所有交易日
    
    Args:
        year: 年份，如果为None则使用当前年份
    
    Returns:
        List[str]: 交易日列表，格式为 ['YYYY-MM-DD', ...]
    """
    df = get_szse_calendar(year)
    
    if df.empty:
        return []
    
    # 筛选交易日
    trading_days = df[df["is_trading_day"] == 1]["date"].tolist()
    
    return trading_days

def save_szse_calendar(year: int = None, output_path: str = None) -> str:
    """
    获取并保存深交所日历到CSV文件
    
    Args:
        year: 年份，如果为None则使用当前年份
        output_path: 输出文件路径，如果为None则自动生成
    
    Returns:
        str: 保存的文件路径
    """
    if year is None:
        year = datetime.now().year
    
    if output_path is None:
        output_path = f"szse_calendar_{year}.csv"
    
    df = get_szse_calendar(year)
    
    if not df.empty:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"日历数据已保存到: {output_path}")
    else:
        print("没有数据可保存")
    
    return output_path

if __name__ == "__main__":
    # 测试获取当前年份日历
    current_year = datetime.now().year
    print(f"正在获取{current_year}年深交所日历...")
    
    # 获取完整日历
    calendar_df = get_szse_calendar(current_year)
    
    if not calendar_df.empty:
        print("\n日历数据预览:")
        print(calendar_df.head(10))
        print(f"\n总计: {len(calendar_df)}天")
        print(f"交易日: {calendar_df['is_trading_day'].sum()}天")
        print(f"非交易日: {len(calendar_df) - calendar_df['is_trading_day'].sum()}天")
        
        # 保存到文件
        output_file = save_szse_calendar(current_year)
        
        # 仅获取交易日列表
        trading_days = get_szse_trading_days(current_year)
        print(f"\n交易日列表(前10个): {trading_days[:10]}")
        print(f"交易日总数: {len(trading_days)}")
        
        # 测试获取2025年数据（如果当前是2026年）
        if current_year > 2025:
            print(f"\n测试获取2025年数据:")
            calendar_2025 = get_szse_calendar(2025)
            if not calendar_2025.empty:
                print(f"2025年数据: {len(calendar_2025)}天，交易日: {calendar_2025['is_trading_day'].sum()}天")
    else:
        print("获取日历数据失败")
        
        # 如果获取当前年份失败，尝试获取2025年数据
        print("\n尝试获取2025年数据:")
        calendar_2025 = get_szse_calendar(2025)
        if not calendar_2025.empty:
            print(f"2025年数据: {len(calendar_2025)}天，交易日: {calendar_2025['is_trading_day'].sum()}天")
            trading_days_2025 = get_szse_trading_days(2025)
            print(f"2025年交易日总数: {len(trading_days_2025)}")
