# -*- coding: utf-8 -*-
"""多分类训练、评估与预测。

- 默认模型：LightGBM 多分类（``objective=multiclass``）。
- 兜底模型：sklearn 的 ``HistGradientBoostingClassifier``（无须 LightGBM）。
- 严格按时间切分训练/验证/测试，禁止随机切分。
- 输出：测试期与最新交易日的板块四阶段概率与主分类。
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .label_builder import INT_TO_LABEL, LABEL_ORDER, LABEL_TO_INT

LOGGER = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """模型训练配置。"""

    model: str = "lightgbm"  # lightgbm | hgb
    train_ratio: float = 0.6
    valid_ratio: float = 0.2
    # LightGBM 参数
    num_leaves: int = 63
    max_depth: int = -1
    learning_rate: float = 0.05
    min_data_in_leaf: int = 50
    feature_fraction: float = 0.9
    bagging_fraction: float = 0.9
    bagging_freq: int = 5
    lambda_l1: float = 0.0
    lambda_l2: float = 1.0
    num_boost_round: int = 800
    early_stopping_rounds: int = 50
    num_threads: int = 8
    # 公共
    random_state: int = 20260522
    use_class_weight: bool = True
    feature_blacklist: Sequence[str] = field(default_factory=tuple)


def _split_by_time(
    long_df: pd.DataFrame,
    train_ratio: float,
    valid_ratio: float,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, str]]:
    if "datetime" not in long_df.index.names:
        raise ValueError("long_df 需要 MultiIndex(datetime, sector)")
    dates = pd.to_datetime(long_df.index.get_level_values("datetime"))
    unique_dates = pd.Index(dates.unique()).sort_values()
    n = len(unique_dates)
    if n < 30:
        raise ValueError(f"可用日期太少 ({n})，无法稳定切分")
    train_end_idx = max(1, int(n * train_ratio) - 1)
    valid_end_idx = max(train_end_idx + 1, int(n * (train_ratio + valid_ratio)) - 1)
    train_end = unique_dates[train_end_idx]
    valid_end = unique_dates[valid_end_idx]
    test_start = unique_dates[min(valid_end_idx + 1, n - 1)]

    date_index = pd.to_datetime(long_df.index.get_level_values("datetime"))
    train_mask = date_index <= train_end
    valid_mask = (date_index > train_end) & (date_index <= valid_end)
    test_mask = date_index >= test_start

    meta = {
        "train_end": str(pd.Timestamp(train_end).date()),
        "valid_end": str(pd.Timestamp(valid_end).date()),
        "test_start": str(pd.Timestamp(test_start).date()),
        "n_dates": int(n),
    }
    return long_df[train_mask], long_df[valid_mask], long_df[test_mask], meta


def _compute_class_weights(y: np.ndarray, n_classes: int) -> Dict[int, float]:
    weights: Dict[int, float] = {}
    total = len(y)
    if total == 0:
        return {i: 1.0 for i in range(n_classes)}
    for cls in range(n_classes):
        cnt = int((y == cls).sum())
        if cnt == 0:
            weights[cls] = 1.0
        else:
            weights[cls] = total / (n_classes * cnt)
    return weights


def _sample_weight_from_class_weight(y: np.ndarray, class_weight: Dict[int, float]) -> np.ndarray:
    return np.array([class_weight.get(int(label), 1.0) for label in y], dtype=float)


def _train_lightgbm(
    X_train: pd.DataFrame, y_train: np.ndarray,
    X_valid: pd.DataFrame, y_valid: np.ndarray,
    feature_cols: List[str], n_classes: int,
    config: ModelConfig,
):
    try:
        import lightgbm as lgb
    except ImportError as exc:
        raise ImportError("使用 LightGBM 需要先 pip install lightgbm") from exc

    class_weight: Optional[Dict[int, float]] = None
    if config.use_class_weight:
        class_weight = _compute_class_weights(y_train, n_classes)

    sample_weight = _sample_weight_from_class_weight(y_train, class_weight) if class_weight else None
    valid_weight = _sample_weight_from_class_weight(y_valid, class_weight) if class_weight is not None and len(y_valid) else None

    train_set = lgb.Dataset(X_train[feature_cols], label=y_train, weight=sample_weight)
    valid_sets = [train_set]
    valid_names = ["train"]
    if len(y_valid):
        valid_set = lgb.Dataset(
            X_valid[feature_cols], label=y_valid, weight=valid_weight, reference=train_set
        )
        valid_sets.append(valid_set)
        valid_names.append("valid")

    params = {
        "objective": "multiclass",
        "num_class": n_classes,
        "metric": "multi_logloss",
        "learning_rate": config.learning_rate,
        "num_leaves": config.num_leaves,
        "max_depth": config.max_depth,
        "min_data_in_leaf": config.min_data_in_leaf,
        "feature_fraction": config.feature_fraction,
        "bagging_fraction": config.bagging_fraction,
        "bagging_freq": config.bagging_freq,
        "lambda_l1": config.lambda_l1,
        "lambda_l2": config.lambda_l2,
        "num_threads": config.num_threads,
        "verbose": -1,
        "seed": config.random_state,
    }

    callbacks = [lgb.log_evaluation(period=0)]
    if len(y_valid) > 0:
        callbacks.append(
            lgb.early_stopping(stopping_rounds=config.early_stopping_rounds, verbose=False)
        )

    model = lgb.train(
        params,
        train_set,
        num_boost_round=config.num_boost_round,
        valid_sets=valid_sets,
        valid_names=valid_names,
        callbacks=callbacks,
    )

    def _predict_proba(df: pd.DataFrame) -> np.ndarray:
        return np.asarray(
            model.predict(df[feature_cols], num_iteration=model.best_iteration)
        )

    info: Dict[str, Any] = {"best_iteration": int(getattr(model, "best_iteration", 0) or 0)}
    try:
        importance = model.feature_importance(importance_type="gain")
        info["feature_importance"] = {
            str(name): float(val) for name, val in zip(feature_cols, importance)
        }
    except Exception:
        pass
    if class_weight is not None:
        info["class_weight"] = {int(k): float(v) for k, v in class_weight.items()}
    return model, _predict_proba, info


def _train_hgb(
    X_train: pd.DataFrame, y_train: np.ndarray,
    feature_cols: List[str], n_classes: int,
    config: ModelConfig,
):
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier
    except ImportError as exc:
        raise ImportError("使用 hgb 需要 sklearn") from exc

    class_weight: Optional[Dict[int, float]] = None
    sample_weight = None
    if config.use_class_weight:
        class_weight = _compute_class_weights(y_train, n_classes)
        sample_weight = _sample_weight_from_class_weight(y_train, class_weight)

    model = HistGradientBoostingClassifier(
        learning_rate=config.learning_rate,
        max_iter=config.num_boost_round,
        max_leaf_nodes=config.num_leaves,
        min_samples_leaf=config.min_data_in_leaf,
        l2_regularization=config.lambda_l2,
        random_state=config.random_state,
    )
    X = X_train[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    model.fit(X, y_train, sample_weight=sample_weight)

    def _predict_proba(df: pd.DataFrame) -> np.ndarray:
        Xp = df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return np.asarray(model.predict_proba(Xp))

    info: Dict[str, Any] = {}
    if class_weight is not None:
        info["class_weight"] = {int(k): float(v) for k, v in class_weight.items()}
    return model, _predict_proba, info


def _classification_report(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> Dict[str, Any]:
    report: Dict[str, Any] = {}
    confusion = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        if 0 <= int(t) < n_classes and 0 <= int(p) < n_classes:
            confusion[int(t), int(p)] += 1
    report["confusion_matrix"] = confusion.tolist()
    report["labels"] = list(LABEL_ORDER)

    f1_scores: List[float] = []
    per_class: Dict[str, Dict[str, float]] = {}
    for cls in range(n_classes):
        tp = int(confusion[cls, cls])
        fp = int(confusion[:, cls].sum() - tp)
        fn = int(confusion[cls, :].sum() - tp)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[INT_TO_LABEL.get(cls, str(cls))] = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "support": int(confusion[cls, :].sum()),
        }
        f1_scores.append(f1)

    total = int(confusion.sum())
    correct = int(np.trace(confusion))
    accuracy = correct / total if total else 0.0
    macro_f1 = float(np.mean(f1_scores)) if f1_scores else 0.0

    # balanced accuracy = mean(per-class recall)
    recalls = [per_class[name]["recall"] for name in per_class]
    balanced = float(np.mean(recalls)) if recalls else 0.0

    report["per_class"] = per_class
    report["accuracy"] = float(accuracy)
    report["macro_f1"] = macro_f1
    report["balanced_accuracy"] = balanced
    report["n_samples"] = total
    return report


def train_and_predict(
    feature_long: pd.DataFrame,
    labels_long: pd.DataFrame,
    config: Optional[ModelConfig] = None,
) -> Dict[str, Any]:
    """完整训练 + 评估 + 全期预测。

    Args:
        feature_long: ``MultiIndex(datetime, sector)`` 的特征长表。
        labels_long: ``MultiIndex(datetime, sector)`` 的标签长表，需含 ``label_id`` 列。
        config: 训练配置。

    Returns:
        包含训练信息、评估指标、测试集预测、最新预测、特征重要性的 dict。
    """
    config = config or ModelConfig()
    n_classes = len(LABEL_ORDER)

    label_id = labels_long["label_id"].dropna().astype(int)
    aligned = feature_long.join(label_id.rename("label_id"), how="left")

    feature_cols = [
        c for c in feature_long.columns
        if c not in set(config.feature_blacklist) and pd.api.types.is_numeric_dtype(feature_long[c])
    ]
    if not feature_cols:
        raise ValueError("没有可用的数值特征列")

    labeled = aligned.dropna(subset=["label_id"])
    if labeled.empty:
        raise ValueError("没有任何带标签的样本，请检查 label_builder 配置")

    train_df, valid_df, test_df, split_meta = _split_by_time(
        labeled, config.train_ratio, config.valid_ratio
    )
    LOGGER.info(
        "时间切分：train=%d 行 (≤%s)，valid=%d 行 (≤%s)，test=%d 行 (≥%s)",
        len(train_df), split_meta["train_end"],
        len(valid_df), split_meta["valid_end"],
        len(test_df), split_meta["test_start"],
    )

    if train_df.empty:
        raise ValueError("训练集为空，无法训练")

    X_train = train_df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y_train = train_df["label_id"].astype(int).values
    X_valid = valid_df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y_valid = valid_df["label_id"].astype(int).values if not valid_df.empty else np.array([], dtype=int)

    if config.model == "lightgbm":
        try:
            model, predict_proba, train_info = _train_lightgbm(
                X_train, y_train, X_valid, y_valid, feature_cols, n_classes, config
            )
            model_used = "lightgbm"
        except ImportError as exc:
            LOGGER.warning("LightGBM 不可用（%s），降级到 HistGradientBoostingClassifier", exc)
            model, predict_proba, train_info = _train_hgb(X_train, y_train, feature_cols, n_classes, config)
            model_used = "hgb"
    elif config.model == "hgb":
        model, predict_proba, train_info = _train_hgb(X_train, y_train, feature_cols, n_classes, config)
        model_used = "hgb"
    else:
        raise ValueError(f"未知 model={config.model}，支持 lightgbm | hgb")

    # 测试集评估
    test_eval: Dict[str, Any] = {}
    test_predictions: Optional[pd.DataFrame] = None
    if not test_df.empty:
        test_proba = predict_proba(test_df)
        test_pred = test_proba.argmax(axis=1)
        test_eval = _classification_report(test_df["label_id"].astype(int).values, test_pred, n_classes)
        test_predictions = pd.DataFrame(
            test_proba,
            index=test_df.index,
            columns=[f"prob_{INT_TO_LABEL[i]}" for i in range(n_classes)],
        )
        test_predictions["pred_id"] = test_pred
        test_predictions["pred_label"] = [INT_TO_LABEL[int(i)] for i in test_pred]
        test_predictions["true_label_id"] = test_df["label_id"].astype(int).values
        test_predictions["true_label"] = [INT_TO_LABEL.get(int(i), "") for i in test_predictions["true_label_id"]]

    # 全期预测（包含没有标签的样本，用于业务输出）
    full_proba = predict_proba(aligned)
    full_pred = full_proba.argmax(axis=1)
    full_predictions = pd.DataFrame(
        full_proba,
        index=aligned.index,
        columns=[f"prob_{INT_TO_LABEL[i]}" for i in range(n_classes)],
    )
    full_predictions["pred_id"] = full_pred
    full_predictions["pred_label"] = [INT_TO_LABEL[int(i)] for i in full_pred]

    # 最新一日预测
    latest_date = aligned.index.get_level_values("datetime").max()
    latest_predictions = full_predictions.xs(latest_date, level="datetime").copy()
    latest_predictions = latest_predictions.sort_values(
        f"prob_{INT_TO_LABEL[LABEL_TO_INT['正在炒作']]}", ascending=False
    )

    return {
        "model": model,
        "model_used": model_used,
        "feature_cols": list(feature_cols),
        "split_meta": split_meta,
        "train_info": train_info,
        "test_eval": test_eval,
        "test_predictions": test_predictions,
        "full_predictions": full_predictions,
        "latest_predictions": latest_predictions,
        "latest_date": str(pd.Timestamp(latest_date).date()),
        "config": asdict(config),
    }


def save_artifacts(result: Dict[str, Any], output_dir: str | Path) -> Dict[str, str]:
    """把核心结果落盘到 output_dir，返回各产物路径。"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    paths: Dict[str, str] = {}

    if result.get("test_predictions") is not None:
        test_path = out / "test_predictions.csv"
        result["test_predictions"].to_csv(test_path, encoding="utf-8-sig")
        paths["test_predictions"] = str(test_path)

    full_path = out / "full_predictions.csv"
    result["full_predictions"].to_csv(full_path, encoding="utf-8-sig")
    paths["full_predictions"] = str(full_path)

    latest_path = out / f"latest_predictions_{result['latest_date']}.csv"
    result["latest_predictions"].to_csv(latest_path, encoding="utf-8-sig")
    paths["latest_predictions"] = str(latest_path)

    info_path = out / "model_info.json"
    payload = {
        "model_used": result["model_used"],
        "split_meta": result["split_meta"],
        "config": result["config"],
        "train_info": {k: v for k, v in result["train_info"].items() if k != "feature_importance"},
        "test_eval": result["test_eval"],
        "latest_date": result["latest_date"],
    }
    if "feature_importance" in result["train_info"]:
        importance_path = out / "feature_importance.csv"
        importance = result["train_info"]["feature_importance"]
        pd.Series(importance).rename("importance").sort_values(ascending=False).to_csv(
            importance_path, encoding="utf-8-sig"
        )
        paths["feature_importance"] = str(importance_path)
    info_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["model_info"] = str(info_path)
    return paths
