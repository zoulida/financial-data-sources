import datetime
import time

import pandas as pd
import pythoncom
import win32com.client as win32


def _convert_pywintypes(val):
    """将 pywintypes.datetime 转为普通 datetime.datetime。"""
    if hasattr(val, "year") and hasattr(val, "tzinfo"):
        try:
            return datetime.datetime(
                val.year,
                val.month,
                val.day,
                val.hour,
                val.minute,
                val.second,
            )
        except Exception:
            return val
    return val


def _normalize_used_range(raw):
    """把 Excel 的 UsedRange 结果统一成二维列表。"""
    if raw is None:
        return []

    if isinstance(raw, tuple):
        if raw and isinstance(raw[0], tuple):
            return [list(row) for row in raw]
        return [list(raw)]

    return [[raw]]


def _has_effective_data(matrix):
    """判断返回结果中是否已经有真实数据。"""
    if len(matrix) < 2:
        return False

    for row in matrix[1:]:
        for value in row:
            if value not in (None, ""):
                return True
    return False


def fetch_wind_formula_to_dataframe(formula, timeout=15, interval=0.2, visible=False):
    """
    执行一个 Wind Excel 公式，轮询等待结果，并返回 DataFrame。

    参数:
        formula: 传入 Excel 公式字符串，例如 '=WSD("600000.SH","CLOSE","2025-01-01","2026-04-01")'
        timeout: 最长等待秒数
        interval: 轮询间隔秒数
        visible: 是否显示 Excel 窗口，调试时可设为 True
    """
    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = visible
    excel.DisplayAlerts = False

    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)

    try:
        ws.Range("A1").Formula = formula
        start_time = time.time()

        while True:
            pythoncom.PumpWaitingMessages()
            excel.Calculate()

            raw = ws.UsedRange.Value
            matrix = _normalize_used_range(raw)
            if _has_effective_data(matrix):
                break

            if time.time() - start_time > timeout:
                raise TimeoutError("Wind 数据加载超时")

            time.sleep(interval)

        matrix = _normalize_used_range(ws.UsedRange.Value)
        if not matrix:
            return pd.DataFrame()

        max_cols = max(len(row) for row in matrix)
        normalized_rows = [row + [None] * (max_cols - len(row)) for row in matrix]
        df = pd.DataFrame(normalized_rows)
        df = df.applymap(_convert_pywintypes)
        return df
    finally:
        wb.Close(SaveChanges=False)
        excel.Quit()
        del ws, wb, excel


if __name__ == "__main__":
    formula = '=WSD("600006.SH","CLOSE,windcode,sec_name","2025-01-01","2026-04-16")'
    df = fetch_wind_formula_to_dataframe(formula)
    print(df)

