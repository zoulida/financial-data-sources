import os
import sys
import argparse
import datetime as dt
from typing import List, Optional, Dict, Any
import pandas as pd

from xtdata_fetcher import fetch_daily_bars
from wind_fetcher import fetch_mv_lhb_turn
from filters import seven_day_lurk_base_filter
from ignite_factors import check_chouma_factor, check_topic_factor, check_pankou_factor

# === 七天潜伏主选股流程 ===
# 对应@说明.md中的完整策略流程，涵盖量价、筹码、题材、盘口三因子，精准筛选候选股。

def _parse_date(s: Optional[str]) -> Optional[dt.date]:
    if not s:
        return None
    try:
        if '-' in s:
            return dt.datetime.strptime(s, '%Y-%m-%d').date()
        return dt.datetime.strptime(s, '%Y%m%d').date()
    except Exception:
        return None

def read_universe_from_csv(path: str) -> List[str]:
    df = pd.read_csv(path)
    # 检测股票代码所在列
    code_col = None
    for col in ["code", "Code", "windcode", "WindCode", "证券代码", "股票代码", "代码"]:
        if col in df.columns:
            code_col = col
            break
    if not code_col:
        code_col = df.columns[0]
    codes = df[code_col].astype(str).str.strip()
    # 检查“名称/简称”相关列
    name_cols = [
        c for c in df.columns if any(x in c for x in ["简称", "名称", "全称", "名字"])
    ]
    def is_st_name(name):
        if not isinstance(name, str):
            return False
        s = name.lower().replace('＊','*').replace(' ','').replace('Ｓ','S').replace('Ｔ','T')
        # 检查多种半角/全角/符号组合
        return (
            s.startswith('st') or
            s.startswith('*st') or
            s.startswith('s*st') or
            '*st' in s or
            'st' in s[1:3] or
            'st' in s  # 包含st大概率也是st股
        )
    st_mask = pd.Series([False]*len(df))
    for nc in name_cols:
        st_mask = st_mask | df[nc].astype(str).apply(is_st_name)
    # 过滤：只要60、00开头，且不是ST
    filtered_idx = (codes.str.startswith('60') | codes.str.startswith('00')) & (~st_mask)
    filtered_codes = codes[filtered_idx]
    return [c if '.' in c else (f'{c[:6]}.SH' if c.startswith('6') else f'{c[:6]}.SZ') for c in filtered_codes]

