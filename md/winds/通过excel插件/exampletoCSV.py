import win32com.client as win32
import time
import datetime
import os
import pandas as pd

def _convert_pywintypes(val):
    """将 pywintypes.datetime 转为普通 datetime.datetime（去时区）"""
    if hasattr(val, 'year') and hasattr(val, 'tzinfo'):
        try:
            return datetime.datetime(val.year, val.month, val.day,
                                     val.hour, val.minute, val.second)
        except Exception:
            pass
    return val

def wind_wsd_auto_fetch(codes, start_date, end_date):
    # 后台启动Excel 不可见（DispatchEx 强制新实例，避免属性设置失败）
    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False

    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)

    # 所有股票的WSD公式一次性写入同一sheet（每只占2列：日期+收盘价）
    for i, code in enumerate(codes):
        col = i * 2 + 1  # 第1、3、5...列
        formula = f'=WSD("{code}","CLOSE","{start_date}","{end_date}")'
        ws.Cells(1, col).Formula = formula

    # 只等一次，Wind并行计算所有公式
    time.sleep(5)

    # 一次性读取全部数据
    raw = ws.UsedRange.Value
    wb.Close(SaveChanges=False)
    excel.Quit()
    del excel

    # 按每2列解析出各股票的 date + close
    all_data = []
    for i, code in enumerate(codes):
        col_idx = i * 2  # raw中每行的列索引
        rows = []
        for row in raw:
            if not isinstance(row, tuple):
                continue
            if col_idx + 1 >= len(row):
                continue
            date_val = _convert_pywintypes(row[col_idx])
            close_val = row[col_idx + 1]
            if date_val is None:
                continue
            rows.append((date_val, close_val))
        if rows:
            df = pd.DataFrame(rows, columns=["date", "close"])
            df["code"] = code
            all_data.append(df)

    # 合并全部股票数据并导出csv
    res = pd.concat(all_data, axis=0, ignore_index=True)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "wind_batch_data.csv")
    res.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"导出完成: {csv_path}")
    return res

if __name__ == "__main__":
    stock_list = [
        "600000.SH",
        "601318.SH",
        "000001.SZ"
    ]
    df_out = wind_wsd_auto_fetch(stock_list, "2025-01-01", "2026-04-08")
    print(df_out.head())