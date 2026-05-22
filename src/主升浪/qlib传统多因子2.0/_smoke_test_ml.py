"""ML 链路冒烟测试：使用 alpha101 + ridge。"""
from __future__ import annotations
import logging, sys, time
from pathlib import Path


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from workflow_v2 import WorkflowConfigV2, WorkflowV2

    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    cfg = WorkflowConfigV2()
    cfg.factor_libraries = ["_root"]  # 最小集，仅验证 ML 链路通畅
    cfg.future_return_mode = "max_close"  # 同时验证 max_close 口径
    cfg.holding_period = 5
    cfg.filter_method = "none"
    cfg.signal_mode = "ml"
    cfg.ml_model = "ridge"  # 最快，无需编译
    cfg.start_time = "2025-06-01"
    cfg.end_time = "2025-12-31"
    cfg.train_end_time = "2025-09-30"
    cfg.valid_end_time = "2025-10-31"
    cfg.test_start_time = "2025-11-01"
    cfg.topn = 20
    cfg.output_dir = "results_smoke_ml"

    print("=== smoke test: ML, alpha101 + _root, ridge ===")
    t0 = time.time()
    wf = WorkflowV2(cfg)
    results = wf.run()
    print(f"\n[smoke-ml] 用时 {time.time()-t0:.1f}s")
    print("[smoke-ml] performance:")
    print(results["performance"].to_string(index=False))
    print("\n[smoke-ml] selected:")
    print(results["selected_factors"])


if __name__ == "__main__":
    main()
