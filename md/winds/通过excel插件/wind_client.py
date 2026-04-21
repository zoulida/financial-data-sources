"""
Wind Excel 插件封装层
======================
简化版：仅通过 Excel COM 获取 `mfd_netbuyamt` 数据。
"""

import datetime
import time
import logging
import argparse
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# 使用说明（供 AI / 调用方参考）
# 1) 单字段时间序列：
#    result = fetch_mfd_netbuyamt_wsd(
#        codes=["600519.SH"],
#        start_date="2026-03-21",
#        end_date="当前交易日",
#    )
#    df = result["600519.SH"]
#
# 2) 多字段时间序列（参考 示例2.xlsx）：
#    result = fetch_multi_fields_wsd(
#        codes=["600519.SH"],
#        fields=[
#            "mfd_netbuyamt",
#            "mfd_inflowproportion_a",
#            "mfd_inflowrate_close_m",
#            "mfd_inflow_m",
#        ],
#        start_date="2026-03-21",
#        end_date="当前交易日",
#    )
#    df = result["600519.SH"]
#
# 3) 原始公式调试：
#    raw_df = fetch_wind_formula(
#        '=WSD("600519.SH","mfd_netbuyamt,mfd_inflowproportion_a,mfd_inflowrate_close_m,mfd_inflow_m",'
#        '"2026-03-21","当前交易日","unit=1","traderType=1","TradingCalendar=SSE",'
#        '"rptType=1","Version=1","ShowParams=Y","UnitMask=9","cols=4;rows=21")'
#    )
#
# 4) 注意：当前 WSD 返回通常是纯数值矩阵，date 列是按 start_date 用工作日顺推补齐的。

DEFAULT_FIELD = "mfd_netbuyamt"
DEFAULT_FIELDS = [
    "mfd_netbuyamt",
    "mfd_inflowproportion_a",
    "mfd_inflowrate_close_m",
    "mfd_inflow_m",
]
DEFAULT_OPTIONS = [
    "unit=1",
    "traderType=1",
    "TradingCalendar=SSE",
    "rptType=1",
    "Version=1",
    "ShowParams=Y",
    "cols=1;rows=21",
]

# COM 组件延迟导入（仅 Windows 可用）
_COM_OK = False
try:
    import pythoncom
    import win32com.client as win32
    _COM_OK = True
except ImportError:
    logger.warning("win32com 不可用，Wind Excel 插件功能将被禁用")


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
    """判断返回结果中是否已经有真实数据。"""
    if len(matrix) < 2:
        return False
    for row in matrix[1:]:
        for value in row:
            if value not in (None, ""):
                return True
    return False


def _parse_wsd_single_field(df: pd.DataFrame, field_name: str, start_date: str | None = None) -> pd.DataFrame:
    """解析单字段 WSD 结果，兼容仅返回数值列的格式。"""
    if df.empty:
        return pd.DataFrame(columns=["date", field_name])

    matrix = df.values.tolist()

    if df.shape[1] == 1:
        value_series = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna().reset_index(drop=True)
        if value_series.empty:
            return pd.DataFrame(columns=["date", field_name])

        if not start_date:
            return pd.DataFrame({field_name: value_series})

        date_index = pd.bdate_range(start=pd.to_datetime(start_date), periods=len(value_series))
        return pd.DataFrame({
            "date": date_index,
            field_name: value_series,
        })

    rows_data = []
    for row in matrix:
        raw_date = row[0] if len(row) > 0 else None
        raw_value = row[1] if len(row) > 1 else None

        parsed_date = pd.to_datetime(raw_date, errors="coerce")
        if pd.isna(parsed_date):
            continue

        rows_data.append({
            "date": parsed_date,
            field_name: pd.to_numeric(raw_value, errors="coerce"),
        })

    if not rows_data:
        return pd.DataFrame(columns=["date", field_name])

    return pd.DataFrame(rows_data).reset_index(drop=True)


def _parse_wsd_multi_fields(df: pd.DataFrame, fields: List[str], start_date: str | None = None) -> pd.DataFrame:
    """解析多字段 WSD 结果，兼容示例2返回的纯数值矩阵。"""
    if df.empty:
        return pd.DataFrame(columns=["date"] + fields)

    numeric_df = df.apply(lambda col: pd.to_numeric(col, errors="coerce"))
    numeric_df = numeric_df.dropna(how="all").reset_index(drop=True)
    if numeric_df.empty:
        return pd.DataFrame(columns=["date"] + fields)

    numeric_df = numeric_df.iloc[:, :len(fields)].copy()
    numeric_df.columns = fields[:numeric_df.shape[1]]

    if not start_date:
        return numeric_df

    date_index = pd.bdate_range(start=pd.to_datetime(start_date), periods=len(numeric_df))
    return pd.concat([
        pd.DataFrame({"date": date_index}),
        numeric_df.reset_index(drop=True),
    ], axis=1)


