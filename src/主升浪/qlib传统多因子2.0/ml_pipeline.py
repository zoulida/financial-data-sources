#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore
# pyright: reportMissingImports=false
"""ML 训练与预测模块。

支持三种模型：

- ``lightgbm``：LightGBM 回归（默认；超参与 ``qlib官方/official_workflow_demo.py`` 对齐）。
- ``ridge``：sklearn Ridge 线性回归。
- ``lasso``：sklearn Lasso 线性回归。

输入：

- ``factor_panel``：``MultiIndex(datetime, instrument)`` 的长表 ``DataFrame``，列为因子名 + ``future_return``。
- ``splits``：时间分割字典 ``{"train_end": "...", "valid_end": "...", "test_start": "..."}``。

输出：

- 测试期 ``prediction``：``MultiIndex(datetime, instrument)`` 的 Series，命名为 ``score_ml``。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

VALID_MODELS = ("lightgbm", "ridge", "lasso")


@dataclass
class MLConfig:
    model: str = "lightgbm"
    train_end: str = "2025-06-30"
    valid_end: str = "2025-09-30"
    test_start: str = "2025-10-01"
    # LightGBM 默认超参（与官方 workflow demo 对齐）
    learning_rate: float = 0.0421
    num_leaves: int = 210
    max_depth: int = 8
    colsample_bytree: float = 0.8879
    subsample: float = 0.8789
    lambda_l1: float = 205.6999
    lambda_l2: float = 580.9768
    num_threads: int = 8
    num_boost_round: int = 1000
    early_stopping_rounds: int = 50
    # 线性模型超参
    alpha: float = 1.0


def _split_by_time(
    panel: pd.DataFrame,
    train_end: str,
    valid_end: str,
    test_start: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """按时间切分长表为训练/验证/测试三段。"""
    if "datetime" in panel.index.names:
        dates = panel.index.get_level_values("datetime")
    else:
        raise ValueError("ml_pipeline 输入需要 MultiIndex(datetime, instrument)")

    train_mask = dates <= pd.Timestamp(train_end)
    valid_mask = (dates > pd.Timestamp(train_end)) & (dates <= pd.Timestamp(valid_end))
    test_mask = dates >= pd.Timestamp(test_start)

    return panel[train_mask], panel[valid_mask], panel[test_mask]


def _auto_split_by_available_label(
    panel: pd.DataFrame,
    label_col: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, str]]:
    labeled = panel.dropna(subset=[label_col])
    if labeled.empty:
        raise ValueError(f"所有样本的 {label_col} 均为 NaN，无法训练")

    dates = pd.to_datetime(labeled.index.get_level_values("datetime")).normalize()
    unique_dates = pd.Index(dates.unique()).sort_values()
    if len(unique_dates) < 10:
        raise ValueError(f"可用于训练的日期过少({len(unique_dates)})，无法训练")

    train_pos = max(1, int(len(unique_dates) * 0.6) - 1)
    valid_pos = max(train_pos + 1, int(len(unique_dates) * 0.8) - 1)
    train_end = unique_dates[train_pos]
    valid_end = unique_dates[valid_pos]
    test_start = unique_dates[min(valid_pos + 1, len(unique_dates) - 1)]

    train_mask = dates <= train_end
    valid_mask = (dates > train_end) & (dates <= valid_end)
    test_mask = dates >= test_start
    meta = {
        "train_end": str(pd.Timestamp(train_end).date()),
        "valid_end": str(pd.Timestamp(valid_end).date()),
        "test_start": str(pd.Timestamp(test_start).date()),
    }
    return labeled[train_mask], labeled[valid_mask], labeled[test_mask], meta


def _train_lightgbm(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    feature_cols: List[str],
    label_col: str,
    config: MLConfig,
):
    try:
        import lightgbm as lgb
    except ImportError as exc:
        raise ImportError("使用 lightgbm 模型需要先 pip install lightgbm") from exc

    train_clean = train_df.dropna(subset=[label_col]).copy()
    valid_clean = valid_df.dropna(subset=[label_col]).copy()
    if not train_clean.empty:
        train_clean[feature_cols] = (
            train_clean[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        )
    if not valid_clean.empty:
        valid_clean[feature_cols] = (
            valid_clean[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        )
    if train_clean.empty:
        date_min = None
        date_max = None
        try:
            dates = train_df.index.get_level_values("datetime")
            date_min = str(pd.to_datetime(dates.min()).date()) if len(dates) else None
            date_max = str(pd.to_datetime(dates.max()).date()) if len(dates) else None
        except Exception:
            pass

        msg = (
            "训练集为空：在训练时间段内，标签有效样本为 0 行。\n"
            f"- model={config.model}\n"
            f"- train_end={config.train_end}, valid_end={config.valid_end}, test_start={config.test_start}\n"
            f"- 训练段原始行数={len(train_df)}, dropna后行数={len(train_clean)}"
        )
        if date_min is not None and date_max is not None:
            msg += f"\n- 训练段实际日期范围={date_min} ~ {date_max}"
        msg += (
            "\n\n可能原因：\n"
            "1) 训练时间段没有覆盖到你的数据日期（train_end 太早或 start_time 太晚）。\n"
            "2) 训练段里 future_return 大面积缺失（NaN），导致无可用标签样本。\n"
            "   - 可尝试缩短 holding_period / 改 future_return_mode。"
        )
        raise ValueError(msg)

    train_set = lgb.Dataset(train_clean[feature_cols], label=train_clean[label_col])
    valid_sets = [train_set]
    valid_names = ["train"]
    if not valid_clean.empty:
        valid_set = lgb.Dataset(valid_clean[feature_cols], label=valid_clean[label_col])
        valid_sets.append(valid_set)
        valid_names.append("valid")

    params = {
        "objective": "regression",
        "metric": "l2",
        "learning_rate": config.learning_rate,
        "num_leaves": config.num_leaves,
        "max_depth": config.max_depth,
        "feature_fraction": config.colsample_bytree,
        "bagging_fraction": config.subsample,
        "bagging_freq": 1,
        "lambda_l1": config.lambda_l1,
        "lambda_l2": config.lambda_l2,
        "num_threads": config.num_threads,
        "verbose": -1,
    }
    callbacks = [lgb.log_evaluation(period=0)]
    if not valid_clean.empty:
        callbacks.append(lgb.early_stopping(stopping_rounds=config.early_stopping_rounds, verbose=False))

    model = lgb.train(
        params,
        train_set,
        num_boost_round=config.num_boost_round,
        valid_sets=valid_sets,
        valid_names=valid_names,
        callbacks=callbacks,
    )
    return model, lambda df: model.predict(df[feature_cols], num_iteration=model.best_iteration)


def _train_linear(
    train_df: pd.DataFrame,
    feature_cols: List[str],
    label_col: str,
    config: MLConfig,
    model_kind: str,
):
    try:
        from sklearn.linear_model import Lasso, Ridge
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise ImportError("使用 ridge/lasso 模型需要先 pip install scikit-learn") from exc

    train_clean = train_df.dropna(subset=[label_col]).copy()
    if not train_clean.empty:
        train_clean[feature_cols] = (
            train_clean[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        )
    if train_clean.empty:
        date_min = None
        date_max = None
        try:
            dates = train_df.index.get_level_values("datetime")
            date_min = str(pd.to_datetime(dates.min()).date()) if len(dates) else None
            date_max = str(pd.to_datetime(dates.max()).date()) if len(dates) else None
        except Exception:
            pass

        msg = (
            "训练集为空：在训练时间段内，标签有效样本为 0 行。\n"
            f"- model={model_kind}\n"
            f"- train_end={config.train_end}, valid_end={config.valid_end}, test_start={config.test_start}\n"
            f"- 训练段原始行数={len(train_df)}, dropna后行数={len(train_clean)}"
        )
        if date_min is not None and date_max is not None:
            msg += f"\n- 训练段实际日期范围={date_min} ~ {date_max}"
        msg += (
            "\n\n可能原因：\n"
            "1) 训练时间段没有覆盖到你的数据日期（train_end 太早或 start_time 太晚）。\n"
            "2) 训练段里 future_return 大面积缺失（NaN），导致无可用标签样本。"
        )
        raise ValueError(msg)

    estimator = Ridge(alpha=config.alpha) if model_kind == "ridge" else Lasso(alpha=config.alpha)
    pipeline = Pipeline([("scaler", StandardScaler()), ("model", estimator)])
    pipeline.fit(train_clean[feature_cols], train_clean[label_col])
    return pipeline, lambda df: pipeline.predict(df[feature_cols])


def train_predict(
    long_panel: pd.DataFrame,
    feature_cols: List[str],
    label_col: str,
    config: MLConfig,
) -> Tuple[pd.Series, Dict[str, object]]:
    """训练 + 预测，返回测试期 prediction（与 long_panel 同 MultiIndex）。

    Args:
        long_panel: 长表 ``DataFrame``，``MultiIndex(datetime, instrument)``，列含 feature_cols 与 label_col。
        feature_cols: 因子列名列表（已过滤后的因子）。
        label_col: 标签列名（一般为 ``future_return``）。
        config: 训练配置。

    Returns:
        ``(prediction_series, info_dict)``。``info_dict`` 包含训练元信息。
    """
    if config.model not in VALID_MODELS:
        raise ValueError(f"model 必须是 {VALID_MODELS}，当前为 {config.model}")

    train_df, valid_df, test_df = _split_by_time(
        long_panel, config.train_end, config.valid_end, config.test_start
    )
    try:
        all_dates = long_panel.index.get_level_values("datetime")
        all_min = str(pd.to_datetime(all_dates.min()).date()) if len(all_dates) else None
        all_max = str(pd.to_datetime(all_dates.max()).date()) if len(all_dates) else None
        LOGGER.info("ML 数据日期范围: %s ~ %s", all_min, all_max)
    except Exception:
        pass
    LOGGER.info(
        "ML 时间切分: train=%d 条, valid=%d 条, test=%d 条",
        len(train_df), len(valid_df), len(test_df),
    )

    if train_df.dropna(subset=[label_col]).empty:
        train_df, valid_df, test_df, meta = _auto_split_by_available_label(long_panel, label_col)
        LOGGER.warning(
            "ML 重新按可用标签样本自动切分: train_end=%s, valid_end=%s, test_start=%s",
            meta["train_end"], meta["valid_end"], meta["test_start"],
        )

    if test_df.empty:
        raise ValueError("测试集为空，请检查 test_start 是否在数据末端之后")

    if config.model == "lightgbm":
        model, predict_fn = _train_lightgbm(train_df, valid_df, feature_cols, label_col, config)
    else:
        model, predict_fn = _train_linear(train_df, feature_cols, label_col, config, config.model)

    test_clean = test_df.copy()
    test_clean[feature_cols] = test_clean[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if test_clean.empty:
        raise ValueError("测试集为空，无法预测")
    test_clean["score_ml"] = predict_fn(test_clean)
    prediction = test_clean["score_ml"]

    info = {
        "model_name": config.model,
        "n_train": int(len(train_df)),
        "n_valid": int(len(valid_df)),
        "n_test": int(len(test_df)),
        "n_features": int(len(feature_cols)),
        "feature_columns": list(feature_cols),
    }
    if config.model == "lightgbm":
        try:
            importance = model.feature_importance(importance_type="gain")
            info["feature_importance"] = dict(zip(feature_cols, [float(v) for v in importance]))
            info["best_iteration"] = int(getattr(model, "best_iteration", 0) or 0)
        except Exception:  # pragma: no cover
            pass
    return prediction, info
