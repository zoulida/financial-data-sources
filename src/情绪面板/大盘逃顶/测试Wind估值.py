"""
测试 Wind Excel 插件获取估值数据
验证 Wind 全A指数 PE 数据获取
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from md.winds.通过excel插件.wind_client import fetch_wind_formula, is_wind_available


def _build_wind_valuation_formula(code, field, start_date, end_date, rows):
    """构造 Wind Excel WSD 估值取数公式。"""
    return (
        f'=WSD("{code}","{field}","{start_date}","{end_date}",'
        f'"ruleType=10","TradingCalendar=SSE","ShowParams=Y","cols=1;rows={rows}")'
    )


def _parse_wind_excel_valuation(raw_df, field_name, start_date):
    """解析 Wind Excel 插件返回的估值数据。"""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["date", field_name])

    df = raw_df.copy()
    date_col = None
    value_col = None

    for col in df.columns:
        parsed_date = pd.to_datetime(df[col], errors="coerce")
        if parsed_date.notna().sum() >= 5:
            date_col = col
            break

    for col in df.columns:
        if col == date_col:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.notna().sum() >= 5:
            value_col = col
            break

    if date_col is not None and value_col is not None:
        result = pd.DataFrame({
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            field_name: pd.to_numeric(df[value_col], errors="coerce"),
        })
    else:
        numeric_values = []
        for col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if not series.empty:
                numeric_values.extend(series.tolist())

        result = pd.DataFrame({
            "date": pd.bdate_range(start=pd.to_datetime(start_date), periods=len(numeric_values)),
            field_name: numeric_values,
        })

    result = result.dropna(subset=["date", field_name]).sort_values("date").reset_index(drop=True)
    return result


def test_wind_valuation():
    """测试 Wind 全A指数 PE 数据获取。"""
    print("=" * 70)
    print("测试 Wind Excel 插件 - Wind全A指数PE数据")
    print("=" * 70)

    try:
        print("\n[1/5] 检查 Wind Excel 插件环境...")
        if not is_wind_available():
            print("  [失败] Wind Excel 插件不可用，或当前环境缺少 win32com/pythoncom")
            return False
        print("  [成功] Wind Excel 插件环境可用")

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365 * 5 + 30)).strftime("%Y-%m-%d")
        rows = 1500
        code = "881001.WI"
        field = "pe"

        print(f"\n[2/5] 获取PE数据...")
        print(f"  指数代码: {code} (Wind全A指数)")
        print(f"  数据字段: {field} (市盈率)")
        print(f"  日期范围: {start_date} 至 {end_date}")
        print(f"  数据方式: Wind Excel 插件 WSD 公式")
        print(f"  参数: ruleType=10, TradingCalendar=SSE, cols=1;rows={rows}")

        formula = _build_wind_valuation_formula(code, field, start_date, end_date, rows)
        raw_df = fetch_wind_formula(formula, timeout=120, interval=0.5, visible=False)

        if raw_df.empty:
            print("\n  [失败] Wind Excel 未返回有效数据")
            return False

        print(f"  [成功] Excel 原始数据获取成功，形状: {raw_df.shape}")

        print(f"\n[3/5] 解析数据...")
        df = _parse_wind_excel_valuation(raw_df, field, start_date)

        print(f"  有效数据点数: {len(df)}")

        if len(df) < 100:
            print(f"  [失败] 数据不足")
            print("\n  原始数据预览:")
            print(raw_df.head(20).to_string())
            return False

        print(f"\n[4/5] 数据预览（最近10个交易日）:")
        print(df.tail(10).to_string())

        current_pe = df.iloc[-1][field]
        current_date = df.iloc[-1]["date"].strftime("%Y-%m-%d")
        min_pe = df[field].min()
        max_pe = df[field].max()
        mean_pe = df[field].mean()

        percentile = (df[field] < current_pe).sum() / len(df) * 100

        print(f"\n[5/5] PE统计信息:")
        print(f"  数据范围: {df.iloc[0]['date'].strftime('%Y-%m-%d')} 至 {current_date}")
        print(f"  交易日数: {len(df)}")
        print(f"  当前PE: {current_pe:.2f}")
        print(f"  近{len(df)}日最小PE: {min_pe:.2f}")
        print(f"  近{len(df)}日最大PE: {max_pe:.2f}")
        print(f"  近{len(df)}日平均PE: {mean_pe:.2f}")
        print(f"  当前百分位: {percentile:.1f}%")

        print(f"\n评分测试（新规则）:")

        if percentile >= 95:
            score = 1.0
            level = "极高估值"
        elif percentile <= 60:
            score = 0.0
            level = "合理估值"
        else:
            score = (percentile - 60) / (95 - 60)
            level = "中等估值"

        print(f"  百分位 {percentile:.1f}% -> 得分: {score:.2f} ({level})")

        print(f"\n评分规则示例:")
        test_percentiles = [50, 60, 70, 80, 90, 95, 98]
        for p in test_percentiles:
            if p >= 95:
                s = 1.0
            elif p <= 60:
                s = 0.0
            else:
                s = (p - 60) / (95 - 60)
            print(f"  百分位 {p:>3.0f}% -> 得分: {s:.2f}")

        print("\n[成功] Wind估值数据测试成功！")
        return True

    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_scoring_rules():
    """对比新旧评分规则。"""
    print("\n" + "=" * 70)
    print("评分规则对比")
    print("=" * 70)

    print("\n旧规则 (v1.0.5):")
    print("  - 百分位<=80% -> 0分")
    print("  - 百分位80%-95% -> 线性插值")
    print("  - 百分位>=95% -> 1分")

    print("\n新规则 (v1.0.6):")
    print("  - 百分位<=60% -> 0分")
    print("  - 百分位60%-95% -> 线性插值")
    print("  - 百分位>=95% -> 1分")

    print("\n变化说明:")
    print("  [改进] 下限从80%降至60%，更早预警")
    print("  [改进] 数据源从akshare改为Wind Excel插件，更可靠")
    print("  [改进] 使用Wind全A指数，更全面")

    print("\n" + "=" * 70)
    print("百分位得分对比表")
    print("=" * 70)

    print(f"\n{'百分位':>10s} | {'旧规则':>10s} | {'新规则':>10s} | {'差异':>10s} | {'说明':>15s}")
    print("-" * 65)

    percentiles = [50, 60, 70, 75, 80, 85, 90, 95, 98]

    for p in percentiles:
        if p >= 95:
            old_score = 1.0
        elif p <= 80:
            old_score = 0.0
        else:
            old_score = (p - 80) / (95 - 80)

        if p >= 95:
            new_score = 1.0
        elif p <= 60:
            new_score = 0.0
        else:
            new_score = (p - 60) / (95 - 60)

        diff = new_score - old_score

        if diff > 0:
            note = "更敏感"
        elif diff < 0:
            note = "更保守"
        else:
            note = "相同"

        print(f"{p:>9.0f}% | {old_score:>10.2f} | {new_score:>10.2f} | {diff:>+10.2f} | {note:>15s}")


if __name__ == "__main__":
    print("\nWind估值数据测试工具")
    print("=" * 70)
    print("测试 Wind Excel 插件获取 Wind 全A指数 PE 数据")
    print("=" * 70)

    success = test_wind_valuation()

    if success:
        compare_scoring_rules()

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)

    if success:
        print("\n提示:")
        print("  [成功] Wind估值数据获取正常")
        print("  [成功] 新规则(60%-95%)比旧规则(80%-95%)更敏感")
        print("  [成功] 建议使用新规则进行逃顶评分")
    else:
        print("\n提示:")
        print("  [提示] 请确保 Wind 终端已启动并登录")
        print("  [提示] 请确保 Excel 已正确加载 Wind 插件")
        print("  [提示] 确保有足够的权限访问 Wind 全A指数数据")
