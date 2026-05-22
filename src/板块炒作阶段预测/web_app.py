# -*- coding: utf-8 -*-
"""板块炒作阶段预测 Web 控制台。

启动：
    python -m src.板块炒作阶段预测.web_app --host 0.0.0.0 --port 8010

页面：
- 参数表单：起止日期、未来窗口、最小成分数、模型类型、是否更新板块数据等
- 实时日志：后台训练任务的日志通过轮询展示
- 最新一日板块四阶段预测榜单（可按各类概率排序）
- 测试集评估指标 + 混淆矩阵 + Top 20 特征重要性
- 产物 CSV 下载
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import sys
import threading
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# 让脚本与包两种运行方式都 work
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR.parent.parent))

from src.板块炒作阶段预测 import (  # noqa: E402
    feature_builder,
    label_builder,
    model_pipeline,
    qlib_market_loader,
    sector_constituents,
)
from src.板块炒作阶段预测.code_utils import xt_to_qlib  # noqa: E402
from src.板块炒作阶段预测.web_index import render_index_html  # noqa: E402

try:
    from flask import Flask, jsonify, request, send_from_directory
except Exception as exc:  # pragma: no cover
    Flask = None  # type: ignore[assignment]
    jsonify = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]
    send_from_directory = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

LOGGER = logging.getLogger("板块炒作阶段预测.web")

CONFIG_FILE = _THIS_DIR / "web_config.json"
RESULTS_DIR = _THIS_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

_RUN_LOCK = threading.Lock()
_RUN_STATE: Dict[str, Any] = {
    "running": False,
    "logs": [],
    "last_results": None,
    "error": None,
    "start_time": None,
    "end_time": None,
}
_MAX_LOG_LINES = 500


# -----------------------------------------------------------------------------
# 配置
# -----------------------------------------------------------------------------

@dataclass
class WebConfig:
    """Web 控制台运行配置。"""
    start_date: str = ""  # 默认在 default_config 里填
    end_date: str = ""
    horizon: int = 10
    short_horizon: int = 5
    long_horizon: int = 20
    min_members: int = 10
    max_members: int = 600
    model: str = "lightgbm"
    train_ratio: float = 0.6
    valid_ratio: float = 0.2
    sector_cache_hours: int = 24
    update_sectors: bool = False
    sectors: List[str] = field(default_factory=list)
    provider_uri: str = ""


def default_config() -> WebConfig:
    today = _dt.date.today()
    return WebConfig(
        start_date=(today - _dt.timedelta(days=400)).strftime("%Y-%m-%d"),
        end_date=today.strftime("%Y-%m-%d"),
    )


def load_saved_config() -> WebConfig:
    base = default_config()
    if not CONFIG_FILE.exists():
        return base
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        valid = set(asdict(base).keys())
        merged = {**asdict(base), **{k: v for k, v in raw.items() if k in valid}}
        if isinstance(merged.get("sectors"), str):
            merged["sectors"] = [
                s.strip() for s in merged["sectors"].replace("，", ",").split(",") if s.strip()
            ]
        return WebConfig(**merged)
    except Exception as exc:
        LOGGER.warning("读取 Web 配置失败，使用默认值: %s", exc)
        return base


def save_config(cfg: WebConfig) -> None:
    CONFIG_FILE.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def merge_payload(payload: Dict[str, Any]) -> WebConfig:
    base = asdict(load_saved_config())
    valid = set(base.keys())
    for k, v in (payload or {}).items():
        if k not in valid:
            continue
        if v is None:
            continue
        if k == "sectors":
            if isinstance(v, list):
                base[k] = [str(x).strip() for x in v if str(x).strip()]
            elif isinstance(v, str):
                base[k] = [
                    s.strip() for s in v.replace("，", ",").split(",") if s.strip()
                ]
        elif k in {"horizon", "short_horizon", "long_horizon", "min_members", "max_members", "sector_cache_hours"}:
            try:
                base[k] = int(v)
            except Exception:
                pass
        elif k in {"train_ratio", "valid_ratio"}:
            try:
                base[k] = float(v)
            except Exception:
                pass
        elif k == "update_sectors":
            base[k] = bool(v)
        else:
            base[k] = str(v)
    return WebConfig(**base)


# -----------------------------------------------------------------------------
# 日志：把后台任务日志导入 _RUN_STATE
# -----------------------------------------------------------------------------

class _StateLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            msg = self.format(record)
        except Exception:
            return
        with _RUN_LOCK:
            _RUN_STATE["logs"].append(msg)
            if len(_RUN_STATE["logs"]) > _MAX_LOG_LINES:
                del _RUN_STATE["logs"][: len(_RUN_STATE["logs"]) - _MAX_LOG_LINES]


def _attach_state_log_handler() -> _StateLogHandler:
    handler = _StateLogHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    targets = [
        "src.板块炒作阶段预测",
        "src.板块炒作阶段预测.web",
        "src.板块炒作阶段预测.feature_builder",
        "src.板块炒作阶段预测.label_builder",
        "src.板块炒作阶段预测.model_pipeline",
        "src.板块炒作阶段预测.qlib_market_loader",
        "src.板块炒作阶段预测.sector_constituents",
    ]
    for name in targets:
        lg = logging.getLogger(name)
        lg.addHandler(handler)
        lg.setLevel(logging.INFO)
    return handler


# -----------------------------------------------------------------------------
# 后台任务
# -----------------------------------------------------------------------------

def _serialize_results(result: Dict[str, Any]) -> Dict[str, Any]:
    """把训练结果转成前端可消费的纯 JSON。"""
    out: Dict[str, Any] = {
        "model_used": result.get("model_used"),
        "split_meta": result.get("split_meta"),
        "test_eval": result.get("test_eval"),
        "latest_date": result.get("latest_date"),
        "feature_importance": (result.get("train_info") or {}).get("feature_importance"),
    }
    latest = result.get("latest_predictions")
    if latest is not None:
        df = latest.reset_index()
        records = df.to_dict(orient="records")
        cleaned: List[Dict[str, Any]] = []
        for row in records:
            new_row: Dict[str, Any] = {}
            for k, v in row.items():
                if isinstance(v, float):
                    if v != v:  # NaN
                        new_row[k] = None
                    else:
                        new_row[k] = float(v)
                else:
                    new_row[k] = v
            cleaned.append(new_row)
        out["latest_predictions"] = cleaned
    if result.get("latest_date"):
        out["latest_csv_url"] = f"/api/result-file/latest_predictions_{result['latest_date']}.csv"
    return out


def _run_background(cfg: WebConfig) -> None:
    handler = _attach_state_log_handler()
    with _RUN_LOCK:
        _RUN_STATE.update(
            running=True,
            logs=[],
            error=None,
            start_time=_dt.datetime.now().isoformat(timespec="seconds"),
            end_time=None,
        )
    logger = logging.getLogger("src.板块炒作阶段预测.web")
    try:
        logger.info("===== 后台任务开始 =====")
        logger.info("配置：%s", asdict(cfg))

        # 1) 板块成分
        sector_cfg = sector_constituents.SectorConfig(
            cache_max_age_hours=cfg.sector_cache_hours,
            min_members=cfg.min_members,
            max_members=cfg.max_members,
        )
        universe = sector_constituents.build_sector_universe(
            sector_cfg,
            update=cfg.update_sectors,
            sector_names=cfg.sectors or None,
        )
        if not universe:
            raise RuntimeError("板块成分为空，请检查 XtQuant / 板块过滤参数")
        logger.info("有效板块数：%d", len(universe))

        # 2) Qlib 行情
        all_xt = sector_constituents.collect_all_members(universe)
        qlib_codes = sorted({xt_to_qlib(c) for c in all_xt})
        logger.info("Qlib 待读取股票数：%d", len(qlib_codes))
        panel = qlib_market_loader.load_market_panel(
            instruments=qlib_codes,
            start_time=cfg.start_date,
            end_time=cfg.end_date,
            provider_uri=cfg.provider_uri or None,
        )

        # 3) 特征
        feat_cfg = feature_builder.FeatureConfig(
            min_members_for_feature=max(3, cfg.min_members // 2)
        )
        feature_long, intermediates = feature_builder.build_sector_feature_table(
            panel, universe, feat_cfg
        )

        # 4) 标签
        label_cfg = label_builder.LabelConfig(
            horizon=cfg.horizon,
            short_horizon=cfg.short_horizon,
            long_horizon=cfg.long_horizon,
        )
        labels_long, _ = label_builder.build_labels(intermediates, label_cfg)

        # 5) 模型
        model_cfg = model_pipeline.ModelConfig(
            model=cfg.model,
            train_ratio=cfg.train_ratio,
            valid_ratio=cfg.valid_ratio,
        )
        result = model_pipeline.train_and_predict(feature_long, labels_long, model_cfg)
        paths = model_pipeline.save_artifacts(result, RESULTS_DIR)
        logger.info("产物路径: %s", paths)

        with _RUN_LOCK:
            _RUN_STATE["last_results"] = _serialize_results(result)
            _RUN_STATE["error"] = None
        logger.info("===== 后台任务完成 =====")
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("任务失败: %s\n%s", exc, tb)
        with _RUN_LOCK:
            _RUN_STATE["error"] = f"{exc}"
    finally:
        with _RUN_LOCK:
            _RUN_STATE["running"] = False
            _RUN_STATE["end_time"] = _dt.datetime.now().isoformat(timespec="seconds")
        # 移除 handler，避免重复挂载
        for name in [
            "src.板块炒作阶段预测",
            "src.板块炒作阶段预测.web",
            "src.板块炒作阶段预测.feature_builder",
            "src.板块炒作阶段预测.label_builder",
            "src.板块炒作阶段预测.model_pipeline",
            "src.板块炒作阶段预测.qlib_market_loader",
            "src.板块炒作阶段预测.sector_constituents",
        ]:
            logging.getLogger(name).removeHandler(handler)


# -----------------------------------------------------------------------------
# Flask 应用
# -----------------------------------------------------------------------------

def build_app() -> Any:
    if Flask is None:
        raise ImportError(
            f"未能导入 Flask（{_IMPORT_ERROR}），请先 pip install flask"
        )

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = Flask(__name__, static_folder=None)
    index_html = render_index_html()

    @app.route("/")
    def index():
        return index_html

    @app.route("/api/config", methods=["GET"])
    def api_config_get():
        return jsonify(asdict(load_saved_config()))

    @app.route("/api/config", methods=["POST"])
    def api_config_post():
        cfg = merge_payload(request.get_json(silent=True) or {})
        save_config(cfg)
        return jsonify({"ok": True, "config": asdict(cfg)})

    @app.route("/api/run", methods=["POST"])
    def api_run():
        with _RUN_LOCK:
            if _RUN_STATE["running"]:
                return jsonify({"ok": False, "error": "已有任务运行中，请稍候"}), 409
        cfg = merge_payload(request.get_json(silent=True) or {})
        save_config(cfg)
        threading.Thread(target=_run_background, args=(cfg,), daemon=True).start()
        return jsonify({"ok": True, "config": asdict(cfg)})

    @app.route("/api/status")
    def api_status():
        with _RUN_LOCK:
            payload = {k: v for k, v in _RUN_STATE.items()}
        return jsonify(payload)

    @app.route("/api/result-file/<path:filename>")
    def api_result_file(filename: str):
        if "/" in filename or "\\" in filename or filename.startswith(".."):
            return jsonify({"ok": False, "error": "非法文件名"}), 400
        if not filename.endswith((".csv", ".json")):
            return jsonify({"ok": False, "error": "只允许下载 CSV/JSON"}), 400
        return send_from_directory(str(RESULTS_DIR), filename)

    return app


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="板块炒作阶段预测 Web 控制台")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，外网访问可设 0.0.0.0")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = build_app()
    print("=" * 80)
    print(f"板块炒作阶段预测 Web 控制台已启动: http://{args.host}:{args.port}")
    print("=" * 80)
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
