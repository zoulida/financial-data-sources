import os
import math
import json
import datetime as dt
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.preprocessing import QuantileTransformer

try:
    from xtquant import xtdata
except Exception:
    xtdata = None


def _to_date(s: str) -> dt.date:
    if isinstance(s, dt.date):
        return s
    if isinstance(s, dt.datetime):
        return s.date()
    s = str(s).replace("-", "")
    return dt.datetime.strptime(s, "%Y%m%d").date()


def get_a_share_codes() -> List[str]:
    if xtdata is None:
        raise RuntimeError("xtdata 未安装或初始化失败")
    codes = xtdata.get_stock_list_in_sector("沪深A股")
    codes = [c for c in codes if not (c.startswith("83") or c.startswith("87"))]
    return codes


def get_instrument_info(code: str) -> Dict:
    if xtdata is None:
        return {}
    try:
        return xtdata.get_instrument_detail(code) or {}
    except Exception:
        return {}


def is_st_stock(code: str) -> bool:
    info = get_instrument_info(code)
    name = str(info.get("InstrumentName", ""))
    return "ST" in name.upper() or "*ST" in name.upper()


def ipo_days_ok(code: str, on_date: dt.date, min_calendar_days: int = 180) -> bool:
    info = get_instrument_info(code)
    ipostr = info.get("OpenDate") or info.get("CreateDate")
    if not ipostr:
        return True
    ipostr = str(ipostr).replace("-", "")
    try:
        ipo_date = dt.datetime.strptime(ipostr, "%Y%m%d").date()
        return (on_date - ipo_date).days >= min_calendar_days
    except Exception:
        return True


def board_limit_ratio(code: str) -> float:
    if code.startswith(("300", "301", "688", "689")):
        return 0.20
    return 0.10


def at_limit_up(pre_close: float, close: float, code: str, price_tick: float = 0.01) -> bool:
    if pre_close <= 0 or close <= 0:
        return False
    r = board_limit_ratio(code)
    limit_px = pre_close * (1 + r)
    limit_px = math.floor(limit_px / price_tick + 1e-6) * price_tick
    return close >= limit_px - (price_tick + 1e-9)


def fetch_daily_bars(codes: List[str], start: str, end: str) -> Dict[str, pd.DataFrame]:
    if xtdata is None:
        raise RuntimeError("xtdata 未安装或初始化失败")
    fields = ["open", "high", "low", "close", "volume", "amount", "preClose"]
    data = {}
    batch = 200
    for i in range(0, len(codes), batch):
        sub = codes[i:i + batch]
        try:
            ret = xtdata.get_market_data_ex(
                field_list=fields, stock_list=sub, period="1d", start_time=start, end_time=end
            )
        except Exception:
            ret = None
        if not ret:
            continue
        for f in fields:
            if f not in ret:
                continue
            ret[f] = ret[f].sort_index()
        for code in sub:
            df = pd.DataFrame({f: (ret.get(f, pd.DataFrame())).get(code) for f in fields})
            if df is None or df.empty:
                continue
            df = df.dropna()
            df.index = pd.to_datetime(df.index).date
            data[code] = df
    return data


def add_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["pct_chg"] = out["close"].pct_change().fillna(0.0)
    out["ret1"] = out["close"].pct_change().fillna(0.0)
    out["ret5"] = out["close"].pct_change(5)
    out["ret10"] = out["close"].pct_change(10)
    out["ret20"] = out["close"].pct_change(20)
    out["amplitude"] = (out["high"] - out["low"]) / out["preClose"].replace(0, np.nan)
    out["open_gap"] = out["open"] / out["preClose"].replace(0, np.nan) - 1
    out["upper_shadow"] = (out["high"] - out["close"]) / out["close"].replace(0, np.nan)
    out["lower_shadow"] = (out["close"] - out["low"]) / out["close"].replace(0, np.nan)
    out["vr5"] = out["volume"] / out["volume"].rolling(5).mean()
    out["vr10"] = out["volume"] / out["volume"].rolling(10).mean()
    out["ar5"] = out["amount"] / out["amount"].rolling(5).mean()
    out["ar10"] = out["amount"] / out["amount"].rolling(10).mean()
    out["max20"] = out["close"].rolling(20).max()
    out["max60"] = out["close"].rolling(60).max()
    out["max120"] = out["close"].rolling(120).max()
    out["max250"] = out["close"].rolling(250).max()
    out["to20h"] = out["close"] / out["max20"] - 1
    out["to120h"] = out["close"] / out["max120"] - 1
    out["to250h"] = out["close"] / out["max250"] - 1
    out["ret_std5"] = out["ret1"].rolling(5).std()
    out["ret_std20"] = out["ret1"].rolling(20).std()
    return out.replace([np.inf, -np.inf], np.nan)


