import os
import argparse
from datetime import datetime
import numpy as np
import pandas as pd
try:
    from xtquant import xtdata
    _xt_ok = True
except Exception:
    xtdata = None
    _xt_ok = False

def get_universe_with_basics(max_price: float = 18.0, max_mcap: float = 200.0) -> pd.DataFrame:
    """
    使用 xtdata 获取A股股票池，并补充基础字段（最新价、流通股本、推算市值）。不依赖 Wind。

    参数:
    - end_date: 截止日期，格式 YYYYMMDD。用于限定K线下载时间区间的结束日期；本函数内部主要用于日志与一致性。

    处理流程:
    1) 获取板块成分：调用 xtdata.get_stock_list_in_sector('沪深A股') 拿到全市场代码。
    2) 代码初筛：仅保留 00/60 开头的主板/沪深 A 股；支持通过环境变量 DEBUG_MAX_CODES 截断用于调试。
    3) 批量补全基础数据：
       - 通过 xtdata.get_full_tick 批量获取最新价（lastPrice/price/close 任一字段）。
       - 通过 xtdata.get_instrument_detail 获取流通股本 FloatVolume。
       - 若两者均有效，则以  市值(亿元)= 流通股本 * 最新价 / 1e8  进行推算。
    4) 基础维度构造：为每个代码写入 market_cap / free_float / last_price。
    5) 基础过滤：
       - 价格过滤：3 ≤ last_price ≤ 18
       - 市值过滤：30 ≤ market_cap < 200（单位：亿元）

    返回:
    - DataFrame(columns=['code','market_cap','free_float','last_price'])，均已按上述过滤完成。
      若获取不到任何代码，返回相同列的空表（数值列为 NaN）。

    失败与兜底:
    - 任一第三方接口异常均被 try/except 吸收，缺失项以 NaN 处理，不中断流程。
    - 若 xtdata 不可用，则直接抛出 RuntimeError 提示配置问题。
    """
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
    df = df[(df["last_price"] >= 3.0) & (df["last_price"] <= max_price)].reset_index(drop=True)
    print(f"价格过滤: {pre} -> {len(df)}")
    pre = len(df)
    df = df[(df["market_cap"] >= 30.0) & (df["market_cap"] < max_mcap)].reset_index(drop=True)
    print(f"市值过滤(亿元): {pre} -> {len(df)}")
    return df
def main() -> None:
    parser = argparse.ArgumentParser(description="上涨缩量-基础股票池测试")
    parser.add_argument("--max-price", dest="max_price", type=float, default=18.0, help="最大价格(元)，默认18")
    parser.add_argument("--max-mcap", dest="max_mcap", type=float, default=200.0, help="最大市值(亿元)，默认200")
    args = parser.parse_args()
    df = get_universe_with_basics(max_price=args.max_price, max_mcap=args.max_mcap)
    print(f"结果数量: {len(df)}")
    if not df.empty:
        print(df.head(20).to_string(index=False))

if __name__ == "__main__":
    main()

