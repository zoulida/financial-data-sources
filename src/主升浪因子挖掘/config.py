"""主升浪因子挖掘配置文件。

设计原则：
- 基础股票池/价格/市值参数沿用 src/多因子/config，避免重复维护；
- 主升浪事件、Top-K、缓存等参数本地维护，互不影响。
"""
from __future__ import annotations

from pathlib import Path

from src.多因子 import config as base_config

# ==================== 主升浪事件参数 ====================
# 未来 N 个交易日内，价格相对 t-1 日累计涨幅 >= 阈值，且期间最大回撤不超过限制，视为一次主升浪事件。
BLASTOFF_FORWARD_DAYS = 20
BLASTOFF_RETURN_THRESHOLD = 0.30
BLASTOFF_MAX_DRAWDOWN = 0.08

# ==================== 评估参数 ====================
# 命中率/召回率/平均最大涨幅等指标的多档 Top-K。
TOP_K_LIST: list[int] = [10, 20, 50, 100]

# ==================== 调仓频率 ====================
# 评估时按调仓周期对齐因子；这里默认与 src/多因子 保持一致。
REBALANCE_FREQ = base_config.REBALANCE_FREQ

# ==================== 股票池参数（从 src/多因子 复用，可在此覆盖） ====================
MAX_PRICE = base_config.MAX_PRICE
MAX_MCAP = base_config.MAX_MCAP
DIVIDEND_TYPE = base_config.DIVIDEND_TYPE
NEED_DOWNLOAD = base_config.NEED_DOWNLOAD
ENABLE_ST_FILTER = base_config.ENABLE_ST_FILTER

# ==================== 输出与缓存 ====================
_BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = _BASE_DIR / "outputs"
FACTOR_CACHE_DIR = _BASE_DIR / "factor_cache"
EVENT_CACHE_DIR = _BASE_DIR / "event_cache"

# 上次运行配置持久化文件。
LAST_RUN_PATH = _BASE_DIR / ".last_run.json"