def _parse_wsd_multi_codes_single_field(df: pd.DataFrame, codes: List[str], field_name: str,
                                        start_date: str | None = None) -> dict:
    """解析示例3那种“多股票、单字段”的 WSD 数值矩阵。"""
    if df.empty or not codes:
        return {}

    numeric_df = df.apply(lambda col: pd.to_numeric(col, errors="coerce"))
    numeric_df = numeric_df.dropna(how="all").reset_index(drop=True)
    if numeric_df.empty:
        return {}

    numeric_df = numeric_df.iloc[:, :len(codes)].copy()
    numeric_df.columns = codes[:numeric_df.shape[1]]

    if start_date:
        date_index = pd.bdate_range(start=pd.to_datetime(start_date), periods=len(numeric_df))
    else:
        date_index = pd.RangeIndex(start=0, stop=len(numeric_df))

    result = {}
    for code in numeric_df.columns:
        series = pd.to_numeric(numeric_df[code], errors="coerce")
        if series.dropna().empty:
            continue
        result[code] = pd.DataFrame({
            "date": date_index,
            field_name: series.reset_index(drop=True),
        })
    return result



def _build_wsd_formula(code: str, start_date: str, end_date: str,
                       fields: Optional[List[str]] = None,
                       options: Optional[List[str]] = None) -> str:
    """按示例文件的方式拼接 WSD 公式。"""
    field_parts = fields or [DEFAULT_FIELD]
    option_parts = options or DEFAULT_OPTIONS
    quoted_options = ",".join(f'"{item}"' for item in option_parts)
    field_str = ",".join(field_parts)
    return f'=WSD("{code}","{field_str}","{start_date}","{end_date}",{quoted_options})'


def _build_multi_codes_wsd_formula(codes: List[str], field_name: str, start_date: str, end_date: str,
                                   options: Optional[List[str]] = None) -> str:
    """按示例3的方式拼接“多股票、单字段”的 WSD 公式。"""
    option_parts = options or DEFAULT_OPTIONS
    normalized_options = []
    cols_found = False
    for item in option_parts:
        if item.startswith("cols="):
            normalized_options.append(f"cols={len(codes)};rows=21")
            cols_found = True
        else:
            normalized_options.append(item)
    if not cols_found:
        normalized_options.append(f"cols={len(codes)};rows=21")

    quoted_options = ",".join(f'"{item}"' for item in normalized_options)
    codes_str = ",".join(codes)
    return f'=WSD("{codes_str}","{field_name}","{start_date}","{end_date}",{quoted_options})'



def _create_excel_session(visible: bool = False):
    """创建并返回一个可复用的 Excel 会话。"""
    if not _COM_OK:
        raise RuntimeError("win32com 不可用，无法调用 Wind Excel 插件")

    pythoncom.CoInitialize()
    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = visible
    excel.DisplayAlerts = False
    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)
    return excel, wb, ws


def _close_excel_session(excel, wb, ws) -> None:
    """关闭 Excel 会话并释放资源。"""
    try:
        if wb is not None:
            wb.Close(SaveChanges=False)
    except Exception:
        pass
    try:
        if excel is not None:
            excel.Quit()
    except Exception:
        pass
    try:
        pythoncom.CoUninitialize()
    except Exception:
        pass


def _fetch_wind_formula_with_sheet(ws, excel, formula: str,
                                   timeout: int = 60, interval: float = 0.3) -> pd.DataFrame:
    """在指定工作表中执行 Wind 公式并返回 DataFrame。"""
    ws.Cells.Clear()
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

    matrix = _normalize_used_range(ws.UsedRange.Value)
    if not matrix:
        return pd.DataFrame()

    max_cols = max(len(row) for row in matrix)
    normalized = [row + [None] * (max_cols - len(row)) for row in matrix]
    df = pd.DataFrame(normalized)
    if hasattr(df, "map"):
        df = df.map(_convert_pywintypes)
    else:
        df = df.applymap(_convert_pywintypes)
    return df


