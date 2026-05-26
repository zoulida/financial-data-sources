"""
测试 Wind Excel 插件融资融券余额数据获取
使用 WSD + EDBclose 取沪市/深市/北交所融资融券余额，合成全市场总余额。

参考 Excel 原始公式：
    =WSD("M0061608,M0061613,Z5080762","EDBclose","起始日","当前日期",
         "TradingCalendar=SSE","PriceAdj=","rptType=1","Version=1",
         "ShowParams=Y","cols=3;rows=264")
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[3]
WIND_EXCEL_DIR = ROOT_DIR / "md" / "winds" / "通过excel插件"
if str(WIND_EXCEL_DIR) not in sys.path:
    sys.path.insert(0, str(WIND_EXCEL_DIR))

from wind_client import fetch_wind_formula, is_wind_available


# 截图确认的指标代码（融资融券余额）
MARGIN_SOURCES = [
    ("M0061608", "沪市"),
    ("M0061613", "深市"),
    ("Z5080762", "北交所"),
]


def _build_margin_wsd_formula(code, start_date, end_date, rows=400):
    return (
        f'=WSD("{code}","EDBclose","{start_date}","{end_date}",'
        f'"TradingCalendar=SSE","PriceAdj=","rptType=1","Version=1",'
        f'"ShowParams=Y","cols=1;rows={rows}")'
    )


def _looks_like_date(value):
    if value in (None, ""):
        return False
    try:
        return pd.notna(pd.to_datetime(value, errors="coerce"))
    except Exception:
        return False


def _looks_like_number(value):
    if value in (None, ""):
        return False
    try:
        return pd.notna(pd.to_numeric(value, errors="coerce"))
    except Exception:
        return False


def _parse_single_series(raw_df, value_name, start_date):
    """从 Excel 返回的二维矩阵中解析出 date+value 序列。"""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["date", value_name])

    df = raw_df.copy()
    date_col = None
    value_col = None

    for col in df.columns:
        if df[col].apply(_looks_like_date).sum() >= 2:
            date_col = col
            break

    for col in df.columns:
        if col == date_col:
            continue
        if df[col].apply(_looks_like_number).sum() >= 2:
            value_col = col
            break

    if date_col is not None and value_col is not None:
        result = pd.DataFrame({
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            value_name: pd.to_numeric(df[value_col], errors="coerce"),
        })
    else:
        values = []
        for col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce").dropna()
            if not numeric.empty:
                values.extend(numeric.tolist())
        if not values:
            return pd.DataFrame(columns=["date", value_name])
        fallback_start = pd.to_datetime(start_date) if start_date else datetime.now()
        result = pd.DataFrame({
            "date": pd.bdate_range(start=fallback_start, periods=len(values)),
            value_name: values,
        })

    result = result.dropna(subset=["date", value_name]).sort_values("date").reset_index(drop=True)
    return result


def _fetch_margin_total(start_date, end_date, rows=400):
    series_list = []
    for code, label in MARGIN_SOURCES:
        formula = _build_margin_wsd_formula(code, start_date, end_date, rows=rows)
        print(f"  获取{label}({code})：{formula}")
        try:
            raw_df = fetch_wind_formula(formula, timeout=40, interval=0.5, visible=False)
        except Exception as exc:
            print(f"  {label}获取失败: {exc}")
            continue
        parsed = _parse_single_series(raw_df, label, start_date)
        if parsed.empty:
            print(f"  {label}返回为空")
            continue
        print(f"  {label}有效数据 {len(parsed)} 条")
        series_list.append(parsed)

    if not series_list:
        raise RuntimeError("所有融资融券余额来源均获取失败")

    merged = series_list[0]
    for series in series_list[1:]:
        merged = merged.merge(series, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    components = [label for _, label in MARGIN_SOURCES if label in merged.columns]
    merged["margin_balance"] = merged[components].sum(axis=1, min_count=1)
    merged["period_net_purchases"] = merged["margin_balance"].diff()
    return merged, components


def test_margin_data():
    print("=" * 70)
    print("Wind Excel 插件 - 融资融券余额数据获取测试")
    print("=" * 70)

    try:
        print("\n[1/4] 检查 Wind Excel 插件...")
        if not is_wind_available():
            print("  Wind Excel 插件不可用，或当前环境缺少 win32com/pythoncom")
            return
        print("  Wind Excel 插件环境可用")

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

        print("\n[2/4] 获取融资融券数据...")
        print(f"  日期范围: {start_date} 至 {end_date}")
        print(f"  数据字段: EDBclose")
        merged, components = _fetch_margin_total(start_date, end_date, rows=120)
        print(f"  合成总余额：使用 {components}")

        print("\n[3/4] 解析数据...")
        print(f"  合并后数据行数: {len(merged)}")
        if merged.empty or merged["margin_balance"].dropna().empty:
            print("  合并后数据为空")
            return

        recent = merged.dropna(subset=["margin_balance", "period_net_purchases"]).sort_values("date", ascending=False)
        if len(recent) < 1:
            print("  数据不足，至少需要 2 个交易日")
            return

        net_buy_values = recent["period_net_purchases"].head(3).astype(float).tolist()
        recent_dates = recent["date"].head(3).dt.strftime("%Y-%m-%d").tolist()

        print("\n[4/4] 最近3日融资融券余额日变化（近似净买入，Wind 返回单位：万元）:")
        for i, (date, value) in enumerate(zip(recent_dates, net_buy_values)):
            status = "净流出" if value < 0 else "净流入"
            print(f"  {date}: {status} {value / 1e4:+.2f} 亿元")

        negative_days = sum(1 for value in net_buy_values if value < 0)
        print("\n评分测试:")
        print(f"  负值天数: {negative_days}/{len(net_buy_values)}")
        if len(net_buy_values) == 3 and negative_days == 3:
            score = 1.0
            print(f"  3日全为负，得分: {score}")
        elif negative_days == 2:
            score = 0.4
            print(f"  2日为负，得分: {score}")
        else:
            score = 0.0
            print(f"  正常情况，得分: {score}")

        print("\n完整数据（最近10日）:")
        display_df = recent.head(10).copy()
        for col in components:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x / 1e4:.2f}亿" if pd.notna(x) else "N/A")
        display_df["margin_balance"] = display_df["margin_balance"].apply(lambda x: f"{x / 1e4:.2f}亿" if pd.notna(x) else "N/A")
        display_df["period_net_purchases"] = display_df["period_net_purchases"].apply(lambda x: f"{x / 1e4:+.2f}亿" if pd.notna(x) else "N/A")
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        cols = ["date"] + components + ["margin_balance", "period_net_purchases"]
        display_df = display_df[cols]
        rename_map = {"date": "日期", "margin_balance": "全市场余额", "period_net_purchases": "日变化"}
        display_df = display_df.rename(columns=rename_map)
        print(display_df.to_string(index=False))

        print("\n" + "=" * 70)
        print("测试完成！")
        print("=" * 70)

    except Exception as exc:
        print(f"\n测试失败: {exc}")
        import traceback
        traceback.print_exc()


def show_info():
    print("\n" + "=" * 70)
    print("Wind Excel 插件融资融券余额字段说明")
    print("=" * 70)
    print("\n常用代码：")
    print(f"{'代码':>10s} | {'名称':>15s} | {'字段':>12s} | {'频率':>8s}")
    print("-" * 60)
    print(f"{'M0061608':>10s} | {'沪市融资融券余额':>15s} | {'EDBclose':>12s} | {'日度':>8s}")
    print(f"{'M0061613':>10s} | {'深市融资融券余额':>15s} | {'EDBclose':>12s} | {'日度':>8s}")
    print(f"{'Z5080762':>10s} | {'北交所融资融券余额':>15s} | {'EDBclose':>12s} | {'日度':>8s}")
    print("\nExcel 原公式（多代码合并）:")
    print(
        '    =WSD("M0061608,M0061613,Z5080762","EDBclose","2025-04-18","当前日期",'
        '"TradingCalendar=SSE","PriceAdj=","rptType=1","Version=1","ShowParams=Y","cols=3;rows=264")'
    )


if __name__ == "__main__":
    test_margin_data()
    show_info()
    print("\n提示:")
    print("  如果测试成功，说明 Wind Excel 插件融资余额数据可用")
    print("  现在可以运行主程序: python escape_top_scorer.py")
