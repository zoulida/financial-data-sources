import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
QLIB_TOOL_DIR = CURRENT_DIR.parent
sys.path.insert(0, str(QLIB_TOOL_DIR))

from qlib_reader import get_calendar, get_data_status, get_features, get_instruments, init_qlib


def main() -> None:
    print("当前 Qlib 数据状态:")
    print(get_data_status())

    init_qlib()

    print("最近交易日历样例:")
    print(get_calendar(freq="day")[:5])

    print("股票列表样例:")
    print(get_instruments(market="all")[:10])

    df = get_features(
        instruments=["SH600519"],
        fields=["$close", "$volume"],
        start_time="2024-01-01",
        end_time="2024-01-31",
        freq="day",
    )
    print(df)


if __name__ == "__main__":
    main()
