from pathlib import Path
from typing import Any

from qlib_config import DEFAULT_QLIB_PROVIDER_URI, DEFAULT_REGION, get_data_status as _get_config_status

_INITIALIZED = False
_INIT_PROVIDER_URI: str | None = None


def _require_qlib():
    try:
        import qlib
        from qlib.data import D
    except Exception as exc:
        raise RuntimeError(f"未能导入 pyqlib，请先安装：pip install pyqlib。原始错误: {exc}") from exc
    return qlib, D


def init_qlib(provider_uri: str | Path | None = None, region: str = DEFAULT_REGION, force: bool = False) -> None:
    global _INITIALIZED, _INIT_PROVIDER_URI
    provider = Path(provider_uri or DEFAULT_QLIB_PROVIDER_URI).resolve()
    if not provider.exists():
        raise FileNotFoundError(f"Qlib 数据目录不存在: {provider}")
    if _INITIALIZED and not force and _INIT_PROVIDER_URI == str(provider):
        return
    qlib, _ = _require_qlib()
    qlib.init(provider_uri=str(provider), region=region)
    _INITIALIZED = True
    _INIT_PROVIDER_URI = str(provider)


def get_data_status() -> dict:
    status = _get_config_status()
    status["reader_initialized"] = _INITIALIZED
    status["reader_provider_uri"] = _INIT_PROVIDER_URI
    return status


def get_calendar(freq: str = "day", provider_uri: str | Path | None = None) -> list[str]:
    init_qlib(provider_uri=provider_uri)
    _, D = _require_qlib()
    calendar = D.calendar(freq=freq)
    return [str(item) for item in calendar]


def get_instruments(market: str = "all", provider_uri: str | Path | None = None) -> list[str]:
    init_qlib(provider_uri=provider_uri)
    _, D = _require_qlib()
    instruments = D.instruments(market)
    if isinstance(instruments, dict):
        return sorted(instruments.keys())
    return list(instruments)


def get_features(
    instruments: list[str] | str,
    fields: list[str],
    start_time: str | None = None,
    end_time: str | None = None,
    freq: str = "day",
    provider_uri: str | Path | None = None,
):
    init_qlib(provider_uri=provider_uri)
    _, D = _require_qlib()
    return D.features(
        instruments=instruments,
        fields=fields,
        start_time=start_time,
        end_time=end_time,
        freq=freq,
    )


def dataframe_to_records(df: Any) -> list[dict]:
    if df is None:
        return []
    result = df.reset_index()
    for column in result.columns:
        if str(result[column].dtype).startswith("datetime"):
            result[column] = result[column].astype(str)
    return result.where(result.notna(), None).to_dict(orient="records")
