"""
Wind Excel 插件封装层
======================
通过 Excel COM 自动化执行 Wind 公式，轮询等待结果并返回 DataFrame。
参考 md/winds/通过excel插件/wind_formula_polling.py 和 exampletoCSV.py。
"""

import datetime
import time
import logging
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# COM 组件延迟导入（仅 Windows 可用）
_COM_OK = False
try:
    import pythoncom
    import win32com.client as win32
    _COM_OK = True
except ImportError:
    logger.warning("win32com 不可用，Wind Excel 插件功能将被禁用")


# ────────────────────────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────────────────────────

def _convert_pywintypes(val):
    """将 pywintypes.datetime 转为普通 datetime.datetime。"""
    if hasattr(val, "year") and hasattr(val, "tzinfo"):
        try:
            return datetime.datetime(
                val.year, val.month, val.day,
                val.hour, val.minute, val.second,
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
    """判断返回结果中是否已经有真实数据（跳过首行标题）。"""
    if len(matrix) < 2:
        return False
    for row in matrix[1:]:
        for value in row:
            if value not in (None, ""):
                return True
    return False


# ────────────────────────────────────────────────────────────
# 核心：单公式获取
# ────────────────────────────────────────────────────────────

def fetch_wind_formula(formula: str, timeout: int = 60, interval: float = 0.3,
                       visible: bool = False) -> pd.DataFrame:
    """
    执行一个 Wind Excel 公式，轮询等待结果，返回 DataFrame。

    参数:
        formula: Excel 公式字符串，例如 '=WSD("600000.SH","CLOSE","2025-01-01","2026-04-01")'
        timeout: 最长等待秒数
        interval: 轮询间隔秒数
        visible: 是否显示 Excel 窗口（调试用）
    """
    if not _COM_OK:
        raise RuntimeError("win32com 不可用，无法调用 Wind Excel 插件")

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
                raise TimeoutError(f"Wind 数据加载超时({timeout}s): {formula[:80]}...")

            time.sleep(interval)

        # 最终读取
        matrix = _normalize_used_range(ws.UsedRange.Value)
        if not matrix:
            return pd.DataFrame()

        max_cols = max(len(row) for row in matrix)
        normalized = [row + [None] * (max_cols - len(row)) for row in matrix]
        df = pd.DataFrame(normalized)
        # 兼容 pandas >= 2.1（applymap 已废弃）
        if hasattr(df, "map"):
            df = df.map(_convert_pywintypes)
        else:
            df = df.applymap(_convert_pywintypes)
        return df

    finally:
        try:
            wb.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            excel.Quit()
        except Exception:
            pass
        del ws, wb, excel


# ────────────────────────────────────────────────────────────
# 批量 WSD：多只股票 × 多字段，一个 Excel 实例并行计算
# ────────────────────────────────────────────────────────────

def fetch_wsd_batch(codes: List[str], fields: List[str],
                    start_date: str, end_date: str,
                    options: str = "",
                    timeout: int = 60, visible: bool = False) -> dict:
    """
    批量获取 WSD 时间序列数据。

    每只股票的每个字段占 1 个公式（写入 sheet 的不同列），
    Wind 在同一 Excel 实例内并行计算，最后一次性读取。

    参数:
        codes: 股票代码列表，如 ["600000.SH", "000001.SZ"]
        fields: Wind 字段列表，如 ["mfd_inflow_m", "mfd_inflow_close_m"]
        start_date: 起始日期，如 "2026-04-01"
        end_date: 结束日期，如 "2026-04-08"
        options: 额外 WSD 参数，如 "ruleType=10;unit=1"

    返回:
        dict: {code: DataFrame}，DataFrame 列为 ["date"] + fields
    """
    if not _COM_OK:
        raise RuntimeError("win32com 不可用")
    if not codes or not fields:
        return {}

    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = visible
    excel.DisplayAlerts = False
    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)

    try:
        # 每只股票占 len(fields)+1 列（第1列日期 + 各字段列）
        # WSD 公式对单只股票+单字段返回 [日期列, 值列]，占2列
        # 所以每只股票每个字段占2列，但日期列共享
        # 简化方案：每只股票一个公式，字段用逗号拼接，返回 日期 + 多字段列
        col = 1
        code_col_map = {}  # {code: 起始列号}
        opt_str = f',"{options}"' if options else ""

        for code in codes:
            fields_str = ",".join(fields)
            formula = f'=WSD("{code}","{fields_str}","{start_date}","{end_date}"{opt_str})'
            ws.Cells(1, col).Formula = formula
            code_col_map[code] = col
            # WSD 多字段返回：第1列日期 + 后续每字段1列 = 1 + len(fields) 列
            col += 1 + len(fields)

        logger.info(f"Wind WSD 批量查询: {len(codes)}只股票, 字段={fields}")

        # 轮询等待
        start_time = time.time()
        while True:
            pythoncom.PumpWaitingMessages()
            excel.Calculate()

            raw = ws.UsedRange.Value
            matrix = _normalize_used_range(raw)
            if _has_effective_data(matrix):
                break

            if time.time() - start_time > timeout:
                logger.warning(f"Wind WSD 批量查询超时({timeout}s)")
                break

            time.sleep(0.5)

        # 读取结果
        raw = ws.UsedRange.Value
        matrix = _normalize_used_range(raw)

        # 解析每只股票的数据
        result = {}
        for code, start_col in code_col_map.items():
            col_idx = start_col - 1  # 0-indexed
            n_cols = 1 + len(fields)  # 日期列 + 字段列

            rows_data = []
            for row in matrix:
                if col_idx >= len(row):
                    continue
                date_val = _convert_pywintypes(row[col_idx]) if col_idx < len(row) else None
                if date_val is None:
                    continue

                row_dict = {"date": date_val}
                for fi, field in enumerate(fields):
                    val_idx = col_idx + 1 + fi
                    val = row[val_idx] if val_idx < len(row) else None
                    row_dict[field] = val
                rows_data.append(row_dict)

            if rows_data:
                df = pd.DataFrame(rows_data)
                # 尝试转换日期列
                try:
                    df["date"] = pd.to_datetime(df["date"])
                except Exception:
                    pass
                # 数值列转换
                for f in fields:
                    df[f] = pd.to_numeric(df[f], errors="coerce")
                result[code] = df

        return result

    finally:
        try:
            wb.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            excel.Quit()
        except Exception:
            pass
        del ws, wb, excel


