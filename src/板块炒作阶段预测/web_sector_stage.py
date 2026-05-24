# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

try:
    from flask import Flask, abort, jsonify, request, send_from_directory
except Exception:
    Flask = None
    abort = None
    jsonify = None
    request = None
    send_from_directory = None

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.板块炒作阶段预测 import run_sector_stage

_CONFIG_PATH = _THIS_DIR / "web_config.json"
_RUN_LOCK = threading.Lock()
_RUN_STATE: Dict[str, Any] = {
    "running": False,
    "logs": [],
    "last_results": None,
    "error": None,
    "start_time": None,
    "end_time": None,
    "current_step": None,
    "current_step_started_at": None,
    "current_step_started_perf": None,
    "step_times": [],
    "total_time": 0.0,
}


class _ListLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        line = self.format(record)
        _append_log(line)


class _StreamToLog(io.TextIOBase):
    def __init__(self, original):
        self.original = original

    def write(self, data: str) -> int:
        if data:
            self.original.write(data)
            self.original.flush()
            for line in data.splitlines():
                if line.strip():
                    _append_log(line)
        return len(data)

    def flush(self) -> None:
        with contextlib.suppress(Exception):
            self.original.flush()


def _append_log(line: str) -> None:
    with _RUN_LOCK:
        _RUN_STATE["logs"].append(str(line))
        _RUN_STATE["logs"] = _RUN_STATE["logs"][-2000:]


@contextlib.contextmanager
def _timed_step(step_name: str):
    start_perf = time.perf_counter()
    start_text = time.strftime("%Y-%m-%d %H:%M:%S")
    with _RUN_LOCK:
        _RUN_STATE["current_step"] = step_name
        _RUN_STATE["current_step_started_at"] = start_text
        _RUN_STATE["current_step_started_perf"] = start_perf
    _append_log(f"▶ 开始步骤：{step_name}")
    try:
        yield
    except Exception:
        seconds = time.perf_counter() - start_perf
        with _RUN_LOCK:
            _RUN_STATE["step_times"].append({
                "step": step_name,
                "seconds": round(seconds, 3),
                "status": "failed",
            })
        _append_log(f"✖ 步骤失败：{step_name}，耗时 {seconds:.2f} 秒")
        raise
    else:
        seconds = time.perf_counter() - start_perf
        with _RUN_LOCK:
            _RUN_STATE["step_times"].append({
                "step": step_name,
                "seconds": round(seconds, 3),
                "status": "completed",
            })
        _append_log(f"✓ 完成步骤：{step_name}，耗时 {seconds:.2f} 秒")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, pd.DataFrame):
        return _json_safe(value.reset_index().to_dict(orient="records"))
    if isinstance(value, pd.Series):
        return _json_safe(value.reset_index().to_dict(orient="records"))
    if isinstance(value, (np.floating, float)):
        v = float(value)
        return v if np.isfinite(v) else None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp,)):
        return str(value)
    return value


def _default_config() -> Dict[str, Any]:
    args = vars(run_sector_stage.parse_args([]))
    args.update({
        "data_source": "opentdx",
        "output_dir": str(_THIS_DIR / "results_web"),
        "opentdx_board_types": ["HY", "GN"],
        "opentdx_max_boards": None,
        "opentdx_kline_count": 800,
        "model": "lightgbm",
    })
    return args


