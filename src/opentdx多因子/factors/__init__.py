"""
OpenTDX 多因子库（v2）。

每个子模块导出 get_factors(panel: dict[str, DataFrame], ctx: dict) -> dict[str, DataFrame]。
panel 字段：open / high / low / close / vol / amount / turnover / float_shares
ctx 字段：index_close: pd.Series（上证综指收盘价，用于相对强度类）
返回的因子 DataFrame 与 panel['close'] 同形。
"""
from __future__ import annotations

# 9 个分组依次列出，主流程会通过 importlib 自动发现
GROUPS = [
    "momentum",
    "reversal",
    "volatility",
    "turnover",
    "corr",
    "position",
    "indicator",
    "relative_pattern",
    "share_change",
]
