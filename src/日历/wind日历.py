from WindPy import w

# 启动 Wind
w.start()

# 获取指定日期范围内的交易日（仅包含交易日，不含节假日）
start_date = "2023-01-01"
end_date = "2023-12-31"
data = w.tdays(start_date, end_date, "")

if data.ErrorCode == 0:
    trade_days = data.Data[0]  # 返回 datetime 对象列表
    for day in trade_days:
        print(day.strftime("%Y-%m-%d"))
else:
    print("获取失败：", data.Data)

w.close()