def detect_limit_flags(df: pd.DataFrame, code: str) -> pd.Series:
    pre = df["preClose"].shift(0)
    close = df["close"]
    price_tick = 0.01
    flags = []
    for pc, c in zip(pre.values, close.values):
        flags.append(at_limit_up(pc, c, code, price_tick))
    s = pd.Series(flags, index=df.index)
    return s


def limit_streak(series: pd.Series) -> pd.Series:
    arr = series.astype(int).values
    streak = np.zeros_like(arr)
    run = 0
    for i, v in enumerate(arr):
        if v:
            run += 1
        else:
            run = 0
        streak[i] = run
    return pd.Series(streak, index=series.index)


def build_events(daily: Dict[str, pd.DataFrame], begin_year: int = 2017) -> pd.DataFrame:
    rows = []
    for code, df in daily.items():
        if df.empty:
            continue
        df2 = add_derived_fields(df)
        lim = detect_limit_flags(df2, code)
        streak = limit_streak(lim)
        dates = list(df2.index)
        for i in range(2, len(df2) - 1):
            d = dates[i]
            if d.year < begin_year:
                continue
            if lim.iloc[i] and streak.iloc[i] >= 2 and not is_st_stock(code) and ipo_days_ok(code, d):
                y = bool(lim.iloc[i + 1])
                r = {
                    "code": code,
                    "date": d,
                    "y": int(y),
                    "pct_chg_t": float(df2["pct_chg"].iloc[i]),
                    "pct_chg_t_1": float(df2["pct_chg"].iloc[i - 1]),
                    "open_gap": float(df2["open_gap"].iloc[i]),
                    "amplitude": float(df2["amplitude"].iloc[i]),
                    "upper_shadow": float(df2["upper_shadow"].iloc[i]),
                    "lower_shadow": float(df2["lower_shadow"].iloc[i]),
                    "vr5": float(df2["vr5"].iloc[i]),
                    "vr10": float(df2["vr10"].iloc[i]),
                    "ar5": float(df2["ar5"].iloc[i]),
                    "ar10": float(df2["ar10"].iloc[i]),
                    "ret5": float(df2["ret5"].iloc[i]),
                    "ret10": float(df2["ret10"].iloc[i]),
                    "ret20": float(df2["ret20"].iloc[i]),
                    "ret_std5": float(df2["ret_std5"].iloc[i]),
                    "ret_std20": float(df2["ret_std20"].iloc[i]),
                    "to20h": float(df2["to20h"].iloc[i]),
                    "to120h": float(df2["to120h"].iloc[i]),
                    "to250h": float(df2["to250h"].iloc[i]),
                    "streak": int(streak.iloc[i]),
                }
                rows.append(r)
    if not rows:
        return pd.DataFrame()
    ev = pd.DataFrame(rows)
    ev["ym"] = ev["date"].apply(lambda d: f"{d.year}-{d.month:02d}")
    return ev


