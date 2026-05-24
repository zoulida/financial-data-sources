# -*- coding: utf-8 -*-
"""板块炒作阶段预测 CLI 入口。

用法示例：
    python -m src.板块炒作阶段预测.run_sector_stage \
        --start-date 2024-01-01 --end-date 2026-05-22 \
        --output-dir results --update-sectors

功能：
1. 默认通过 OpenTDX 拉取板块列表、板块成分与板块自身日K。
2. 可选保留旧版 XtQuant 成分 + Qlib 股票行情合成板块。
3. 构造板块特征与未来窗口四阶段标签。
4. LightGBM 多分类训练 + 评估，输出最新一日板块阶段预测榜单。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# 包内导入（脚本方式运行时也能 work）
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR.parent.parent))

from src.板块炒作阶段预测 import (  # noqa: E402
    feature_builder,
    label_builder,
    model_pipeline,
    opentdx_sector_loader,
    qlib_market_loader,
    sector_constituents,
)
from src.板块炒作阶段预测.code_utils import xt_to_qlib  # noqa: E402

LOGGER = logging.getLogger("板块炒作阶段预测")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    today = _dt.date.today()
    default_end = today.strftime("%Y-%m-%d")
    default_start = (today - _dt.timedelta(days=400)).strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="板块炒作阶段预测")
    parser.add_argument("--start-date", default=default_start, help="行情起始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", default=default_end, help="行情结束日期 YYYY-MM-DD")
    parser.add_argument("--data-source", choices=("opentdx", "xtquant_qlib"), default="opentdx",
                        help="数据源：opentdx=OpenTDX板块成分+板块K线；xtquant_qlib=旧版XtQuant成分+Qlib股票行情")
    parser.add_argument("--provider-uri", default=None, help="Qlib 数据目录，默认自动定位")
    parser.add_argument("--output-dir", default=str(_THIS_DIR / "results"), help="输出目录")
    parser.add_argument("--horizon", type=int, default=10, help="未来主预测窗口（交易日）")
    parser.add_argument("--short-horizon", type=int, default=5)
    parser.add_argument("--long-horizon", type=int, default=20)
    parser.add_argument("--min-members", type=int, default=10)
    parser.add_argument("--max-members", type=int, default=600)
    parser.add_argument("--update-sectors", action="store_true",
                        help="xtquant_qlib 模式下启动时调用 xtdata.download_sector_data 更新板块数据")
    parser.add_argument("--sector-cache-hours", type=int, default=24,
                        help="板块成分缓存最大小时数")
    parser.add_argument("--sectors", nargs="*", default=None,
                        help="只处理指定板块名称（默认全部）")
    parser.add_argument("--opentdx-root", default=None, help="OpenTDX 根目录，默认自动定位 md/通达信/opentdx-main")
    parser.add_argument("--opentdx-board-types", nargs="*", default=["HY", "GN"],
                        help="OpenTDX 板块类型，常用 HY GN FG DQ ALL")
    parser.add_argument("--opentdx-max-boards", type=int, default=None,
                        help="OpenTDX 最多处理板块数，用于快速冒烟")
    parser.add_argument("--opentdx-kline-count", type=int, default=800,
                        help="每个板块最多读取的 OpenTDX 日K根数")
    parser.add_argument("--model", choices=("lightgbm", "hgb"), default="lightgbm")
    parser.add_argument("--train-ratio", type=float, default=0.6)
    parser.add_argument("--valid-ratio", type=float, default=0.2)
    parser.add_argument("--snapshot", default=None,
                        help="把板块成分快照保存到指定路径（JSON）")
    parser.add_argument("--load-snapshot", default=None,
                        help="xtquant_qlib 模式下从指定 JSON 快照加载板块成分")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 1) 板块成分 ----------
    board_meta: Dict[str, Dict[str, Any]] = {}
    n_stocks_loaded = 0

    if args.data_source == "opentdx":
        if args.load_snapshot:
            raise ValueError("OpenTDX 模式需要板块代码元数据，暂不支持 --load-snapshot")

        opentdx_cfg = opentdx_sector_loader.OpenTdxSectorConfig(
            opentdx_root=args.opentdx_root,
            board_types=args.opentdx_board_types,
            min_members=args.min_members,
            max_members=args.max_members,
            max_boards=args.opentdx_max_boards,
            kline_count=args.opentdx_kline_count,
        )
        universe, board_meta = opentdx_sector_loader.build_opentdx_sector_universe(
            opentdx_cfg,
            sector_names=args.sectors,
        )
    else:
        sector_cfg = sector_constituents.SectorConfig(
            cache_max_age_hours=args.sector_cache_hours,
            min_members=args.min_members,
            max_members=args.max_members,
        )

        if args.load_snapshot:
            LOGGER.info("从快照加载板块成分：%s", args.load_snapshot)
            universe = sector_constituents.load_universe_snapshot(args.load_snapshot)
            universe = {
                name: members for name, members in universe.items()
                if args.min_members <= len(members) <= args.max_members
            }
        else:
            universe = sector_constituents.build_sector_universe(
                sector_cfg,
                update=args.update_sectors,
                sector_names=args.sectors,
            )
    if not universe:
        raise RuntimeError("板块成分为空，无法继续")

    if args.snapshot:
        sector_constituents.save_universe_snapshot(universe, args.snapshot)
        LOGGER.info("板块快照已保存：%s", args.snapshot)

    # ---------- 3) 特征 ----------
    feat_cfg = feature_builder.FeatureConfig(min_members_for_feature=max(3, args.min_members // 2))

    if args.data_source == "opentdx":
        panel = opentdx_sector_loader.load_opentdx_sector_kline_panel(
            board_meta,
            start_time=args.start_date,
            end_time=args.end_date,
            config=opentdx_cfg,
        )
        n_stocks_loaded = len(sector_constituents.collect_all_members(universe))
        member_counts = {name: len(members) for name, members in universe.items()}
        feature_long, intermediates = feature_builder.build_sector_feature_table_from_sector_panel(
            panel, member_counts, feat_cfg
        )
    else:
        all_members_xt = sector_constituents.collect_all_members(universe)
        qlib_codes = sorted({xt_to_qlib(c) for c in all_members_xt})
        n_stocks_loaded = len(qlib_codes)
        LOGGER.info("Qlib 待读取股票数：%d", len(qlib_codes))

        panel = qlib_market_loader.load_market_panel(
            instruments=qlib_codes,
            start_time=args.start_date,
            end_time=args.end_date,
            provider_uri=args.provider_uri,
        )
        feature_long, intermediates = feature_builder.build_sector_feature_table(
            panel, universe, feat_cfg
        )

    # ---------- 4) 标签 ----------
    label_cfg = label_builder.LabelConfig(
        horizon=args.horizon,
        short_horizon=args.short_horizon,
        long_horizon=args.long_horizon,
    )
    labels_long, _ = label_builder.build_labels(intermediates, label_cfg)

    # ---------- 5) 训练 + 预测 ----------
    model_cfg = model_pipeline.ModelConfig(
        model=args.model,
        train_ratio=args.train_ratio,
        valid_ratio=args.valid_ratio,
    )
    result = model_pipeline.train_and_predict(feature_long, labels_long, model_cfg)

    paths = model_pipeline.save_artifacts(result, output_dir)
    LOGGER.info("产物路径: %s", paths)

    # 同时保存运行参数
    run_info_path = output_dir / "run_info.json"
    run_info_path.write_text(
        json.dumps(
            {
                "args": vars(args),
                "data_source": args.data_source,
                "feature_cfg": asdict(feat_cfg),
                "label_cfg": asdict(label_cfg),
                "model_cfg": asdict(model_cfg),
                "n_sectors": len(universe),
                "n_stocks_loaded": n_stocks_loaded,
                "panel_dates": int(panel["close"].shape[0]),
                "opentdx_board_meta": board_meta,
                "split_meta": result["split_meta"],
                "test_eval": result.get("test_eval", {}),
                "model_used": result["model_used"],
                "latest_date": result["latest_date"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    LOGGER.info("运行信息已保存：%s", run_info_path)

    # 控制台打印 Top 板块
    latest = result["latest_predictions"].copy()
    if not latest.empty:
        print("\n=== 最新交易日板块阶段预测 ({}) Top 20 按 '正在炒作' 概率 ===".format(result["latest_date"]))
        print(latest.head(20).to_string())

    return result


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    _setup_logging(args.verbose)
    try:
        run(args)
        return 0
    except Exception as exc:  # pragma: no cover
        LOGGER.exception("运行失败: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