# run_selector主流程
# 1. 读取股票池，过滤ST及非沪深A股
# 2. 拉行情（xtdata优先，见规则）覆盖近80日
# 3. 可选Wind因子：浮动市值、龙虎榜、换手率（筹码）
# 4. 对每个股票依次进行量价基础过滤、筹码因子、题材因子、盘口因子判断
# 5. 满足叠加点火条件>=2的进入最终备选
# 6. 输出csv，字段展开，并输出异常与完整路径
def run_selector(
    universe_csv: str,
    output_csv: Optional[str],
    use_wind: bool,
    end_date: Optional[str],
    top_n: Optional[int]
) -> str:
    codes = read_universe_from_csv(universe_csv)
    if not codes:
        raise ValueError('Universe is empty or unreadable.')
    # 1. 拉行情
    # 根据当前时间判断交易日：21:00之前用昨天，21:00之后用今天
    now = dt.datetime.now()
    if now.hour >= 21:
        trade_date = dt.date.today()
    else:
        trade_date = dt.date.today() - dt.timedelta(days=1)
    today = trade_date.strftime('%Y%m%d')
    N = 80
    end_dt = trade_date
    start_dt = end_dt - dt.timedelta(days=N)
    start_str = '20241101'
    end_str = trade_date.strftime('%Y%m%d')
    bars = fetch_daily_bars(codes, start_date=start_str, end_date=end_str, dividend_type='front', need_download=0)
    # === 先做量价基础过滤，仅通过者进入下一步 ===
    base_passed_codes = []
    base_passed_info = {}
    for code in codes:
        df = bars.get(code)
        if df is None or df.empty:
            continue
        base = seven_day_lurk_base_filter(df)
        if base.get('pass'):
            base_passed_codes.append(code)
            base_passed_info[code] = base
            print(f'[BASE通过] {code} | base: {base}')
    if not base_passed_codes:
        raise ValueError('无通过量价基础过滤的股票')
    # 仅对通过基础量价过滤的股票批量取Wind因子
    wind_data = fetch_mv_lhb_turn(base_passed_codes, end_date if end_date else today) if use_wind else {}
    results: List[Dict[str, Any]] = []
    for code in base_passed_codes:
        df = bars.get(code)
        if df is None or df.empty:
            continue
        base = base_passed_info[code]
        windinfo = wind_data.get(code, {}) if use_wind else {}
        # 打印Wind因子获取状态
        print(f"[WIND因子] {code} float_mv={windinfo.get('float_mv')}, lhb_net={windinfo.get('lhb_net')}, turn_5={windinfo.get('turn_5')}")
        cho_result = check_chouma_factor(
            code,
            wind_mv=windinfo.get('float_mv'),
            lhb_net=windinfo.get('lhb_net'),
            turn_5=windinfo.get('turn_5')
        ) if use_wind else {"pass": False}
        # 题材、盘口留空/可对接具体接口
        topic_result = check_topic_factor(code)  # 需要外部输入具体topic/event
        pankou_result = check_pankou_factor(code)  # 需要外部传l2、盘口资金等
        # 不再作为过滤条件，仅作为数据展示输出到结果CSV
        r = {'code': code, 'base': base, 'chouma': cho_result, 'topic': topic_result, 'pankou': pankou_result}
        results.append(r)
    # 平展输出
    flat = []
    for row in results:
        out = {'code': row['code']}
        out.update({f'base_{k}': v for k, v in row['base'].items()})
        out.update({f'chouma_{k}': v for k, v in row['chouma'].items()})
        out.update({f'topic_{k}': v for k, v in row['topic'].items()})
        out.update({f'pankou_{k}': v for k, v in row['pankou'].items()})
        flat.append(out)
    dfout = pd.DataFrame(flat)
    if top_n and top_n > 0:
        dfout = dfout.head(top_n)
    ts = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = output_csv or os.path.join('data', f'seven_day_lurk_candidates_{ts}.csv')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    dfout.to_csv(out_path, index=False, encoding='utf-8-sig')
    return out_path

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="七天潜伏再涨停候选股筛选器(无任何数据下载逻辑)")
    p.add_argument("--universe", type=str, default=os.path.join(os.getcwd(), "中证全指成分股_20251028.csv"), help="股票池CSV路径，需包含代码列")
    p.add_argument("--output", type=str, default="", help="输出CSV路径（默认写入data目录）")
    p.add_argument("--use-wind", action="store_true", help="启用Wind筹码/资金因子过滤")
    p.add_argument("--end-date", type=str, default="", help="交易日期 YYYYMMDD 或 YYYY-MM-DD，用于Wind快照/换手")
    p.add_argument("--top-n", type=int, default=0, help="仅输出前N名（评分排序）")
    return p

def ensure_csi2000_sample_csv(csv_path="csi2000_test_universe10.csv", sample_n=2000, date="2025-10-30"):
    import os
    if os.path.exists(csv_path):
        return
    try:
        from WindPy import w
        import pandas as pd
        w.start()
        # Wind获取中证2000最新成分股，指数代码为'932000.CSI'
        data = w.wset("sectorconstituent", f"date={date};windcode=932000.CSI")
        print(f"WIND返回: ErrorCode={data.ErrorCode}, Data字段Len={len(data.Data)}")
        if data.ErrorCode == 0 and len(data.Data) > 2:
            codes, names = data.Data[1], data.Data[2]
            df = pd.DataFrame({"证券代码": codes, "证券名称": names})
            test_df = df.sample(n=sample_n, random_state=42)
            test_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"自动下载并生成测试池: {csv_path}")
        else:
            print("Wind接口数据异常, Data=", data.Data)
            raise RuntimeError(f"Wind中证2000成分获取失败，错误码：{data.ErrorCode}")
        w.stop()
    except Exception as e:
        print(f"自动生成csi2000测试池失败: {e}")
        raise

def main() -> None:
    parser = build_arg_parser()
    import sys
    default_csv = "csi2000_test_universe2000.csv"
    if len(sys.argv) == 1:
        # 自动检测并生成池文件
        ensure_csi2000_sample_csv(default_csv)
        universe_csv = default_csv
        output_csv = None
        use_wind = True
        end_date = None
        top_n = None
    else:
        args = parser.parse_args()
        universe_csv = args.universe
        output_csv = args.output if args.output else None
        use_wind = bool(args.use_wind)
        end_date = args.end_date if args.end_date else None
        top_n = args.top_n if args.top_n and args.top_n > 0 else None
    try:
        out_path = run_selector(universe_csv, output_csv, use_wind, end_date, top_n)
        print(f"Saved results: {out_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


