# -*- coding: utf-8 -*-
"""Qlib 全市场日线行情读取。

- 自动定位 ``md/qlib数据/qlib_data/cn_data`` 作为 provider_uri。
- 读取 ``$open/$high/$low/$close/$volume/$amount`` 字段。
- 输出宽表字典 ``{字段: DataFrame(index=datetime, columns=qlib_code)}``。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

_DEFAULT_FIELDS = ("$open", "$high", "$low", "$close", "$volume", "$amount")
_FIELD_ALIASES = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$amount": "amount",
    "$vwap": "vwap",
}

_INITIALIZED_PROVIDER: Optional[str] = None


def default_provider_uri() -> str:
    """自动找到本项目的 Qlib 数据目录。"""
    here = Path(__file__).resolve()
    for base in (here.parent, *here.parents):
        candidate = base / "md" / "qlib数据" / "qlib_data" / "cn_data"
        if candidate.exists():
            return str(candidate)
    # 回退：项目根
    return str(here.parents[2] / "md" / "qlib数据" / "qlib_data" / "cn_data")


def init_qlib(provider_uri: Optional[str] = None) -> str:
    """初始化 Qlib 环境，返回最终使用的 provider_uri。"""
    global _INITIALIZED_PROVIDER
    try:
        import qlib
        from qlib.constant import REG_CN
        from qlib.utils import exists_qlib_data
    except Exception as exc:  # pragma: no cover
        raise ImportError("未能导入 pyqlib，请先 pip install pyqlib") from exc

    provider = provider_uri or default_provider_uri()
    if not exists_qlib_data(provider):
        raise FileNotFoundError(f"Qlib 数据不存在: {provider}")

    if _INITIALIZED_PROVIDER == provider:
        return provider

    qlib.init(
        provider_uri=provider,
        region=REG_CN,
        joblib_backend="threading",
        kernels=1,
    )
    _INITIALIZED_PROVIDER = provider
    LOGGER.info("Qlib 初始化完成: %s", provider)
    return provider


def list_instruments(market: str = "all", provider_uri: Optional[str] = None) -> List[str]:
    """列出市场的全部股票代码（Qlib 大写格式）。"""
    init_qlib(provider_uri)
    from qlib.data import D

    instruments = D.instruments(market=market)
    codes = D.list_instruments(
        instruments=instruments,
        as_list=True,
    )
    return [str(c).upper() for c in codes]


def load_market_panel(
    instruments: Iterable[str],
    start_time: str,
    end_time: str,
    provider_uri: Optional[str] = None,
    fields: Iterable[str] = _DEFAULT_FIELDS,
) -> Dict[str, pd.DataFrame]:
    """读取行情并整理成宽表字典。"""
    init_qlib(provider_uri)
    from qlib.data import D

    instrument_list = sorted({str(c).upper() for c in instruments})
    if not instrument_list:
        raise ValueError("instruments 为空")

    field_list = list(fields)
    has_amount = "$amount" in field_list
    if has_amount:
        try:
            data = D.features(
                instruments=instrument_list,
                fields=field_list,
                start_time=start_time,
                end_time=end_time,
                freq="day",
            )
        except Exception as exc:
            LOGGER.warning("读取 $amount 失败（%s），改为不含 amount", exc)
            field_list = [f for f in field_list if f != "$amount"]
            has_amount = False
            data = D.features(
                instruments=instrument_list,
                fields=field_list,
                start_time=start_time,
                end_time=end_time,
                freq="day",
            )
    else:
        data = D.features(
            instruments=instrument_list,
            fields=field_list,
            start_time=start_time,
            end_time=end_time,
            freq="day",
        )

    if data is None or data.empty:
        raise ValueError(f"未读取到行情数据：{start_time} ~ {end_time}")

    rename_map = {f: _FIELD_ALIASES.get(f, f.lstrip("$")) for f in field_list}
    data.columns = [rename_map[f] for f in field_list]
    data = data.replace([np.inf, -np.inf], np.nan).sort_index()

    index_names = list(data.index.names)
    if "instrument" in index_names:
        inst_level = "instrument"
    elif "code" in index_names:
        inst_level = "code"
    else:
        inst_level = 0

    panel: Dict[str, pd.DataFrame] = {}
    for col in data.columns:
        wide = data[col].unstack(inst_level)
        wide.index = pd.to_datetime(wide.index)
        wide = wide.sort_index()
        wide.columns = [str(c).upper() for c in wide.columns]
        panel[col] = wide.astype(float)

    if not has_amount and "amount" not in panel:
        panel["amount"] = panel["close"] * panel["volume"]
    if "vwap" not in panel:
        panel["vwap"] = panel["close"]

    n_days, n_codes = panel["close"].shape
    LOGGER.info("读取行情完成：%d 天 × %d 只标的（amount=%s）",
                n_days, n_codes, "真实" if has_amount else "近似")
    return panel
