import pandas_market_calendars as mcal

# 获取中国上海证券交易所日历
cn_exchange = mcal.get_calendar('SSE')  # Shanghai Stock Exchange

# 获取指定日期范围内的交易日
schedule = cn_exchange.schedule(start_date='2023-01-01', end_date='2026-12-31')
trade_days = schedule.index.strftime('%Y-%m-%d').tolist()

for day in trade_days:
    print(day)