def quantile_scale_df(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    qt = QuantileTransformer(n_quantiles=min(1000, max(10, len(df))), output_distribution="uniform", subsample=int(1e6), random_state=42)
    scaled = df[cols].copy()
    scaled[:] = qt.fit_transform(scaled.fillna(scaled.median()))
    for c in cols:
        df[c + "_q"] = scaled[c]
    return df


def split_sets(ev: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = ev[(ev["date"] >= dt.date(2017, 1, 1)) & (ev["date"] <= dt.date(2022, 12, 31))]
    valid = ev[(ev["date"] >= dt.date(2023, 1, 1)) & (ev["date"] <= dt.date(2023, 12, 31))]
    test = ev[(ev["date"] >= dt.date(2024, 1, 1))]
    return train, valid, test


def train_logit(train: pd.DataFrame, valid: pd.DataFrame, feat_cols: List[str]) -> LogisticRegression:
    Xtr = train[feat_cols].values
    ytr = train["y"].values
    Xva = valid[feat_cols].values
    yva = valid["y"].values
    model = LogisticRegression(penalty="l1", solver="saga", C=1.0, max_iter=2000, n_jobs=1, class_weight="balanced", random_state=42)
    model.fit(Xtr, ytr)
    if len(np.unique(yva)) > 1:
        p = model.predict_proba(Xva)[:, 1]
        try:
            auc = roc_auc_score(yva, p)
        except Exception:
            auc = np.nan
        try:
            pr = average_precision_score(yva, p)
        except Exception:
            pr = np.nan
        print(json.dumps({"valid_auc": float(auc) if not np.isnan(auc) else None, "valid_pr_auc": float(pr) if not np.isnan(pr) else None}, ensure_ascii=False))
    return model


def evaluate_daily_topk(ev: pd.DataFrame, probs: np.ndarray, top_ratio: float = 0.10) -> Dict:
    df = ev[["code", "date", "y"]].copy()
    df["p"] = probs
    g = df.groupby("date")
    hits = []
    daily_sel = []
    for d, sub in g:
        k = max(1, int(len(sub) * top_ratio))
        pick = sub.sort_values("p", ascending=False).head(k)
        hit = pick["y"].mean() if len(pick) else np.nan
        hits.append(hit)
        daily_sel.append((d, pick))
    hit_rate = float(np.nanmean(hits)) if hits else np.nan
    return {"hit_at_top10pct": hit_rate, "daily_selection": daily_sel}


def backtest_nextday_open2close(ev: pd.DataFrame, probs: np.ndarray, daily_bars: Dict[str, pd.DataFrame], fee: float = 0.0012, slip: float = 0.003, top_ratio: float = 0.10) -> Dict:
    df = ev[["code", "date"]].copy()
    df["p"] = probs
    g = df.groupby("date")
    rets = []
    for d, sub in g:
        k = max(1, int(len(sub) * top_ratio))
        pick = sub.sort_values("p", ascending=False).head(k)
        if pick.empty:
            continue
        rr = []
        for _, row in pick.iterrows():
            code = row["code"]
            bars = daily_bars.get(code)
            if bars is None or bars.empty or d not in bars.index:
                continue
            idx = list(bars.index).index(d)
            if idx + 1 >= len(bars):
                continue
            o = float(bars["open"].iloc[idx + 1])
            c = float(bars["close"].iloc[idx + 1])
            if o <= 0:
                continue
            r = (c - o) / o - (fee + slip)
            rr.append(r)
        if rr:
            rets.append(np.mean(rr))
    if not rets:
        return {"days": 0}
    arr = np.array(rets)
    mu = np.mean(arr)
    sd = np.std(arr) + 1e-12
    sharpe = (mu / sd) * np.sqrt(252)
    curve = (1 + arr).cumprod()
    peak = np.maximum.accumulate(curve)
    mdd = float(np.max((peak - curve) / (peak + 1e-12)))
    return {"days": int(len(arr)), "avg_daily_ret": float(mu), "sharpe": float(sharpe), "max_drawdown": float(mdd)}


def run(start="20160101", end=None, limit_codes: int = 1000) -> Dict:
    if end is None:
        end = dt.date.today().strftime("%Y%m%d")
    codes = get_a_share_codes()
    if limit_codes and limit_codes > 0:
        codes = codes[:limit_codes]
    daily = fetch_daily_bars(codes, start, end)
    ev = build_events(daily, begin_year=2017)
    if ev.empty:
        print("无有效二板事件样本")
        return {}
    feat_cols_raw = [
        "pct_chg_t", "pct_chg_t_1", "open_gap", "amplitude", "upper_shadow", "lower_shadow",
        "vr5", "vr10", "ar5", "ar10", "ret5", "ret10", "ret20", "ret_std5", "ret_std20",
        "to20h", "to120h", "to250h", "streak"
    ]
    ev = quantile_scale_df(ev, feat_cols_raw)
    feat_cols = [c + "_q" for c in feat_cols_raw]
    tr, va, te = split_sets(ev)
    if len(tr) < 50 or len(va) < 20 or len(te) < 20:
        print("样本量不足，建议扩大代码数或日期范围")
    model = train_logit(tr, va, feat_cols)
    p_test = model.predict_proba(te[feat_cols].values)[:, 1]
    auc = roc_auc_score(te["y"].values, p_test) if len(np.unique(te["y"])) > 1 else np.nan
    prauc = average_precision_score(te["y"].values, p_test) if len(np.unique(te["y"])) > 1 else np.nan
    hit = evaluate_daily_topk(te, p_test, top_ratio=0.10)
    bt = backtest_nextday_open2close(te, p_test, daily, fee=0.0012, slip=0.003, top_ratio=0.10)
    res = {
        "samples": int(len(ev)),
        "test_auc": float(auc) if not np.isnan(auc) else None,
        "test_pr_auc": float(prauc) if not np.isnan(prauc) else None,
        "hit_at_top10pct": float(hit.get("hit_at_top10pct", np.nan)) if hit else None,
        "backtest": bt,
    }
    print(json.dumps(res, ensure_ascii=False))
    return res


if __name__ == "__main__":
    run()