def load_config() -> Dict[str, Any]:
    cfg = _default_config()
    if _CONFIG_PATH.exists():
        try:
            saved = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                cfg.update(saved)
        except Exception:
            pass
    if not cfg.get("data_source"):
        cfg["data_source"] = "opentdx"
    if not cfg.get("output_dir"):
        cfg["output_dir"] = str(_THIS_DIR / "results_web")
    if not cfg.get("opentdx_board_types"):
        cfg["opentdx_board_types"] = ["HY", "GN"]
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    payload = {k: v for k, v in cfg.items() if k not in {"verbose"}}
    _CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _coerce_payload(payload: Dict[str, Any]) -> argparse.Namespace:
    defaults = _default_config()
    merged = load_config()
    merged.update({k: v for k, v in payload.items() if k in defaults})

    list_fields = {"sectors", "opentdx_board_types"}
    bool_fields = {"update_sectors", "verbose"}
    int_fields = {"horizon", "short_horizon", "long_horizon", "min_members", "max_members", "sector_cache_hours", "opentdx_kline_count"}
    optional_int_fields = {"opentdx_max_boards"}
    float_fields = {"train_ratio", "valid_ratio"}

    for key in list_fields:
        value = merged.get(key)
        if isinstance(value, str):
            merged[key] = [x.strip() for x in value.replace("，", ",").split(",") if x.strip()]
        elif value is None:
            merged[key] = []
    for key in bool_fields:
        merged[key] = bool(merged.get(key))
    for key in int_fields:
        merged[key] = int(merged.get(key) or defaults[key])
    for key in optional_int_fields:
        value = merged.get(key)
        merged[key] = None if value in (None, "", 0, "0") else int(value)
    for key in float_fields:
        merged[key] = float(merged.get(key) or defaults[key])
    for key in ("provider_uri", "snapshot", "load_snapshot", "opentdx_root"):
        if merged.get(key) == "":
            merged[key] = None
    if not merged.get("sectors"):
        merged["sectors"] = None
    save_config(merged)
    return argparse.Namespace(**{k: merged[k] for k in defaults})


def _output_dir_from_args(args: argparse.Namespace) -> Path:
    out = Path(args.output_dir)
    if not out.is_absolute():
        out = (_PROJECT_ROOT / out).resolve()
    return out


