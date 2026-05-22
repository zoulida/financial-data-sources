# -*- coding: utf-8 -*-
"""离线冒烟测试：合成行情 → 特征 → 标签 → 模型，不依赖 XtQuant/Qlib。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR.parent.parent))

from src.板块炒作阶段预测 import feature_builder, label_builder, model_pipeline  # noqa: E402
from src.板块炒作阶段预测.code_utils import qlib_to_xt, xt_to_qlib  # noqa: E402


def _make_synthetic_panel(n_days: int = 300, n_stocks: int = 80, seed: int = 42):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-02", periods=n_days)
    # 用 SH/SZ 主板代码
    codes_xt = []
    for i in range(n_stocks):
        if i % 2 == 0:
            codes_xt.append(f"{600000 + i:06d}.SH")
        else:
            codes_xt.append(f"{i:06d}.SZ")
    codes_qlib = [xt_to_qlib(c) for c in codes_xt]

    # 简单收益模拟：每只股票按板块漂移
    n_sectors = 6
    sector_assign = {c: i % n_sectors for i, c in enumerate(codes_xt)}
    sector_drift = rng.normal(0.0005, 0.001, n_sectors)
    sector_vol = rng.uniform(0.01, 0.03, n_sectors)

    returns = np.zeros((n_days, n_stocks))
    for j, c in enumerate(codes_xt):
        s = sector_assign[c]
        # 加一段"炒作 -> 末期"事件：第 100~150 日板块 0 飙升，之后回落
        base = rng.normal(sector_drift[s], sector_vol[s], n_days)
        if s == 0:
            base[100:130] += 0.015
            base[130:170] -= 0.012
        if s == 1:
            base[180:210] += 0.012
            base[210:230] -= 0.008
        returns[:, j] = base

    close = 10.0 * np.exp(np.cumsum(returns, axis=0))
    volume = rng.uniform(1e5, 5e5, (n_days, n_stocks))
    # 让正在炒作板块的成交额放大
    for j, c in enumerate(codes_xt):
        s = sector_assign[c]
        if s == 0:
            volume[100:140, j] *= 3.0
        if s == 1:
            volume[180:220, j] *= 2.5
    amount = close * volume

    panel = {
        "close": pd.DataFrame(close, index=dates, columns=codes_qlib),
        "open": pd.DataFrame(close * 0.999, index=dates, columns=codes_qlib),
        "high": pd.DataFrame(close * 1.005, index=dates, columns=codes_qlib),
        "low": pd.DataFrame(close * 0.995, index=dates, columns=codes_qlib),
        "volume": pd.DataFrame(volume, index=dates, columns=codes_qlib),
        "amount": pd.DataFrame(amount, index=dates, columns=codes_qlib),
        "vwap": pd.DataFrame(close, index=dates, columns=codes_qlib),
    }

    universe = {}
    for s in range(n_sectors):
        members = [c for c, sec in sector_assign.items() if sec == s]
        universe[f"概念{s}"] = members
    return panel, universe


def main() -> int:
    panel, universe = _make_synthetic_panel()
    print("[1/4] 合成行情：close.shape =", panel["close"].shape, ", 板块数 =", len(universe))

    feat_cfg = feature_builder.FeatureConfig(min_members_for_feature=5)
    feature_long, intermediates = feature_builder.build_sector_feature_table(
        panel, universe, feat_cfg
    )
    print("[2/4] 特征长表 shape =", feature_long.shape, ", 列数 =", feature_long.shape[1])
    assert feature_long.index.names == ["datetime", "sector"], feature_long.index.names

    label_cfg = label_builder.LabelConfig(horizon=10, short_horizon=5, long_horizon=20)
    labels_long, debug_panels = label_builder.build_labels(intermediates, label_cfg)
    print("[3/4] 标签长表 shape =", labels_long.shape)
    print("   标签分布：")
    print(labels_long["label"].value_counts())

    model_cfg = model_pipeline.ModelConfig(
        model="lightgbm",
        train_ratio=0.6,
        valid_ratio=0.2,
        num_boost_round=100,
        early_stopping_rounds=20,
    )
    result = model_pipeline.train_and_predict(feature_long, labels_long, model_cfg)
    print("[4/4] 训练完成 model_used =", result["model_used"],
          ", split_meta =", result["split_meta"])
    print("   测试评估 macro_f1 =", result["test_eval"].get("macro_f1"),
          ", balanced_acc =", result["test_eval"].get("balanced_accuracy"),
          ", accuracy =", result["test_eval"].get("accuracy"))
    print("   最新一日 latest_predictions head:")
    print(result["latest_predictions"].head(6).to_string())

    # 验证代码转换
    assert xt_to_qlib("600000.SH") == "SH600000"
    assert qlib_to_xt("SH600000") == "600000.SH"

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
