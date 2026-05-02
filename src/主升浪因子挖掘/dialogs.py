"""主升浪因子挖掘 GUI 对话框。

设计思路：
- 模仿 src/多因子/main.py 的 Tkinter 风格；
- 单一对话框搞定：日期范围 / 因子勾选 / 事件参数 / Top-K / 缓存开关；
- 不做多 tab。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import ttk

from src.主升浪因子挖掘 import config
from src.主升浪因子挖掘.factor_registry import FACTOR_REGISTRY
from src.多因子.data_loader import get_strategy_date_range


def _load_last_run_config() -> dict[str, Any]:
    if not config.LAST_RUN_PATH.exists():
        return {}
    try:
        data = json.loads(config.LAST_RUN_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        print(f"[配置] 读取 {config.LAST_RUN_PATH.name} 失败：{exc}")
        return {}
    return data if isinstance(data, dict) else {}


def save_last_run_config(run_config: dict[str, Any]) -> None:
    try:
        config.LAST_RUN_PATH.write_text(
            json.dumps(run_config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:  # pragma: no cover
        print(f"[配置] 写入 {config.LAST_RUN_PATH.name} 失败：{exc}")


class BlastoffRunDialog:
    """主升浪运行参数对话框。"""

    def __init__(self) -> None:
        self.result: dict[str, Any] | None = None

        latest_start, latest_end, _ = get_strategy_date_range()
        last_run = _load_last_run_config()

        default_start = str(last_run.get("start_date") or latest_start)
        default_end = str(last_run.get("end_date") or latest_end)
        default_forward_days = int(last_run.get("forward_days", config.BLASTOFF_FORWARD_DAYS))
        default_return_threshold = float(last_run.get("return_threshold", config.BLASTOFF_RETURN_THRESHOLD))
        default_max_drawdown = float(last_run.get("max_drawdown", config.BLASTOFF_MAX_DRAWDOWN))
        # top_k_list 在 .last_run.json 里以 list 形式存储，这里要还原成 "10,20,50,100" 文本，
        # 否则恢复后会拿到 "[10, 20, 50, 100]" 这种带中括号的字符串，下次校验会失败。
        last_top_k = last_run.get("top_k_list")
        if isinstance(last_top_k, list) and last_top_k:
            default_top_k = ",".join(str(int(k)) for k in last_top_k)
        elif isinstance(last_top_k, str) and last_top_k.strip():
            default_top_k = last_top_k.strip().strip("[]")
        else:
            default_top_k = ",".join(str(k) for k in config.TOP_K_LIST)
        default_use_event_cache = bool(last_run.get("use_event_cache", True))
        default_use_batch_data_cache = bool(last_run.get("use_batch_data_cache", False))
        default_selected_factors = list(last_run.get("selected_factors") or list(FACTOR_REGISTRY.keys()))
        default_enable_combo = bool(last_run.get("enable_combo_backtest", True))
        default_corr_threshold = float(last_run.get("corr_threshold", 0.8))
        default_hold_num = int(last_run.get("hold_num", 26))

        self.root = tk.Tk()
        self.root.title("主升浪因子挖掘 - 运行参数")
        # 允许自由缩放与最大化
        self.root.resizable(True, True)
        self.root.minsize(560, 480)
        self._center_window(680, 760)

        # ===== 顶层布局：上方可滚动表单区 + 下方固定按钮区 =====
        # 按钮区先 pack 到底部，确保始终可见，不会被表单挤出窗口外
        bottom_bar = ttk.Frame(self.root, padding=(16, 8))
        bottom_bar.pack(side="bottom", fill="x")

        # 错误提示放在按钮区上方
        self.message_var = tk.StringVar(value="")
        ttk.Label(bottom_bar, textvariable=self.message_var, foreground="#cc3333").pack(side="left")
        ttk.Button(bottom_bar, text="取消", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(bottom_bar, text="运行", command=self._confirm).pack(side="right")

        # 主滚动区域
        outer_frame = ttk.Frame(self.root)
        outer_frame.pack(side="top", fill="both", expand=True)

        main_canvas = tk.Canvas(outer_frame, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=main_canvas.yview)
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        main_scrollbar.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)

        container = ttk.Frame(main_canvas, padding=16)
        container_window = main_canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_container_configure(event: tk.Event) -> None:
            del event
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event) -> None:
            # 让内部 frame 宽度跟随 canvas，避免左侧出现大量空白
            main_canvas.itemconfigure(container_window, width=event.width)

        container.bind("<Configure>", _on_container_configure)
        main_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event: tk.Event) -> None:
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        ttk.Label(
            container, text="主升浪因子挖掘", font=("Microsoft YaHei", 14, "bold")
        ).pack(anchor="w")
        ttk.Label(
            container,
            text="选择日期范围、事件参数、因子组合，点击运行开始评估。",
            foreground="#666666",
        ).pack(anchor="w", pady=(4, 12))

        # ===== 日期范围 =====
        date_frame = ttk.LabelFrame(container, text="日期范围 (YYYYMMDD)", padding=8)
        date_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(date_frame, text="开始日期").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.start_var = tk.StringVar(value=default_start)
        ttk.Entry(date_frame, textvariable=self.start_var, width=14).grid(row=0, column=1, sticky="w")
        ttk.Label(date_frame, text="结束日期").grid(row=0, column=2, sticky="w", padx=(16, 8))
        self.end_var = tk.StringVar(value=default_end)
        ttk.Entry(date_frame, textvariable=self.end_var, width=14).grid(row=0, column=3, sticky="w")
        ttk.Button(
            date_frame, text="更新到最新", command=self._refresh_latest_dates
        ).grid(row=0, column=4, sticky="w", padx=(16, 0))

        # ===== 事件参数 =====
        event_frame = ttk.LabelFrame(container, text="主升浪事件参数", padding=8)
        event_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(event_frame, text="未来 N 日 (forward_days)").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.forward_days_var = tk.IntVar(value=default_forward_days)
        ttk.Entry(event_frame, textvariable=self.forward_days_var, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(event_frame, text="涨幅阈值 (例 0.30)").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self.return_threshold_var = tk.DoubleVar(value=default_return_threshold)
        ttk.Entry(event_frame, textvariable=self.return_threshold_var, width=10).grid(row=1, column=1, sticky="w", pady=(4, 0))
        ttk.Label(event_frame, text="最大回撤限制 (例 0.08)").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self.max_drawdown_var = tk.DoubleVar(value=default_max_drawdown)
        ttk.Entry(event_frame, textvariable=self.max_drawdown_var, width=10).grid(row=2, column=1, sticky="w", pady=(4, 0))

        # ===== Top-K =====
        topk_frame = ttk.LabelFrame(container, text="Top-K 列表 (英文逗号分隔)", padding=8)
        topk_frame.pack(fill="x", pady=(0, 8))
        self.top_k_var = tk.StringVar(value=default_top_k)
        ttk.Entry(topk_frame, textvariable=self.top_k_var, width=40).pack(anchor="w")

        # ===== 因子勾选 =====
        factor_frame = ttk.LabelFrame(container, text="参与评估的因子", padding=8)
        factor_frame.pack(fill="both", expand=True, pady=(0, 8))

        action_row = ttk.Frame(factor_frame)
        action_row.pack(anchor="w", pady=(0, 4))
        ttk.Button(action_row, text="全选", command=self._select_all).pack(side="left")
        ttk.Button(action_row, text="全不选", command=self._clear_all).pack(side="left", padx=(8, 0))
        ttk.Button(action_row, text="反选", command=self._invert_all).pack(side="left", padx=(8, 0))

        canvas = tk.Canvas(factor_frame, height=180, highlightthickness=0)
        scrollbar = ttk.Scrollbar(factor_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.factor_vars: dict[str, tk.BooleanVar] = {}
        for row_index, (factor_name, spec) in enumerate(FACTOR_REGISTRY.items()):
            var = tk.BooleanVar(value=factor_name in default_selected_factors)
            self.factor_vars[factor_name] = var
            label = f"{factor_name}（{spec.get('label', factor_name)}）"
            ttk.Checkbutton(scroll_frame, text=label, variable=var).grid(
                row=row_index, column=0, sticky="w", pady=2
            )

        # ===== 缓存开关 =====
        cache_frame = ttk.LabelFrame(container, text="缓存与数据", padding=8)
        cache_frame.pack(fill="x", pady=(0, 8))
        self.use_event_cache_var = tk.BooleanVar(value=default_use_event_cache)
        ttk.Checkbutton(
            cache_frame, text="使用事件缓存（命中则跳过事件计算）", variable=self.use_event_cache_var
        ).pack(anchor="w")
        self.use_batch_data_cache_var = tk.BooleanVar(value=default_use_batch_data_cache)
        ttk.Checkbutton(
            cache_frame,
            text="使用批量数据缓存（沿用 src/多因子 的 batch_data_cache）",
            variable=self.use_batch_data_cache_var,
        ).pack(anchor="w")

        # ===== 多因子组合回测 =====
        combo_frame = ttk.LabelFrame(container, text="多因子组合回测", padding=8)
        combo_frame.pack(fill="x", pady=(0, 8))

        self.enable_combo_var = tk.BooleanVar(value=default_enable_combo)
        ttk.Checkbutton(
            combo_frame,
            text="启用相关性筛选 + 等权回测（在单因子评估后追加运行）",
            variable=self.enable_combo_var,
        ).grid(row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(combo_frame, text="相关性阈值（|corr|≥)").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0)
        )
        self.corr_threshold_var = tk.DoubleVar(value=default_corr_threshold)
        ttk.Entry(combo_frame, textvariable=self.corr_threshold_var, width=10).grid(
            row=1, column=1, sticky="w", pady=(6, 0)
        )
        ttk.Label(combo_frame, text="持仓数量 N").grid(
            row=1, column=2, sticky="w", padx=(16, 8), pady=(6, 0)
        )
        self.hold_num_var = tk.IntVar(value=default_hold_num)
        ttk.Entry(combo_frame, textvariable=self.hold_num_var, width=10).grid(
            row=1, column=3, sticky="w", pady=(6, 0)
        )

        ttk.Label(
            combo_frame,
            text="说明：去冗余按因子优先级（命中率优先，IC 兜底）保留高相关因子对中较强的一方；保留因子等权合成综合分数后做 vectorbt 回测。",
            foreground="#666666",
            wraplength=560,
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        self.root.protocol("WM_DELETE_WINDOW", self._cancel)

    def _center_window(self, width: int, height: int) -> None:
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max((screen_w - width) // 2, 0)
        y = max((screen_h - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _refresh_latest_dates(self) -> None:
        """重新从 get_date_range 拉取最新交易日，覆盖到结束日期输入框。

        会清空 src.多因子.data_loader 中的模块级日期缓存，确保拿到最新值。
        """
        try:
            from src.多因子 import data_loader as _dl
            _dl._STRATEGY_DATE_RANGE_CACHE = None  # 失效缓存以拉到最新
            latest_start, latest_end, _ = _dl.get_strategy_date_range()
        except Exception as exc:
            self.message_var.set(f"获取最新日期失败：{exc}")
            return
        self.end_var.set(str(latest_end))
        # 开始日期为空时也填充
        if not self.start_var.get().strip():
            self.start_var.set(str(latest_start))
        self.message_var.set(f"已更新结束日期到最新交易日：{latest_end}")

    def _select_all(self) -> None:
        for var in self.factor_vars.values():
            var.set(True)

    def _clear_all(self) -> None:
        for var in self.factor_vars.values():
            var.set(False)

    def _invert_all(self) -> None:
        for var in self.factor_vars.values():
            var.set(not var.get())

    def _cancel(self) -> None:
        self.result = None
        self.root.destroy()

    def _confirm(self) -> None:
        # 解析 Top-K
        try:
            top_k_list = [int(x.strip()) for x in self.top_k_var.get().split(",") if x.strip()]
            if not top_k_list:
                raise ValueError
        except Exception:
            self.message_var.set("Top-K 列表格式错误，请用英文逗号分隔正整数。")
            return

        selected_factors = [name for name, var in self.factor_vars.items() if var.get()]
        if not selected_factors:
            self.message_var.set("请至少勾选一个因子。")
            return

        try:
            forward_days = int(self.forward_days_var.get())
            return_threshold = float(self.return_threshold_var.get())
            max_drawdown = float(self.max_drawdown_var.get())
        except Exception:
            self.message_var.set("事件参数格式错误。")
            return

        if forward_days <= 0 or return_threshold <= 0 or max_drawdown <= 0:
            self.message_var.set("事件参数必须为正数。")
            return

        try:
            corr_threshold = float(self.corr_threshold_var.get())
            hold_num = int(self.hold_num_var.get())
        except Exception:
            self.message_var.set("组合回测参数格式错误。")
            return
        if corr_threshold <= 0 or corr_threshold > 1.0:
            self.message_var.set("相关性阈值需在 (0, 1] 之间。")
            return
        if hold_num <= 0:
            self.message_var.set("持仓数量必须为正整数。")
            return

        self.result = {
            "start_date": self.start_var.get().strip(),
            "end_date": self.end_var.get().strip(),
            "forward_days": forward_days,
            "return_threshold": return_threshold,
            "max_drawdown": max_drawdown,
            "top_k_list": top_k_list,
            "selected_factors": selected_factors,
            "use_event_cache": bool(self.use_event_cache_var.get()),
            "use_batch_data_cache": bool(self.use_batch_data_cache_var.get()),
            "enable_combo_backtest": bool(self.enable_combo_var.get()),
            "corr_threshold": corr_threshold,
            "hold_num": hold_num,
        }
        self.root.destroy()

    def show(self) -> dict[str, Any] | None:
        self.root.mainloop()
        return self.result