def _collect_files(output_dir: Path) -> list[dict[str, Any]]:
    if not output_dir.exists():
        return []
    files = []
    for path in sorted(output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_file():
            files.append({"name": path.name, "size": path.stat().st_size})
    return files


def _summarize_result(result: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    latest = result.get("latest_predictions", pd.DataFrame())
    full = result.get("full_predictions", pd.DataFrame())
    test = result.get("test_predictions", pd.DataFrame())
    output_dir = _output_dir_from_args(args)
    return _json_safe({
        "latest_date": result.get("latest_date"),
        "model_used": result.get("model_used"),
        "split_meta": result.get("split_meta", {}),
        "test_eval": result.get("test_eval", {}),
        "feature_cols": result.get("feature_cols", []),
        "latest_predictions": latest,
        "full_preview": full.reset_index().tail(500).to_dict(orient="records") if isinstance(full, pd.DataFrame) and not full.empty else [],
        "test_predictions": test.reset_index().to_dict(orient="records") if isinstance(test, pd.DataFrame) and not test.empty else [],
        "output_dir": str(output_dir),
        "files": _collect_files(output_dir),
    })


def _run_sector_stage_steps(args: argparse.Namespace) -> Dict[str, Any]:
    with _timed_step("初始化输出目录"):
        output_dir = _output_dir_from_args(args)
        output_dir.mkdir(parents=True, exist_ok=True)
        board_meta: Dict[str, Dict[str, Any]] = {}
        n_stocks_loaded = 0

    with _timed_step("获取板块列表和成分"):
        if args.data_source == "opentdx":
            if args.load_snapshot:
                raise ValueError("OpenTDX 模式需要板块代码元数据，暂不支持 --load-snapshot")
            opentdx_cfg = run_sector_stage.opentdx_sector_loader.OpenTdxSectorConfig(
                opentdx_root=args.opentdx_root,
                board_types=args.opentdx_board_types,
                min_members=args.min_members,
                max_members=args.max_members,
                max_boards=args.opentdx_max_boards,
                kline_count=args.opentdx_kline_count,
            )
            universe, board_meta = run_sector_stage.opentdx_sector_loader.build_opentdx_sector_universe(
                opentdx_cfg,
                sector_names=args.sectors,
            )
        else:
            sector_cfg = run_sector_stage.sector_constituents.SectorConfig(
                cache_max_age_hours=args.sector_cache_hours,
                min_members=args.min_members,
                max_members=args.max_members,
            )
            if args.load_snapshot:
                universe = run_sector_stage.sector_constituents.load_universe_snapshot(args.load_snapshot)
                universe = {
                    name: members for name, members in universe.items()
                    if args.min_members <= len(members) <= args.max_members
                }
            else:
                universe = run_sector_stage.sector_constituents.build_sector_universe(
                    sector_cfg,
                    update=args.update_sectors,
                    sector_names=args.sectors,
                )
        if not universe:
            raise RuntimeError("板块成分为空，无法继续")

    with _timed_step("保存板块快照"):
        if args.snapshot:
            run_sector_stage.sector_constituents.save_universe_snapshot(universe, args.snapshot)

    with _timed_step("读取行情或板块K线"):
        feat_cfg = run_sector_stage.feature_builder.FeatureConfig(
            min_members_for_feature=max(3, args.min_members // 2)
        )
        if args.data_source == "opentdx":
            panel = run_sector_stage.opentdx_sector_loader.load_opentdx_sector_kline_panel(
                board_meta,
                start_time=args.start_date,
                end_time=args.end_date,
                config=opentdx_cfg,
            )
            n_stocks_loaded = len(run_sector_stage.sector_constituents.collect_all_members(universe))
        else:
            all_members_xt = run_sector_stage.sector_constituents.collect_all_members(universe)
            qlib_codes = sorted({run_sector_stage.xt_to_qlib(c) for c in all_members_xt})
            n_stocks_loaded = len(qlib_codes)
            panel = run_sector_stage.qlib_market_loader.load_market_panel(
                instruments=qlib_codes,
                start_time=args.start_date,
                end_time=args.end_date,
                provider_uri=args.provider_uri,
            )

    with _timed_step("构造板块特征"):
        if args.data_source == "opentdx":
            member_counts = {name: len(members) for name, members in universe.items()}
            feature_long, intermediates = run_sector_stage.feature_builder.build_sector_feature_table_from_sector_panel(
                panel,
                member_counts,
                feat_cfg,
            )
        else:
            feature_long, intermediates = run_sector_stage.feature_builder.build_sector_feature_table(
                panel,
                universe,
                feat_cfg,
            )

    with _timed_step("构造训练标签"):
        label_cfg = run_sector_stage.label_builder.LabelConfig(
            horizon=args.horizon,
            short_horizon=args.short_horizon,
            long_horizon=args.long_horizon,
        )
        labels_long, _ = run_sector_stage.label_builder.build_labels(intermediates, label_cfg)

    with _timed_step("训练模型并预测"):
        model_cfg = run_sector_stage.model_pipeline.ModelConfig(
            model=args.model,
            train_ratio=args.train_ratio,
            valid_ratio=args.valid_ratio,
        )
        result = run_sector_stage.model_pipeline.train_and_predict(feature_long, labels_long, model_cfg)

    with _timed_step("保存结果文件"):
        paths = run_sector_stage.model_pipeline.save_artifacts(result, output_dir)
        run_info_path = output_dir / "run_info.json"
        run_info_path.write_text(
            json.dumps(
                {
                    "args": vars(args),
                    "data_source": args.data_source,
                    "feature_cfg": run_sector_stage.asdict(feat_cfg),
                    "label_cfg": run_sector_stage.asdict(label_cfg),
                    "model_cfg": run_sector_stage.asdict(model_cfg),
                    "n_sectors": len(universe),
                    "n_stocks_loaded": n_stocks_loaded,
                    "panel_dates": int(panel["close"].shape[0]),
                    "opentdx_board_meta": board_meta,
                    "split_meta": result["split_meta"],
                    "test_eval": result.get("test_eval", {}),
                    "model_used": result["model_used"],
                    "latest_date": result["latest_date"],
                    "paths": paths,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    with _timed_step("整理页面展示数据"):
        latest = result["latest_predictions"].copy()
        if not latest.empty:
            print("\n=== 最新交易日板块阶段预测 ({}) Top 20 按 '正在炒作' 概率 ===".format(result["latest_date"]))
            print(latest.head(20).to_string())

    return result


def _run_background(args: argparse.Namespace) -> None:
    total_start = time.perf_counter()
    with _RUN_LOCK:
        _RUN_STATE.update({
            "running": True,
            "logs": [],
            "last_results": None,
            "error": None,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": None,
            "current_step": None,
            "current_step_started_at": None,
            "current_step_started_perf": None,
            "step_times": [],
            "total_time": 0.0,
        })
    root_logger = logging.getLogger()
    old_level = root_logger.level
    handler = _ListLogHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    handler.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _StreamToLog(original_stdout), _StreamToLog(original_stderr)
    try:
        _append_log("开始运行板块炒作阶段预测...")
        result = _run_sector_stage_steps(args)
        summary = _summarize_result(result, args)
        with _RUN_LOCK:
            _RUN_STATE["last_results"] = summary
    except Exception as exc:
        traceback.print_exc()
        with _RUN_LOCK:
            _RUN_STATE["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        root_logger.removeHandler(handler)
        root_logger.setLevel(old_level)
        total_seconds = time.perf_counter() - total_start
        with _RUN_LOCK:
            _RUN_STATE["running"] = False
            _RUN_STATE["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _RUN_STATE["current_step"] = None
            _RUN_STATE["current_step_started_at"] = None
            _RUN_STATE["current_step_started_perf"] = None
            _RUN_STATE["total_time"] = round(total_seconds, 3)
        _append_log(f"总耗时：{total_seconds:.2f} 秒")


def _build_flask_app() -> Any:
    if Flask is None:
        raise ImportError("缺少 flask，请先 pip install flask")
    app = Flask(__name__, static_folder=None)

    @app.after_request
    def _no_cache(resp):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    @app.route("/")
    def index():
        return _render_index_html()

    @app.route("/api/config")
    def api_config():
        return jsonify(load_config())

    @app.route("/api/run", methods=["POST"])
    def api_run():
        with _RUN_LOCK:
            if _RUN_STATE["running"]:
                return jsonify({"ok": False, "msg": "已有运行中的任务"}), 400
        payload = request.get_json(force=True, silent=True) or {}
        try:
            args = _coerce_payload(payload)
        except Exception as exc:
            return jsonify({"ok": False, "msg": str(exc)}), 400
        threading.Thread(target=_run_background, args=(args,), daemon=True).start()
        return jsonify({"ok": True})

    @app.route("/api/status")
    def api_status():
        with _RUN_LOCK:
            current_elapsed = 0.0
            if _RUN_STATE["running"] and _RUN_STATE["current_step_started_perf"]:
                current_elapsed = time.perf_counter() - float(_RUN_STATE["current_step_started_perf"])
            return jsonify({
                "running": _RUN_STATE["running"],
                "logs": list(_RUN_STATE["logs"][-500:]),
                "last_results": _RUN_STATE["last_results"],
                "error": _RUN_STATE["error"],
                "start_time": _RUN_STATE["start_time"],
                "end_time": _RUN_STATE["end_time"],
                "current_step": _RUN_STATE["current_step"],
                "current_step_started_at": _RUN_STATE["current_step_started_at"],
                "current_step_elapsed": round(current_elapsed, 3),
                "step_times": list(_RUN_STATE["step_times"]),
                "total_time": _RUN_STATE["total_time"],
            })

    @app.route("/api/file/<path:filename>")
    def api_file(filename: str):
        cfg = load_config()
        args = _coerce_payload(cfg)
        output_dir = _output_dir_from_args(args).resolve()
        target = (output_dir / Path(filename).name).resolve()
        if not str(target).startswith(str(output_dir)) or not target.exists() or not target.is_file():
            return abort(404)
        return send_from_directory(str(output_dir), target.name, as_attachment=False)

    return app


def _render_index_html() -> str:
    return r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>板块炒作阶段预测</title>
<style>
body{margin:0;background:#f4f6fb;color:#1f2937;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft Yahei",sans-serif;font-size:13px}.layout{display:grid;grid-template-columns:360px 1fr;gap:12px;padding:12px}.panel{background:#fff;border-radius:12px;box-shadow:0 8px 24px rgba(15,23,42,.06);padding:14px;overflow:auto}h1{margin:0;padding:14px 16px;background:linear-gradient(135deg,#1d4ed8,#06b6d4);color:#fff;font-size:20px}h2{font-size:15px;margin:0 0 10px}.row{display:flex;gap:8px;margin:8px 0}.row label{flex:1}.hint{font-size:11px;color:#6b7280;margin-bottom:3px}input,select{width:100%;box-sizing:border-box;border:1px solid #d1d5db;border-radius:8px;padding:7px 8px;font-size:13px;background:#fff}button{border:0;border-radius:9px;padding:9px 14px;background:#2563eb;color:#fff;font-weight:700;cursor:pointer}button:disabled{background:#93c5fd}.danger{background:#dc2626}.status{border-radius:9px;padding:9px;background:#e5e7eb}.run{background:#fef3c7}.ok{background:#dcfce7}.err{background:#fee2e2}pre{height:230px;overflow:auto;background:#0f172a;color:#dbeafe;border-radius:10px;padding:10px;line-height:1.35;font-size:12px}.tabs{display:flex;gap:8px;margin-bottom:8px}.tab{background:#e5e7eb;color:#111827}.tab.active{background:#2563eb;color:#fff}.table-wrap{max-height:620px;overflow:auto;border:1px solid #e5e7eb;border-radius:10px}table{border-collapse:collapse;width:100%;font-size:12px}th,td{border-bottom:1px solid #eef2f7;padding:6px 8px;text-align:right;white-space:nowrap}th{position:sticky;top:0;background:#f8fafc;z-index:1}th:first-child,td:first-child{text-align:left}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.badge{display:inline-block;padding:3px 8px;border-radius:999px;background:#e0f2fe;color:#075985;margin:2px}.files a{display:inline-block;margin:3px 8px 3px 0;color:#2563eb}.toolbar{display:flex;gap:8px;align-items:center;margin:8px 0}.toolbar input{max-width:260px}.small{font-size:12px;color:#6b7280}.wide{grid-column:1/-1}.timing{margin-top:10px;border:1px solid #e5e7eb;border-radius:10px;overflow:auto;max-height:260px}.timing table{font-size:12px}.step-now{font-weight:700;color:#92400e}.step-ok{color:#047857}.step-fail{color:#b91c1c}
</style></head><body><h1>📈 板块炒作阶段预测 Web 控制台</h1><div class="layout"><form id="form" class="panel"><h2>运行参数</h2>
<div class="row"><label><div class="hint">数据源</div><select name="data_source"><option value="opentdx">OpenTDX板块K线</option><option value="xtquant_qlib">XtQuant成分+Qlib合成</option></select></label></div>
<div class="row"><label><div class="hint">开始日期</div><input name="start_date"></label><label><div class="hint">结束日期</div><input name="end_date"></label></div>
<div class="row"><label><div class="hint">输出目录</div><input name="output_dir"></label></div>
<div class="row"><label><div class="hint">OpenTDX路径</div><input name="opentdx_root" placeholder="留空自动定位"></label></div>
<div class="row"><label><div class="hint">板块类型，逗号分隔</div><input name="opentdx_board_types" placeholder="HY,GN"></label><label><div class="hint">最多板块数，空=全部</div><input name="opentdx_max_boards" type="number"></label></div>
<div class="row"><label><div class="hint">K线根数</div><input name="opentdx_kline_count" type="number"></label><label><div class="hint">模型</div><select name="model"><option value="lightgbm">lightgbm</option><option value="hgb">hgb</option></select></label></div>
<div class="row"><label><div class="hint">最小成分数</div><input name="min_members" type="number"></label><label><div class="hint">最大成分数</div><input name="max_members" type="number"></label></div>
<div class="row"><label><div class="hint">主窗口</div><input name="horizon" type="number"></label><label><div class="hint">短窗口</div><input name="short_horizon" type="number"></label><label><div class="hint">长窗口</div><input name="long_horizon" type="number"></label></div>
<div class="row"><label><div class="hint">训练比例</div><input name="train_ratio" type="number" step="0.01"></label><label><div class="hint">验证比例</div><input name="valid_ratio" type="number" step="0.01"></label></div>
<div class="row"><label><div class="hint">指定板块，逗号分隔，空=全部</div><input name="sectors"></label></div>
<div class="row"><button id="run" type="submit">▶ 运行并生成结果</button><button type="button" id="refresh" class="tab">刷新状态</button></div>
<p class="small">默认走 OpenTDX，可直接读取板块自身日K。全量运行可能需要几分钟。</p></form><div><div class="grid"><div class="panel"><h2>运行状态</h2><div id="status" class="status">空闲</div><div id="timing" class="timing">等待运行...</div><pre id="logs">等待运行...</pre></div><div class="panel"><h2>结果摘要</h2><div id="summary">暂无结果</div></div><div class="panel wide"><h2>结果表格</h2><div class="tabs"><button class="tab active" type="button" data-table="latest">最新日全部板块</button><button class="tab" type="button" data-table="test">测试集预测</button><button class="tab" type="button" data-table="full">全量预测预览</button></div><div class="toolbar"><input id="filter" placeholder="搜索板块/标签"><span id="count" class="small"></span></div><div id="table" class="table-wrap">运行后显示结果</div></div></div></div></div>
<script>
const form=document.getElementById('form'),btn=document.getElementById('run'),statusEl=document.getElementById('status'),logsEl=document.getElementById('logs'),summaryEl=document.getElementById('summary'),tableEl=document.getElementById('table'),filterEl=document.getElementById('filter'),countEl=document.getElementById('count'),timingEl=document.getElementById('timing');let current=null,tableName='latest';
function fill(cfg){for(const[k,v]of Object.entries(cfg)){const el=form.elements.namedItem(k);if(!el)continue;if(Array.isArray(v))el.value=v.join(',');else if(v!==null&&typeof v!=='object')el.value=v;else el.value='';}}
function read(){const d={};for(const el of form.elements){if(!el.name)continue;let v=el.value;if(['opentdx_board_types','sectors'].includes(el.name))v=v.split(/[,，]/).map(x=>x.trim()).filter(Boolean);d[el.name]=v;}return d;}
function n(v,d=4){if(v===null||v===undefined||v==='')return '-';const x=Number(v);return Number.isFinite(x)?x.toFixed(d):String(v)}
function pct(v){if(v===null||v===undefined)return '-';return (Number(v)*100).toFixed(2)+'%'}
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function init(){const cfg=await fetch('/api/config').then(r=>r.json());fill(cfg);poll();setInterval(poll,1000)}
async function poll(){let s;try{s=await fetch('/api/status',{cache:'no-store'}).then(r=>r.json())}catch(e){return}btn.disabled=!!s.running;statusEl.className='status '+(s.running?'run':s.error?'err':s.last_results?'ok':'');statusEl.textContent=s.running?'运行中 '+(s.start_time||''):s.error?'失败：'+s.error:s.last_results?'完成：'+(s.end_time||''):'空闲';renderTiming(s);logsEl.textContent=(s.logs&&s.logs.length)?s.logs.join('\n'):'等待运行...';if(s.running)logsEl.scrollTop=logsEl.scrollHeight;if(s.last_results){current=s.last_results;renderSummary();renderTable();}}
function renderTiming(s){const steps=s.step_times||[];let total=Number(s.total_time||0);let html=`<p><b>总耗时：</b>${total>0?n(total,2)+' 秒':(s.running?'运行中':'-')}</p>`;if(s.running&&s.current_step)html+=`<p class="step-now">当前步骤：${esc(s.current_step)}，已运行 ${n(s.current_step_elapsed||0,2)} 秒</p>`;html+='<table><thead><tr><th>步骤</th><th>状态</th><th>耗时(s)</th></tr></thead><tbody>';for(const x of steps){const cls=x.status==='failed'?'step-fail':'step-ok';html+=`<tr><td>${esc(x.step)}</td><td class="${cls}">${x.status==='failed'?'失败':'完成'}</td><td>${n(x.seconds,2)}</td></tr>`;}if(s.running&&s.current_step)html+=`<tr><td>${esc(s.current_step)}</td><td class="step-now">运行中</td><td>${n(s.current_step_elapsed||0,2)}</td></tr>`;html+='</tbody></table>';timingEl.innerHTML=html;}
function renderSummary(){const r=current;if(!r)return;const e=r.test_eval||{}, files=r.files||[];let html=`<p><b>最新日期：</b>${esc(r.latest_date)} <b>模型：</b>${esc(r.model_used)}</p>`;html+=`<p><span class="badge">准确率 ${pct(e.accuracy)}</span><span class="badge">Macro F1 ${n(e.macro_f1,4)}</span><span class="badge">Balanced Acc ${n(e.balanced_accuracy,4)}</span><span class="badge">样本 ${e.n_samples||0}</span></p>`;if(r.split_meta)html+=`<p class="small">切分：train≤${esc(r.split_meta.train_end)}，valid≤${esc(r.split_meta.valid_end)}，test≥${esc(r.split_meta.test_start)}</p>`;html+='<h3>产物文件</h3><div class="files">';for(const f of files)html+=`<a href="/api/file/${encodeURIComponent(f.name)}" target="_blank">${esc(f.name)}</a>`;html+='</div>';summaryEl.innerHTML=html;}
function rowsFor(){if(!current)return[];if(tableName==='test')return current.test_predictions||[];if(tableName==='full')return current.full_preview||[];return current.latest_predictions||[];}
function renderTable(){let rows=rowsFor();const q=filterEl.value.trim().toLowerCase();if(q)rows=rows.filter(r=>JSON.stringify(r).toLowerCase().includes(q));countEl.textContent=`显示 ${rows.length} 行`;if(!rows.length){tableEl.innerHTML='无数据';return}const cols=Object.keys(rows[0]);let html='<table><thead><tr>'+cols.map(c=>`<th>${esc(c)}</th>`).join('')+'</tr></thead><tbody>';for(const r of rows){html+='<tr>'+cols.map(c=>{const v=r[c];const isNum=typeof v==='number';return `<td>${esc(isNum?n(v, c.startsWith('prob_')?6:4):v)}</td>`}).join('')+'</tr>'}html+='</tbody></table>';tableEl.innerHTML=html;}
form.addEventListener('submit',async e=>{e.preventDefault();btn.disabled=true;logsEl.textContent='正在提交任务...';const resp=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(read())});const j=await resp.json();if(!j.ok){alert(j.msg||'启动失败');btn.disabled=false;}poll();});
document.getElementById('refresh').onclick=poll;filterEl.oninput=renderTable;document.querySelectorAll('.tab[data-table]').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab[data-table]').forEach(x=>x.classList.remove('active'));b.classList.add('active');tableName=b.dataset.table;renderTable();});init();
</script></body></html>'''


def main_web(host: str = "127.0.0.1", port: int = 7791) -> None:
    app = _build_flask_app()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print(f"板块炒作阶段预测 Web 控制台启动: http://{host}:{port}/")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="板块炒作阶段预测 Web 控制台")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7791)
    args = parser.parse_args()
    main_web(args.host, args.port)
