"""主升浪因子评估结果输出（CSV + PNG）。"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

_CJK_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    "KaiTi",
    "FangSong",
    "DengXian",
]


def _configure_plot_font() -> None:
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in _CJK_FONT_CANDIDATES:
        if font_name in available_fonts:
            plt.rcParams["font.sans-serif"] = [font_name]
            plt.rcParams["axes.unicode_minus"] = False
            return
    plt.rcParams["axes.unicode_minus"] = False


_configure_plot_font()


def save_factor_blastoff_report(
    output_root: Path,
    factor_name: str,
    metrics_df: pd.DataFrame,
    topk_picks: dict[int, pd.DataFrame],
    snapshot_date: str | None,
    ic_summary_df: pd.DataFrame | None = None,
    events_summary_df: pd.DataFrame | None = None,
) -> Path:
    """保存单因子评估结果到 output_root/<factor_name>/。

    返回因子目录路径。
    """
    factor_dir = output_root / factor_name.replace("/", "_")
    factor_dir.mkdir(parents=True, exist_ok=True)

    # 1. metrics CSV
    metrics_df.to_csv(factor_dir / "metrics.csv", index=False, encoding="utf-8-sig")

    if ic_summary_df is not None and not ic_summary_df.empty:
        ic_summary_df.to_csv(factor_dir / "ic_reference.csv", index=False, encoding="utf-8-sig")

    if events_summary_df is not None and not events_summary_df.empty:
        events_summary_df.to_csv(factor_dir / "events_summary.csv", index=False, encoding="utf-8-sig")

    # 2. Top-K 末期个股清单
    for k, picks_df in topk_picks.items():
        picks_filename = f"top_{k}_picks_{snapshot_date or 'latest'}.csv"
        picks_df.to_csv(factor_dir / picks_filename, index=False, encoding="utf-8-sig")

    # 3. Precision@K 柱状图
    if not metrics_df.empty and "Precision@K" in metrics_df.columns:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            fig, ax = plt.subplots(figsize=(8, 4.5))
            x_labels = metrics_df["TopK"].astype(str).tolist()
            ax.bar(x_labels, metrics_df["Precision@K"].fillna(0).tolist(), color="#cc3333")
            ax.set_title(f"{factor_name} 主升浪命中率 Precision@K")
            ax.set_xlabel("Top-K")
            ax.set_ylabel("Precision@K")
            for i, value in enumerate(metrics_df["Precision@K"].fillna(0).tolist()):
                ax.text(i, value, f"{value:.2%}", ha="center", va="bottom")
            fig.tight_layout()
            fig.savefig(factor_dir / "precision_at_k.png", dpi=150)
            plt.close(fig)

    # 4. 平均最大涨幅柱状图
    if not metrics_df.empty and "平均最大涨幅" in metrics_df.columns:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            fig, ax = plt.subplots(figsize=(8, 4.5))
            x_labels = metrics_df["TopK"].astype(str).tolist()
            ax.bar(x_labels, metrics_df["平均最大涨幅"].fillna(0).tolist(), color="#226699")
            ax.set_title(f"{factor_name} TopK 平均最大涨幅")
            ax.set_xlabel("Top-K")
            ax.set_ylabel("平均最大涨幅")
            for i, value in enumerate(metrics_df["平均最大涨幅"].fillna(0).tolist()):
                ax.text(i, value, f"{value:.2%}", ha="center", va="bottom")
            fig.tight_layout()
            fig.savefig(factor_dir / "max_return_at_k.png", dpi=150)
            plt.close(fig)

    return factor_dir


def save_overall_summary(
    output_root: Path,
    overall_rows: list[dict[str, Any]],
) -> None:
    """保存所有因子的综合排名摘要。"""
    if not overall_rows:
        return
    summary_df = pd.DataFrame(overall_rows)
    summary_df.to_csv(output_root / "overall_summary.csv", index=False, encoding="utf-8-sig")


def plot_time_to_peak_distribution(
    output_path: Path,
    time_to_peak_values: np.ndarray,
    title: str,
) -> None:
    """绘制起爆速度分布直方图。"""
    valid = time_to_peak_values[~np.isnan(time_to_peak_values)]
    valid = valid[valid > 0]
    if valid.size == 0:
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.hist(valid, bins=20, color="#669933", edgecolor="white")
        ax.set_title(title)
        ax.set_xlabel("起爆速度 (天)")
        ax.set_ylabel("频次")
        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