def fetch_wind_formula(formula: str, timeout: int = 60, interval: float = 0.3,
                       visible: bool = False) -> pd.DataFrame:
    """执行一个 Wind Excel 公式，轮询等待结果，返回 DataFrame。"""
    excel = wb = ws = None
    try:
        excel, wb, ws = _create_excel_session(visible=visible)
        return _fetch_wind_formula_with_sheet(
            ws=ws,
            excel=excel,
            formula=formula,
            timeout=timeout,
            interval=interval,
        )
    finally:
        _close_excel_session(excel, wb, ws)


def fetch_multi_fields_wsd(codes: List[str], fields: List[str], start_date: str, end_date: str,
                           options: Optional[List[str]] = None, timeout: int = 60,
                           visible: bool = False) -> dict:
    """
    优先按示例3的方式批量获取：多股票单字段；若失败则回退为示例2：逐股多字段。

    返回:
        dict[str, pd.DataFrame]，每个 code 对应一个 DataFrame，列为 ["date"] + fields
    """
    if not _COM_OK:
        raise RuntimeError("win32com 不可用")
    if not codes or not fields:
        return {}

    effective_options = options or [
        item if not item.startswith("cols=") else f"cols={len(fields)};rows=21"
        for item in DEFAULT_OPTIONS
    ]
    if not any(item.startswith("UnitMask=") for item in effective_options):
        effective_options = effective_options + ["UnitMask=9"]

    excel = wb = ws = None
    try:
        excel, wb, ws = _create_excel_session(visible=visible)

        field_results: dict[str, dict] = {}
        batch_mode_ok = True
        for field in fields:
            formula = _build_multi_codes_wsd_formula(
                codes=codes,
                field_name=field,
                start_date=start_date,
                end_date=end_date,
                options=effective_options,
            )
            try:
                raw_df = _fetch_wind_formula_with_sheet(
                    ws=ws,
                    excel=excel,
                    formula=formula,
                    timeout=timeout,
                )
                parsed = _parse_wsd_multi_codes_single_field(
                    raw_df,
                    codes=codes,
                    field_name=field,
                    start_date=start_date,
                )
                if not parsed:
                    batch_mode_ok = False
                    logger.warning(f"Wind 多股票单字段模式解析为空，字段 {field}，回退逐股模式")
                    break
                field_results[field] = parsed
            except Exception as e:
                batch_mode_ok = False
                logger.warning(f"Wind 多股票单字段模式失败，字段 {field}: {e}，回退逐股模式")
                break

        if batch_mode_ok and field_results:
            result = {}
            for code in codes:
                code_frames = []
                for field in fields:
                    df = field_results.get(field, {}).get(code)
                    if df is not None and not df.empty:
                        code_frames.append(df.set_index("date"))
                if code_frames:
                    merged = pd.concat(code_frames, axis=1)
                    merged = merged.loc[:, ~merged.columns.duplicated()].reset_index()
                    result[code] = merged
            if result:
                return result

        result = {}
        for code in codes:
            formula = _build_wsd_formula(code, start_date, end_date, fields=fields, options=effective_options)
            raw_df = _fetch_wind_formula_with_sheet(
                ws=ws,
                excel=excel,
                formula=formula,
                timeout=timeout,
            )
            parsed_df = _parse_wsd_multi_fields(raw_df, fields, start_date=start_date)
            if not parsed_df.empty:
                result[code] = parsed_df
        return result
    finally:
        _close_excel_session(excel, wb, ws)



def fetch_mfd_netbuyamt_wsd(codes: List[str], start_date: str, end_date: str,
                            options: List[str] | None = None, timeout: int = 60,
                            visible: bool = False) -> dict:
    """逐只获取 `mfd_netbuyamt` 时间序列。"""
    if not _COM_OK:
        raise RuntimeError("win32com 不可用")
    if not codes:
        return {}

    result = {}
    excel = wb = ws = None
    try:
        excel, wb, ws = _create_excel_session(visible=visible)
        for code in codes:
            formula = _build_wsd_formula(code, start_date, end_date, fields=[DEFAULT_FIELD], options=options)
            raw_df = _fetch_wind_formula_with_sheet(
                ws=ws,
                excel=excel,
                formula=formula,
                timeout=timeout,
            )
            parsed_df = _parse_wsd_single_field(raw_df, DEFAULT_FIELD, start_date=start_date)
            if not parsed_df.empty:
                result[code] = parsed_df
    finally:
        _close_excel_session(excel, wb, ws)

    return result


