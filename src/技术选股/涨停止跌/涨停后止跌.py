import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import importlib.util
import numpy as np
import pandas as pd

# ========== 路径初始化 ==========
# 项目根路径与合并下载数据路径注入，确保与参考脚本一致
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
MERGE_DL_PATH = PROJECT_ROOT / "md" / "合并下载数据"
if MERGE_DL_PATH.exists() and str(MERGE_DL_PATH) not in sys.path:
    sys.path.insert(0, str(MERGE_DL_PATH))

# ========== 动态加载参考函数 ==========
# 从 src/技术选股/上涨缩量/main.py 加载 get_universe_with_basics 与 _fetch_kline_dict
_REF_MODULE = None

def _load_ref_module():
    global _REF_MODULE
    if _REF_MODULE is not None:
        return _REF_MODULE
    ref_file = PROJECT_ROOT / "src" / "技术选股" / "上涨缩量" / "main.py"
    if not ref_file.exists():
        raise FileNotFoundError(f"未找到参考模块: {ref_file}")
    spec = importlib.util.spec_from_file_location("up_on_small_vol_main", str(ref_file))
    if spec is None or spec.loader is None:
        raise ImportError("无法加载参考模块spec")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    _REF_MODULE = mod
    return mod


def _get_universe_with_basics(end_date: str) -> pd.DataFrame:
    mod = _load_ref_module()
    return mod.get_universe_with_basics(end_date)


def _fetch_kline_dict(codes, start_date: str, end_date: str) -> dict:
    mod = _load_ref_module()
    return mod._fetch_kline_dict(codes, start_date, end_date)


# ========== 工具函数 ==========

def _to_yyyymmdd(s: str | None) -> str:
    """将 'YYYY-MM-DD' 或 'YYYYMMDD' 统一为 'YYYYMMDD'。若 s 为空，返回今日。"""
    if not s:
        return datetime.now().strftime("%Y%m%d")
    s = s.strip()
    if len(s) == 8 and s.isdigit():
        return s
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%Y%m%d")
    except Exception:
        # 兜底：尝试其他格式
        try:
            return datetime.strptime(s, "%Y/%m/%d").strftime("%Y%m%d")
        except Exception:
            return datetime.now().strftime("%Y%m%d")


def _start_date_from(end_date: str, back_days: int = 120) -> str:
    """从 end_date 往前回溯 back_days 天（自然日）得到 start_date。"""
    try:
        dt = datetime.strptime(end_date, "%Y%m%d")
    except Exception:
        dt = datetime.now()
    start_dt = dt - timedelta(days=back_days)
    return start_dt.strftime("%Y%m%d")


def _check_conditions(df: pd.DataFrame) -> tuple[bool, dict]:
    """
    条件筛选：
    1）前30交易日内存在单日涨幅 >= 8%
    2）最近5日内存在连续下跌 >= 3 天，且5日累计跌幅 <= -3%
    3）今日（最后一个交易日）涨跌幅 > -1%
    返回 (是否满足, 度量字典)
    """
    if df is None or df.empty:
        return False, {}
    df = df.copy()
    # 字段转数值
    for c in ["open", "high", "low", "close", "volume", "amount"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    if len(df) < 40:
        return False, {}
    df["preclose"] = df["close"].shift(1)
    df = df.dropna(subset=["preclose"]).reset_index(drop=True)
    if df.empty:
        return False, {}
    df["ret"] = df["close"] / df["preclose"] - 1

    # 1) 前30日（不含今日）是否存在单日涨幅>=8%
    if len(df) < 31:
        return False, {}
    last_30 = df.iloc[-31:-1]  # 排除最后一天
    cond1 = bool((last_30["ret"] >= 0.08).any())

    # 2) 最近5日 连续下跌>=3 且 5日累计跌幅<=-3%
    df5 = df.tail(5)
    if len(df5) < 5:
        return False, {}
    ret5 = df5["ret"].tolist()
    # 统计连续为负的最长长度
    max_streak = 0
    cur = 0
    for r in ret5:
        if pd.notna(r) and r < 0:
            cur += 1
            max_streak = max(max_streak, cur)
        else:
            cur = 0
    cond2_streak = max_streak >= 3
    cum5 = float(df5["close"].iloc[-1] / df5["close"].iloc[0] - 1)
    cond2_drop = cum5 <= -0.03
    cond2 = cond2_streak and cond2_drop

    # 3) 今日涨跌幅 > -1%
    today_ret = float(df["ret"].iloc[-1]) if pd.notna(df["ret"].iloc[-1]) else np.nan
    cond3 = pd.notna(today_ret) and (today_ret > -0.01)

    ok = cond1 and cond2 and cond3
    metrics = {
        "has_8pct_up_in_30d": cond1,
        "max_down_streak_5d": int(max_streak),
        "cum_ret_5d": float(cum5),
        "ret_today": float(today_ret) if pd.notna(today_ret) else np.nan,
    }
    return ok, metrics


def select_stocks(end_date: str | None = None, save_csv: bool = True) -> pd.DataFrame:
    """筛选“涨停后止跌”候选股。
    参数：
    - end_date: 结束日期，'YYYYMMDD' 或 'YYYY-MM-DD'；默认取今天。
    - save_csv: 是否保存CSV到 data/result。
    返回：DataFrame
    """
    mod = _load_ref_module()
    start_date, end_date, reason = mod.get_date_range()

    print(f"日期区间: {start_date} ~ {end_date}")
    # 1) 获取基础股票池（价格/市值已内置限制）
    basics = _get_universe_with_basics(end_date)
    if basics is None or basics.empty:
        print("基础股票池为空")
        return pd.DataFrame(columns=["code", "has_8pct_up_in_30d", "max_down_streak_5d", "cum_ret_5d", "ret_today"]) 

    codes = basics["code"].dropna().astype(str).tolist()
    print(f"进入K线阶段，股票数: {len(codes)}")

    # 2) 获取K线
    kline_dict = _fetch_kline_dict(codes, start_date, end_date)

    # 3) 逐只计算与过滤
    rows = []
    for _, row in basics.iterrows():
        code = str(row["code"]).strip()
        if not code:
            continue
        df = kline_dict.get(code)
        if df is None or df.empty:
            continue
        # 排序
        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)
        ok, m = _check_conditions(df)
        if ok:
            rows.append({
                "code": code,
                "has_8pct_up_in_30d": m.get("has_8pct_up_in_30d", False),
                "max_down_streak_5d": m.get("max_down_streak_5d", np.nan),
                "cum_ret_5d": m.get("cum_ret_5d", np.nan),
                "ret_today": m.get("ret_today", np.nan),
            })

    result = pd.DataFrame(rows)

    # 4) 保存CSV
    if save_csv:
        out_dir = PROJECT_ROOT / "data" / "result"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"涨停后止跌_选股_{end_date}.csv"
        try:
            result.to_csv(out_file, index=False, encoding="utf-8-sig")
            print(f"结果已保存: {out_file}")
        except Exception as e:
            print(f"保存CSV失败: {e}")

    print(f"完成，结果数: {len(result)}")
    return result


def _build_arg_parser():
    parser = argparse.ArgumentParser(description="涨停后止跌 选股")
    parser.add_argument("--date", type=str, default=None, help="结束日期，YYYYMMDD 或 YYYY-MM-DD；默认今天")
    parser.add_argument("--no-save", action="store_true", help="不保存CSV")
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    df = select_stocks(end_date=args.date, save_csv=(not args.no_save))
    print(f"候选股票数: {len(df)}")
    if not df.empty:
        print(df.head(30))

