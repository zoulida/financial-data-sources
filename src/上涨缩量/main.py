import sys
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import math
import numpy as np
import pandas as pd

# 项目根路径与工具路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# 合并下载数据模块路径
MERGE_DL_PATH = PROJECT_ROOT / "md" / "合并下载数据"
if MERGE_DL_PATH.exists() and str(MERGE_DL_PATH) not in sys.path:
    sys.path.insert(0, str(MERGE_DL_PATH))

# Wind（禁用）
w = None
WIND_AVAILABLE = False

# 日期范围
try:
    from md.获取enddate.get_date_range import get_date_range
except Exception:
    def get_date_range():
        end = datetime.now()
        start = end - timedelta(days=600)
        return start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), "fallback"

# 合并下载数据
getDayData = None
batchDownloadDayData = None
try:
    from source.实盘.xuntou.datadownload.合并下载数据 import getDayData as _getDayData, batchDownloadDayData as _batchDownloadDayData  # type: ignore
    getDayData = _getDayData
    batchDownloadDayData = _batchDownloadDayData
except Exception:
    pass

# xtquant 兜底
_xt_ok = False
try:
    from xtquant import xtdata
    _xt_ok = True
except Exception:
    _xt_ok = False


def _wind_start():
    # 已禁用Wind，留空占位
    pass

def _get_universe_with_basics(end_date: str) -> pd.DataFrame:
    """使用 xtdata 获取A股股票池与市值/流通股本（不依赖Wind）。名称与ST过滤延后处理。"""
    if not _xt_ok:
        raise RuntimeError("xtdata不可用，无法获取基础信息")

    # 获取全部A股代码
    print("获取板块代码...")
    try:
        #xtdata.download_sector_data()
        pass
    except Exception:
        pass
    try:
        codes_all = xtdata.get_stock_list_in_sector('沪深A股') or []
    except Exception:
        codes_all = []

    # 仅保留 00/60 开头
    codes = [c for c in codes_all if isinstance(c, str) and c.startswith(("00", "60"))]
    debug_max = int(os.environ.get("DEBUG_MAX_CODES", "0") or 0)
    if debug_max > 0:
        codes = codes[:debug_max]
    print(f"股票数: {len(codes)}")

    # 暂不获取名称（加速），名称与ST过滤在结果阶段再做
    df = pd.DataFrame({"code": codes})

    codes = df["code"].tolist()
    if not codes:
        return df.assign(market_cap=np.nan, free_float=np.nan)

    print("获取Tick最新价与流通股本...")
    market_caps, free_floats = [], []
    try:
        ticks = xtdata.get_full_tick(codes)
    except Exception:
        ticks = {}

    last_prices = []
    for c in codes:
        mv = np.nan
        ff = np.nan
        close = np.nan
        try:
            tick = ticks.get(c) if isinstance(ticks, dict) else None
            if isinstance(tick, pd.DataFrame) and not tick.empty:
                if 'lastPrice' in tick.columns:
                    close = pd.to_numeric(tick['lastPrice'].iloc[-1], errors='coerce')
                elif 'price' in tick.columns:
                    close = pd.to_numeric(tick['price'].iloc[-1], errors='coerce')
                elif 'close' in tick.columns:
                    close = pd.to_numeric(tick['close'].iloc[-1], errors='coerce')
            elif isinstance(tick, dict):
                for k in ['lastPrice', 'price', 'close', 'LastPrice', 'Price', 'Close']:
                    v = pd.to_numeric(tick.get(k, np.nan), errors='coerce')
                    if pd.notna(v) and v > 0:
                        close = float(v)
                        break

            info = xtdata.get_instrument_detail(c)
            if isinstance(info, dict):
                ff = pd.to_numeric(info.get('FloatVolume', np.nan), errors='coerce')

            if pd.notna(ff) and ff > 0 and pd.notna(close) and close > 0:
                mv = float(ff) * float(close) / 1e8
        except Exception:
            pass
        market_caps.append(mv)
        free_floats.append(ff)
        last_prices.append(float(close) if pd.notna(close) else np.nan)

    df["market_cap"] = market_caps
    df["free_float"] = free_floats
    df["last_price"] = last_prices

    pre = len(df)
    df = df[(df["last_price"] >= 3.0) & (df["last_price"] <= 18.0)].reset_index(drop=True)
    print(f"价格过滤: {pre} -> {len(df)}")
    # 市值区间过滤 [30亿, 200亿)
    pre = len(df)
    df = df[(df["market_cap"] >= 30.0) & (df["market_cap"] < 200.0)].reset_index(drop=True)
    print(f"市值过滤(亿元): {pre} -> {len(df)}")
    return df