def fetch_mfd_netbuyamt_wss(codes: List[str], trade_date: str = "",
                            options: List[str] | None = None, timeout: int = 60,
                            visible: bool = False) -> pd.DataFrame:
    """批量获取多只股票某一交易日的 `mfd_netbuyamt` 截面数据。"""
    if not codes:
        return pd.DataFrame(columns=[DEFAULT_FIELD])

    codes_str = ",".join(codes)
    opt_parts = []
    if trade_date:
        opt_parts.append(f"tradeDate={trade_date.replace('-', '')}")
    opt_parts.extend(options or DEFAULT_OPTIONS)
    opt_str = f',"{";".join(opt_parts)}"' if opt_parts else ""

    formula = f'=WSS("{codes_str}","{DEFAULT_FIELD}"{opt_str})'
    df = fetch_wind_formula(formula, timeout=timeout, visible=visible)
    if df.empty:
        return pd.DataFrame(index=codes, columns=[DEFAULT_FIELD])

    matrix = df.values.tolist()
    if len(matrix) < 2:
        return pd.DataFrame(index=codes, columns=[DEFAULT_FIELD])

    rows = []
    for row in matrix[1:]:
        if not row or row[0] is None:
            continue
        rows.append(row[:2])

    if not rows:
        return pd.DataFrame(index=codes, columns=[DEFAULT_FIELD])

    result_df = pd.DataFrame(rows, columns=["code", DEFAULT_FIELD])
    result_df = result_df.set_index("code")
    result_df[DEFAULT_FIELD] = pd.to_numeric(result_df[DEFAULT_FIELD], errors="coerce")
    return result_df


def is_wind_available() -> bool:
    return _COM_OK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["wsd", "wss", "formula"], default="wsd")
    parser.add_argument("--codes", default="600000.SH,000001.SZ")
    parser.add_argument("--fields", default=",".join(DEFAULT_FIELDS))
    parser.add_argument("--start-date", default=(datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d"))
    parser.add_argument("--end-date", default=datetime.date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--trade-date", default=datetime.date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--options", nargs="*", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--visible", action="store_true")
    parser.add_argument(
        "--formula",
        default='=WSD("600519.SH","mfd_netbuyamt,mfd_inflowproportion_a,mfd_inflowrate_close_m,mfd_inflow_m","2026-03-21","当前交易日","unit=1","traderType=1","TradingCalendar=SSE","rptType=1","Version=1","ShowParams=Y","UnitMask=9","cols=4;rows=21")',
    )
    args = parser.parse_args()

    # 命令行示例（供 AI / 调用方参考）:
    # 1) 多字段时间序列：
    #    python wind_client.py --mode wsd --codes 600519.SH --start-date 2026-03-21 --end-date 当前交易日 \
    #      --fields mfd_netbuyamt,mfd_inflowproportion_a,mfd_inflowrate_close_m,mfd_inflow_m
    #
    # 2) 单字段时间序列：
    #    python wind_client.py --mode wsd --codes 600519.SH --start-date 2026-03-21 --end-date 当前交易日 \
    #      --fields mfd_netbuyamt
    #
    # 3) 原始公式调试：
    #    python wind_client.py --mode formula --formula "=WSD(\"600519.SH\",\"mfd_netbuyamt\",\"2026-03-21\",\"当前交易日\",\"unit=1\",\"traderType=1\",\"TradingCalendar=SSE\",\"rptType=1\",\"Version=1\",\"ShowParams=Y\",\"cols=1;rows=21\")"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    if not is_wind_available():
        print("Wind Excel 插件不可用，或当前环境缺少 win32com/pythoncom")
        return

    codes = [item.strip() for item in args.codes.split(",") if item.strip()]
    fields = [item.strip() for item in args.fields.split(",") if item.strip()]

    if args.mode == "formula":
        print(fetch_wind_formula(args.formula, timeout=args.timeout, visible=args.visible))
        return

    if args.mode == "wss":
        print(fetch_mfd_netbuyamt_wss(
            codes=codes,
            trade_date=args.trade_date,
            options=args.options,
            timeout=args.timeout,
            visible=args.visible,
        ))
        return

    result = fetch_multi_fields_wsd(
        codes=codes,
        fields=fields,
        start_date=args.start_date,
        end_date=args.end_date,
        options=args.options,
        timeout=args.timeout,
        visible=args.visible,
    )
    for code, df in result.items():
        print(f"\n===== {code} =====")
        print(df)


if __name__ == "__main__":
    main()
