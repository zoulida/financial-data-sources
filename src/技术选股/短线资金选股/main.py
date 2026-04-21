"""
短线资金进场选股 —— 主入口
============================
每日尾盘执行，输出按总分降序排列的前30只候选股票。

用法:
    python main.py
    python main.py --no-wind          # 跳过 Wind 资金流向
    python main.py --top 50           # 输出前50只
    python main.py --max-mcap 100     # 市值上限100亿
"""

import sys
import os
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta

from tqdm import tqdm

import pandas as pd

# ── 路径设置 ──
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from 技术选股.短线资金选股.config import OUTPUT_DIR, TOP_N, KLINE_DAYS
from 技术选股.短线资金选股.data_fetcher import (
    get_stock_universe,
    fetch_kline_batch,
    fetch_wind_capital_flow,
    get_stock_name,
    is_st_stock,
    filter_st_stocks,
    get_date_range,
)
from md.winds.通过excel插件.wind_client import is_wind_available
from 技术选股.短线资金选股.scorer import score_stock

# ── 日志配置 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_screener(use_wind: bool = True, top_n: int = TOP_N,
                 max_mcap: float = None, save_csv: bool = True) -> pd.DataFrame:
    """
    执行短线资金选股主流程。

    参数:
        use_wind: 是否使用 Wind 资金流向数据
        top_n: 输出前N只
        max_mcap: 市值上限（亿），覆盖 config 中的默认值
        save_csv: 是否保存CSV

    返回:
        DataFrame: 打分结果，按总分降序
    """
    t0 = time.time()

    # 覆盖市值上限
    if max_mcap is not None:
        import 技术选股.短线资金选股.config as cfg
        cfg.MAX_MARKET_CAP = max_mcap

    # ═══════════════════════════════════════════════════════
    # 第1步：获取股票池
    # ═══════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("第1步：获取股票池")
    universe = get_stock_universe()
    if universe.empty:
        logger.error("股票池为空，退出")
        return pd.DataFrame()

    codes = universe["code"].tolist()

    # ST 过滤
    codes = filter_st_stocks(codes)
    if not codes:
        logger.error("过滤ST后股票池为空")
        return pd.DataFrame()

    # 构建市值查找表
    mcap_map = dict(zip(universe["code"], universe["market_cap"]))
    logger.info(f"有效股票池: {len(codes)} 只")

    # ═══════════════════════════════════════════════════════
    # 第2步：批量获取K线
    # ═══════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("第2步：批量获取K线数据")
    start_date, end_date, reason = get_date_range()
    logger.info(f"K线区间: {start_date} ~ {end_date} ({reason})")

    kline_dict = fetch_kline_batch(codes, start_date, end_date)
    logger.info(f"K线获取完成: {len(kline_dict)}/{len(codes)}")

    # 过滤掉没有K线的股票
    codes = [c for c in codes if c in kline_dict]
    if not codes:
        logger.error("无有效K线数据")
        return pd.DataFrame()

    # ═══════════════════════════════════════════════════════
    # 第3步：获取 Wind 资金流向（可选）
    # ═══════════════════════════════════════════════════════
    wind_data = {}
    wind_ok = use_wind and is_wind_available()

    if wind_ok:
        logger.info("=" * 60)
        logger.info("第3步：获取 Wind 资金流向数据")
        try:
            wind_data = fetch_wind_capital_flow(codes)
        except Exception as e:
            logger.error(f"Wind 资金流向获取失败: {e}")
            wind_data = {}
            wind_ok = False
    else:
        if use_wind:
            logger.warning("Wind Excel 插件不可用，跳过资金流向维度")
        else:
            logger.info("已禁用 Wind，跳过资金流向维度")

    # ═══════════════════════════════════════════════════════
    # 第4步：逐只打分
    # ═══════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info(f"第4步：逐只打分 ({len(codes)} 只)")

    all_scores = []
    for code in tqdm(codes, desc="打分进度", ncols=80):

        kdf = kline_dict.get(code)
        wdf = wind_data.get(code)
        mcap = mcap_map.get(code, float("nan"))

        # 检查ST（名称在前面已过滤，这里用标记）
        scores = score_stock(
            code=code,
            kline_df=kdf,
            wind_df=wdf,
            all_wind_data=wind_data,
            all_kline_data=kline_dict,
            market_cap=mcap,
            is_st=False,
            wind_available=wind_ok,
        )
        all_scores.append(scores)

    # ═══════════════════════════════════════════════════════
    # 第5步：排序输出
    # ═══════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("第5步：排序并输出结果")

    result_df = pd.DataFrame(all_scores)
    if result_df.empty:
        logger.warning("无打分结果")
        return pd.DataFrame()

    # 按总分降序排列
    result_df = result_df.sort_values("total_score", ascending=False).reset_index(drop=True)

    # 补充名称
    names = []
    for c in result_df["code"]:
        names.append(get_stock_name(c))
    result_df.insert(1, "name", names)

    # 补充市值
    result_df["market_cap"] = result_df["code"].map(mcap_map)

    # 取前N
    top_df = result_df.head(top_n).copy()

    # 输出关键列摘要
    summary_cols = [
        "code", "name", "market_cap", "total_score",
        "capital_flow_total", "volume_price_total",
        "technical_total", "chip_total", "fundamental_total",
    ]
    display_cols = [c for c in summary_cols if c in top_df.columns]
    logger.info(f"\n前{top_n}只候选股票:")
    print(top_df[display_cols].to_string(index=False))

    # 保存CSV
    if save_csv:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        today_str = end_date if end_date else datetime.now().strftime("%Y%m%d")
        # 完整结果
        full_path = OUTPUT_DIR / f"短线资金选股_全部_{today_str}.csv"
        result_df.to_csv(full_path, index=False, encoding="utf-8-sig")
        # Top N
        top_path = OUTPUT_DIR / f"短线资金选股_TOP{top_n}_{today_str}.csv"
        top_df.to_csv(top_path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV已保存:")
        logger.info(f"  完整: {full_path}")
        logger.info(f"  Top{top_n}: {top_path}")

    elapsed = time.time() - t0
    logger.info(f"完成! 用时 {elapsed:.1f}s, 股票池 {len(codes)} 只, 输出 {len(top_df)} 只")

    return top_df


def main():
    parser = argparse.ArgumentParser(description="短线资金进场选股 —— 尾盘执行")
    parser.add_argument("--no-wind", action="store_true",
                        help="禁用 Wind 资金流向数据")
    parser.add_argument("--top", type=int, default=TOP_N,
                        help=f"输出前N只，默认{TOP_N}")
    parser.add_argument("--max-mcap", type=float, default=None,
                        help="市值上限(亿)，默认使用config配置")
    parser.add_argument("--no-csv", action="store_true",
                        help="不保存CSV文件")
    args = parser.parse_args()

    result = run_screener(
        use_wind=not args.no_wind,
        top_n=args.top,
        max_mcap=args.max_mcap,
        save_csv=not args.no_csv,
    )

    if result.empty:
        logger.warning("未找到候选股票")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