def _fetch_kline_dict(codes, start_date: str, end_date: str) -> dict:
    result = {}
    print("尝试读取本地K线缓存...")
    if batchDownloadDayData is not None:
        try:
            result = batchDownloadDayData(stock_codes=codes, start_date=start_date, end_date=end_date, dividend_type="front", need_download=0)
            if isinstance(result, dict) and result:
                print(f"命中缓存: {len(result)}")
                return result
        except Exception:
            pass
    print("批量获取K线(xtdata)...")
    if _xt_ok:
        try:
            all_data = xtdata.get_market_data_ex([], codes, period="1d", start_time=start_date, end_time=end_date, count=-1, dividend_type='front')
            if isinstance(all_data, dict) and len(all_data) > 0:
                for code in codes:
                    df = all_data.get(code)
                    if df is not None and not df.empty:
                        df = df.reset_index().rename(columns={"index": "date"})
                        df = df.sort_values("date").reset_index(drop=True)
                        result[code] = df
                if result:
                    print(f"xtdata批量获取: {len(result)}")
                    return result
        except Exception:
            pass
    print("逐只获取K线...")
    # 兜底：逐只读取或xtdata
    for code in codes:
        df = None
        if getDayData is not None:
            try:
                df = getDayData(stock_code=code, start_date=start_date, end_date=end_date, is_download=0, dividend_type="front")
            except Exception:
                df = None
        if df is None and _xt_ok:
            try:
                data = xtdata.get_market_data_ex([], [code], period="1d", start_time=start_date, end_time=end_date, count=-1, dividend_type='front')
                if code in data:
                    df = data[code].reset_index().rename(columns={"index": "date"})
            except Exception:
                df = None
        if isinstance(df, pd.DataFrame) and not df.empty:
            df = df.sort_values("date").reset_index(drop=True)
            result[code] = df
    return result


