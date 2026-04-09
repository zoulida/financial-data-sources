import time
import pythoncom
import win32com.client as win32


def has_effective_value(cell_value):
    """单元格有真实返回值，而不是空白/None。"""
    return cell_value not in (None, "")


excel = win32.DispatchEx("Excel.Application")
excel.Visible = False       # 不弹出窗口，全自动
excel.DisplayAlerts = False # 屏蔽弹窗

wb = excel.Workbooks.Add()
ws = wb.Worksheets(1)

try:
    # WSD(代码,指标,起始时间,结束时间)
    ws.Range("A1").Formula = '=WSD("600000.SH","CLOSE","2025-01-01","2026-04-01")'

    # 轮询关键结果单元格，有数据就立刻读取
    # Wind WSD 一般会把标题放在首行，实际数据通常从 B2 开始出现
    interval = 0.2
    timeout = 30
    start_time = time.time()

    while True:
        pythoncom.PumpWaitingMessages()
        excel.Calculate()

        if has_effective_value(ws.Range("B2").Value):
            break

        if time.time() - start_time > timeout:
            raise TimeoutError("Wind 数据加载超时")

        time.sleep(interval)

    data = ws.UsedRange.Value
    print(data)
finally:
    wb.Close(SaveChanges=False)
    excel.Quit()
    del ws, wb, excel

