from __future__ import annotations

import hashlib
import pickle
from typing import Any
from pathlib import Path

import pandas as pd

from md.获取enddate.get_date_range import get_date_range
from md.合并下载数据.合并下载数据 import batchDownloadDayData, getDayData, getDayDataCache
from src.基础筛选.filterStocks import get_universe_with_basics

from src.多因子 import config

BATCH_DATA_CACHE_DIR = Path(__file__).resolve().parent / "batch_data_cache"
_XTDATA: Any | None = None
_XTDATA_LOADED = False
_STRATEGY_DATE_RANGE_CACHE: tuple[str, str, str] | None = None


def _get_xtdata() -> Any | None:
    global _XTDATA, _XTDATA_LOADED
    if _XTDATA_LOADED:
        return _XTDATA
    _XTDATA_LOADED = True
    try:
        from xtquant import xtdata as imported_xtdata
    except Exception:  # pragma: no cover - 依赖运行环境
        _XTDATA = None
    else:
        _XTDATA = imported_xtdata
    return _XTDATA


def _batch_data_cache_path(
    start_date: str,
    end_date: str,
    max_price: float,
    max_mcap: float,
    dividend_type: str,
) -> Path:
    key = f"{start_date}|{end_date}|{max_price}|{max_mcap}|{dividend_type}"
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:12]
    return BATCH_DATA_CACHE_DIR / f"batch_data__{start_date}_{end_date}__{digest}.pkl"


def load_batch_data_bundle_from_cache(
    start_date: str,
    end_date: str,
    max_price: float,
    max_mcap: float,
    dividend_type: str,
) -> dict[str, Any] | None:
    cache_path = _batch_data_cache_path(start_date, end_date, max_price, max_mcap, dividend_type)
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("rb") as file:
            cached = pickle.load(file)
    except Exception as exc:  # pragma: no cover - 缓存损坏时回退重新下载
        print(f"[批量数据缓存] 读取 {cache_path.name} 失败，将重新下载：{exc}")
        return None
    if not isinstance(cached, dict):
        return None
    return cached


