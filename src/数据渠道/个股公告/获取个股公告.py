# -*- coding: utf-8 -*-
"""
获取个股公告数据

依赖:
- efinance

函数:
- 获取个股公告(证券代码: str, 数量: int = 30, 仅返回核心列: bool = False) -> pandas.DataFrame
"""
import pandas as pd
import efinance as ef
import argparse

DEFAULT_CONFIG = {
    "code": "000001",
    "count": 30,
    "core_only": True,
    "start": None,
    "end": None,
    "keyword": None,
    "export": None,
    "dedup": False,
}


def _标准化证券代码(symbol: str) -> str:
    """将输入证券代码标准化为6位数字字符串（如 '000001'）。"""
    if not isinstance(symbol, str):
        symbol = str(symbol)
    s = symbol.strip().upper()
    # 处理如 '000001.SZ' / '600000.SH' 等格式
    if "." in s:
        s = s.split(".")[0]
    # 仅保留数字并左侧补零
    s = "".join(ch for ch in s if ch.isdigit()).zfill(6)
    return s


def 获取个股公告(证券代码: str, 数量: int = 30, 仅返回核心列: bool = False, 开始日期: str = None, 结束日期: str = None, 关键词: str = None, 导出路径: str = None, 去重: bool = False) -> pd.DataFrame:
    """
    获取指定证券最近 N 条公告。

    参数:
    - 证券代码: 支持 '000001' 或 '000001.SZ' / '600000.SH' 等格式。
    - 数量: 公告条数，默认 30。
    - 仅返回核心列: 是否仅返回 ['标题','公告日期','PDF 链接'] 三列。

    返回:
    - pandas.DataFrame，efinance 原始结构或核心列视参数而定。
    """
    code = _标准化证券代码(证券代码)

    try:
        df = ef.stock.get_announcement(code, count=数量)
        pass
    except Exception:
        # 发生异常时返回空表，避免上层崩溃
        return pd.DataFrame(columns=["标题", "公告日期", "PDF 链接"]) if 仅返回核心列 else pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame(columns=["标题", "公告日期", "PDF 链接"]) if 仅返回核心列 else pd.DataFrame()

    if 开始日期 is not None or 结束日期 is not None:
        if "公告日期" in df.columns:
            _dt = pd.to_datetime(df["公告日期"], errors="coerce")
            if 开始日期 is not None:
                df = df[_dt >= pd.to_datetime(开始日期, errors="coerce")]
            if 结束日期 is not None:
                df = df[_dt <= pd.to_datetime(结束日期, errors="coerce")]

    if 关键词 is not None and "标题" in df.columns and len(关键词) > 0:
        df = df[df["标题"].astype(str).str.contains(关键词, na=False)]

    if 去重:
        _sub = None
        if any(c in df.columns for c in ["PDF 链接", "PDF链接"]):
            _sub = [c for c in ["PDF 链接", "PDF链接"] if c in df.columns]
        elif "标题" in df.columns:
            _sub = ["标题"]
        if _sub:
            df = df.drop_duplicates(subset=_sub, keep="first")

    if 导出路径:
        try:
            df.to_csv(导出路径, index=False, encoding="utf-8-sig")
        except Exception:
            pass

    if 仅返回核心列:
        _pdf_candidates = ["PDF 链接", "PDF链接", "pdf 链接", "pdf链接"]
        _pdf_col = next((c for c in _pdf_candidates if c in df.columns), None)
        core_cols = [c for c in ["标题", "公告日期"] if c in df.columns]
        if _pdf_col:
            core_cols.append(_pdf_col)
        if core_cols:
            return df[core_cols].copy()
        return df

    return df


def main():
    parser = argparse.ArgumentParser(prog="获取个股公告")
    parser.add_argument("--code", default=DEFAULT_CONFIG["code"])
    parser.add_argument("--count", type=int, default=DEFAULT_CONFIG["count"])
    parser.add_argument("--core-only", dest="core_only", action="store_true")
    parser.add_argument("--no-core-only", dest="core_only", action="store_false")
    parser.add_argument("--start", dest="start", default=DEFAULT_CONFIG["start"])
    parser.add_argument("--end", dest="end", default=DEFAULT_CONFIG["end"])
    parser.add_argument("--keyword", dest="keyword", default=DEFAULT_CONFIG["keyword"])
    parser.add_argument("--export", dest="export", default=DEFAULT_CONFIG["export"])
    parser.add_argument("--dedup", dest="dedup", action="store_true")
    parser.add_argument("--no-dedup", dest="dedup", action="store_false")
    parser.set_defaults(core_only=DEFAULT_CONFIG["core_only"], dedup=DEFAULT_CONFIG["dedup"])
    args = parser.parse_args()
    df = 获取个股公告(
        args.code,
        数量=args.count,
        仅返回核心列=args.core_only,
        开始日期=args.start,
        结束日期=args.end,
        关键词=args.keyword,
        导出路径=args.export,
        去重=args.dedup,
    )
    if df is not None:
        try:
            pd.set_option("display.max_rows", None)
            pd.set_option("display.width", 200)
        except Exception:
            pass
        print(df)


if __name__ == "__main__":
    main()
