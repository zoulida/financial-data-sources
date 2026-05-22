"""使用 mootdx Affair API 获取并打印 600519 财务数据。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from mootdx.affair import Affair

TARGET_CODE = "600519"


def pick_finance_zip_candidates(limit: int = 12) -> list[str]:
    """按日期倒序返回不晚于今天的财务包候选列表。"""
    from datetime import datetime

    files = Affair.files()
    if not files:
        raise RuntimeError("Affair.files() 未返回任何财务文件。")

    today = datetime.today().strftime("%Y%m%d")

    valid_names: list[str] = []
    for item in files:
        name = item.get("filename", "")
        if not (name.startswith("gpcw") and name.endswith(".zip")):
            continue
        date_str = name[4:12]
        if len(date_str) == 8 and date_str.isdigit() and date_str <= today:
            valid_names.append(name)

    if not valid_names:
        raise RuntimeError("未找到不晚于今天的财务包文件。")

    return sorted(valid_names, reverse=True)[:limit]


def filter_by_stock_code(df: pd.DataFrame, code: str) -> pd.DataFrame:
    """在财务 DataFrame 中按索引精确筛选股票代码。"""
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    if df.empty:
        return df

    # mootdx Affair.parse 的 index 通常就是证券代码
    normalized_index = df.index.astype(str).str.replace(".0", "", regex=False).str.zfill(6)
    mask = normalized_index == code
    if mask.any():
        return df.loc[mask]

    return df.iloc[0:0].copy()


def main() -> None:
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_candidates = pick_finance_zip_candidates(limit=12)

    # 从最近一期开始回退，直到找到 600519
    for filename in zip_candidates:
        print(f"尝试财务包: {filename}")
        Affair.fetch(downdir=str(output_dir), filename=filename)
        all_finance_df = Affair.parse(downdir=str(output_dir), filename=filename)

        if not isinstance(all_finance_df, pd.DataFrame) or all_finance_df.empty:
            print(f"  -> {filename} 为空或仅占位文件，跳过")
            continue

        target_df = filter_by_stock_code(all_finance_df, TARGET_CODE)
        if not target_df.empty:
            pd.set_option("display.max_columns", None)
            pd.set_option("display.width", 240)

            print("=" * 100)
            print(f"{TARGET_CODE} 财务数据（{filename}）")
            print("=" * 100)
            print(target_df)
            return

        print(f"  -> {filename} 中没有 {TARGET_CODE}，继续回退")

    print(f"在最近 {len(zip_candidates)} 期财务包中都未找到 {TARGET_CODE} 的财务数据。")


if __name__ == "__main__":
    main()