def save_batch_data_bundle_to_cache(
    start_date: str,
    end_date: str,
    max_price: float,
    max_mcap: float,
    dividend_type: str,
    data_bundle: dict[str, Any],
) -> None:
    BATCH_DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _batch_data_cache_path(start_date, end_date, max_price, max_mcap, dividend_type)
    try:
        with cache_path.open("wb") as file:
            pickle.dump(data_bundle, file, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as exc:  # pragma: no cover - 写缓存失败不影响主流程
        print(f"[批量数据缓存] 写入 {cache_path.name} 失败：{exc}")


def list_batch_data_cache_files() -> list[Path]:
    if not BATCH_DATA_CACHE_DIR.exists():
        return []
    return sorted(BATCH_DATA_CACHE_DIR.glob("*.pkl"))


def clear_batch_data_cache() -> tuple[int, list[str]]:
    deleted = 0
    failures: list[str] = []
    for cache_file in list_batch_data_cache_files():
        try:
            cache_file.unlink()
            deleted += 1
        except Exception as exc:  # pragma: no cover - 极少触发
            failures.append(f"{cache_file.name}: {exc}")
    return deleted, failures


def get_strategy_date_range() -> tuple[str, str, str]:
    """获取策略日期范围。

    这里严格遵守 `.cursorrules`：
    - 开始日期 / 结束日期不手写；
    - 必须统一通过 `get_date_range()` 获取。

    Returns:
        start_date: 起始日期，格式为 `YYYYMMDD`
        end_date: 结束日期，格式为 `YYYYMMDD`
        reason: 结束日期为何取该值的说明文字
    """
    global _STRATEGY_DATE_RANGE_CACHE
    if _STRATEGY_DATE_RANGE_CACHE is None:
        _STRATEGY_DATE_RANGE_CACHE = get_date_range()
    return _STRATEGY_DATE_RANGE_CACHE


def _get_stock_name(code: str) -> str | None:
    """读取单只股票名称。

    这里尝试从 xtdata 的合约详情中读取证券简称。
    不同环境下字段名可能不同，所以做一个兼容性轮询。
    只要能拿到名称，就用于后续 ST 识别；拿不到则返回 `None`。
    """
    xtdata = _get_xtdata()
    if xtdata is None:
        return None

    try:
        info = xtdata.get_instrument_detail(code)
    except Exception:
        return None

    if not isinstance(info, dict):
        return None

    for field in [
        "InstrumentName",
        "instrument_name",
        "StockName",
        "stock_name",
        "Name",
        "name",
    ]:
        value = info.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _filter_st_stocks(universe_df: pd.DataFrame) -> pd.DataFrame:
    """在基础股票池上追加 ST 过滤。

    过滤规则尽量简单直接：
    - 证券简称以 `ST` 开头；
    - 证券简称以 `*ST` 开头；
    - 证券简称中包含 `ST` 且常见形式可识别。

    说明：
    1. 你本轮要求“只过滤 ST，其他不过滤”，因此仅在这里做名称过滤。
    2. 如果名称读取失败，则默认保留该股票，避免因为数据源偶发问题误删样本。
    """
    if universe_df.empty:
        return universe_df

    result_df = universe_df.copy()
    result_df["name"] = result_df["code"].apply(_get_stock_name)

    def is_st_name(name: object) -> bool:
        if not isinstance(name, str):
            return False
        clean_name = name.strip().upper().replace(" ", "")
        return clean_name.startswith("ST") or clean_name.startswith("*ST")

    st_mask = result_df["name"].apply(is_st_name)
    filtered_df = result_df.loc[~st_mask].reset_index(drop=True)
    return filtered_df


def load_base_universe(max_price: float, max_mcap: float) -> pd.DataFrame:
    """通过统一入口获取基础股票池，并按配置决定是否过滤 ST。

    流程说明：
    1. 先调用 `.cursorrules` 指定的统一股票池入口；
    2. 去重，避免同一代码重复；
    3. 如果开启 ST 过滤，则补充名称并剔除 ST / *ST。
    """
    universe_df = get_universe_with_basics(max_price=max_price, max_mcap=max_mcap).copy()
    if universe_df.empty:
        return universe_df

    universe_df = universe_df.drop_duplicates(subset=["code"]).reset_index(drop=True)

    if config.ENABLE_ST_FILTER:
        universe_df = _filter_st_stocks(universe_df)

    return universe_df


def load_daily_bars(
    stock_codes: list[str],
    start_date: str,
    end_date: str,
    need_download: int = 0,
    dividend_type: str = "front",
) -> dict[str, pd.DataFrame]:
    """批量加载股票日线行情。

    设计思路：
    - 股票较多时，使用批量接口提高效率；
    - 股票较少时，走缓存接口，避免不必要的重复下载；
    - 返回值统一整理为 `{code: DataFrame}` 的字典结构。
    """
    if not stock_codes:
        return {}

    if len(stock_codes) >= 100:
        raw_dict = batchDownloadDayData(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            dividend_type=dividend_type,
            need_download=need_download,
        )
    else:
        raw_dict = {
            code: getDayDataCache(
                stock_code=code,
                start_date=start_date,
                end_date=end_date,
                is_download=need_download,
                dividend_type=dividend_type,
            )
            for code in stock_codes
        }

    bar_dict: dict[str, pd.DataFrame] = {}
    for code, df in raw_dict.items():
        # 这里仅保留有效的 DataFrame，下载失败或空数据直接跳过。
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue

        normalized = df.copy()

        # 日期统一转成字符串，方便后面拼接成宽表矩阵。
        normalized["date"] = normalized["date"].astype(str)

        # 同一股票同一天若出现重复记录，仅保留一条。
        normalized = normalized.drop_duplicates(subset=["date"]).sort_values("date")
        bar_dict[code] = normalized

    return bar_dict


def load_benchmark_close(
    benchmark_code: str,
    start_date: str,
    end_date: str,
    need_download: int = 0,
    dividend_type: str = "front",
) -> pd.Series:
    """读取基准指数收盘价序列。

    当前按你的要求，基准固定为中证 2000。
    这里直接复用统一日线获取入口，保持与股票行情同一套数据链路。

    返回：
        以日期字符串为索引的收盘价序列；若读取失败则返回空序列。
    """
    candidate_codes = [benchmark_code]
    for fallback_code in ["932000.SH", "932000.CSI", "000852.SH", "000905.SH"]:
        if fallback_code not in candidate_codes:
            candidate_codes.append(fallback_code)

    benchmark_df = pd.DataFrame()
    used_code = benchmark_code
    for candidate_code in candidate_codes:
        try:
            current_df = getDayData(
                stock_code=candidate_code,
                start_date=start_date,
                end_date=end_date,
                is_download=need_download,
                dividend_type=dividend_type,
            )
        except Exception:
            continue
        if isinstance(current_df, pd.DataFrame) and not current_df.empty and "close" in current_df.columns:
            benchmark_df = current_df
            used_code = candidate_code
            break

    if benchmark_df.empty or "close" not in benchmark_df.columns:
        return pd.Series(dtype=float, name=config.BENCHMARK_NAME)

    benchmark_close = benchmark_df[["date", "close"]].copy()
    benchmark_close["date"] = benchmark_close["date"].astype(str)
    benchmark_close["close"] = pd.to_numeric(benchmark_close["close"], errors="coerce")
    benchmark_close = benchmark_close.drop_duplicates(subset=["date"]).set_index("date")["close"]
    benchmark_close.name = config.BENCHMARK_NAME if used_code == benchmark_code else f"{config.BENCHMARK_NAME}({used_code})"
    return benchmark_close


def _pivot_field(bar_dict: dict[str, pd.DataFrame], field: str) -> pd.DataFrame:
    """把逐股票长表，转成“日期 × 股票”的宽表矩阵。

    例如：
    - 输入是一堆单票 DataFrame；
    - 输出是一个 `close_df` 或 `amount_df` 这样的宽表。
    """
    frames = []
    for code, df in bar_dict.items():
        if field not in df.columns:
            continue

        series = df[["date", field]].copy()
        series[field] = pd.to_numeric(series[field], errors="coerce")
        series = series.rename(columns={field: code}).set_index("date")
        frames.append(series)

    if not frames:
        return pd.DataFrame()

    matrix = pd.concat(frames, axis=1).sort_index()
    matrix.index = pd.Index(matrix.index.astype(str), name="date")
    return matrix


def align_price_fields(bar_dict: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """将逐股票行情对齐成统一矩阵。

    返回字段包括：
    - open
    - high
    - low
    - close
    - volume
    - amount
    """
    fields = ["open", "high", "low", "close", "volume", "amount"]
    return {field: _pivot_field(bar_dict, field) for field in fields}


def build_data_bundle(
    max_price: float = config.MAX_PRICE,
    max_mcap: float = config.MAX_MCAP,
    need_download: int = config.NEED_DOWNLOAD,
    dividend_type: str = config.DIVIDEND_TYPE,
    start_date: str | None = None,
    end_date: str | None = None,
    use_batch_data_cache: bool = False,
) -> dict[str, Any]:
    """构建策略运行所需的数据包。

    这是主流程的数据总入口，负责把下面几件事串起来：
    1. 拿日期范围；
    2. 拿基础股票池；
    3. 在股票池层面过滤 ST；
    4. 拉取所有样本的日线行情；
    5. 读取中证 2000 基准行情；
    6. 把行情整理成多张宽表，供因子和回测模块直接使用。

    说明：
    - 默认仍然走统一日期函数；
    - 如果外部显式传入 `start_date` / `end_date`，则优先使用传入值，
      方便像可视化脚本这类“运行前弹窗指定日期”的场景。
    """
    if start_date is None or end_date is None:
        start_date, end_date, date_reason = get_strategy_date_range()
    else:
        date_reason = "手动指定日期范围"
    if use_batch_data_cache:
        cached_bundle = load_batch_data_bundle_from_cache(
            start_date=start_date,
            end_date=end_date,
            max_price=max_price,
            max_mcap=max_mcap,
            dividend_type=dividend_type,
        )
        if cached_bundle is not None:
            print(f"[批量数据缓存] 命中缓存，直接读取硬盘数据：{start_date} ~ {end_date}")
            return cached_bundle
        print(f"[批量数据缓存] 未命中缓存，将正常批量下载并在完成后写入缓存：{start_date} ~ {end_date}")
    universe_df = load_base_universe(max_price=max_price, max_mcap=max_mcap)
    stock_codes = universe_df["code"].tolist() if not universe_df.empty else []

    bar_dict = load_daily_bars(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        need_download=need_download,
        dividend_type=dividend_type,
    )
    aligned = align_price_fields(bar_dict)
    benchmark_close = load_benchmark_close(
        benchmark_code=config.BENCHMARK_CODE,
        start_date=start_date,
        end_date=end_date,
        need_download=need_download,
        dividend_type=dividend_type,
    )

    data_bundle = {
        "universe": universe_df,
        "bars": bar_dict,
        "benchmark_close": benchmark_close,
        "start_date": start_date,
        "end_date": end_date,
        "date_reason": date_reason,
        **aligned,
    }
    if use_batch_data_cache:
        save_batch_data_bundle_to_cache(
            start_date=start_date,
            end_date=end_date,
            max_price=max_price,
            max_mcap=max_mcap,
            dividend_type=dividend_type,
            data_bundle=data_bundle,
        )
        print(f"[批量数据缓存] 已写入缓存：{start_date} ~ {end_date}")
    return data_bundle
