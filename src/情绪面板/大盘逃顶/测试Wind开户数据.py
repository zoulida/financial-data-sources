"""
测试 Wind Excel 插件开户数据获取
验证 M0010401 字段是否正常工作
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
WIND_EXCEL_DIR = ROOT_DIR / "md" / "winds" / "通过excel插件"
if str(WIND_EXCEL_DIR) not in sys.path:
    sys.path.insert(0, str(WIND_EXCEL_DIR))

from wind_client import fetch_wind_formula, is_wind_available

DEFAULT_ACCOUNT_CODE = "M0010401"
DEFAULT_ACCOUNT_NAME = "上证所A股账户新增开户数"
DEFAULT_ACCOUNT_FIELD = "EDBclose"
DEFAULT_ACCOUNT_UNIT = "户"


def _build_edb_formula(code, start_date, end_date, rows=240):
    return (
        f'=EDB("{code}","{start_date}","{end_date}",'
        f'"Fill=Previous","ShowParams=Y","cols=1;rows={rows}")'
    )


def _build_wedb_formula(code, start_date, end_date, rows=240):
    return (
        f'=WEDB("{code}","{start_date}","{end_date}",'
        f'"Fill=Previous","ShowParams=Y","cols=1;rows={rows}")'
    )


def _build_wsd_formula(code, start_date, end_date, rows=240, field=DEFAULT_ACCOUNT_FIELD):
    return (
        f'=WSD("{code}","{field}","{start_date}","{end_date}",'
        f'"TradingCalendar=SSE","PriceAdj=","rptType=1",'
        f'"Version=1","ShowParams=Y","cols=1;rows={rows}")'
    )


def _build_formula_candidates(code, start_date, end_date):
    month_start = pd.to_datetime(start_date).replace(day=1).strftime("%Y-%m-%d")
    return [
        ("WSD", _build_wsd_formula(code, month_start, end_date)),
        ("WSD短窗口", _build_wsd_formula(code, start_date, end_date, rows=24)),
        ("EDB", _build_edb_formula(code, month_start, end_date)),
        ("WEDB", _build_wedb_formula(code, month_start, end_date)),
    ]


def _fetch_account_data(codes, start_date, end_date):
    errors = []
    for code in codes:
        print(f"  正在尝试指标: {code}")
        for name, formula in _build_formula_candidates(code, start_date, end_date):
            print(f"  尝试{name}公式: {formula}")
            try:
                raw_df = fetch_wind_formula(formula, timeout=25, interval=0.5, visible=False)
                parsed = _parse_edb_result(raw_df, start_date)
                if not parsed.empty:
                    print(f"  ✓ {code} {name}公式成功")
                    return raw_df, parsed, formula, code
                errors.append(f"{code} {name}: 返回为空")
            except Exception as exc:
                errors.append(f"{code} {name}: {exc}")
                print(f"  ✗ {code} {name}失败: {exc}")
    raise RuntimeError("开户数据所有公式尝试失败：\n" + "\n".join(errors))


def _parse_edb_result(raw_df, start_date=None):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["date", "value"])

    df = raw_df.copy()
    date_col = None
    value_col = None

    for col in df.columns:
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.notna().sum() >= 2:
            date_col = col
            break

    for col in df.columns:
        if col == date_col:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.notna().sum() >= 2:
            value_col = col
            break

    if date_col is None or value_col is None:
        values = []
        for col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce").dropna()
            if not numeric.empty:
                values.extend(numeric.tolist())
        if not values:
            return pd.DataFrame(columns=["date", "value"])
        fallback_start = pd.to_datetime(start_date).replace(day=1) if start_date else datetime.now()
        result = pd.DataFrame({
            "date": pd.date_range(start=fallback_start, periods=len(values), freq="ME"),
            "value": values,
        })
        return result.sort_values("date", ascending=False).reset_index(drop=True)

    result = pd.DataFrame({
        "date": pd.to_datetime(df[date_col], errors="coerce"),
        "value": pd.to_numeric(df[value_col], errors="coerce"),
    })
    return result.dropna(subset=["date", "value"]).sort_values("date", ascending=False).reset_index(drop=True)

def test_wind_account_data():
    """测试Wind开户数据获取"""
    
    print("=" * 70)
    print("Wind Excel 插件 - 开户数据获取测试")
    print("=" * 70)
    
    try:
        print("\n[1/4] 检查 Wind Excel 插件...")
        if not is_wind_available():
            print("  ✗ Wind Excel 插件不可用，或当前环境缺少 win32com/pythoncom")
            return
        print("  ✓ Wind Excel 插件环境可用")
        
        # 设置日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        print(f"\n[2/4] 获取开户数据...")
        print(f"  日期范围: {start_date} 至 {end_date}")
        print(f"  数据代码: {DEFAULT_ACCOUNT_CODE} ({DEFAULT_ACCOUNT_NAME})")
        print(f"  数据字段: {DEFAULT_ACCOUNT_FIELD}")
        print(f"  数据单位: {DEFAULT_ACCOUNT_UNIT}")
        
        candidate_codes = [DEFAULT_ACCOUNT_CODE, "F5536637", "K7243555", "M0010362"]
        raw_df, df, formula, used_code = _fetch_account_data(candidate_codes, start_date, end_date)
        print(f"  成功指标: {used_code}")
        print(f"  成功公式: {formula}")
        
        print("  ✓ 数据获取成功")
        
        # 解析数据
        print("\n[3/4] 解析数据...")
        
        if df.empty:
            print("  ✗ 返回数据为空")
            print("  原始返回:")
            print(raw_df.to_string())
            return

        print(f"  原始返回形状: {raw_df.shape}")
        print(f"  有效数据点数: {len(df)}")
        
        print(f"  数据范围: {df.iloc[-1]['date'].strftime('%Y-%m')} 至 {df.iloc[0]['date'].strftime('%Y-%m')}")
        
        # 获取最近两个月数据
        print("\n[4/4] 最近两个月开户数:")
        
        if len(df) < 2:
            print("  ✗ 数据不足2个月")
            return
        
        recent_two = df.head(2)
        last_month = float(recent_two.iloc[0]['value'])
        prev_month = float(recent_two.iloc[1]['value'])
        last_date = recent_two.iloc[0]['date'].strftime('%Y-%m')
        prev_date = recent_two.iloc[1]['date'].strftime('%Y-%m')
        
        print(f"  {prev_date}: {prev_month:.2f} {DEFAULT_ACCOUNT_UNIT}")
        print(f"  {last_date}: {last_month:.2f} {DEFAULT_ACCOUNT_UNIT}")
        
        # 计算环比
        if prev_month > 0:
            change_rate = (last_month - prev_month) / prev_month * 100
            decline_rate = -change_rate
            
            print(f"  环比变化: {change_rate:+.1f}%")
            print(f"  环比降幅: {decline_rate:.1f}%")
            
            # 评分测试
            print(f"\n评分测试（新规则）:")
            if decline_rate >= 30:
                score = 1.5
                print(f"  降幅 ≥30% → 得分: {score:.2f} ⚠️⚠️ 强烈逃顶信号")
            elif decline_rate > 0:
                score = decline_rate / 30.0 * 1.5
                print(f"  降幅 {decline_rate:.1f}% → 得分: {score:.2f}")
            else:
                score = 0.0
                print(f"  降幅 {decline_rate:.1f}% → 得分: {score:.2f} ✓ 正常")
        
        # 显示最近6个月数据
        print(f"\n最近6个月开户数据:")
        display_df = df.head(6).copy()
        display_df['date_str'] = display_df['date'].dt.strftime('%Y-%m')
        display_df['value_str'] = display_df['value'].apply(lambda x: f"{x:.2f}{DEFAULT_ACCOUNT_UNIT}")
        
        print(f"{'日期':>10s} | {'新增开户数':>15s}")
        print("-" * 30)
        for _, row in display_df.iterrows():
            print(f"{row['date_str']:>10s} | {row['value_str']:>15s}")
        
        # 趋势分析
        print(f"\n趋势分析:")
        recent_6 = df.head(6)['value'].tolist()
        avg_6 = sum(recent_6) / len(recent_6)
        current = recent_6[0]
        
        if current < avg_6 * 0.7:
            print(f"  ⚠️⚠️ 当前开户数({current:.2f}{DEFAULT_ACCOUNT_UNIT})远低于近6个月平均({avg_6:.2f}{DEFAULT_ACCOUNT_UNIT})")
            print(f"      散户入市热情极度低迷")
        elif current < avg_6:
            print(f"  ⚠️ 当前开户数({current:.2f}{DEFAULT_ACCOUNT_UNIT})低于近6个月平均({avg_6:.2f}{DEFAULT_ACCOUNT_UNIT})")
            print(f"     散户入市热情下降")
        else:
            print(f"  ✓ 当前开户数({current:.2f}{DEFAULT_ACCOUNT_UNIT})高于近6个月平均({avg_6:.2f}{DEFAULT_ACCOUNT_UNIT})")
            print(f"    散户入市热情正常或升温")
        
        print("\n" + "=" * 70)
        print("测试完成！")
        print("=" * 70)
        
        print("\n✓ Wind Excel 插件取数完成")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def show_wind_edb_info():
    """显示Wind经济数据库字段信息"""
    
    print("\n" + "=" * 70)
    print("Wind Excel 插件 EDB 开户数据字段说明")
    print("=" * 70)
    
    print("\n常用字段:")
    print(f"{'字段代码':>12s} | {'字段名称':>20s} | {'单位':>8s} | {'频率':>8s}")
    print("-" * 70)
    print(f"{'M0010362':>12s} | {'深交所投资者开户总数':>20s} | {'万户':>8s} | {'月度':>8s}")
    print(f"{'M0010342':>12s} | {'上证所投资者开户总数':>20s} | {'万户':>8s} | {'年度':>8s}")
    print(f"{'M0010401':>12s} | {'上证所A股账户新增开户数':>20s} | {'户':>8s} | {'月度':>8s}")
    print(f"{'M0067863':>12s} | {'中登上海新增开户投资者数:个人':>20s} | {'户':>8s} | {'月度':>8s}")
    print(f"{'M0001780':>12s} | {'新增A股账户数':>20s} | {'万户':>8s} | {'月度':>8s}")
    print(f"{'M0001781':>12s} | {'期末投资者总数':>20s} | {'万户':>8s} | {'月度':>8s}")
    
    print("\n推荐使用: M0010401 (上证所A股账户新增开户数)")
    print("  - 数据最新")
    print("  - 包含所有类型投资者")
    print("  - 月度更新")
    
    print("\nWind Excel 插件公式示例:")
    print("""
    =WSD("M0010401","EDBclose","2025-07-01","2025-10-20","TradingCalendar=SSE","PriceAdj=","rptType=1","Version=1","ShowParams=Y","cols=1;rows=12")
    """)


if __name__ == "__main__":
    # 运行测试
    test_wind_account_data()
    
    # 显示字段信息
    show_wind_edb_info()
    
    print("\n提示:")
    print("  如果测试成功，说明 Wind Excel 插件配置正确")
    print("  现在可以运行主程序: python escape_top_scorer.py")

