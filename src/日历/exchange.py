# 使用 exchange_calendars 获取交易日历
try:
    import exchange_calendars as xcals
    EXCHANGE_CALENDARS_AVAILABLE = True
except ImportError:
    EXCHANGE_CALENDARS_AVAILABLE = False
    print("警告: exchange_calendars模块未安装，相关功能将不可用")



def get_exchange_calendar_dates(start_date='20200101', end_date = None  ):
    """
    使用 exchange_calendars 获取交易日历
    
    Args:
        start_date (str): 开始日期，格式：YYYYMMDD 或 YYYY-MM-DD
        end_date (str): 结束日期，格式：YYYYMMDD 或 YYYY-MM-DD
    
    Returns:
        pd.DataFrame: 包含交易日期的DataFrame
    """
    if not EXCHANGE_CALENDARS_AVAILABLE:
        print("exchange_calendars模块不可用，请先安装该模块")
        return pd.DataFrame()
    
    try:
        # 处理日期格式，统一转换为 YYYY-MM-DD 格式
        def format_date(date_str):
            if '-' in date_str:
                return date_str
            else:
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        start_formatted = format_date(start_date)
        end_formatted = format_date(end_date)
        
        # 获取上交所+深交所交易日历
        xshg = xcals.get_calendar("XSHG")
        
        # 获取指定日期范围的交易日
        trading_days = xshg.sessions_in_range(start_formatted, end_formatted)
        
        # 转换为DataFrame - 处理pandas Timestamp对象
        trade_dates_list = []
        for day in trading_days:
            if hasattr(day, 'strftime'):
                # 如果是datetime对象或pandas Timestamp对象
                trade_dates_list.append(day.strftime('%Y%m%d'))
            else:
                # 如果是其他格式，转换为字符串
                day_str = str(day).replace('-', '')
                trade_dates_list.append(day_str)
        
        df = pd.DataFrame({
            'trade_date': trade_dates_list,
            'is_open': [1] * len(trading_days)  # 1表示交易日
        })
        
        print(f"exchange_calendars获取到 {len(df)} 个交易日")
        return df
        
    except Exception as e:
        print(f"exchange_calendars获取交易日历失败: {e}")
        return pd.DataFrame()