# ────────────────────────────────────────────────────────────
# 批量 WSS：截面数据（多只股票 × 多字段，单时点）
# ────────────────────────────────────────────────────────────

def fetch_wss_batch(codes: List[str], fields: List[str],
                    trade_date: str = "",
                    options: str = "",
                    timeout: int = 60, visible: bool = False) -> pd.DataFrame:
    """
    批量获取 WSS 截面数据。

    参数:
        codes: 股票代码列表
        fields: Wind 字段列表
        trade_date: 交易日期，如 "2026-04-08"
        options: 额外参数

    返回:
        DataFrame，index=code，columns=fields
    """
    if not _COM_OK:
        raise RuntimeError("win32com 不可用")
    if not codes or not fields:
        return pd.DataFrame()

    # WSS 公式：=WSS("代码1,代码2,...","字段1,字段2,...","tradeDate=YYYYMMDD")
    codes_str = ",".join(codes)
    fields_str = ",".join(fields)
    opt_parts = []
    if trade_date:
        opt_parts.append(f"tradeDate={trade_date.replace('-', '')}")
    if options:
        opt_parts.append(options)
    opt_str = f',"{";".join(opt_parts)}"' if opt_parts else ""

    formula = f'=WSS("{codes_str}","{fields_str}"{opt_str})'

    df = fetch_wind_formula(formula, timeout=timeout, visible=visible)
    if df.empty:
        return pd.DataFrame(index=codes, columns=fields)

    # WSS 返回格式：第1行为标题（字段名），第1列为股票代码，后续列为数据
    # 解析
    try:
        matrix = df.values.tolist()
        if len(matrix) < 2:
            return pd.DataFrame(index=codes, columns=fields)

        # 跳过标题行
        data_rows = []
        for row in matrix[1:]:
            if row[0] is None:
                continue
            data_rows.append(row)

        if not data_rows:
            return pd.DataFrame(index=codes, columns=fields)

        result_df = pd.DataFrame(data_rows)
        # 第0列是代码，后续列是字段值
        result_df.columns = ["code"] + fields[:result_df.shape[1] - 1]
        result_df = result_df.set_index("code")
        for f in result_df.columns:
            result_df[f] = pd.to_numeric(result_df[f], errors="coerce")
        return result_df
    except Exception as e:
        logger.error(f"WSS 结果解析失败: {e}")
        return pd.DataFrame(index=codes, columns=fields)


def is_wind_available() -> bool:
    """检查 Wind Excel 插件是否可用。"""
    return _COM_OK
