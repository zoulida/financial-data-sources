"""端到端冒烟测试：最小配置跑一遍 traditional 链路。

注意：必须用 ``if __name__ == "__main__":`` 守卫，避免 Windows 下 multiprocessing
spawn 子进程时重新执行整个脚本（即使 workflow 已强制 threading backend，标准做法仍应保留）。
"""
from __future__ import annotations
import logging, sys, time
from pathlib import Path


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from workflow_v2 import WorkflowConfigV2, WorkflowV2

    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    cfg = WorkflowConfigV2()
    cfg.factor_libraries = ["_root"]
    cfg.future_return_mode = "holding_close"
    cfg.holding_period = 1
    cfg.filter_method = "none"
    cfg.signal_mode = "traditional"
    cfg.start_time = "2025-06-01"
    cfg.end_time = "2025-12-31"
    cfg.topn = 20
    cfg.output_dir = "results_smoke"
    # 默认 csi300 中市值在 20-150 亿区间股票较少，先放宽到 1000 亿验证过滤功能
    cfg.enable_market_cap_filter = True
    cfg.min_market_cap_yi = 20.0
    cfg.max_market_cap_yi = 1000.0
    cfg.enable_price_filter = True
    cfg.min_close_price = 2.0
    cfg.max_close_price = 50.0

    print("=== smoke test: traditional, _root only ===")
    t0 = time.time()
    wf = WorkflowV2(cfg)
    results = wf.run()
    print(f"\n[smoke] 用时 {time.time()-t0:.1f}s")
    print("[smoke] performance:")
    print(results["performance"].to_string(index=False))


if __name__ == "__main__":
    main()