def _calc_metrics(df: pd.DataFrame, free_float: float) -> dict:
    df = df.copy()
    for c in ["open", "high", "low", "close", "volume", "amount"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    if len(df) < 180:
        return {}

    df["preclose"] = df["close"].shift(1)
    df["ret"] = df["close"] / df["preclose"] - 1
    df["yang"] = (df["close"] > df["open"]).astype(int)
    df["amp_day"] = (df["high"] - df["low"]) / df["preclose"]

    # 120日整理
    df120 = df.tail(120)
    if len(df120) < 120:
        return {}
    max_c = df120["close"].max()
    min_c = df120["close"].min()
    amplitude_120 = (max_c - min_c) / min_c if min_c > 0 else np.nan
    small_amp_days = (df120["amp_day"] <= 0.05).sum()

    # 最近5日
    df5 = df.tail(5)
    yang_5 = int(df5["yang"].sum())
    cum_5 = df5["close"].iloc[-1] / df5["close"].iloc[0] - 1
    avg_vol_5 = float(df5["volume"].mean()) if "volume" in df5.columns else np.nan
    avg_vol_120 = float(df120["volume"].mean()) if "volume" in df120.columns else np.nan
    avg_turn_5 = (avg_vol_5 / free_float * 100.0) if free_float and free_float > 0 and not math.isnan(avg_vol_5) else np.nan

    # MA 偏离
    ma120 = df120["close"].mean()
    ma20 = df.tail(20)["close"].mean() if len(df) >= 20 else np.nan
    last_close = df["close"].iloc[-1]
    dev_ma120 = last_close / ma120 - 1 if ma120 and ma120 > 0 else np.nan
    dev_ma20 = last_close / ma20 - 1 if ma20 and ma20 > 0 else np.nan

    # 250日 7%阳线次数
    df250 = df.tail(250)
    cnt_7pct_up = int(((df250["ret"] >= 0.07) & (df250["yang"] == 1)).sum()) if len(df250) > 0 else 0

    # 60日均换手
    df60 = df.tail(60)
    avg_turn_60 = (float(df60["volume"].mean()) / free_float * 100.0) if free_float and free_float > 0 and "volume" in df60.columns else np.nan

    # 最近5日是否有跌停(主板10%)
    limit_down = False
    if len(df) >= 2:
        df5_tmp = df.tail(5).copy()
        df5_tmp["ret"] = df5_tmp["close"] / df5_tmp["preclose"] - 1
        limit_down = bool(((df5_tmp["ret"] <= -0.099) & (np.isclose(df5_tmp["close"], df5_tmp["low"])) ).any())

    return {
        "amplitude_120": amplitude_120,
        "small_amp_days_120": int(small_amp_days),
        "yang_5": yang_5,
        "cum_ret_5": float(cum_5),
        "avg_turn_5": float(avg_turn_5) if not pd.isna(avg_turn_5) else np.nan,
        "avg_vol_5": avg_vol_5,
        "avg_vol_120": avg_vol_120,
        "dev_ma120": float(dev_ma120) if not pd.isna(dev_ma120) else np.nan,
        "dev_ma20": float(dev_ma20) if not pd.isna(dev_ma20) else np.nan,
        "cnt_7pct_up_250": cnt_7pct_up,
        "avg_turn_60": float(avg_turn_60) if not pd.isna(avg_turn_60) else np.nan,
        "limit_down_recent5": limit_down,
    }


def _apply_filters(m: dict) -> bool:
    if not m:
        return False
    # 长期整理
    if not (m.get("amplitude_120") is not None and m["amplitude_120"] <= 0.20 and m.get("small_amp_days_120", 0) >= 80):
        return False
    # 无量上涨（阳线3根+，累计涨幅3%-10%，且5日均换手<=1.2% 或 5日均量<=120日均量的0.9倍）
    cond_yang = m.get("yang_5", 0) >= 3
    cond_ret = (m.get("cum_ret_5") is not None) and (0.03 <= m["cum_ret_5"] <= 0.10)
    turn5 = m.get("avg_turn_5")
    vol5 = m.get("avg_vol_5")
    vol120 = m.get("avg_vol_120")
    cond_turn = (turn5 is not None) and (not pd.isna(turn5)) and (turn5 <= 1.2)
    cond_vol = (vol5 is not None) and (vol120 is not None) and (not pd.isna(vol5)) and (not pd.isna(vol120)) and (vol5 <= 0.9 * vol120)
    if not (cond_yang and cond_ret and (cond_turn or cond_vol)):
        return False
    # 涨幅不大
    if not ((m.get("dev_ma120") is not None and m["dev_ma120"] <= 0.15) and (m.get("dev_ma20") is not None and m["dev_ma20"] <= 0.08)):
        return False
    # 股性较好
    if not (m.get("cnt_7pct_up_250", 0) >= 3 and (m.get("avg_turn_60") is not None) and (not pd.isna(m["avg_turn_60"])) and m["avg_turn_60"] >= 1.0):
        return False
    # 过滤最近5日有跌停
    if m.get("limit_down_recent5"):
        return False
    return True


def select_stocks(save_csv: bool = True) -> pd.DataFrame:
    t0 = time.time()
    start_date, end_date, reason = get_date_range()
    print(f"日期区间: {start_date} ~ {end_date}")
    print(f"原因: {reason}")
    basics = _get_universe_with_basics(end_date)
    if basics.empty:
        return pd.DataFrame(columns=["code", "name", "amplitude_120", "cum_ret_5", "avg_turn_5", "cnt_7pct_up_250", "market_cap"]) 

    codes = basics["code"].tolist()
    print(f"进入K线阶段: {len(codes)}")
    kline_dict = _fetch_kline_dict(codes, start_date, end_date)

    rows = []
    for _, row in basics.iterrows():
        code = row["code"]
        name = row.get("name") if "name" in basics.columns else code
        free_float = float(row["free_float"]) if not pd.isna(row["free_float"]) else np.nan
        mktcap = float(row["market_cap"]) if not pd.isna(row["market_cap"]) else np.nan
        df = kline_dict.get(code)
        if df is None or df.empty:
            continue
        eff_free_float = free_float
        if (pd.isna(eff_free_float) or eff_free_float <= 0) and (not pd.isna(mktcap)):
            try:
                last_close_val = pd.to_numeric(df["close"].iloc[-1], errors="coerce")
                if last_close_val and last_close_val > 0:
                    eff_free_float = float(mktcap) * 1e8 / float(last_close_val)
            except Exception:
                pass
        metrics = _calc_metrics(df, eff_free_float)
        if not metrics:
            continue
        if _apply_filters(metrics):
            rows.append({
                "code": code,
                "name": name,
                "amplitude_120": metrics["amplitude_120"],
                "cum_ret_5": metrics["cum_ret_5"],
                "avg_turn_5": metrics.get("avg_turn_5", np.nan),
                "cnt_7pct_up_250": metrics["cnt_7pct_up_250"],
                "market_cap": mktcap,
            })

    result = pd.DataFrame(rows)
    if not result.empty:
        # 获取名称并进行ST过滤
        names = []
        for c in result["code"].tolist():
            nm = c
            try:
                if _xt_ok:
                    info = xtdata.get_instrument_detail(c)
                    if isinstance(info, dict):
                        nm = info.get('InstrumentName', '') or c
            except Exception:
                pass
            names.append(nm)
        result["name"] = names
        pre_cnt = len(result)
        result = result[~result["name"].str.contains("ST", na=False)].copy()
        if pre_cnt != len(result):
            print(f"ST过滤: {pre_cnt} -> {len(result)}")
        result = result.sort_values(["amplitude_120", "cum_ret_5"], ascending=[True, True]).reset_index(drop=True)
    if save_csv:
        out_dir = PROJECT_ROOT / "data" / "result"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"上涨缩量_选股_{end_date}.csv"
        try:
            result.to_csv(out_file, index=False, encoding="utf-8-sig")
        except Exception:
            pass
    print(f"完成，用时 {time.time()-t0:.1f}s，结果数 {len(result)}")
    return result


if __name__ == "__main__":
    df = select_stocks(save_csv=True)
    print(f"候选股票数: {len(df)}")
    if not df.empty:
        print(df.head(30))
