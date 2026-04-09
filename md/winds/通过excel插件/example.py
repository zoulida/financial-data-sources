import win32com.client as win32
import time

# 1. 后台启动excel 不可见
excel = win32.Dispatch("Excel.Application")
excel.Visible = False       # 不弹出窗口，全自动
excel.DisplayAlerts = False # 屏蔽弹窗

# 2. 新建工作簿
wb = excel.Workbooks.Add()
ws = wb.Worksheets(1)

# 3. 写入wind公式取数，示例：浦发银行 2025-01-01至今日线收盘价
# WSD(代码,指标,起始时间,结束时间)
ws.Range("A1").Formula = '=WSD("600000.SH","CLOSE","2025-01-01","2026-04-01")'

# 4. 等待wind插件计算加载
time.sleep(3)

# 5. 读取数据
data = ws.UsedRange.Value
print(data)

# 6. 关闭释放资源
wb.Close(SaveChanges=False)
excel.Quit()

# 彻底释放COM进程
del ws, wb, excel